#!/usr/bin/env python3
"""Build the integrated N27 + N26 4096 image.

Pipeline: build_n27_full.py (F1/F2/F3 + S1/S2/S3 + C1/C3 + 4096-entry
g_EdictFreeTime), then the two N26 capacity immediates 0x800 -> 0x1000.
Network wire format is NOT changed.
"""
import hashlib, struct, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TMP = Path("/tmp/n27/n27_full.so")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/n27/n27_full_4096.so")
SITES = [(0x1EE0D9, 0x800, 0x1000), (0x1EE0E3, 0x800, 0x1000)]

def main():
    subprocess.check_call([sys.executable, str(REPO/"tools/linux/build_n27_full.py"), str(TMP)])
    original = TMP.read_bytes()
    data = bytearray(original)
    for off, old, new in SITES:
        cur = bytes(data[off:off+4])
        if cur != struct.pack("<I", old):
            raise SystemExit(f"capacity immediate at 0x{off:X} is {cur.hex()}")
        data[off:off+4] = struct.pack("<I", new)
    OUT.write_bytes(data)
    changed = sum(1 for a, b in zip(original, data) if a != b)
    if changed != 2:
        raise SystemExit(f"expected exactly 2 changed bytes, got {changed}")
    print(f"built {OUT} sha256={hashlib.sha256(data).hexdigest()} changed={changed}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
