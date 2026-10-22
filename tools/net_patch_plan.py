#!/usr/bin/env python3
"""Static patch plan for widening the svc_PacketEntities header fields.

Why this tool exists
--------------------
``bf_write::WriteUBitLong`` (``FUN_10061340`` in engine.dll) resolves its write
mask through a flat table indexed by

    (curbit & 31) * 33 + numBits

so ``numBits`` must be 0..32.  The intuitive "widen the 32-bit header reserve"
patch -- replacing ``push 0x20`` at ``0x1011A144`` with ``push 0x22`` -- indexes
column 34, i.e. the *next row's* 1-bit mask, and for ``curbit & 31 == 31`` it
walks off the end of the table.  It does not fault and does not set
``m_bOverflow``: it silently writes the wrong mask.

The reserve does not have to *write* 34 bits, only to *advance* 34 bits: the
three backfilled fields (13 + 20 + 1 = 34) overwrite the whole region right
after the entity body.  So the planner refuses any width > 32 and offers two
legal implementations of the "+2 bits" cursor advance.

Usage:
    python net_patch_plan.py                 # plan + position model
    python net_patch_plan.py --check         # strict CSV structure gate, then
                                             # verify expected bytes in engine.dll
    python net_patch_plan.py --json          # machine-readable
    python net_patch_plan.py --old-max 11 --old-updated 11 \
                             --new-max 13 --new-updated 13

Read-only: ``--check`` only reads the data CSVs and engine.dll, never writes.
The CSV gate is standard-library-only and runs before any PE import, so a
malformed table fails first with its file name and line number.
"""
import argparse
import hashlib
import json
import sys
from collections import namedtuple

from config import require, ENGINE_DLL

# ``pefile`` is only needed for ``--check``.  Importing it at module level would
# abort before the standard-library CSV structure gate gets a chance to run, so
# it is imported inside ``check_binary`` and reported as a distinct failure.

# The recorded build (reports/network-n1.md); only a warning if it differs,
# the real gate is the expected-byte comparison below.
BUILD_SHA256 = "8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86"

# --- the hard constraint (network-n2.md 13.1) ------------------------------
MAX_NUM_BITS = 32
MASK_ROW_WIDTH = 33          # (curbit & 31) * 33 + numBits
MASK_ROWS = 32               # curbit & 31

# --- header layout (network-n2.md 11.1 / 13.2) -----------------------------
TYPE_BITS = 6
IS_DELTA_BITS = 1
DELTA_FROM_BITS = 32
FRAME_FLAG_BITS = 1
LENGTH_BITS = 20
BACKFILL_FLAG_BITS = 1

Site = namedtuple("Site", "va expect patch purpose")

# 13/13 plan.  Reserved width is derived from the fields, not hardcoded.
SITES = (
    Site(0x1011A09B, "6a0b", "6a0d", "writer m_nMaxEntries 11 -> 13"),
    Site(0x1011A259, "6a0b", "6a0d", "writer m_nUpdatedEntries 11 -> 13"),
    Site(0x1011A156, "898598feffff", "83470c029090",
         "reserve: add [edi+0xC],2 (dead store [ebp-0x168] reused)"),
    Site(0x101D7474, "83f90b", "83f90d", "reader #1: cmp avail,13"),
    Site(0x101D747E, "23357cce3e10", "233584ce3e10",
         "reader #1: mask -> existing 0x1FFF at 0x103ECE84"),
    Site(0x101D7484, "83c1f5", "83c1f3", "reader #1: add avail,-13"),
    Site(0x101D748E, "c1ea0b", "c1ea0d", "reader #1: shr dword,13"),
    Site(0x101D74E5, "ba0b000000", "ba0d000000", "reader #1 slow path: numBits = 13"),
    Site(0x101D778E, "83f90b", "83f90d", "reader #2: cmp avail,13"),
    Site(0x101D7798, "23357cce3e10", "233584ce3e10", "reader #2: mask -> 0x1FFF"),
    Site(0x101D779E, "83c1f5", "83c1f3", "reader #2: add avail,-13"),
    Site(0x101D77A8, "c1ea0b", "c1ea0d", "reader #2: shr dword,13"),
    Site(0x101D77FF, "ba0b000000", "ba0d000000", "reader #2 slow path: numBits = 13"),
)

