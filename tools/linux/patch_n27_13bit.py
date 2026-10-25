#!/usr/bin/env python3
"""Candidate server 13-bit PacketEntities patch (experimental).

Widens the two inline header writes in CBaseServer::WriteDeltaEntities:
availability checks, 13-bit mask column, boundary compares, slow-path widths
and the max-entries cursor advance. Updated-entries cursor handling is left as
in the original; low-index integration is the acceptance test.
"""
import hashlib, struct, sys
from pathlib import Path

SITES = [
    (0x1DD994, "8d4e0b", "8d4e0d"),
    (0x1DD9B5, "23948fcc2d3e00", "23948fd42d3e00"),
    (0x1DD9CF, "83fa0a", "83fa0c"),
    (0x1DD9D8, "83400c0b", "83400c0d"),
    (0x1DDCEC, "b90b000000", "b90d000000"),
    (0x1DDB77, "83c00b", "83c00d"),
    (0x1DDBA0, "23948fcc2d3e00", "23948fd42d3e00"),
    (0x1DDBBA, "83fa0a", "83fa0c"),
    (0x1DDBBF, "b90b000000", "b90d000000"),
]

def main():
    src=Path(sys.argv[1] if len(sys.argv)>1 else "/tmp/n27/n27_full_4096.so")
    out=Path(sys.argv[2] if len(sys.argv)>2 else "/tmp/n27/n27_full_4096_13bit.so")
    b=bytearray(src.read_bytes())
    for off, old, new in SITES:
        ob=bytes.fromhex(old)
        if bytes(b[off:off+len(ob)]) != ob:
            raise SystemExit(f"mismatch at 0x{off:X}: {bytes(b[off:off+len(ob)]).hex()}")
        b[off:off+len(ob)] = bytes.fromhex(new)
    changed=sum(1 for x,y in zip(src.read_bytes(),b) if x!=y)
    out.write_bytes(b)
    print(f"out {out} sha256={hashlib.sha256(b).hexdigest()} changed={changed} sites={len(SITES)}")
    return 0

if __name__=="__main__": sys.exit(main())
