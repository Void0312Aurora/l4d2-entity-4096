#!/usr/bin/env python3
"""Merged engine.dll build: storage layer (11 dwords + .edict2) then N4-S (11 operands).

Reads engine/manifest.json for the storage patch set (never regenerates it).
Verifies the storage-only stage against the recorded artifact hash before applying N4-S.
"""
import hashlib, json, pathlib, re, struct, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path("/run/media/void0312/566EBEB06EBE87EF/SteamLibrary/steamapps/common/Left 4 Dead 2/bin/engine.dll")
OUT = ROOT / "out" / "engine.4096.n4s.dll"
MANIFEST = ROOT / "out" / "manifest.4096.n4s.json"
STORAGE_SHA = "3ac18292d746d1d33445b82e83c237fa25b7a3daab5968c18ddf42144059012e"

def die(m): raise SystemExit("REFUSED: " + m)

def load_checksum():
    import ast
    src = (ROOT / "engine" / "verify_pe.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "pe_checksum":
            seg = ast.get_source_segment(src, node)
            ns = {"struct": struct}
            exec(seg, ns)
            return ns["pe_checksum"]
    die("pe_checksum not found")

def main():
    manifest = json.loads((ROOT / "engine" / "manifest.json").read_text(encoding="utf-8"))
    blob = SRC.read_bytes()
    sha = hashlib.sha256(blob).hexdigest()
    if sha != manifest["artifact"]["sha256"]:
        die("input sha256 mismatch")
    checksum = load_checksum()

    out = bytearray(blob)
    # 1) storage dwords
    for p in manifest["patches"]:
        off = p["file_offset"]
        cur = struct.unpack_from("<I", out, off)[0]
        if cur != p["old"]:
            die("%s: expected 0x%X got 0x%X" % (p["id"], p["old"], cur))
        struct.pack_into("<I", out, off, p["new"])

    # 2) .edict2 section header + PE header fields
    e = struct.unpack_from("<I", blob, 0x3C)[0]
    coff = e + 4
    opt = coff + 20
    nsec_off, nsec = coff + 2, struct.unpack_from("<H", out, coff + 2)[0]
    soi_off, souninit_off, csum_off = opt + 56, opt + 12, opt + 64
    ns = manifest["new_section"]
    hdr = int(ns["header_offset"], 16)
    struct.pack_into("<8sIIIIIIHHI", out, hdr,
                     ns["name"].encode().ljust(8, b"\0"), int(ns["virtual_size"]),
                     int(ns["virtual_address"], 16), int(ns["size_of_raw_data"]),
                     int(ns["pointer_to_raw_data"]), 0, 0, 0, 0,
                     int(ns["characteristics"], 16))
    struct.pack_into("<H", out, nsec_off, nsec + 1)
    struct.pack_into("<I", out, soi_off, int(ns["size_of_image_new"], 16))
    struct.pack_into("<I", out, souninit_off,
                     struct.unpack_from("<I", out, souninit_off)[0] + int(ns["virtual_size"]))
    cert = manifest["file_layout"]["active_certificate"]
    cert_off, cert_sz = int(cert["offset"], 16), int(cert["size"], 16)
    struct.pack_into("<I", out, csum_off, 0)
    struct.pack_into("<I", out, csum_off, checksum(bytes(out), csum_off, cert_off, cert_sz))

    stage_sha = hashlib.sha256(bytes(out)).hexdigest()
    print("storage stage sha256: %s" % stage_sha)
    print("recorded    sha256: %s  (%s)" % (STORAGE_SHA, "MATCH" if stage_sha == STORAGE_SHA else "MISMATCH"))
    if stage_sha != STORAGE_SHA:
        die("storage stage does not reproduce the recorded engine.4096.dll")

    # 3) N4-S operands
    spec = json.loads((ROOT / "tools" / "n4s_sites.json").read_text(encoding="utf-8"))
    if len(spec["sites"]) != 10 or len({s["va"] for s in spec["sites"]}) != 10:
        die("n4s site table is not 10 unique entries")
    # VA -> file offset via sections of the storage-stage image
    e = struct.unpack_from("<I", out, 0x3C)[0]
    nsec = struct.unpack_from("<H", out, e + 6)[0]; optsz = struct.unpack_from("<H", out, e + 20)[0]
    base = struct.unpack_from("<I", out, e + 24 + 28)[0]; so = e + 24 + optsz
    secs = []
    for i in range(nsec):
        o = so + i * 40
        vsz, rva, rawsz, rp = struct.unpack_from("<IIII", out, o + 8)
        secs.append((rva, rawsz, rp))
    def va2off(va):
        for rva, rawsz, rp in secs:
            if base + rva <= va < base + rva + rawsz:
                return rp + (va - (base + rva))
        die("VA 0x%08X unmapped" % va)
    chk = va2off(int(spec["chkstk_va"], 16))
    if bytes(out[chk:chk+5]) != bytes.fromhex(spec["chkstk_old"]):
        die("chkstk bytes changed by storage layer")
    out[chk:chk+5] = bytes.fromhex(spec["chkstk_new"])
    for s in spec["sites"]:
        off = va2off(int(s["va"], 16))
        if bytes(out[off-4:off]) != bytes.fromhex(s["prefix"]):
            die("prefix mismatch at " + s["va"])
        if bytes(out[off:off+4]) != bytes.fromhex(s["disp_old"]):
            die("disp mismatch at " + s["va"])
        out[off:off+4] = bytes.fromhex(s["disp_new"])
    print("n4s stage: 11 operands applied")

    # 4) recompute checksum over the merged image
    struct.pack_into("<I", out, csum_off, 0)
    struct.pack_into("<I", out, csum_off, checksum(bytes(out), csum_off, cert_off, cert_sz))

    # 5) write + reopen verify
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(bytes(out))
    disk = bytearray(OUT.read_bytes())
    if len(disk) != len(blob):
        die("output length changed")
    dsha = hashlib.sha256(bytes(disk)).hexdigest()
    e2 = struct.unpack_from("<I", disk, 0x3C)[0]
    n2 = struct.unpack_from("<H", disk, e2 + 6)[0]
    if n2 != nsec:
        die("section count changed on disk")
    d = bytearray(disk)
    base2 = struct.unpack_from("<I", d, e2 + 24 + 28)[0]; so2 = e2 + 24 + struct.unpack_from("<H", d, e2+20)[0]
    secs2 = []
    for i in range(n2):
        o = so2 + i * 40
        vsz, rva, rawsz, rp = struct.unpack_from("<IIII", d, o + 8)
        secs2.append((rva, rawsz, rp))
    def va2off2(va):
        for rva, rawsz, rp in secs2:
            if base2 + rva <= va < base2 + rva + rawsz:
                return rp + (va - (base2 + rva))
        die("disk VA unmapped")
    for s in spec["sites"]:
        off = va2off2(int(s["va"], 16))
        if bytes(d[off:off+4]) != bytes.fromhex(s["disp_new"]):
            die("disk disp verify failed at " + s["va"])
    if bytes(d[va2off2(int(spec["chkstk_va"], 16)):][:5]) != bytes.fromhex(spec["chkstk_new"]):
        die("disk chkstk verify failed")
    print("disk verify: %d bytes, sha256 %s" % (len(d), dsha))

    MANIFEST.write_text(json.dumps({
        "artifact": {"path": "engine.dll", "sha256_in": sha, "sha256_storage_stage": stage_sha,
                     "sha256_out": dsha, "size": len(d), "buildid": "23990068"},
        "storage_reproduced_recorded_sha256": True,
        "groups": [
            {"id": "storage_layer", "records": len(manifest["patches"]),
             "note": "11 dwords + .edict2 header + SizeOfImage/SizeOfUninitializedData/CheckSum"},
            {"id": "n4s_stack_array", "operands": 11,
             "note": "chkstk immediate 0x1010->0x2010 and 10 disp32 sites -0x1010/-0x100C/-0x1008/-0x1004 -> -0x2010/-0x200C/-0x2008/-0x2004"},
        ],
        "checksum": {"field_offset": hex(csum_off), "value": hex(struct.unpack_from("<I", d, csum_off)[0])},
    }, indent=2) + "\n")
    print("manifest: %s" % MANIFEST)

main()
