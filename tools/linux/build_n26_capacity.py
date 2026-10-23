#!/usr/bin/env python3
"""Build the isolated N26 capacity image from the pristine engine_srv.so.

Only two 32-bit immediates change: 0x800 -> 0x1000 for the mirror global at
0x3A7F50 and for sv+0x210 (max_edicts). Instruction lengths are unchanged.

usage: build_n26_capacity.py SRC DST [--mode both|p2only]
"""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

EXPECTED_SHA256 = "5fa15f2820ab67b955ff227a20dbb3fda54d463f3799f33d71b6fd6f38e309b7"

# (instruction start, immediate offset, old immediate, new immediate)
SITES = [
    ("mirror_0x3A7F50", 0x1EE0D3, 0x1EE0D9, 0x800, 0x1000),
    ("sv_max_edicts",   0x1EE0DD, 0x1EE0E3, 0x800, 0x1000),
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--mode", choices=("both", "p2only"), default="both")
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)
    if src.resolve() == dst.resolve():
        raise SystemExit("source and destination must differ")
    if dst.exists():
        raise SystemExit(f"refusing to overwrite {dst}")

    original = src.read_bytes()
    digest = sha256(original)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unexpected source SHA-256: {digest}")

    patched = bytearray(original)
    chosen = [s for s in SITES if args.mode == "both" or s[0] == "sv_max_edicts"]

    for name, insn, imm_off, old, new in chosen:
        expected = struct.pack("<I", old)
        current = bytes(patched[imm_off:imm_off + 4])
        if current != expected:
            raise SystemExit(
                f"{name}: immediate at 0x{imm_off:X} is {current.hex()}, "
                f"expected {expected.hex()}"
            )
        # sanity: the instruction byte itself must still be the original C7 form
        if not (patched[insn] == 0xC7 and patched[insn + 1] in (0x05, 0x83)):
            raise SystemExit(f"{name}: unexpected instruction opcode at 0x{insn:X}")
        patched[imm_off:imm_off + 4] = struct.pack("<I", new)

    changed = [i for i in range(len(original)) if original[i] != patched[i]]
    allowed = set()
    for _, _, imm_off, _, _ in chosen:
        allowed.update(range(imm_off, imm_off + 4))
    if set(changed) - allowed:
        raise SystemExit(f"unexpected byte changes: {sorted(set(changed) - allowed)}")

    dst.write_bytes(patched)
    dst.chmod(src.stat().st_mode)

    print(f"source  {src}  sha256={digest}")
    print(f"output  {dst}  sha256={sha256(patched)}")
    print(f"mode    {args.mode}")
    for name, insn, imm_off, old, new in chosen:
        print(f"  {name}: 0x{imm_off:X} 0x{old:X} -> 0x{new:X} (insn 0x{insn:X})")
    print(f"changed bytes: {len(changed)}; file size {len(original)} -> {len(patched)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
