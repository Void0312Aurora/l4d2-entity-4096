#!/usr/bin/env python3
"""CGlobalEntityList migration audit — read-only, no patching.

Task A: per-site semantic analysis of member-displacement candidates
Task B: full absolute-reference audit of the old object range [0x107E0760,0x107F0798)
Task C: old->new migration mapping + machine-readable CSVs

Outputs: member_offsets.csv, object_references.csv, unresolved_references.csv
Nothing in the game install is written.
"""
import struct, csv, re, os, bisect

from config import require, SERVER_DLL
DLL = require(SERVER_DLL)
OUT = os.path.dirname(os.path.abspath(__file__))

BASE        = 0x10000000
OLD_BASE    = 0x107E0760
OLD_END     = 0x107F0798
OBJ_SIZE    = 0x10038
NEW_BASE    = 0x10982000          # placeholder: first free RVA after .reloc (0x982000)

REG = ["eax","ecx","edx","ebx","esp","ebp","esi","edi"]
MEMBER_OFFS = [0x10004,0x10008,0x1000C,0x10010,0x10014,0x10018,0x1001C,0x10020,
               0x10024,0x10028,0x1002C,0x10030,0x10034]
FIELD_NAME = {0x10004:"m_activeList.head", 0x10008:"m_activeList.tail",
              0x1000C:"m_freeNonNetworkableList.head", 0x10010:"m_freeNonNetworkableList.tail",
              0x10014:"m_iHighestEnt", 0x10018:"m_iNumEnts", 0x1001C:"m_iNumEdicts",
              0x10020:"m_bClearingEntities", 0x10024:"m_entityListeners.pMemory",
              0x10028:"m_entityListeners.nAllocationCount", 0x1002C:"m_entityListeners.nGrowSize",
              0x10030:"m_entityListeners.m_Size", 0x10034:"m_entityListeners.pElements"}

d = open(DLL, "rb").read()
e = struct.unpack_from("<I", d, 0x3c)[0]; coff = e + 4
nsec = struct.unpack_from("<H", d, coff + 2)[0]
osz  = struct.unpack_from("<H", d, coff + 16)[0]
opt  = coff + 20
soi  = struct.unpack_from("<I", d, opt + 56)[0]
secs = []
for i in range(nsec):
    b = opt + osz + i * 40
    nm = d[b:b+8].rstrip(b"\0").decode(); vsz, va, rs, pr = struct.unpack_from("<IIII", d, b+8)
    secs.append((nm, va, vsz, rs, pr))
def vo(va):
    r = va - BASE
    for nm,v,vsz,rs,pr in secs:
        if v <= r < v + max(vsz,rs): return pr + (r - v)
def va_of(off):
    for nm,v,vsz,rs,pr in secs:
        if pr <= off < pr + rs: return BASE + v + (off - pr), nm
    return None, None
def sec_of(va):
    r = va - BASE
    for nm,v,vsz,rs,pr in secs:
        if v <= r < v + max(vsz,rs): return nm
    return None
TEXT = [s for s in secs if s[0] == ".text"][0]
T0, T1 = BASE + TEXT[1], BASE + TEXT[1] + TEXT[2]

