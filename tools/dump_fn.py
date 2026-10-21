#!/usr/bin/env python3
"""Dump the disassembly of the function containing a given VA.

Function starts are recovered from call targets (E8 rel32) plus common MSVC
prologues, which is enough to bracket Source-engine functions in a stripped
image. Read-only.

Usage: python dump_fn.py 0x10076b6e [more VAs]
       python dump_fn.py --all 0x10076b6e   (widen window, no int3 stop)
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
secs = [dict(name=s.Name.rstrip(b"\0").decode(errors="replace"), va=s.VirtualAddress,
             vsz=s.Misc_VirtualSize, rs=s.SizeOfRawData, pr=s.PointerToRawData)
        for s in pe.sections]


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

starts = set()
i = tlo
while True:
    i = raw.find(b"\xe8", i, thi)
    if i < 0:
        break
    va = off2va(i)
    if va:
        tgt = va + 5 + struct.unpack_from("<i", raw, i + 1)[0]
        if T0 < tgt < T1:
            starts.add(tgt)
    i += 1
for off in range(tlo, thi - 4):
    if raw[off:off + 3] in (b"\x55\x8b\xec", b"\x55\x89\xe5"):
        va = off2va(off)
        if va:
            starts.add(va)
starts = sorted(starts)

md = Cs(CS_ARCH_X86, CS_MODE_32)


def containing(va):
    lo, hi = 0, len(starts) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if starts[mid] <= va:
            best = starts[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def dump(va, limit=4000):
    fs = containing(va)
    if fs is None:
        print("no function start before 0x%08x" % va)
        return
    nxt = next((s for s in starts if s > fs), T1)
    end = min(nxt, fs + 0x6000)
    off = va2off(fs)
    code = raw[off:off + (end - fs)]
    print("=== function 0x%08x .. 0x%08x  (hit 0x%08x) ===" % (fs, end, va))
    n = 0
    for insn in md.disasm(code, fs):
        n += 1
        if n > limit:
            print("    ... truncated at %d instructions" % limit)
            break
        mark = "*" if insn.address == va else " "
        print("  %s %08x  %s %s" % (mark, insn.address, insn.mnemonic, insn.op_str))
        if insn.mnemonic == "ret" and insn.address >= va:
            break
        if insn.mnemonic == "int3" and insn.address > fs + 16:
            break


args = [a for a in sys.argv[1:] if not a.startswith("--")]
for a in args:
    dump(int(a, 0))
