#!/usr/bin/env python3
"""N1 network-protocol field scan for engine.dll (read-only, byte level).

Goal: locate the engine's bit-buffer primitives and every call site that passes
a *constant* bit width, so the wire format of SVC_PacketEntities and the
network EHANDLE can be audited from binary evidence instead of the SDK.

Method (no decompiler, no symbol table):
  1. recover candidate function starts from call targets + prologue bytes
  2. linear-sweep disassemble with capstone, streaming (nothing kept but
     call sites, their pushed constant argument, and boundary compares)
  3. group call sites by callee: a callee that is called with many small
     constant widths is a bit-buffer primitive
  4. report functions that read *two* 11-bit fields in one body
     (SVC_PacketEntities reads m_nMaxEntries and m_nUpdatedEntries that way)
  5. report 21-bit sites (networked EHANDLE), and boundary immediates

Outputs data/netproto_*.csv and a JSON summary on stdout.
The game install is read-only.
"""
import collections
import csv
import hashlib
import json
import os
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

from config import require, ENGINE_DLL, DATA

SRC = require(ENGINE_DLL)
pe = pefile.PE(SRC, fast_load=True)
BASE = pe.OPTIONAL_HEADER.ImageBase
raw = open(SRC, "rb").read()

secs = []
for s in pe.sections:
    name = s.Name.rstrip(b"\0").decode(errors="replace")
    secs.append(dict(name=name, va=s.VirtualAddress, vsz=s.Misc_VirtualSize,
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
T0 = BASE + text["va"]
T1 = T0 + text["vsz"]
ok_lo, ok_hi = text["pr"], text["pr"] + text["rs"]

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

# ---------- 1. function starts ----------
starts = set()
i = 0
while True:
    i = raw.find(b"\xe8", i)
    if i < 0 or i >= ok_hi:
        break
    tgt = off2va(i)
    if tgt:
        rel = struct.unpack_from("<i", raw, i + 1)[0]
        a = tgt + 5 + rel
        if T0 < a < T1:
            starts.add(a)
    i += 1

PROLOGUES = (b"\x55\x8b\xec", b"\x55\x89\xe5", b"\x8b\xff\x55\x8b\xec", b"\x53\x8b\xdc")
for off in range(ok_lo, ok_hi - 4):
    for pr in PROLOGUES:
        if raw[off:off + len(pr)] == pr:
            va = off2va(off)
            if va and va not in starts:
                starts.add(va)
            break
starts = sorted(starts)
start_index = {a: k for k, a in enumerate(starts)}

# ---------- 2. streaming disassembly ----------
call_sites = []            # (site_va, callee_va, const_arg or None, n_puts)
cmp_imm = []               # (site_va, imm, mnem)
shift_imm = []             # (site_va, imm, mnem)
site_fn = {}               # site_va -> function start

BOUND = {0x7FF, 0x800, 0xFFF, 0x1000, 0x1FFF, 0x2000, 0x1FFFFF, 0x3FFFFF}

for k, fs in enumerate(starts):
    end = starts[k + 1] if k + 1 < len(starts) else T1
    end = min(end, fs + 0x8000)
    off = va2off(fs)
    if off is None:
        continue
    code = raw[off:off + (end - fs)]
    prev = collections.deque(maxlen=4)   # (mnemonic, op_str)
    misses = 0
    for insn in md.disasm(code, fs):
        m, o = insn.mnemonic, insn.op_str
        if m == "int3":
            misses += 1
            if misses > 6:
                break
        else:
            misses = 0
        if m == "call":
            const = None
            for pm, po in reversed(prev):
                if pm == "push":
                    try:
                        const = int(po, 0)
                    except ValueError:
                        const = None
                    break
            try:
                callee = int(o, 0)
            except ValueError:
                callee = None
            call_sites.append((insn.address, callee, const))
            site_fn[insn.address] = fs
        elif m in ("cmp", "sub", "add", "test") and "," in o:
            try:
                imm = int(o.rsplit(",", 1)[1].strip(), 0)
                if imm in BOUND:
                    cmp_imm.append((insn.address, imm, m))
                    site_fn[insn.address] = fs
            except ValueError:
                pass
        elif m in ("shl", "shr", "sar", "and", "or") and "," in o:
            try:
                imm = int(o.rsplit(",", 1)[1].strip(), 0)
                if imm in (0x0A, 0x0B, 0x0C, 0x0D, 0x15, 0x16, 0x1F, 0x1FFFFF, 0x3FFFFF):
                    shift_imm.append((insn.address, imm, m))
                    site_fn[insn.address] = fs
            except ValueError:
                pass
        prev.append((m, o))

# ---------- 3. group by callee ----------
by_callee = collections.defaultdict(list)
for site, callee, const in call_sites:
    if callee is None:
        continue
    by_callee[callee].append((site, const))

prim = []
for callee, sites in by_callee.items():
    consts = [c for _, c in sites if c is not None and 0 < c <= 32]
    if len(consts) < 12:
        continue
    hist = collections.Counter(consts)
    prim.append(dict(callee=callee, rva=callee - BASE, sites=len(sites),
                     const_sites=len(consts), widths=dict(sorted(hist.items()))))
prim.sort(key=lambda d: -d["const_sites"])

# ---------- 4. functions that read two 11-bit fields ----------
prim_ids = {p["callee"] for p in prim[:8]}
reads = collections.defaultdict(list)     # function -> [(site, callee, width)]
for site, callee, const in call_sites:
    if callee in prim_ids and const is not None and const in (11, 21, 12, 10):
        reads[site_fn.get(site)].append((site, callee, const))

double11 = []
for fn, items in reads.items():
    w11 = [x for x in items if x[2] == 11]
    if len(w11) >= 2:
        # the two reads must be close together to belong to one message header
        w11.sort()
        for a, b in zip(w11, w11[1:]):
            if b[0] - a[0] <= 0x80:
                double11.append(dict(fn=fn, rva=fn - BASE,
                                     first=hex(a[0]), second=hex(b[0]),
                                     span=b[0] - a[0]))
                break
double11.sort(key=lambda d: d["rva"])

# ---------- 5. emit ----------
os.makedirs(DATA, exist_ok=True)
with open(os.path.join(DATA, "netproto_primitives.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["callee_va", "callee_rva", "call_sites", "constant_width_sites", "width_histogram"])
    for p in prim[:40]:
        w.writerow([hex(p["callee"]), hex(p["rva"]), p["sites"], p["const_sites"],
                    " ".join("%d:%d" % kv for kv in p["widths"].items())])

with open(os.path.join(DATA, "netproto_width_sites.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["site_va", "site_rva", "function_va", "callee_va", "width_bits", "kind"])
    for site, callee, const in sorted(call_sites):
        if callee in prim_ids and const is not None and const in (10, 11, 12, 21, 22):
            w.writerow([hex(site), hex(site - BASE), hex(site_fn.get(site, 0)),
                        hex(callee), const, "bitfield"])

summary = dict(
    artifact=dict(path=SRC, sha256=hashlib.sha256(raw).hexdigest()),
    text=dict(va_start=hex(T0), va_end=hex(T1), functions=len(starts),
              call_sites=len(call_sites)),
    primitives=prim[:12],
    double11_functions=double11[:40],
    counts=dict(
        width11=sum(1 for s, c, k in call_sites if k == 11),
        width12=sum(1 for s, c, k in call_sites if k == 12),
        width21=sum(1 for s, c, k in call_sites if k == 21),
        width22=sum(1 for s, c, k in call_sites if k == 22),
        width10=sum(1 for s, c, k in call_sites if k == 10),
        bound_imm={hex(k): sum(1 for _, v, _ in cmp_imm if v == k)
                   for k in sorted({v for _, v, _ in cmp_imm})},
    ),
)
print(json.dumps(summary, indent=1))
