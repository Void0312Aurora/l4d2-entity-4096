#!/usr/bin/env python3
"""client.dll 8192-slot migration manifest (read-only analysis + manifest emit)."""
import struct, json, hashlib, os, collections, bisect


from config import require, CLIENT_DLL
SRC = require(CLIENT_DLL)
d = bytearray(open(SRC, "rb").read())

e = struct.unpack_from("<I", d, 0x3c)[0]; coff = e + 4
nsec = struct.unpack_from("<H", d, coff + 2)[0]
osz = struct.unpack_from("<H", d, coff + 16)[0]
opt = coff + 20
BASE = struct.unpack_from("<I", d, opt + 28)[0]
secs = []
for i in range(nsec):
    b = opt + osz + i * 40
    nm = d[b:b+8].rstrip(b"\0").decode()
    vsz, va, rs, pr = struct.unpack_from("<IIII", d, b + 8)
    secs.append((nm, va, vsz, rs, pr))
def vo(va):
    r = va - BASE
    for nm, v, vsz, rs, pr in secs:
        if v <= r < v + max(vsz, rs): return pr + (r - v)
def va_of(off):
    for nm, v, vsz, rs, pr in secs:
        if pr <= off < pr + rs: return BASE + v + (off - pr), nm
    return None, None
T = [s for s in secs if s[0] == ".text"][0]
T0, T1 = T[4], T[4] + T[3]

OLD_CL = 0x1073A560
DELTA1, DELTA2 = 0x10000, 0x8000
NEW_CL = 0x10963000          # RVA 0x963000 (first free after .reloc)
SIZE_OLD, SIZE_NEW = 0x180A8, 0x300A8

# ---- seeds ----
SEED = [0x100BB500, 0x100BB3F0, 0x100B9960, 0x100BB7F0, 0x100BB9E0]
def vtable_targets(vt, limit=64):
    out = []
    for i in range(limit):
        v = struct.unpack_from("<I", d, vo(vt) + i * 4)[0]
        if not (BASE + 0x1000 <= v < BASE + 0x528000): break
        out.append(v)
    return out
SEED += vtable_targets(0x10564B8C) + vtable_targets(0x10564B60)
SEED = sorted(set(SEED))

def callers_of(tgt, limit=0x20000):
    out = []
    j = T0
    while True:
        j = d.find(b"\xe8", j)
        if j < 0 or j >= T1: break
        rel = struct.unpack_from("<i", d, j + 1)[0]
        nxt = va_of(j + 5)[0]
        if nxt and nxt + rel == tgt:
            out.append(nxt)
        j += 1
    return out

seed_set = set(SEED)
lvl2 = set()
for s in SEED:
    for c in callers_of(s):
        lvl2.add(c - 5 if False else c)
METHODS = sorted(seed_set | lvl2)
print("seed=%d  expanded=%d" % (len(seed_set), len(METHODS)))

# ---- instruction scan inside methods ----
BASE_REG = ["eax","ecx","edx","ebx","esp","ebp","esi","edi"]
MEMOP = {0x8b,0x89,0x8d,0x3b,0x39,0x03,0x0b,0xc7,0xc6,0x80,0x83,0x85,0xff,0x01,0x09,0x2b,0x29,0x8f}
addrs = [(vo(f), f) for f in METHODS]
starts = [a for a, f in addrs]

def owner(va):
    o = vo(va)
    i = bisect.bisect_right(starts, o) - 1
    if i < 0: return None
    s, f = addrs[i]
    if o - s > 0x6000: return None
    return f

patches = []
PEND = []
def add(foff, old, new, cid, ev):
    patches.append(dict(id=cid, rva=va_of(foff)[0] - BASE, file_offset=foff,
                        old=bytes(old).hex(), new=bytes(new).hex(), size=len(old), evidence=ev))

# scan every method body for mod=10 disp32 accesses
seen_site = set()
for f in METHODS:
    o = vo(f)
    for k in range(0, 0x4000):
        j = o + k
        if j + 6 > T1: break
        if d[j] not in MEMOP: continue
        m = d[j+1]
        if (m >> 6) != 2: continue
        if (m & 7) == 4: continue
        disp = struct.unpack_from("<I", d, j+2)[0]
        if disp < 0x10004 or disp >= SIZE_OLD: continue
        if j in seen_site: continue
        seen_site.add(j)
        reg = BASE_REG[m & 7]
        delta = DELTA1 if disp < 0x1803C else DELTA2
        add(j+2, struct.pack("<I", disp), struct.pack("<I", disp+delta), "C6-member",
            "fn 0x%X base=%s off=0x%X" % (f, reg, disp))

# C1: absolute refs into object range
rrva, rsz = struct.unpack_from("<II", d, opt + 96 + 5*8)
p0 = None
for nm, vv, vsz, rs, pr in secs:
    if vv <= rrva < vv + rs: p0 = pr + (rrva - vv)
