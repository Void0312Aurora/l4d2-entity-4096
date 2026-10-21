#!/usr/bin/env python3
"""server.dll unified migration manifest  (v2, read-only).

Fixes vs v1:
  - .simthnk section name (<=8 bytes), VA = 0x109A3000, SizeOfImage = 0x9A8000
  - explicit new HIGHLOW relocation block
  - dedupe key = (rva, operand_offset, size) with drop logging
  - A10-vec restricted to functions proven to receive this=&g_SimThinkManager
  - every entry carries an evidence string
"""
import struct, json, hashlib, csv, os, collections, bisect

from config import require, SERVER_DLL, OUT, MANIFESTS
DLL = require(SERVER_DLL)

BASE = 0x10000000
OLD_GL, NEW_GL = 0x107E0760, 0x10982000
OLD_ST, NEW_ST = 0x1075E9E0, 0x109A3000
D_GL, D_ST = 0x10000, 0x2000

d = open(DLL, "rb").read()
SHA = hashlib.sha256(d).hexdigest()
e = struct.unpack_from("<I", d, 0x3c)[0]; coff = e + 4
nsec = struct.unpack_from("<H", d, coff + 2)[0]
osz = struct.unpack_from("<H", d, coff + 16)[0]
opt = coff + 20
sa = struct.unpack_from("<I", d, opt + 32)[0]
secs = []
for i in range(nsec):
    b = opt + osz + i * 40
    nm = d[b:b+8].rstrip(b"\0").decode(); vsz, va, rs, pr = struct.unpack_from("<IIII", d, b+8)
    secs.append((nm, va, vsz, rs, pr))
def vo(va):
    r = va - BASE
    for nm, v, vsz, rs, pr in secs:
        if v <= r < v + max(vsz, rs): return pr + (r - v)
def va_of(off):
    for nm, v, vsz, rs, pr in secs:
        if pr <= off < pr + rs: return BASE + v + (off - pr)
T = [s for s in secs if s[0] == ".text"][0]
T0, T1 = T[4], T[4] + T[3]

