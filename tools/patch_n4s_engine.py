#!/usr/bin/env python3
"""N4-S: FUN_1011D900 stack array 2048 -> 4096 (engine.dll build 23990068).

Data-driven: the ten disp32 sites are pinned in tools/n4s_sites.json, each with the
four bytes that precede the displacement and the exact old displacement. No pattern
sweep is used; every site is verified by address, context bytes and displacement.

Gates (all raise SystemExit, none rely on assert):
  1. input SHA-256 == audited original;
  2. __chkstk immediate matches 11 D903 b810100000;
  3. every pinned site matches prefix + old disp;
  4. output is reopened and re-verified (sha, length, all 11 operands, no old disp).

Usage:
  python3 tools/patch_n4s_engine.py --check
  python3 tools/patch_n4s_engine.py --out out/engine.n4s.dll
"""
import argparse, hashlib, json, pathlib, struct, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = json.loads((ROOT / "tools" / "n4s_sites.json").read_text())

def die(msg):
    raise SystemExit("REFUSED: " + msg)

def sections(blob):
    e = struct.unpack_from("<I", blob, 0x3C)[0]
    if blob[e:e+4] != b"PE\0\0":
        die("not a PE image")
    nsec = struct.unpack_from("<H", blob, e + 6)[0]
    optsz = struct.unpack_from("<H", blob, e + 20)[0]
    base = struct.unpack_from("<I", blob, e + 24 + 28)[0]
    off = e + 24 + optsz
    out = []
    for i in range(nsec):
        o = off + i * 40
        vsz, rva, rawsz, rp = struct.unpack_from("<IIII", blob, o + 8)
        out.append((rva, rawsz, rp))
    return base, out

def make_mapper(base, secs, blob):
    def va2off(va):
        for rva, rawsz, rp in secs:
            s = base + rva
            if s <= va < s + min(rawsz, len(blob) - rp):
                return rp + (va - s)
        die("VA 0x%08X is not mapped" % va)
    return va2off

def verify_sites(blob, va2off, want):
    """want: 'old' or 'new'. Returns list of verified addresses."""
    if len(SPEC["sites"]) != 10:
        die("expected exactly 10 pinned sites, got %d" % len(SPEC["sites"]))
    vas = [int(x["va"], 16) for x in SPEC["sites"]]
    if len(set(vas)) != 10:
        die("pinned sites are not unique")
    ok = []
    for s in SPEC["sites"]:
        va = int(s["va"], 16)
        off = va2off(va)
        if bytes.fromhex(s["prefix"]) != blob[off-4:off]:
            die("prefix mismatch at 0x%08X (got %s)" % (va, blob[off-4:off].hex()))
        if want == "old":   # 只在原始文件上核对上下文；new 形态下相邻站点会互相覆盖该窗口
            ctx = bytes.fromhex(s["context"])
            if blob[off-8:off-4] != ctx[:4]:
                die("context-before mismatch at 0x%08X (got %s)" % (va, blob[off-8:off-4].hex()))
        target = bytes.fromhex(s["disp_old" if want == "old" else "disp_new"])
        if blob[off:off+4] != target:
            die("disp mismatch at 0x%08X (want %s, got %s)" % (va, target.hex(), blob[off:off+4].hex()))
        ok.append(va)
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dll", default="/run/media/void0312/566EBEB06EBE87EF/SteamLibrary/steamapps/common/Left 4 Dead 2/bin/engine.dll")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    src = pathlib.Path(a.dll)
    blob = bytearray(src.read_bytes())
    sha = hashlib.sha256(blob).hexdigest()
    print("input : %s\nsha256: %s" % (src, sha))
    if sha != SPEC["audited_sha256"]:
        die("sha256 != audited original (%s)" % SPEC["audited_sha256"])

    base, secs = sections(blob)
    va2off = make_mapper(base, secs, blob)

    # chkstk
    c = va2off(int(SPEC["chkstk_va"], 16))
    if blob[c:c+5] != bytes.fromhex(SPEC["chkstk_old"]):
        die("chkstk mismatch at %s" % SPEC["chkstk_va"])
    print("chkstk: %s %s -> %s" % (SPEC["chkstk_va"], SPEC["chkstk_old"], SPEC["chkstk_new"]))

    # sites
    verified = verify_sites(blob, va2off, "old")
    print("sites : %d pinned disp32 references verified (old form)" % len(verified))
    for s in SPEC["sites"]:
        print("  %s  %s -> %s  prefix %s" % (s["va"], s["disp_old"], s["disp_new"], s["prefix"]))

    # apply in memory
    blob[c:c+5] = bytes.fromhex(SPEC["chkstk_new"])
    for s in SPEC["sites"]:
        off = va2off(int(s["va"], 16))
        blob[off:off+4] = bytes.fromhex(s["disp_new"])

    # in-memory re-check
    verify_sites(blob, va2off, "new")
    f0 = va2off(0x1011D900); f1 = va2off(0x1011DAC9)
    body = bytes(blob[f0:f1])
    for s in SPEC["sites"]:
        if bytes.fromhex(s["disp_old"]) in body:
            die("old disp still present after patch: " + s["disp_old"])
    print("verify: old disp eliminated, %d new disp present, chkstk updated" % len(SPEC["sites"]))

    if a.check:
        print("\nCHECK ONLY: no file written")
        return

    out = pathlib.Path(a.out or "out/engine.n4s.dll")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(blob))

    # reopen and verify the artifact on disk
    disk = out.read_bytes()
    got = hashlib.sha256(disk).hexdigest()
    if len(disk) != len(blob) or got != hashlib.sha256(bytes(blob)).hexdigest():
        die("written file does not match the patched buffer")
    db = bytearray(disk); base2, secs2 = sections(db); va2off2 = make_mapper(base2, secs2, db)
    verify_sites(db, va2off2, "new")
    c2 = va2off2(int(SPEC["chkstk_va"], 16))
    if db[c2:c2+5] != bytes.fromhex(SPEC["chkstk_new"]):
        die("chkstk on disk is wrong")
    print("disk  : reopened and verified (%d bytes, sha256 %s)" % (len(disk), got))
    print("output: %s" % out)

if __name__ == "__main__":
    main()