# Not part of the default plan: the object-version writer is a cold/possibly
# dead path (network-n2.md 11.2).  Kept here so the numbers are visible.
COLD_SITES = (
    Site(0x101D7366, "6a0b", "6a0d", "object writer m_nMaxEntries (COLD, unconfirmed)"),
    Site(0x101D73D5, "6a0b", "6a0d", "object writer m_nUpdatedEntries (COLD, unconfirmed)"),
)

MASK_0X1FFF = 0x103ECE84
MASK_0X1FFF_BYTES = "ff1f0000"


def assert_width(num_bits, where):
    """numBits must address an existing mask-table column."""
    if not 0 <= num_bits <= MAX_NUM_BITS:
        raise SystemExit(
            "invalid WriteUBitLong width %d at %s: numBits must be 0..%d "
            "(mask index (curbit&31)*%d + numBits, %d columns). "
            "The 'push 0x22' reserve widening is exactly this bug."
            % (num_bits, where, MAX_NUM_BITS, MASK_ROW_WIDTH, MASK_ROW_WIDTH)
        )


def guard_selftest():
    """Fail loudly if the width guard is ever loosened.

    This is the tripwire for the ``push 0x22`` idea: widening the reserve by
    hand must never turn into a 34-bit ``WriteUBitLong`` call.
    """
    try:
        assert_width(MAX_NUM_BITS + 2, "selftest")
    except SystemExit:
        return True
    raise SystemExit("width guard broken: numBits=%d was accepted" % (MAX_NUM_BITS + 2))


def reserve_bits(max_bits, updated_bits):
    """Reserved header width implied by the two fields plus the backfill flag.

    The *total* may legitimately exceed 32: it is covered by three separate
    writes.  Only the individual writes are constrained.
    """
    for n, name in ((max_bits, "max"), (updated_bits, "updated")):
        assert_width(n, "reserve(%s)" % name)
    assert_width(LENGTH_BITS, "reserve(length)")
    assert_width(BACKFILL_FLAG_BITS, "reserve(flag)")
    return max_bits + LENGTH_BITS + BACKFILL_FLAG_BITS


def position_model(old_max=11, old_updated=11, new_max=13, new_updated=13):
    """Bit offsets of the four positions, plus the acceptance invariants.

    F = header reserve start (== the frozen writer's initial m_iCurBit)
    B = entity body start
    E = entity body end (== end of payload)
    """
    old_res = reserve_bits(old_max, old_updated)
    new_res = reserve_bits(new_max, new_updated)

    # prefix = type + maxEntries + isDelta + frameFlag (deltaFrom is optional
    # and sits before frameFlag; it shifts everything equally, so it cancels).
    f_old = TYPE_BITS + old_max + IS_DELTA_BITS + FRAME_FLAG_BITS
    f_new = TYPE_BITS + new_max + IS_DELTA_BITS + FRAME_FLAG_BITS

    b_old = f_old + old_res
    b_new = f_new + new_res

    # backfill ranges, relative to the reserve start
    ranges = {
        "updated": (f_new, f_new + new_updated),
        "length": (f_new + new_updated, f_new + new_updated + LENGTH_BITS),
        "flag": (f_new + new_updated + LENGTH_BITS,
                 f_new + new_updated + LENGTH_BITS + BACKFILL_FLAG_BITS),
    }

    out = {
        "old": {"max": old_max, "updated": old_updated, "reserve": old_res,
                "F": f_old, "B": b_old, "body": b_old - f_old},
        "new": {"max": new_max, "updated": new_updated, "reserve": new_res,
                "F": f_new, "B": b_new, "body": b_new - f_new},
        "delta": {"F": f_new - f_old, "B": b_new - b_old,
                  "reserve": new_res - old_res},
        "ranges": {k: list(v) for k, v in ranges.items()},
        "invariants": {},
    }

    checks = {
        # the four positions the widening has to move to
        "F' = F + (max_size_delta)": out["delta"]["F"] == new_max - old_max,
        "B' = F' + new_reserve": b_new == f_new + new_res,
        "B = F + old_reserve": b_old == f_old + old_res,
        "B' = B + 4": out["delta"]["B"] == (new_max - old_max) + (new_res - old_res),
        "frozen cursor ends at B'": f_new + new_res == b_new,
        # the backfill must tile [F'..B'] exactly, no gap and no overlap
        "fields tile the reserve": all(
            ranges["updated"][0] == f_new
            and ranges["updated"][1] == ranges["length"][0]
            and ranges["length"][1] == ranges["flag"][0]
            and ranges["flag"][1] == b_new
            for _ in (0,)
        ),
        "flag lands on the frozen cursor": ranges["flag"][0] == f_new + new_res - 1,
    }
    out["invariants"] = checks
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise SystemExit("position model self-check failed: %s" % ", ".join(failed))
    return out


