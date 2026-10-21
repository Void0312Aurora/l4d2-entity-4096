#!/usr/bin/env python3
"""Build an isolated EXPERTIMENTAL static copy of client.dll.

Applies the 1089 Class-A patches from manifests/client.json plus PE surgery:
  - one new BSS section (.clentls, 0x300A8 bytes at RVA 0x963000)
  - NumberOfSections, SizeOfImage, checksum

It deliberately does NOT:
  - apply the 3 pending `cmp 0x7FF` candidates
  - touch the 802 unclassified B-mask sites
  - claim any runtime correctness

The artifact is an experimental candidate for loader/format testing only.
The game install is opened read-only and never written.
"""
import hashlib
import json
import os
import struct

from config import require, CLIENT_DLL, OUTDIR, MANIFESTS

SRC = require(CLIENT_DLL)
DST = os.path.join(OUTDIR, "client.4096.dll")
VLOG = os.path.join(OUTDIR, "client.4096.log.json")

NEW_SEC_NAME = b".clentls"
NEW_SEC_RVA = 0x963000
NEW_SEC_VSZ = 0x300A8
NEW_SEC_CHAR = 0xC0000080          # CNT_UNINITIALIZED_DATA | MEM_READ | MEM_WRITE
NEW_SOI = 0x994000


def align(v, a):
    return (v + a - 1) // a * a


def pe_checksum(data, csum_off, cert_off, cert_sz):
    total = 0
    n = len(data)
    for i in range(0, n - 1, 2):
        if csum_off <= i < csum_off + 4:
            continue
        if cert_sz and cert_off <= i < cert_off + cert_sz:
            continue
        total = (total + struct.unpack_from("<H", data, i)[0]) & 0xFFFFFFFF
        total = (total & 0xFFFF) + (total >> 16)
    if n % 2:
        total = (total + data[-1]) & 0xFFFFFFFF
        total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (total + n) & 0xFFFFFFFF


d = bytearray(open(SRC, "rb").read())
man = json.load(open(os.path.join(MANIFESTS, "client.json")))
src_sha = hashlib.sha256(d).hexdigest()
assert src_sha == man["sha256"], (src_sha, man["sha256"])

e = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, e + 6)[0]
soh = struct.unpack_from("<H", d, e + 20)[0]
opt = e + 24
sec_align, file_align = struct.unpack_from("<II", d, opt + 32)
size_image, size_headers = struct.unpack_from("<II", d, opt + 56)
image_base = struct.unpack_from("<I", d, opt + 28)[0]
dd = opt + 96
rel_rva, rel_size = struct.unpack_from("<II", d, dd + 5 * 8)
cert_off, cert_sz = struct.unpack_from("<II", d, dd + 4 * 8)

secs = []
for i in range(nsec):
    b = opt + soh + i * 40
    nm = d[b:b + 8].rstrip(b"\0").decode()
    vsz, va, rs, pr = struct.unpack_from("<IIII", d, b + 8)
    ch = struct.unpack_from("<I", d, b + 36)[0]
    secs.append(dict(name=nm, vsz=vsz, va=va, rs=rs, pr=pr, ch=ch, hdr=b))

report = dict(
    module="client.dll",
    source_sha256=src_sha,
    source_size=len(d),
    status="experimental-static-only",
    notes=[
        "no runtime verification of any kind",
        "3 pending cmp 0x7FF candidates not applied",
        "802 unclassified B-mask sites not applied",
        "S10/C10 shift/mask pairing not proven",
    ],
)

# ---------- 0. header space ----------
first_raw = min(s["pr"] for s in secs if s["rs"] > 0)
hdr_end = opt + soh + (nsec + 1) * 40
assert hdr_end <= min(first_raw, size_headers), (hex(hdr_end), hex(first_raw), hex(size_headers))
report["header_check"] = dict(header_end=hex(hdr_end), first_raw=hex(first_raw), size_of_headers=hex(size_headers))

# ---------- 1. section layout sanity ----------
ranges = [(s["va"], s["va"] + max(s["vsz"], s["rs"]), s["name"]) for s in secs]
for i in range(len(ranges) - 1):
    assert ranges[i][1] <= ranges[i + 1][0], (ranges[i], ranges[i + 1])
for s in secs:
    assert not (s["va"] < NEW_SEC_RVA < s["va"] + max(s["vsz"], s["rs"])), s
report["new_section"] = dict(name=NEW_SEC_NAME.decode(), rva=hex(NEW_SEC_RVA),
                             va=hex(image_base + NEW_SEC_RVA), virtual_size=NEW_SEC_VSZ,
                             size_of_raw_data=0, characteristics=hex(NEW_SEC_CHAR))