pp = p0; endp = p0 + rsz
while pp + 8 <= endp:
    page, bsz = struct.unpack_from("<II", d, pp)
    if bsz < 8: break
    for i in range((bsz-8)//2):
        ent = struct.unpack_from("<H", d, pp + 8 + i*2)[0]
        if (ent >> 12) != 3: continue
        a = page + (ent & 0xFFF)
        oo = None
        for nm, vv, vsz, rs, pr in secs:
            if vv <= a < vv + max(vsz,1): oo = pr + (a - vv)
        if oo is None: continue
        v = struct.unpack_from("<I", d, oo)[0]
        if OLD_CL <= v < OLD_CL + SIZE_OLD:
            off = v - OLD_CL
            if off == 0x10014:
                tgt = NEW_CL + 0x20014          # secondary interface moves with the object
                cid = "C1-interface"
            else:
                tgt = NEW_CL + off
                cid = "C1-global"
            add(oo, struct.pack("<I", v), struct.pack("<I", tgt), cid, "object ref off=0x%X" % off)
    pp += bsz

# C3/C4/C2: all 0x10014 operands, classified by modrm at j-1 and opcode at j-2
j = T0
PRI = {"C5":5,"C1":5,"C2":4,"C3":3,"C4":2,"C6":1}
while True:
    j = d.find(struct.pack("<I", 0x10014), j)
    if j < 0 or j >= T1: break
    op = d[j-2]; m = d[j-1]
    if (m >> 6) == 2 and op == 0x8b:
        add(j, b"\x14\x00\x01\x00", struct.pack("<I",0x20014), "C4-vtload", "load [reg+0x10014]")
    elif (m >> 6) == 2 and op == 0x8d:
        add(j, b"\x14\x00\x01\x00", struct.pack("<I",0x20014), "C3-this", "lea reg,[reg+0x10014]")
    elif m >= 0xC0 and op == 0x81 and ((m >> 3) & 7) == 0:
        add(j, b"\x14\x00\x01\x00", struct.pack("<I",0x20014), "C3-this", "add reg,0x10014")
    elif (m >> 6) == 2 and op == 0xc7:
        add(j, b"\x14\x00\x01\x00", struct.pack("<I",0x20014), "C2-vptr", "write [reg+0x10014]")
    j += 1

# C5: RTTI
add(vo(0x1068E298), struct.pack("<I",0x10014), struct.pack("<I",0x20014), "C5-col", "COL#2 offset")
add(vo(0x1068E280), struct.pack("<I",0x10014), struct.pack("<I",0x20014), "C5-bcd", "BCD mdisp (IClientEntityList)")

# C7: network bound compares  cmp reg,0x7FF -> 0xFFF
j = T0
while True:
    j = d.find(b"\xff\x07\x00\x00", j)
    if j < 0 or j >= T1: break
    op = d[j-2]; m = d[j-1]
    if (op == 0x81 and (m >> 6) == 3 and ((m >> 3) & 7) == 7) or op == 0x3d:
        va = va_of(j)[0]
        if va in (0x100BB8D6, 0x100BB9F3):
            add(j, b"\xff\x07\x00\x00", struct.pack("<I",0xFFF), "C7-bound", "network bound 2048->4096 (confirmed)")
        else:
            PEND.append(dict(id="P7-bound", rva=(va-BASE) if isinstance(va,int) else None, evidence="cmp 0x7FF semantic unproven"))
    j += 1

# C12: RemoveEntity(handle) mask (missed by the C9 pattern: no add/lea)
o = vo(0x100EA997)
assert d[o:o+4] == b"\xff\x0f\x00\x00", d[o:o+4].hex()
add(o, b"\xff\x0f\x00\x00", struct.pack("<I",0x1FFF), "C9-mask", "RemoveEntity(handle & 0xFFF) -> 0x1FFF")

# C11: client RemoveEntityAtSlot 0x100EA660
o = vo(0x100EA695)
assert d[o:o+3] == b"\xc1\xe1\x0c", d[o:o+3].hex()
add(o+2, b"\x0c", b"\x0d", "C11-rel", "RemoveEntityAtSlot: handle pack <<12 -> <<13")
o = vo(0x100EA6F6)
print("release cmp bytes:", d[o:o+8].hex(" "))
assert d[o:o+2] == b"\x81\xfb" and struct.unpack_from("<I", d, o+2)[0] == 0x800, d[o:o+6].hex()
add(o+2, struct.pack("<I",0x800), struct.pack("<I",0x1000), "C11-rel", "RemoveEntityAtSlot: non-network boundary 0x800 -> 0x1000")

# C9: handle index decode  and REG,0xFFF ; add REG,REG ; lea [base+REG*8]
c9_offs = []
j = T0
while True:
    j = d.find(b"\xff\x0f\x00\x00", j)
    if j < 0 or j >= T1: break
    op = d[j-2]; m = d[j-1]
    if (op == 0x81 and (m >> 6) == 3 and ((m >> 3) & 7) == 4) or op == 0x25:
        reg = 0 if op == 0x25 else (m & 7)
        w = d[j+4:j+48]
        if (bytes([0x03, 0xc0|((reg<<3)&0x38)|reg]) in w or bytes([0x03, reg|((reg<<3)&0x38)]) in w) \
           and bytes([0x8d, 0x4c, 0xca]) in w[:16]:
            add(j, b"\xff\x0f\x00\x00", struct.pack("<I",0x1FFF), "C9-mask", "handle index decode -> &CEntInfo[idx]")
            c9_offs.append(j)
    j += 1

# C10: serial extraction shr reg,0xC paired with a C9 decode
j = T0
while True:
    j = d.find(b"\x0c", j)
    if j < 0 or j >= T1: break
    if d[j-2] == 0xc1 and 0xe8 <= d[j-1] <= 0xef and (d[j-1] & 0x38) == 0x28:
        if any(abs(j - m) <= 32 for m in c9_offs):
            add(j, b"\x0c", b"\x0d", "C10-shr", "serial = handle >> 12 -> >> 13 (paired with index decode)")
    j += 1

# B class (not patched): 0xFFF masks need dataflow
B = []
j = T0
while True:
    j = d.find(b"\xff\x0f\x00\x00", j)
    if j < 0 or j >= T1: break
    op = d[j-2]; m = d[j-1]
    if (op == 0x81 and (m >> 6) == 3 and ((m >> 3) & 7) == 4) or op == 0x25:
        B.append(dict(id="B-mask", rva=va_of(j)[0] - BASE, evidence="and reg,0xFFF needs dataflow"))
    j += 1

# C7-ctor: base class ctor constants (8192 slots, pool 0x1001, count 0xFFF)
add(vo(0x100EA5A8)+1, struct.pack("<I",0x1000), struct.pack("<I",0x2000), "C7-ctor", "slot count 4096->8192")
add(vo(0x100EA5CF)+2, struct.pack("<I",0x801C), struct.pack("<I",0x1001C), "C7-ctor", "free pool base 0x801->0x1001")
add(vo(0x100EA5D5)+1, struct.pack("<I",0x7FF), struct.pack("<I",0xFFF), "C7-ctor", "pool count 2047->4095")

# C8-handle: serial << 12 -> << 13 near entity array refs
for pat in (b"\xc1\xe0\x0c", b"\xc1\xe1\x0c", b"\xc1\xe2\x0c", b"\xc1\xe6\x0c", b"\xc1\xe7\x0c"):
    j = T0
    while True:
        j = d.find(pat, j)
        if j < 0 or j >= T1: break
        win = d[j:j+0x30] + d[max(0,j-0x30):j]
        if struct.pack("<I", 0x1003C) in win or struct.pack("<I", 0x10014) in win or struct.pack("<I", 0x1803C) in win:
            add(j+2, b"\x0c", b"\x0d", "C8-shl", "handle pack serial<<12")
        j += 1

# dedupe by (rva, file_offset, size)
seen = {}
drops = 0
prio = {"C1-interface":9,"C1-global":8,"C5-col":9,"C5-bcd":9,"C2-vptr":7,"C3-this":6,"C4-vtload":5,"C6-member":1,"C7-bound":6,"C7-ctor":7,"C8-shl":5,"C9-mask":4,"C10-shr":5,"C11-rel":6}
for p in patches:
    k = (p["file_offset"], p["size"])
    if k in seen:
        drops += 1
        if prio.get(p["id"],0) > prio.get(seen[k]["id"],0):
            seen[k] = p
        continue
    seen[k] = p
patches = sorted(seen.values(), key=lambda x: x["file_offset"])

# validate
buf = bytearray(d); bad = 0
for p in patches:
    o = p["file_offset"]; old = bytes.fromhex(p["old"])
    if bytes(buf[o:o+len(old)]) != old: bad += 1; continue
    buf[o:o+len(old)] = bytes.fromhex(p["new"])
diff = sum(1 for i in range(len(d)) if buf[i] != d[i])

assert all(len(x["name"]) <= 8 for x in [dict(name=".clentls")]), "section name > 8 bytes"
man = dict(module="client.dll", sha256=hashlib.sha256(d).hexdigest(), size=len(d),
           size_of_image_new=0x994000,
           sections=[dict(name=".clentls", rva=0x963000, va=NEW_CL, virtual_size=SIZE_NEW, size_of_raw_data=0)],
           objects=dict(CClientEntityList=dict(old=OLD_CL, new=NEW_CL, size_old=SIZE_OLD, size_new=SIZE_NEW)),
           methods=METHODS,
           counts=dict(total=len(patches), drops=drops, B_mask=len(B), **collections.Counter(p["id"] for p in patches)),
           patches=patches, class_B=B, pending=PEND)
json.dump(man, open(os.path.join(MANIFESTS, "client.json"), "w"), indent=1)
print("patches=%d drops=%d bad=%d changed_bytes=%d" % (len(patches), drops, bad, diff))
print(dict(collections.Counter(p["id"] for p in patches)))