def cave_budget():
    """Bytes for the two-write code cave (option A), derived from components."""
    store = 6            # mov [ebp-0x170/0x16c/0x168], reg
    push_imm8 = 2
    mov_ecx_edi = 2
    call_rel32 = 5
    one_write = push_imm8 + push_imm8 + mov_ecx_edi + call_rel32
    jmp_back = 5
    parts = {
        "3 stores (curbit/overflow/0x14)": 3 * store,
        "WriteUBitLong(0,32)": one_write,
        "WriteUBitLong(0,2)": one_write,
        "jmp back": jmp_back,
    }
    return sum(parts.values()), parts


def va_to_offset(pe, va):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            d = rva - s.VirtualAddress
            if d < s.SizeOfRawData:
                return s.PointerToRawData + d
    return None


def check_csv_structure():
    """Run the strict CSV structure gate before any binary work.

    Standard library only: this must be evaluable even when ``pefile`` is not
    installed.  Returns a small summary on success; raises ``SystemExit(1)``
    with ``file:line: expected N columns, got M`` on the first bad table.
    """
    from check_fields_csv import format_error, scan_all

    reports = scan_all()
    problems = [error for report in reports for error in report.errors]
    if problems:
        print("csv structure: FAILED (strict gate)", file=sys.stderr)
        for error in problems:
            print("  " + format_error(error), file=sys.stderr)
        raise SystemExit(1)
    return {
        "status": "ok",
        "files": len(reports),
        "rows": sum(report.rows for report in reports),
    }


