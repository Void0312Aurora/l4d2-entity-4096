#!/usr/bin/env python3
"""N4-S: FUN_1011D900 stack array 2048 -> 4096 (engine.dll, build 23990068).

Patches every EBP-relative access to the four locals/array inside the function by
rewriting the disp32 low word: -0x1010/-0x100C/-0x1008/-0x1004 -> -0x2010/-0x200C/-0x2008/-0x2004,
plus the __chkstk size immediate 0x1010 -> 0x2010.

Hard gates:
  * input SHA-256 must equal the audited original (8a6d4680...), otherwise refuse;
  * the __chkstk instruction must match b8 10 10 00 00 exactly;
  * at least one reference to the array base must be found;
  * the security cookie disp (-4) must not be rewritten (we never match it);
  * after patching, no old disp pattern may remain in the function body.

Usage:
  python3 tools/patch_n4s_engine.py --check
  python3 tools/patch_n4s_engine.py --out out/engine.n4s.dll
"""
import argparse, hashlib, pathlib, struct, sys

AUDITED_SHA256 = "8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86"
FUNC_START, FUNC_END = 0x1011D900, 0x1011DAC9          # inclusive-exclusive body range
CHKSTK_VA, CHKSTK_OLD, CHKSTK_NEW = 0x1011D903, b"\xb8\x10\x10\x00\x00", b"\xb8\x10\x20\x00\x00"

# disp32 (low word changes ef -> df, keeping 0xffff high word)
DISP_MAP = {
    bytes.fromhex("f0ef ffff".replace(" ", "")): bytes.fromhex("f0dfffff"),
    bytes.fromhex("f4ef ffff".replace(" ", "")): bytes.fromhex("f4dfffff"),
    bytes.fromhex("f8ef ffff".replace(" ", "")): bytes.fromhex("f8dfffff"),
    bytes.fromhex("fcef ffff".replace(" ", "")): bytes.fromhex("fcdfffff"),
}
LOCAL_NAME = {
    "f0ef": "local_1010 (saved ECX)",
    "f4ef": "local_100c (max_clients)",
    "f8ef": "local_1008 (loop index)",
    "fcef": "array base -0x1004 (short[2048])",
}

def sections(blob):
    e = struct.unpack_from("<I", blob, 0x3C)[0]
    nsec = struct.unpack_from("<H", blob, e + 6)[0]
    optsz = struct.unpack_from("<H", blob, e + 20)[0]
    base = struct.unpack_from("<I", blob, e + 24 + 28)[0]
    off = e + 24 + optsz
    out = []
    for i in range(nsec):
        o = off + i * 40
        name = blob[o:o + 8].rstrip(b"\0").decode(errors="replace")
        vsz, rva, rawsz, rawptr = struct.unpack_from("<IIII", blob, o + 8)
        out.append((name, rva, vsz, rawptr, rawsz))
    return base, out

def va2off(base, secs, va):
    for name, rva, vsz, rp, rs in secs:
        s = base + rva
        if s <= va < s + rs:
            return rp + (va - s)
    raise SystemExit("VA 0x%08X not mapped" % va)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dll", default="/run/media/void0312/566EBEB06EBE87EF/SteamLibrary/steamapps/common/Left 4 Dead 2/bin/engine.dll")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--allow-hash", action="store_true")
    a = ap.parse_args()

    src = pathlib.Path(a.dll)
    blob = bytearray(src.read_bytes())
    sha = hashlib.sha256(blob).hexdigest()
    print("input : %s" % src)
    print("sha256: %s" % sha)
    if sha != AUDITED_SHA256 and not a.allow_hash:
        raise SystemExit("REFUSED: sha256 != audited original (use --allow-hash to override)")

    base, secs = sections(blob)
    f0 = va2off(base, secs, FUNC_START)
    f1 = va2off(base, secs, FUNC_END)

    # 1) __chkstk immediate
    c = va2off(base, secs, CHKSTK_VA)
    assert bytes(blob[c:c+5]) == CHKSTK_OLD, "chkstk bytes mismatch: " + bytes(blob[c:c+5]).hex()
    print("chkstk: 0x%08X %s -> %s" % (CHKSTK_VA, CHKSTK_OLD.hex(), CHKSTK_NEW.hex()))

    # 2) enumerate disp references
    body = bytes(blob[f0:f1])
    sites = []
    for pat, new in DISP_MAP.items():
        start = 0
        while True:
            i = body.find(pat, start)
            if i < 0:
                break
            va = FUNC_START + i          # address of the disp32 field itself
            sites.append((va, pat, new))
            start = i + 1
    sites.sort()
    print("\ndisp32 references found in FUN_1011D900: %d" % len(sites))
    for va, pat, new in sites:
        tag = LOCAL_NAME[pat[:2].hex()]
        print("  0x%08X  %s -> %s   %s" % (va, pat.hex(), new.hex(), tag))
    if not any(p[:2].hex() == "fcef" for _, p, _ in sites):
        raise SystemExit("REFUSED: no array-base reference found")

    # 3) apply
    blob[c:c+5] = CHKSTK_NEW
    for va, pat, new in sites:
        off = va2off(base, secs, va)
        blob[off:off+4] = new

    # 4) verify
    body2 = bytes(blob[f0:f1])
    for pat in DISP_MAP:
        assert body2.find(pat) < 0, "old disp remains: " + pat.hex()
    for pat in DISP_MAP.values():
        assert body2.count(pat) == sum(1 for _, p, _ in sites if DISP_MAP[p] == pat)
    assert bytes(blob[c:c+5]) == CHKSTK_NEW
    # cookie invariant: disp32 fffffffc must not be touched by our map (it is not in DISP_MAP)
    print("\nnew disp counts:", {p.hex(): body2.count(p) for p in DISP_MAP.values()})
    print("cookie access is disp8 0xfc (never matched by the disp32 map); unchanged by design")
    print("frame: 0x1010 -> 0x2010; array [-0x2004,-0x4) covers 4096*2=%d bytes, ends at cookie-1" % (4096*2))

    if a.check:
        print("\nCHECK ONLY: no file written")
        return
    out = pathlib.Path(a.out or "out/engine.n4s.dll")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(blob)
    print("\nwrote %s (%d bytes, sha256 %s)" % (out, len(blob), hashlib.sha256(blob).hexdigest()))

if __name__ == "__main__":
    main()
