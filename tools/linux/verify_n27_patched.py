#!/usr/bin/env python3
"""Post-build gate for the N27 stack/frame image.

Run objdump on a patched engine_srv.so and reject:
  * any residual old EBP displacement in WriteDeltaEntities
  * any remaining 0x7FF entity bound
  * missing 0x230 bitmap base or missing 0xFFF bounds
  * stale prologue bytes
"""
import re, subprocess, sys
from pathlib import Path

START, END = 0x1DD830, 0x1DF044

def disasm(path):
    return subprocess.check_output(
        ["objdump", "-d", "-Mintel",
         f"--start-address=0x{START:X}", f"--stop-address=0x{END:X}", str(path)],
        text=True, errors="replace")

def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/n27/engine_srv_n27.so")
    out = disasm(path)
    data = path.read_bytes()
    bad = []

    disps = [int(m, 16) for m in re.findall(r"ebp[^\]]*?[-+]0x([0-9a-fA-F]+)", out)]
    illegal = [d for d in disps if d == 0x130]
    if illegal:
        bad.append(f"residual old EBP disps: {sorted(set(illegal))[:8]}")
    if 0x3CC not in disps:
        bad.append("bitmap base -0x3CC not found")

    cmps7ff = re.findall(r"cmp\s+\w+,0x7ff\b", out, re.I)
    if cmps7ff:
        bad.append(f"{len(cmps7ff)} remaining cmp 0x7ff")
    cmpsfff = re.findall(r"cmp\s+\w+,0xfff\b", out, re.I)
    if len(cmpsfff) != 9:
        bad.append(f"expected 9 cmp 0xFFF, got {len(cmpsfff)}")

    if data[0x1DD83C:0x1DD842] != bytes.fromhex("8d bd 34 fc ff ff"):
        bad.append("prologue lea [ebp-0x3CC] missing")
    if data[0x1DD843:0x1DD849] != bytes.fromhex("81 ec cc 03 00 00"):
        bad.append("prologue sub esp,0x3CC missing")
    if data[0x1DD833:0x1DD838] != bytes.fromhex("b9 80 00 00 00"):
        bad.append("prologue mov ecx,0x80 missing")

    if bad:
        print("FAIL")
        for b in bad:
            print(" -", b)
        return 1
    print("PASS: no residual old EBP displacement, nine 0xFFF bounds, 0x3CC base")
    return 0

if __name__ == "__main__":
    sys.exit(main())
