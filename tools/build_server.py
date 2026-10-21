#!/usr/bin/env python3
"""Build an isolated patched copy of server.dll (workshop only).

Applies manifest.server.json A-class patches + PE surgery:
  - two new sections (.entlist BSS, .simthnk initialized 0x200 bytes at EOF)
  - appends the 12-byte HIGHLOW block inside .reloc slack
  - updates NumberOfSections, SizeOfImage, reloc dir size, checksum
Writes ./out/server.4096.dll and a verification log. Never touches the game install.
"""
import struct, json, hashlib, os


from config import require, SERVER_DLL
SRC = require(SERVER_DLL)

DST = os.path.join(OUTDIR, "server.4096.dll")

d = bytearray(open(SRC, "rb").read())
man = json.load(open(os.path.join(MANIFESTS, "server.json")))
assert hashlib.sha256(d).hexdigest() == man["sha256"]

e = struct.unpack_from("<I", d, 0x3c)[0]
nsec = struct.unpack_from("<H", d, e+6)[0]
soh  = struct.unpack_from("<H", d, e+20)[0]
opt  = e + 24
sec_align, file_align = struct.unpack_from("<II", d, opt+32)
size_image = struct.unpack_from("<I", d, opt+56)[0]
dd = opt + 96
rel_rva, rel_size = struct.unpack_from("<II", d, dd+5*8)

secs = []
for i in range(nsec):
    b = opt + soh + i*40
    nm = d[b:b+8].rstrip(b"\0").decode()
    vsz, va, rs, pr = struct.unpack_from("<IIII", d, b+8)
    secs.append(dict(name=nm, vsz=vsz, va=va, rs=rs, pr=pr, hdr=b))

def align(v, a): return (v + a - 1)//a*a

# ---- 1. apply operand patches ----
bad = 0
for p in man["patches"]:
    o = p["file_offset"]; old = bytes.fromhex(p["old"]); new = bytes.fromhex(p["new"])
    if d[o:o+len(old)] != old: bad += 1; continue
    d[o:o+len(old)] = new
assert bad == 0, bad

# ---- 2. reloc: append block into .reloc slack ----
rel_sec = [s for s in secs if s["va"] <= rel_rva < s["va"]+max(s["vsz"], s["rs"])][0]
rel_pr = rel_sec["pr"] + (rel_rva - rel_sec["va"])
slack = rel_sec["rs"] - rel_size
assert slack >= 12, slack
struct.pack_into("<IIHH", d, rel_pr + rel_size, 0x9A3000, 0x0C, 0x3000, 0x0000)
struct.pack_into("<I", d, dd + 5*8 + 4, rel_size + 12)

# ---- 3. .simthnk raw at EOF (aligned) ----
raw_off = align(len(d), file_align)
if raw_off > len(d): d += b"\0" * (raw_off - len(d))
sim_pr = raw_off
d += b"\0" * 0x200
struct.pack_into("<I", d, sim_pr, 0x105F3A94)     # vptr (relocated by new HIGHLOW block)

# ---- 4. two section headers ----
first_raw = min(s["pr"] for s in secs if s["rs"] > 0)
assert opt + soh + (nsec+2)*40 <= min(first_raw, struct.unpack_from("<I", d, opt+60)[0])
new_secs = [
    (".entlist", 0x20038, 0x982000, 0, 0,        0xE0000040),
    (".simthnk", 0x4018,  0x9A3000, 0x200, sim_pr, 0x40000040),
]
for i, (nm, vsz, va, rs, pr, ch) in enumerate(new_secs):
    b = opt + soh + (nsec+i)*40
    struct.pack_into("<8sIIIIIIHHI", d, b, nm.encode(), vsz, va, rs, pr, 0,0,0,0, ch)

struct.pack_into("<H", d, e+6, nsec+2)
soi = align(0x9A3000 + 0x4018, sec_align)      # 0x9A8000
struct.pack_into("<I", d, opt+56, soi)

# ---- 5. checksum ----
ck_off = opt + 64
struct.pack_into("<I", d, ck_off, 0)
ck = 0; n = len(d)
for i in range(0, n - (n % 2), 2):
    if i == ck_off or i == ck_off+2: continue
    ck = (ck + struct.unpack_from("<H", d, i)[0]) & 0xFFFFFFFF
    ck = (ck & 0xFFFF) + (ck >> 16)
if n % 2:
    ck = (ck + d[-1]) & 0xFFFFFFFF
    ck = (ck & 0xFFFF) + (ck >> 16)
ck = (ck & 0xFFFF) + (ck >> 16)
checksum = (ck + n) & 0xFFFFFFFF
struct.pack_into("<I", d, ck_off, checksum)

open(DST, "wb").write(d)

# ---- 6. verify by re-parsing the written file ----
v = open(DST, "rb").read()
assert struct.unpack_from("<H", v, e+6)[0] == nsec + 2
assert struct.unpack_from("<I", v, opt+56)[0] == 0x9A8000
assert struct.unpack_from("<I", v, dd+5*8+4)[0] == rel_size + 12
b = opt + soh + (nsec+1)*40
nm, vsz, va, rs, pr = struct.unpack_from("<8sIIII", v, b)
assert nm.rstrip(b"\0") == b".simthnk" and va == 0x9A3000 and struct.unpack_from("<I", v, pr)[0] == 0x105F3A94
# reloc block visible
ok = False; p = rel_pr
while p + 8 <= rel_pr + rel_size + 12:
    page, bsz = struct.unpack_from("<II", v, p)
    if page == 0x9A3000 and bsz == 0xC: ok = True; break
    p += bsz
assert ok
print("wrote", DST)
print("size 0x%X  sha256 %s" % (len(v), hashlib.sha256(v).hexdigest()))
print("SizeOfImage 0x%X  sections %d  checksum 0x%X" % (0x9A8000, nsec+2, checksum))
print("patches applied: %d" % len(man["patches"]))
