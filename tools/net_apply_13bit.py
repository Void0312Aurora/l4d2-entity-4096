#!/usr/bin/env python3
"""Apply the 13/13 svc_PacketEntities plan to engine.dll and write a patched PE.

Reads the source path from L4D2_ENGINE_BIN (directory) or --src. Verifies the
recorded SHA-256 and every expected byte before writing. Does not install the
DLL into Steam.
"""
import argparse, hashlib, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import net_patch_plan as plan

EXPECTED = "8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86"

def pe_checksum(data, csum_off, cert_off, cert_sz):
    d = bytearray(data); struct.pack_into("<I", d, csum_off, 0)
    remainder = len(d) % 4
    data_len = len(d) + ((4 - remainder) * (remainder != 0))
    checksum = 0
    for i in range(data_len // 4):
        if i == csum_off // 4:
            continue
        chunk = d[i*4:i*4+4]
        if len(chunk) < 4: chunk = chunk + b"\0"*(4-len(chunk))
        checksum += struct.unpack("<I", chunk)[0]
        if checksum >= 2**32:
            checksum = (checksum & 0xFFFFFFFF) + (checksum >> 32)
    checksum = (checksum & 0xFFFF) + (checksum >> 16)
    checksum = checksum + (checksum >> 16)
    checksum &= 0xFFFF
    return checksum + len(d)

def va_to_off(blob, va):
    e = struct.unpack_from("<I", blob, 0x3C)[0]
    opt = e + 24
    image_base = struct.unpack_from("<I", blob, opt+28)[0]
    rva = va - image_base
    nsec = struct.unpack_from("<H", blob, e+6)[0]
    optsz = struct.unpack_from("<H", blob, e+20)[0]
    sec = e + 24 + optsz
    for i in range(nsec):
        off = sec + 40*i
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", blob, off+8)
        if vaddr <= rva < vaddr + max(vsize, rawsize):
            return rawptr + (rva - vaddr)
    raise SystemExit(f"VA 0x{va:X} not mapped")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=None)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1]/"out/engine.4096.13bit.dll"))
    a = ap.parse_args()
    src = Path(a.src) if a.src else Path(plan.ENGINE_DLL)
    blob = src.read_bytes()
    sha = hashlib.sha256(blob).hexdigest()
    if sha != EXPECTED:
        raise SystemExit(f"unexpected engine.dll sha256 {sha}")
    out = bytearray(blob)
    for s in plan.SITES:
        off = va_to_off(blob, s.va)
        exp = bytes.fromhex(s.expect)
        cur = bytes(out[off:off+len(exp)])
        if cur != exp:
            raise SystemExit(f"{s.va:#x}: {cur.hex()} != {exp.hex()}")
        out[off:off+len(exp)] = bytes.fromhex(s.patch)
    changed = sum(1 for x,y in zip(blob,out) if x!=y)
    print(f"applied {len(plan.SITES)} sites, {changed} changed bytes")
    e = struct.unpack_from("<I", out, 0x3C)[0]
    opt = e + 24
    csum_off = opt + 64
    # PE32 DataDirectory[4] (certificate table) is at opt+96+4*8 = opt+128
    cert_off, cert_sz = struct.unpack_from("<II", out, opt+128)
    struct.pack_into("<I", out, csum_off, pe_checksum(out, csum_off, cert_off, cert_sz))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(out)
    print(f"src {src} sha256={sha}")
    print(f"out {a.out} sha256={hashlib.sha256(out).hexdigest()} changed={changed}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
