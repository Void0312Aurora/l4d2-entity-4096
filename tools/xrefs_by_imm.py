#!/usr/bin/env python3
"""Find code references to absolute VAs (typically string literals) in engine.dll.

Read-only. For each target VA, scan .text for
  68 <va>            push imm32
  B8..BF <va>        mov reg, imm32
  C7 05 <addr> <va>  mov dword ptr [addr], imm32
and print a short disassembly window around every hit, plus the enclosing
function start recovered from the nearest preceding prologue.

Usage: python xrefs_by_imm.py 0x1036a3ce 0x1037866b ...
"""
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

from config import require, ENGINE_DLL

SRC = require(ENGINE_DLL)
pe = pefile.PE(SRC, fast_load=True)
BASE = pe.OPTIONAL_HEADER.ImageBase
raw = open(SRC, "rb").read()
secs = []
for s in pe.sections:
    secs.append(dict(name=s.Name.rstrip(b"\0").decode(errors="replace"),
                     va=s.VirtualAddress, vsz=s.Misc_VirtualSize,
                     rs=s.SizeOfRawData, pr=s.PointerToRawData))


def va2off(va):
    r = va - BASE
    for s in secs:
        if s["va"] <= r < s["va"] + max(s["vsz"], s["rs"]):
            d = r - s["va"]
            if d < s["rs"]:
                return s["pr"] + d
    return None


def off2va(off):
    for s in secs:
        if s["pr"] <= off < s["pr"] + s["rs"]:
            return BASE + s["va"] + (off - s["pr"])
    return None


text = [s for s in secs if s["name"] == ".text"][0]
T0, T1 = BASE + text["va"], BASE + text["vsz"]
tlo, thi = text["pr"], text["pr"] + text["rs"]

md = Cs(CS_ARCH_X86, CS_MODE_32)
PROLOGUES = (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x8b\xff\x55\x8b\xec", b"\x53\x8b\xdc")


def func_start(va):
    off = va2off(va)
    while off is not None and off > tlo:
        if raw[off:off + 4] in (b"\x55\x8b\xec\x00",) or raw[off:off + 3] in PROLOGUES[:3]:
            return off2va(off)
        off -= 1
    return None


def dump(va, before=32, after=48):
    off = va2off(va)
    if off is None:
        print("    <unmapped>")
        return
    start = off2va(max(tlo, off - before))
    code = raw[max(tlo, off - before):min(thi, off + after)]
    for insn in md.disasm(code, start):
        mark = "  <== " if insn.address == va else "        "
        print("    %08x  %-22s %s%s" % (insn.address, insn.bytes.hex(), insn.mnemonic + " " + insn.op_str, mark))


for arg in sys.argv[1:]:
    tgt = int(arg, 0)
    pat = struct.pack("<I", tgt)
    hits = []
    off = tlo
    while True:
        i = raw.find(pat, off, thi)
        if i < 0:
            break
        va = off2va(i)
        hits.append(va)
        off = i + 1
    print("=" * 70)
    print("target 0x%08x  hits %d" % (tgt, len(hits)))
    for h in hits[:8]:
        prev = raw[h - 1] if h > 0 else 0
        print("  ref site 0x%08x  (prefix byte 0x%02x)  fn~0x%08x"
              % (h, prev, func_start(h) or 0))
        dump(h - 8, 40, 56)