def check_binary(path):
    try:
        import pefile
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "pefile is required to verify engine.dll bytes; the CSV structure "
            "gate above already passed, so this is a PE-stage dependency, not "
            "a data-file failure.\n"
            "install it with: python3 -m pip install pefile"
        ) from exc
    path = require(path)
    raw = open(path, "rb").read()
    pe = pefile.PE(path, fast_load=True)
    digest = hashlib.sha256(raw).hexdigest()
    results = []
    for site in SITES:
        off = va_to_offset(pe, site.va)
        seen = raw[off:off + len(site.expect) // 2].hex() if off is not None else None
        results.append({
            "va": site.va, "offset": off, "expect": site.expect, "seen": seen,
            "ok": seen == site.expect, "purpose": site.purpose,
            "patch": site.patch,
        })
    mask_off = va_to_offset(pe, MASK_0X1FFF)
    mask_seen = raw[mask_off:mask_off + 4].hex() if mask_off is not None else None
    return {
        "path": path,
        "sha256": digest,
        "sha256_matches_recorded_build": digest == BUILD_SHA256,
        "size": len(raw),
        "sites": results,
        "mask_0x1fff": {"va": MASK_0X1FFF, "offset": mask_off,
                        "expect": MASK_0X1FFF_BYTES, "seen": mask_seen,
                        "ok": mask_seen == MASK_0X1FFF_BYTES},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old-max", type=int, default=11)
    ap.add_argument("--old-updated", type=int, default=11)
    ap.add_argument("--new-max", type=int, default=13)
    ap.add_argument("--new-updated", type=int, default=13)
    ap.add_argument("--check", action="store_true",
                    help="run the strict CSV structure gate, then verify the "
                         "expected bytes in engine.dll")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    csv_structure = None
    if args.check:
        # Gate 1: data-file structure (standard library, always runs first).
        csv_structure = check_csv_structure()
        if not args.json:
            print("csv structure: OK (%d files, %d data rows, every row matches "
                  "its header width)" % (csv_structure["files"], csv_structure["rows"]))

    guard_selftest()
    model = position_model(args.old_max, args.old_updated,
                           args.new_max, args.new_updated)
    # every single planned write must be a legal width; the reserve *total* is
    # deliberately not checked here -- 34 is legal as an advance, illegal as a
    # width.  That distinction is the whole point of the reserve patch.
    for name, n in (("maxEntries", args.new_max), ("updatedEntries", args.new_updated),
                    ("payloadBitLength", LENGTH_BITS), ("backfillFlag", BACKFILL_FLAG_BITS),
                    ("reserveWrite#1", min(model["new"]["reserve"], MAX_NUM_BITS)),
                    ("reserveWrite#2", max(0, model["new"]["reserve"] - MAX_NUM_BITS))):
        assert_width(n, name)

    cave_total, cave_parts = cave_budget()
    patched = sum(len(s.patch) // 2 for s in SITES)
    patched_cold = sum(len(s.patch) // 2 for s in COLD_SITES)

    report = {
        "plan": "%d/%d" % (args.new_max, args.new_updated),
        "guard_selftest": True,
        "constraint": {"max_num_bits": MAX_NUM_BITS,
                       "mask_index": "(curbit & 31) * %d + numBits" % MASK_ROW_WIDTH},
        "positions": model,
        "sites": [s._asdict() for s in SITES],
        "cold_sites": [s._asdict() for s in COLD_SITES],
        "bytes_changed": {"hot": patched, "cold": patched_cold},
        "cave": {"option_a_bytes": cave_total, "option_b_bytes": len(SITES[2].patch) // 2,
                 "breakdown": cave_parts},
    }
    if csv_structure is not None:
        report["csv_structure"] = csv_structure
    if args.check:
        report["binary"] = check_binary(ENGINE_DLL)
        bad = [s for s in report["binary"]["sites"] if not s["ok"]]
        if not report["binary"]["mask_0x1fff"]["ok"] or bad:
            report["check_passed"] = False
        else:
            report["check_passed"] = True

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        p = model
        print("plan %s: F=%d->%d (max %d->%d), B=%d->%d (%+d), reserve %d->%d" % (
            report["plan"], p["old"]["F"], p["new"]["F"], p["old"]["max"], p["new"]["max"],
            p["old"]["B"], p["new"]["B"], p["delta"]["B"],
            p["old"]["reserve"], p["new"]["reserve"]))
        print("backfill ranges (absolute bit offsets): %s" % p["ranges"])
        print("invariants: %s" % ", ".join("%s=%s" % (k, "ok" if v else "FAIL")
                                           for k, v in p["invariants"].items()))
        print("\nconstraint: numBits 0..%d (%d-column mask row); 34 is invalid -- "
              "the reserve advances the cursor instead" % (MAX_NUM_BITS, MASK_ROW_WIDTH))
        print("reserve option A (code cave): %d bytes; option B (in place): %d bytes"
              % (cave_total, len(SITES[2].patch) // 2))
        print("\n%-12s %-22s %-8s %s" % ("VA", "purpose", "off", "bytes"))
        binfo = report.get("binary")
        for i, s in enumerate(SITES):
            off = ("0x%06X" % binfo["sites"][i]["offset"]) if binfo and binfo["sites"][i]["offset"] else "-"
            mark = ""
            if binfo:
                mark = "  ok" if binfo["sites"][i]["ok"] else "  MISMATCH(%s)" % binfo["sites"][i]["seen"]
            print("0x%08X  %-22s %-8s %s -> %s%s" % (s.va, s.purpose, off,
                                                     s.expect, s.patch, mark))
        if binfo:
            print("\nengine.dll sha256 %s (%d bytes), recorded build: %s"
                  % (binfo["sha256"], binfo["size"],
                     "match" if binfo["sha256_matches_recorded_build"] else "DIFFERENT"))
            print("mask 0x1FFF @0x%08X: %s" % (MASK_0X1FFF,
                                               "ok" if binfo["mask_0x1fff"]["ok"] else "missing"))
            print("check %s" % ("PASSED" if report["check_passed"] else "FAILED"))
    return 0 if report.get("check_passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