rrva, rsz = struct.unpack_from("<II", d, opt + 96 + 5*8)
p0 = vo(BASE + rrva); pp = p0; end = p0 + rsz; rel = []
while pp + 8 <= end:
    page, bsz = struct.unpack_from("<II", d, pp)
    if bsz < 8: break
    for i in range((bsz-8)//2):
        ent = struct.unpack_from("<H", d, pp + 8 + i*2)[0]
        if (ent >> 12) == 3: rel.append(page + (ent & 0xFFF))
    pp += bsz

P = []
def add(foff, old, new, cid, evidence, rva=None):
    P.append(dict(id=cid, rva=(va_of(foff) - BASE) if rva is None else rva,
                  file_offset=foff, old=bytes(old).hex(), new=bytes(new).hex(),
                  size=len(old), evidence=evidence))

# --- object absolute references ---
for r in rel:
    va = BASE + r; o = vo(va)
    if o is None: continue
    v = struct.unpack_from("<I", d, o)[0]
    if OLD_GL <= v < OLD_GL + 0x10038:
        off = v - OLD_GL; new = NEW_GL + off + (D_GL if off >= 0x10004 else 0)
        add(o, struct.pack("<I", v), struct.pack("<I", new), "A1-glref", "reloc target off=0x%05X" % off)
    elif OLD_ST <= v < OLD_ST + 0x2018:
        off = v - OLD_ST; new = NEW_ST + off + (D_ST if off >= 0x2004 else 0)
        add(o, struct.pack("<I", v), struct.pack("<I", new), "A10-stref", "reloc target off=0x%05X" % off)

# --- member displacements ---
for row in csv.DictReader(open(os.path.join(OUT, "member_offsets.csv"))):
    if row["classification"] == "confirm_entity_list":
        site = int(row["site_va"], 16); off = int(row["old_offset"], 16); o = vo(site)
        m = d[o+1]; do = o + (3 if (m & 7) == 4 else 2)
        if struct.unpack_from("<I", d, do)[0] == off:
            add(do, struct.pack("<I", off), struct.pack("<I", off + D_GL), "A3-gldisp",
                "this+0x%05X in entity-list method" % off)
    elif row["classification"] == "offset_immediate":
        site = int(row["site_va"], 16); off = int(row["old_offset"], 16); o = vo(site)
        ln = 5 if d[o] in (0x05,0x2D,0x3D,0x68,0xB8,0xB9,0xBA,0xBB,0xBC,0xBD,0xBE,0xBF) else 6
        add(o + ln - 4, struct.pack("<I", off), struct.pack("<I", off + D_GL), "A4-glimm", "member offset imm32")

# --- ctor constants ---
add(vo(0x100B78B8)+1, struct.pack("<I",0x1000), struct.pack("<I",0x2000), "A7-ctor", "num entries 4096->8192")
add(vo(0x100B78DF)+2, struct.pack("<I",0x801C), struct.pack("<I",0x1001C), "A7-ctor", "free pool base 0x801->0x1001")
add(vo(0x100B78E5)+1, struct.pack("<I",0x7FF), struct.pack("<I",0xFFF), "A7-ctor", "free pool count 2047->4095")

# --- thresholds ---
for fn in (0x100B7970, 0x100B7A30, 0x100B62E0):
    o = vo(fn)
    for k in range(0x180):
        if d[o+k:o+k+6] == b"\x81\xfb\x00\x08\x00\x00":
            add(o+k+2, struct.pack("<I",0x800), struct.pack("<I",0x1000), "A8-thresh",
                "network bound in 0x%X" % fn)

# --- handle width ---
for site in (0x100B79A5, 0x100B7A86, 0x100B7BA3, 0x100B7C65):
    o = vo(site)
    if d[o+2] == 0x0C:
        add(o+2, b"\x0c", b"\x0d", "A9-shl", "list-API handle pack")
for pat, n in ((b"\x25\xff\x0f\x00\x00",1),(b"\x81\xe1\xff\x0f\x00\x00",2),
               (b"\x81\xe2\xff\x0f\x00\x00",2),(b"\x81\xe6\xff\x0f\x00\x00",2),
               (b"\x81\xe7\xff\x0f\x00\x00",2)):
    j = T0
    while True:
        j = d.find(pat, j)
        if j < 0 or j >= T1: break
        if struct.pack("<I", OLD_GL + 4) in d[j:j+24]:
            add(j+n, struct.pack("<I",0xFFF), struct.pack("<I",0x1FFF), "A9-mask",
                "handle->index mask followed by array access")
        j += 1
# OnAddEntity / OnRemoveEntity: handle & 0xFFF used for m_iHighestEnt
for fn, rng in ((0x100B5820, 0xC0), (0x100B5890, 0xC0)):
    o = vo(fn)
    for k in range(rng):
        if d[o+k:o+k+5] == b"\x25\xff\x0f\x00\x00":
            add(o+k+1, struct.pack("<I",0xFFF), struct.pack("<I",0x1FFF), "A9-mask",
                "listener callback handle index mask in 0x%X" % fn)
        if d[o+k:o+k+6] in (b"\x81\xe1\xff\x0f\x00\x00", b"\x81\xe2\xff\x0f\x00\x00",
                            b"\x81\xe6\xff\x0f\x00\x00", b"\x81\xe7\xff\x0f\x00\x00"):
            add(o+k+2, struct.pack("<I",0xFFF), struct.pack("<I",0x1FFF), "A9-mask",
                "listener callback handle index mask in 0x%X" % fn)

o = vo(0x100B7CA0); j = d.find(b"\x25\xff\x0f\x00\x00", o)
if 0 < j < o + 0x40:
    add(j+1, struct.pack("<I",0xFFF), struct.pack("<I",0x1FFF), "A9-mask", "RemoveEntity(handle & 0xFFF)")
add(vo(0x104CF65C)+2, struct.pack("<I",0xFFF),  struct.pack("<I",0x1FFF),  "A9-h9", "H9 index mask")
add(vo(0x104CF662)+2, struct.pack("<I",0x800),  struct.pack("<I",0x1000),  "A9-h9", "H9 network bound")
add(vo(0x104CF66E)+2, struct.pack("<I",0x1000), struct.pack("<I",0x2000),  "A9-h9", "H9 total bound")
add(vo(0x104CF68B)+2, b"\x0c", b"\x0d", "A9-h9", "H9 serial << 13")
add(vo(0x104CF697)+1, struct.pack("<I",0x3FF000), struct.pack("<I",0x7FE000), "A9-h9", "H9 serial compare mask")

# S11: release-path (RemoveEntityAtSlot 0x100B7970)
o = vo(0x100B79A5)
assert d[o:o+3] == b"\xc1\xe1\x0c", d[o:o+3].hex()
add(o+2, b"\x0c", b"\x0d", "S11-rel", "RemoveEntityAtSlot: handle pack serial<<12 -> <<13")
o = vo(0x100B7A06)
assert d[o:o+6] == b"\x81\xfb\x00\x08\x00\x00", d[o:o+6].hex()
add(o+2, struct.pack("<I",0x800), struct.pack("<I",0x1000), "S11-rel", "RemoveEntityAtSlot: non-network boundary 0x800 -> 0x1000")

# S10: serial extraction shr reg,0xC paired with an A9-mask site
a9_offs = [p["file_offset"] for p in P if p["id"] == "A9-mask"]
j = T0
while True:
    j = d.find(b"\x0c", j)
    if j < 0 or j >= T1: break
    if d[j-2] == 0xc1 and 0xe8 <= d[j-1] <= 0xef and (d[j-1] & 0x38) == 0x28:
        if any(abs(j - m) <= 32 for m in a9_offs):
            add(j, b"\x0c", b"\x0d", "S10-shr", "serial = handle >> 12 -> >> 13 (paired with index mask)")
    j += 1

# --- simthink: Clear count, vector members ---
j = d.find(b"\xb9\x00\x08\x00\x00", vo(0x100B62E0))
add(j+1, struct.pack("<I",0x800), struct.pack("<I",0x1000), "A10-clear", "Clear() fills 0x4000 bytes")

st_t = []
j = T0
while True:
    j = d.find(b"\xb9" + struct.pack("<I", OLD_ST), j)
    if j < 0 or j >= T1: break
    w = d[j+5:j+25]; k = w.find(b"\xe8")
    if k >= 0:
        st_t.append(va_of(j+5+k+5) + struct.unpack_from("<i", d, j+5+k+1)[0])
    j += 1
st_t = sorted(set(st_t))
def st_owner(va):
    i = bisect.bisect_right(st_t, va) - 1
    if i < 0: return None
    t = st_t[i]
    if va - t > 0x2000 or b"\xcc\xcc\xcc" in d[vo(t):vo(va)]: return None
    return t

for off in (0x2004, 0x2008, 0x200C, 0x2010, 0x2014):
    pat = struct.pack("<I", off); j = T0
    while True:
        j = d.find(pat, j)
        if j < 0 or j >= T1: break
        va = va_of(j)
        if 0x100B5C00 <= va < 0x100B6E00:
            # RemoveEntinfoIndex: ECX is never reloaded; 0x100B5CA7 proves ECX==this
            if 0x100B5CA0 <= va < 0x100B5D09:
                add(j, pat, struct.pack("<I", off + D_ST), "A10-vec",
                    "m_simThinkList[+0x%X] in RemoveEntinfoIndex 0x100B5CA0 (ECX uniform with 0x100B5CA7)" % off)
                j += 1; continue
            ow = st_owner(va)
            if ow is not None:
                add(j, pat, struct.pack("<I", off + D_ST), "A10-vec",
                    "m_simThinkList[+0x%X] in fn 0x%X (this=simthink proven)" % (off, ow))
            else:
                add(j, pat, struct.pack("<I", off + D_ST), "B-vec", "owner unproven for 0x%X" % off)
        j += 1

# --- dedupe by (rva, operand_offset, size) ---
seen = {}; drops = []
for p in P:
    k = (p["rva"], p["file_offset"], p["size"])
    if k in seen:
        drops.append(dict(dropped=p["id"], kept=seen[k]["id"], rva=hex(p["rva"]), reason=p["evidence"]))
        continue
    seen[k] = p
P = sorted(seen.values(), key=lambda x: x["file_offset"])

A = [p for p in P if not p["id"].startswith("B-")]
Bp = [p for p in P if p["id"].startswith("B-")]

manifest = dict(
    module="server.dll", sha256=SHA, size=len(d),
    section_alignment=hex(sa),
    sections=[
        dict(name=".entlist", rva=0x982000, va=NEW_GL, virtual_size=0x20038, size_of_raw_data=0,
             initialized="runtime ctor (0x105859B1 writes vptr)"),
        dict(name=".simthnk", rva=0x9A3000, va=NEW_ST, virtual_size=0x4018, size_of_raw_data=0x200,
             initialized="static vptr 0x105F3A94 + 1 HIGHLOW"),
    ],
    size_of_image_new=0x9A8000,
    new_reloc_block=dict(page_rva=0x9A3000, size_of_block=0x0C,
                         entries=["0x3000 HIGHLOW offset 0", "0x0000 ABSOLUTE pad"]),
    objects={
        "CGlobalEntityList": dict(old=OLD_GL, new=NEW_GL, size_old=0x10038, size_new=0x20038),
        "CSimThinkManager":  dict(old=OLD_ST, new=NEW_ST, size_old=0x2018, size_new=0x4018),
    },
    counts=dict(A=len(A), B=len(Bp), total=len(P), **collections.Counter(p["id"] for p in A)),
    dedupe_drops=drops,
    class_B=[dict(id=p["id"], rva=hex(p["rva"]), evidence=p["evidence"]) for p in Bp],
    patches=A,
)
json.dump(manifest, open(os.path.join(MANIFESTS, "server.json"), "w"), indent=1)

# --- validate: apply A only, check bytes ---
buf = bytearray(d); bad = 0
for p in A:
    o = p["file_offset"]; old = bytes.fromhex(p["old"])
    if buf[o:o+len(old)] != old:
        bad += 1; print("MISMATCH", p["id"], hex(o)); continue
    buf[o:o+len(bytes.fromhex(p["new"]))] = bytes.fromhex(p["new"])
diff = [i for i in range(len(d)) if buf[i] != d[i]]
print("sha256=%s" % SHA)
print("A=%d  B=%d  total=%d  dedupe_drops=%d" % (len(A), len(Bp), len(P), len(drops)))
print("mismatch=%d changed_bytes=%d" % (bad, len(diff)))
print("counts:", dict(collections.Counter(p["id"] for p in A)))
