#!/usr/bin/env python3
"""N27 static gate: verify every planned edit against the pristine ELF.

Checks:
  1. explicit byte patches match the original bytes at elf_addr == file offset
  2. no two explicit patches overlap
  3. frame-member and stack-reference rows do not collide with explicit patches
  4. frame-member rows contain the recorded old displacement in their bytes
  5. stack-reference rows cover exactly 212 shifted, 3 bitmap-base,
     24 unchanged-above and 23 argument references
  6. no duplicate instruction addresses inside the frame/stack tables
"""
import csv, hashlib, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ELF = Path("/home/void0312/l4d2_server/bin/engine_srv.so")
EXPECTED_SHA = "5fa15f2820ab67b955ff227a20dbb3fda54d463f3799f33d71b6fd6f38e309b7"

def rows(path):
    with open(REPO / path, newline="") as f:
        for r in csv.DictReader(f):
            yield r

def hexbytes(s):
    s = (s or "").strip()
    if not s or s == "-":
        return None
    try:
        return bytes.fromhex(s)
    except ValueError:
        return None

def le32(v):
    return (v & 0xFFFFFFFF).to_bytes(4, "little")

def main():
    data = ELF.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    bad = False
    if sha != EXPECTED_SHA:
        print(f"FAIL: ELF sha256 {sha} != pristine {EXPECTED_SHA}")
        return 1

    spans = []
    for path in ("data/linux/n27b_patch_sites.csv", "data/linux/n27c_patch_sites.csv"):
        for r in rows(path):
            b = hexbytes(r.get("old_bytes"))
            if not b:
                continue
            addr = int(r["elf_addr"], 16)
            if addr != int(r.get("file_offset", r["elf_addr"]), 16):
                print(f"FAIL: {path} {r['elf_addr']} addr/file_offset mismatch")
                bad = True
            got = data[addr:addr + len(b)]
            if got != b:
                print(f"FAIL: {path} {r['elf_addr']} bytes {got.hex()} != {b.hex()}")
                bad = True
            spans.append((addr, addr + len(b), r.get("group", "?"), path))
    spans.sort()
    for i in range(len(spans) - 1):
        a0, a1, g0, p0 = spans[i]
        a2, a3, g2, p2 = spans[i + 1]
        if a2 < a1:
            print(f"FAIL overlap: {p0} {g0} 0x{a0:X} vs {p2} {g2} 0x{a2:X}")
            bad = True

    explicit_addrs = {a for a, _, _, _ in spans}
    frame_addrs = set()
    for r in rows("data/linux/n27b_frame_member_sites.csv"):
        addr = int(r["elf_addr"], 16)
        if addr in frame_addrs:
            print(f"FAIL: duplicate frame site 0x{addr:X}")
            bad = True
        frame_addrs.add(addr)
        if addr in explicit_addrs:
            print(f"FAIL: frame site 0x{addr:X} also claimed by an explicit patch")
            bad = True
        old = int(r["old_disp"], 16)
        pat = le32(old)
        if pat not in data[addr:addr + 16]:
            print(f"FAIL: frame site 0x{addr:X} does not contain disp {r['old_disp']}")
            bad = True

    counts = {"below_bitmap_shift": 0, "bitmap_base": 0,
              "above_bitmap_keep": 0, "arg_keep": 0, "bitmap_region_other": 0}
    stack_addrs = set()
    for r in rows("data/linux/n27c_stack_sites.csv"):
        addr = int(r["elf_addr"], 16)
        if addr in stack_addrs:
            print(f"FAIL: duplicate stack site 0x{addr:X}")
            bad = True
        stack_addrs.add(addr)
        if addr in explicit_addrs and r["class"] != "bitmap_base":
            print(f"FAIL: stack site 0x{addr:X} also claimed by an explicit patch")
            bad = True
        b = hexbytes(r["old_bytes"])
        if b is None or data[addr:addr + len(b)] != b:
            print(f"FAIL: stack site 0x{addr:X} bytes mismatch")
            bad = True
        d = int(r["old_disp"], 16)
        d = d - 0x100000000 if d & 0x80000000 else d
        if r["class"] in ("below_bitmap_shift", "bitmap_base"):
            if le32(d) not in (b or b""):
                print(f"FAIL: stack site 0x{addr:X} lacks disp32 {r['old_disp']}")
                bad = True
        counts[r["class"]] = counts.get(r["class"], 0) + 1

    expect = {"below_bitmap_shift": 212, "bitmap_base": 3,
              "above_bitmap_keep": 24, "arg_keep": 23, "bitmap_region_other": 0}
    if counts != expect:
        print(f"FAIL: stack class counts {counts} != {expect}")
        bad = True

    print("FAIL" if bad else "PASS: pristine bytes, spans, frame/stack coverage all consistent")
    print("counts:", counts, "explicit spans:", len(spans), "frame:", len(frame_addrs), "stack:", len(stack_addrs))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
