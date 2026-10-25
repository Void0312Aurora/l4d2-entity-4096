#!/usr/bin/env python3
"""Resize CFrameSnapshotManager::TakeTickSnapshot's fixed 2060-entry stack array.

The original frame is 0x102c and stores uint16 entity indices at ebp-0x1018,
i.e. 2060 slots. At sv.num_edicts >= 2060 the store walks into saved registers,
saved ebp and arguments. Resize the frame to 0x302c and move the array to
ebp-0x3018 (8192+ bytes, 4096 slots).
"""
import hashlib, sys
from pathlib import Path

SITES = [
    (0x1E2718, "81ec2c100000", "81ec2c300000"),  # sub esp,0x102c -> 0x302c
    (0x1E27D5, "6689b445e8efffff", "6689b445e8cfffff"),  # store ebp-0x1018 -> ebp-0x3018
    (0x1E2827, "8d8de8efffff", "8d8de8cfffff"),  # lea ebp-0x1018 -> ebp-0x3018
    (0x1E28B7, "81c42c100000", "81c42c300000"),  # add esp,0x102c -> 0x302c
]

def main():
    src=Path(sys.argv[1] if len(sys.argv)>1 else "/tmp/n27/n27_full_4096_13bit_v2.so")
    out=Path(sys.argv[2] if len(sys.argv)>2 else "/tmp/n27/n27_full_4096_13bit_v3.so")
    b=bytearray(src.read_bytes())
    for off, old, new in SITES:
        ob=bytes.fromhex(old)
        if bytes(b[off:off+len(ob)]) != ob:
            raise SystemExit(f"mismatch at 0x{off:X}")
        b[off:off+len(ob)] = bytes.fromhex(new)
    changed=sum(1 for x,y in zip(src.read_bytes(),b) if x!=y)
    out.write_bytes(b)
    print(f"out {out} sha256={hashlib.sha256(b).hexdigest()} changed={changed}")
    return 0

if __name__ == "__main__": sys.exit(main())