# ---------- 2. reloc table (for VA-coverage check) ----------
rel_sec = [s for s in secs if s["va"] <= rel_rva < s["va"] + max(s["vsz"], s["rs"])][0]
rel_pr = rel_sec["pr"] + (rel_rva - rel_sec["va"])
higlow = set()
p = rel_pr
end = rel_pr + rel_size
while p + 8 <= end:
    page, bsz = struct.unpack_from("<II", d, p)
    if bsz < 8:
        break
    for i in range((bsz - 8) // 2):
        ent = struct.unpack_from("<H", d, p + 8 + i * 2)[0]
        if (ent >> 12) == 3:
            higlow.add(page + (ent & 0xFFF))
    p += bsz
report["reloc_entries_higlow"] = len(higlow)

# ---------- 3. apply patches, checking old bytes ----------
bad, applied = [], 0
patched = []
for pt in man["patches"]:
    o = pt["file_offset"]
    old = bytes.fromhex(pt["old"])
    new = bytes.fromhex(pt["new"])
    if d[o:o + len(old)] != old:
        bad.append(dict(id=pt["id"], rva=hex(pt["rva"]), file_offset=o, why="old bytes mismatch"))
        continue
    d[o:o + len(old)] = new
    applied += 1
    patched.append((o, len(old), pt))
assert not bad, bad[:5]
report["patches_applied"] = applied
report["pending_not_applied"] = man.get("pending", [])
report["b_mask_not_applied"] = len(man.get("class_B", []))

# ---------- 4. VA-writing patches must sit on an existing HIGHLOW ----------
va_like, missing_reloc = 0, []
for o, ln, pt in patched:
    if ln != 4:
        continue
    for field in ("old", "new"):
        v = struct.unpack("<I", bytes.fromhex(pt[field]))[0]
        if image_base <= v < image_base + NEW_SOI:
            va_like += 1
            rva = pt["rva"] if pt["rva"] >= 0 else pt["rva"] + (1 << 32)
            if rva not in higlow:
                missing_reloc.append(dict(id=pt["id"], rva=hex(rva), field=field, value=hex(v)))
report["va_patch_fields_checked"] = va_like
report["va_patch_missing_reloc"] = missing_reloc[:50]
report["va_patch_missing_reloc_count"] = len(missing_reloc)

# ---------- 5. section header + headers ----------
b = opt + soh + nsec * 40
struct.pack_into("<8sIIIIIIHHI", d, b, NEW_SEC_NAME, NEW_SEC_VSZ, NEW_SEC_RVA,
                 0, 0, 0, 0, 0, 0, NEW_SEC_CHAR)
struct.pack_into("<H", d, e + 6, nsec + 1)
assert align(NEW_SEC_RVA + NEW_SEC_VSZ, sec_align) == NEW_SOI
struct.pack_into("<I", d, opt + 56, NEW_SOI)

# ---------- 6. checksum ----------
ck_off = opt + 64
struct.pack_into("<I", d, ck_off, 0)
ck = pe_checksum(d, ck_off, cert_off, cert_sz) if cert_sz else pe_checksum(d, ck_off, 0, 0)
struct.pack_into("<I", d, ck_off, ck)

os.makedirs(OUTDIR, exist_ok=True)
open(DST, "wb").write(d)

# ---------- 7. re-parse the written artifact ----------
v = open(DST, "rb").read()
checks = {}
checks["size_unchanged"] = len(v) == len(open(SRC, "rb").read())
checks["sections"] = struct.unpack_from("<H", v, e + 6)[0] == nsec + 1
checks["size_of_image"] = struct.unpack_from("<I", v, opt + 56)[0] == NEW_SOI
nb = opt + soh + nsec * 40
nm, vsz, va, rs, pr = struct.unpack_from("<8sIIII", v, nb)
checks["new_section_fields"] = (nm.rstrip(b"\0") == NEW_SEC_NAME and va == NEW_SEC_RVA
                                and vsz == NEW_SEC_VSZ and rs == 0 and pr == 0)
checks["checksum"] = struct.unpack_from("<I", v, opt + 64)[0] == ck
checks["reloc_dir_unchanged"] = struct.unpack_from("<II", v, dd + 5 * 8) == (rel_rva, rel_size)
# every patched site still holds its new bytes
checks["patched_bytes_hold"] = all(v[o:o + len(bytes.fromhex(pt["new"]))] == bytes.fromhex(pt["new"])
                                   for o, _, pt in patched)
# diff budget
src = open(SRC, "rb").read()
diff = [i for i in range(len(v)) if v[i] != src[i]]
allowed = set()
for o, ln, pt in patched:
    allowed.update(range(o, o + ln))
allowed.update(range(nb, nb + 40))
allowed.update(range(opt + 56, opt + 60))
allowed.update(range(opt + 64, opt + 68))
allowed.update(range(e + 6, e + 8))
stray = [i for i in diff if i not in allowed]
checks["no_stray_bytes"] = not stray
report["checks"] = checks
report["changed_bytes"] = len(diff)
report["stray_offsets"] = [hex(i) for i in stray[:20]]
report["output"] = dict(path=DST, size=len(v), sha256=hashlib.sha256(v).hexdigest())

json.dump(report, open(VLOG, "w"), indent=1)

print("wrote %s" % DST)
print("size 0x%X  sha256 %s" % (len(v), report["output"]["sha256"]))
print("patches applied %d  changed_bytes %d  stray %d" % (applied, len(diff), len(stray)))
for k, ok in checks.items():
    print("[%s] %s" % ("PASS" if ok else "FAIL", k))
print("va-like patch fields checked: %d  missing reloc: %d" %
      (va_like, len(missing_reloc)))
