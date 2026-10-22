"""Reproduce the N2.2 producer/consumer data-flow evidence for SVC_PacketEntities.

Scans engine.dll (build 23990068) for:
  1. direct E8 callers of a target VA            -> `calls TARGET`
  2. imm32 references to a VA                    -> `imm TARGET`
  3. `push imm32` sites and the call they feed   -> `push 0x800`

The findings this reproduces (all coordinates in reports/network-n2.md sec.7-9):
  - FUN_10119F50 writes exactly two 11-bit fields: [[to+0x118]+0xC] and a counter.
  - FUN_1011D320 stores maxEntities into obj+0x0C without adjusting it.
  - push 0x800 feeds FUN_1011D320 from 0x1004F3AE and 0x1005158F.
  - FUN_1004E310 hard-codes the 2048-bit sweep bound (0x800 / 0x40).

Usage (paths default to the verified local install):
    python tools/probe_deltaflow.py
    python tools/probe_deltaflow.py --engine "F:/.../engine.dll" --push 0x800
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import pefile

DEFAULT_ENGINE = Path(r"F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll")
EXPECT_SHA256 = "8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86"

CALL_TARGETS = (0x10119490, 0x1011D320, 0x1004E310, 0x1004EAB0)
IMM_TARGETS = (0x103584DC, 0x103584D8)
PUSH_VALUES = (0x800, 0x7FF, 0x1000, 0xFFF)


def load_text(engine: Path):
    import hashlib

    raw = engine.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECT_SHA256:
        print(f"[warn] engine.dll SHA-256 {digest} != expected {EXPECT_SHA256}")
    pe = pefile.PE(str(engine), fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    sec = next(s for s in pe.sections if s.Name.rstrip(b"\x00") == b".text")
    return base + sec.VirtualAddress, sec.get_data()


def callers(text_base: int, text: bytes, target: int):
    out = []
    for i in range(len(text) - 5):
        if text[i] == 0xE8:
            rel = struct.unpack_from("<i", text, i + 1)[0]
            if (text_base + i + 5 + rel) & 0xFFFFFFFF == target:
                out.append(text_base + i)
    return out


def imm_refs(text_base: int, text: bytes, value: int):
    needle = struct.pack("<I", value)
    out, i = [], 0
    while True:
        j = text.find(needle, i)
        if j < 0:
            return out
        out.append(text_base + j)
        i = j + 1


def push_sites(text_base: int, text: bytes, value: int):
    if -128 <= value < 128:
        needle = bytes([0x6A, value & 0xFF])
    else:
        needle = b"\x68" + struct.pack("<I", value & 0xFFFFFFFF)
    out, i = [], 0
    while True:
        j = text.find(needle, i)
        if j < 0:
            return out
        target = None
        for k in range(j + len(needle), min(j + len(needle) + 12, len(text) - 5)):
            if text[k] == 0xE8:
                target = (text_base + k + 5 + struct.unpack_from("<i", text, k + 1)[0]) & 0xFFFFFFFF
                break
        out.append((text_base + j, target))
        i = j + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", type=Path, default=DEFAULT_ENGINE)
    ap.add_argument("--push", type=lambda s: int(s, 0), default=None,
                    help="scan only this push value, e.g. 0x800")
    args = ap.parse_args()

    text_base, text = load_text(args.engine)
    print(f".text {text_base:#010x}  size {len(text):#x}")

    print("\n== direct callers ==")
    for target in CALL_TARGETS:
        sites = callers(text_base, text, target)
        print(f"  {target:#010x}: {len(sites):3d}  " + " ".join(f"{s:#010x}" for s in sites[:12]))

    print("\n== imm32 references to vftable slots ==")
    for target in IMM_TARGETS:
        sites = imm_refs(text_base, text, target)
        print(f"  {target:#010x}: " + " ".join(f"{s:#010x}" for s in sites[:12]))

    print("\n== push imm -> following call ==")
    for value in ([args.push] if args.push is not None else PUSH_VALUES):
        sites = push_sites(text_base, text, value)
        hits = [(va, t) for va, t in sites if t is not None]
        print(f"  push {value:#x}: {len(sites)} sites, {len(hits)} with a call within 12 B")
        for va, tgt in hits[:10]:
            print(f"      {va:#010x} -> call {tgt:#010x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