# ---------- relocations ----------
rrva, rsz = struct.unpack_from("<II", d, opt + 96 + 5 * 8)
p0 = vo(BASE + rrva); p = p0; end = p0 + rsz
relocs = []
while p + 8 <= end:
    page, bsz = struct.unpack_from("<II", d, p)
    if bsz < 8: break
    for i in range((bsz - 8) // 2):
        ent = struct.unpack_from("<H", d, p + 8 + i*2)[0]
        if (ent >> 12) == 3:
            relocs.append(page + (ent & 0xFFF))
    p += bsz
relocs.sort()
print(f"[init] relocs(HIGHLOW)={len(relocs)}  SizeOfImage=0x{soi:X}  NEW_BASE=0x{NEW_BASE:X}")

# ---------- Task B: absolute references into the old object range ----------
def new_addr(old):
    off = old - OLD_BASE
    if off < 0x10004:
        return NEW_BASE + off
    return NEW_BASE + off + 0x10000

def new_off(old):
    off = old - OLD_BASE
    return off if off < 0x10004 else off + 0x10000

obj_rows = []
for r in relocs:
    va = BASE + r
    o = vo(va)
    if o is None or o + 4 > len(d): continue
    val = struct.unpack_from("<I", d, o)[0]
    if OLD_BASE <= val < OLD_END:
        sec = sec_of(va) or "?"
        kind = "code" if sec == ".text" else ("data-table" if sec in (".data",".rdata") else sec)
        obj_rows.append(dict(loc_va=f"0x{va:08X}", section=sec, kind=kind,
                             target_old=f"0x{val:08X}", old_offset=f"0x{val-OLD_BASE:05X}",
                             new_offset=f"0x{new_off(val):05X}", target_new=f"0x{new_addr(val):08X}",
                             slot=("array" if 4 <= val-OLD_BASE < 0x10004 else "post-array")))
print(f"[B] absolute refs into object range: {len(obj_rows)}")
for grp in sorted(set(r['old_offset'] for r in obj_rows)):
    rows=[r for r in obj_rows if r['old_offset']==grp]
    if grp in ("0x00000","0x00004"): 
        print(f"    off {grp}: {len(rows)} refs")
    else:
        print(f"    off {grp}: {len(rows)} refs -> " + ", ".join(r['loc_va'] for r in rows[:8]))
from collections import Counter
print("    by kind:", Counter(r['kind'] for r in obj_rows))
print("    by old_offset:", Counter(r['old_offset'] for r in obj_rows).most_common(8))

# ---------- Task A: member displacement candidates ----------
# called-with-this set: B9 <OBJ> ... E8 rel32
OBJB = struct.pack("<I", OLD_BASE)
this_calls = []          # (call_va, target_va)
i = TEXT[4]
while True:
    i = d.find(b"\xb9" + OBJB, i)
    if i < 0: break
    site = va_of(i)[0]
    win = d[i+5:i+25]
    k = win.find(b"\xe8")
    if k >= 0:
        rel = struct.unpack_from("<i", d, i+5+k+1)[0]
        tgt = va_of(i+5+k+5)[0] + rel
        this_calls.append((site, tgt))
    i += 1
tgt_set = sorted(set(t for _, t in this_calls))
print(f"[A] mov ecx,OBJ; call 站点 {len(this_calls)}  -> 唯一目标函数 {len(tgt_set)}")

def find_owner(va):
    """nearest entity-list method whose body plausibly contains va"""
    k = bisect.bisect_right(tgt_set, va) - 1
    while k >= 0:
        t = tgt_set[k]
        if va - t > 0x2000: return None, None
        seg = d[vo(t):vo(va)]
        if b"\xcc\xcc\xcc" not in seg and b"\xc3\xcc" not in seg:
            sites = [s for s,tt in this_calls if tt == t]
            return t, sites[0]
        k -= 1
    return None, None

def decode_disp(disp_off):
    """find instruction whose disp32 field ends at disp_off"""
    for start in range(disp_off-7, disp_off-1):
        if start < TEXT[4]: continue
        b0 = d[start]
        if b0 in (0x8B,0x89,0x8A,0x88,0x03,0x01,0x0B,0x09,0x2B,0x29,0x23,0x21,
                  0x33,0x31,0x3B,0x39,0x85,0x8D,0x02,0x3A,0xC7,0xC6,0x80,0xFF,0x0F):
            if b0 == 0x0F:
                if d[start+1] not in (0xB6,0xB7,0xBE,0xBF): continue
                m = start + 2
            else:
                m = start + 1
            modrm = d[m]
            if (modrm >> 6) != 2: continue
            rm = modrm & 7
            if rm == 4:
                sib = d[m+1]; disp = m + 2; base = sib & 7
            else:
                sib = None; disp = m + 1; base = rm
            if disp != disp_off: continue
            ln = disp + 4 - start
            return start, ln, b0, modrm, sib, base
    return None

KNOWN_METHODS = [
    (0x100B7830, 0x100B7890, "AddToTail"),
    (0x100B7890, 0x100B7960, "ctor"),
    (0x100B7970, 0x100B7A2A, "RemoveEntityAtSlot"),
    (0x100B7A30, 0x100B7B6F, "Clear"),
    (0x100B7B70, 0x100B7BCF, "AddEntityAtSlot"),
    (0x100B7BD0, 0x100B7CA0, "AddNonNetworkableEntity"),
    (0x100B7CA0, 0x100B7CC0, "RemoveEntity"),
    (0x100B5820, 0x100B5890, "OnAddEntity(vtbl0)"),
    (0x100B5890, 0x100B5960, "OnRemoveEntity(vtbl1)"),
]
def known_method(va):
    for a,b,n in KNOWN_METHODS:
        if a <= va < b: return a, n
    return None, None

def traces_to_ecx(owner, site_va, base):
    """True if `base` provably holds the incoming this (ecx) at site_va."""
    if owner is None: return False
    if base == 1: return True                      # ecx directly
    lo, hi = vo(owner), vo(site_va)
    body = d[lo:hi]
    # mov r32, ecx  -> 8B /r with rm=001 and reg=base
    pat = bytes([0x8B, 0xC0 | (base << 3) | 0x01])
    ok = False
    k = 0
    while True:
        k = body.find(pat, k)
        if k < 0: break
        ok = True; k += 1
    # push ecx / pop base  -> 51 .. 5<base>
    if not ok:
        push = body.find(b"\x51")
        while push >= 0:
            seg = body[push:push+16]
            if bytes([0x58 | base]) in seg: ok = True; break
            push = body.find(b"\x51", push+1)
    return ok

def decode_imm(imm_off):
    """detect instruction whose imm32 == member offset (address arithmetic)"""
    p1 = d[imm_off-1]
    if p1 in (0x05,0x2D,0x3D,0x68,0xB8,0xB9,0xBA,0xBB,0xBC,0xBD,0xBE,0xBF):
        return imm_off-1, 5, p1
    if imm_off >= 2 and d[imm_off-2] in (0x81,0xC7):
        modrm = d[imm_off-1]
        if (modrm >> 6) == 3:          # register form -> genuine imm32
            return imm_off-2, 6, d[imm_off-2]
        return None                    # memory form -> matched bytes are disp8+imm
    return None

member_rows = []
for off in MEMBER_OFFS:
    pat = struct.pack("<I", off)
    j = 0
    while True:
        j = d.find(pat, j)
        if j < 0: break
        if j < TEXT[4] or j >= TEXT[4] + TEXT[3]:
            j += 1; continue
        va = va_of(j)[0]
        dec = decode_disp(j)
        if dec is None:
            idec = decode_imm(j)
            if idec is not None:
                istart, ilen, iop = idec
                insn_va = va_of(istart)[0]
                km, kmname = known_method(insn_va)
                member_rows.append(dict(site_va=f"0x{insn_va:08X}",
                                        function=(f"0x{km:08X}" if km else ""),
                                        instruction=f"{iop:02X} imm32=0x{off:05X}",
                                        bytes=d[istart:istart+ilen].hex(" "),
                                        base_reg="", field=FIELD_NAME.get(off,f"0x{off:05X}"),
                                        old_offset=f"0x{off:05X}",
                                        new_offset=f"0x{off+0x10000:05X}",
                                        provenance=(f"core_method:{kmname}" if km else ""),
                                        classification="offset_immediate",
                                        evidence="imm32 == member offset (address arithmetic); needs +0x10000"))
                j += 1; continue
            member_rows.append(dict(site_va=f"0x{va:08X}", function="", instruction="",
                                    bytes=d[j-4:j+8].hex(" "), base_reg="",
                                    field=FIELD_NAME.get(off,f"0x{off:05X}"),
                                    old_offset=f"0x{off:05X}", new_offset="",
                                    provenance="", classification="false_positive",
                                    evidence="bytes span two instructions (disp8 + imm32), not a disp32 operand"))
            j += 1; continue
        start, ln, b0, modrm, sib, base = dec
        insn_va = va_of(start)[0]
        owner, callsite = find_owner(insn_va)
        km, kmname = known_method(insn_va)
        if km is not None:
            owner = km; callsite = None
        breg = REG[base]
        traced = traces_to_ecx(owner, insn_va, base)
        if owner is not None and traced and callsite is None:
            prov = f"core_method:{kmname};fn0x{owner:08X};base={breg}<-ecx"
            cls = "confirm_entity_list"
        elif owner is not None and traced:
            prov = f"this=gEntList@0x{callsite:08X};fn0x{owner:08X};base={breg}<-ecx"
            cls = "confirm_entity_list"
        elif owner is not None:
            prov = f"fn0x{owner:08X};base={breg} not traced to ecx"
            cls = "unresolved"
        else:
            prov = ""
            cls = "unresolved"
        member_rows.append(dict(site_va=f"0x{insn_va:08X}",
                                function=(f"0x{owner:08X}" if owner else ""),
                                instruction=f"{b0:02X} {modrm:02X}" + (f" {sib:02X}" if sib is not None else "") + f" [disp=0x{off:05X}]",
                                bytes=d[start:start+ln].hex(" "),
                                base_reg=breg,
                                field=FIELD_NAME.get(off,f"0x{off:05X}"),
                                old_offset=f"0x{off:05X}",
                                new_offset=f"0x{off+0x10000:05X}" if cls=="confirm_entity_list" else "",
                                provenance=prov, classification=cls,
                                evidence=("base=ecx/other + owner function receives this=gEntList" if cls=="confirm_entity_list"
                                          else "cannot prove base register holds gEntList")))
        j += 1

print(f"[A] member-displacement candidates: {len(member_rows)}")
print("    classification:", Counter(r['classification'] for r in member_rows))
print("    by base reg:", Counter(r['base_reg'] for r in member_rows).most_common())

def dump(name, rows, cols):
    with open(os.path.join(OUT,name),"w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c:r.get(c,"") for c in cols})
    print(f"    wrote {name} ({len(rows)} rows)")

dump("member_offsets.csv", member_rows,
     ["site_va","function","instruction","bytes","base_reg","field","old_offset","new_offset",
      "provenance","classification","evidence"])
dump("object_references.csv", obj_rows,
     ["loc_va","section","kind","target_old","old_offset","new_offset","target_new","slot"])
unres = [r for r in member_rows if r["classification"] != "confirm_entity_list"]
dump("unresolved_references.csv", unres,
     ["site_va","function","instruction","bytes","base_reg","field","old_offset","provenance","classification","evidence"])
