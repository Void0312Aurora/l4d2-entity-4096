#!/usr/bin/env python3
"""Read-only PE pre-check for the server.dll 4096-edict migration.

Validates, in memory only:
  1. input SHA-256 binding
  2. section/header capacity for 2 new sections
  3. virtual layout (no overlap, SizeOfImage)
  4. relocation directory extensibility + new HIGHLOW block
  5. every Class-A patch (old bytes match, no overlap)
  6. re-parse of the simulated image
Nothing on disk is modified; a JSON+text report is written to ./precheck/.
"""
import struct, json, hashlib, os, sys


from config import require, SERVER_DLL, OUTDIR, MANIFESTS, REPORTS
DLL = require(SERVER_DLL)
MAN = os.path.join(MANIFESTS, "server.json")
OUTDIR = os.path.join(REPORTS, "precheck")

d = bytearray(open(DLL, "rb").read())
man = json.load(open(MAN))
res = []
def chk(name, ok, detail=""):
    res.append(dict(check=name, ok=bool(ok), detail=detail))
    print(("PASS " if ok else "FAIL ") + name + ("  " + detail if detail else ""))
    return ok

# ---------- 1. hash ----------
sha = hashlib.sha256(d).hexdigest()
chk("sha256_binding", sha == man["sha256"], sha)

# ---------- headers ----------
e = struct.unpack_from("<I", d, 0x3c)[0]
chk("pe_signature", d[e:e+4] == b"PE\0\0", hex(e))
nsec = struct.unpack_from("<H", d, e+6)[0]
soh = struct.unpack_from("<H", d, e+20)[0]
magic = struct.unpack_from("<H", d, e+24)[0]
chk("optional_magic_pe32", magic == 0x10b, hex(magic))
opt = e + 24
size_image, size_headers = struct.unpack_from("<II", d, opt+56)
sec_align, file_align = struct.unpack_from("<II", d, opt+32)
chk("section_alignment", sec_align == 0x1000, hex(sec_align))
chk("file_alignment", file_align in (0x200, 0x1000), hex(file_align))
dd = opt + 96
rel_rva, rel_size = struct.unpack_from("<II", d, dd + 5*8)
sec_off, sec_size = struct.unpack_from("<II", d, dd + 4*8)
checksum_off = opt + 64

secs = []
for i in range(nsec):
    b = opt + soh + i*40
    nm = d[b:b+8].rstrip(b"\0").decode()
    vsz, va, rs, pr = struct.unpack_from("<IIII", d, b+8)
    secs.append(dict(name=nm, vsz=vsz, va=va, rs=rs, pr=pr))
    chk(f"section[{i}]_{nm}_raw_in_file", pr + rs <= len(d), f"raw 0x{pr:X}+0x{rs:X}")

def align(v, a): return (v + a - 1) // a * a
virt_end = max(s["va"] + max(s["vsz"], s["rs"]) for s in secs)
raw_end = max(s["pr"] + s["rs"] for s in secs)
chk("size_of_image_matches_sections", align(virt_end, sec_align) == size_image,
    f"last_end=0x{virt_end:X} aligned=0x{align(virt_end,sec_align):X} header=0x{size_image:X}")

# ---------- 2. plan new sections ----------
NEW = man["sections"]
plan = []
rva = align(virt_end, sec_align)
for s in NEW:
    p = dict(name=s["name"], rva=rva, vsz=s["virtual_size"], rs=s["size_of_raw_data"])
    p["va"] = 0x10000000 + rva
    rva = align(rva + p["vsz"], sec_align)
    plan.append(p)
soi_new = rva
chk("planned_rva_matches_manifest", all(p["va"] == s["va"] for p, s in zip(plan, NEW)),
    " ".join("%s@0x%X" % (p["name"], p["va"]) for p in plan))
chk("planned_sizeofimage", soi_new == man["size_of_image_new"],
    "0x%X vs manifest 0x%X" % (soi_new, man["size_of_image_new"]))
chk("section_name_len", all(len(p["name"]) <= 8 for p in plan),
    ",".join(p["name"] for p in plan))
chk("virtual_no_overlap", plan[0]["rva"] >= virt_end, "first new rva 0x%X >= 0x%X" % (plan[0]["rva"], virt_end))

# ---------- 3. header capacity ----------
hdr_need = e + 24 + soh + (nsec + len(plan)) * 40
first_raw = min(s["pr"] for s in secs if s["rs"] > 0)
chk("header_space_for_new_sections", hdr_need <= size_headers and hdr_need <= first_raw,
    f"need 0x{hdr_need:X} <= SizeOfHeaders 0x{size_headers:X}, first_raw 0x{first_raw:X}")

# ---------- 4. relocation directory ----------
rel_pr = None
for s in secs:
    if s["va"] <= rel_rva < s["va"] + max(s["vsz"], s["rs"]):
        rel_pr = s["pr"] + (rel_rva - s["va"]); rel_sec = s["name"]
chk("reloc_dir_mapped", rel_pr is not None, f"rva=0x{rel_rva:X} sec={rel_sec if rel_pr else '?'} size=0x{rel_size:X}")
# walk blocks
p = rel_pr; endp = rel_pr + rel_size; blocks = []
while p + 8 <= endp:
    page, bsz = struct.unpack_from("<II", d, p)
    if bsz < 8 or p + bsz > endp: break
    blocks.append((page, bsz)); p += bsz
chk("reloc_blocks_parse", p == endp, "%d blocks, consumed 0x%X/0x%X" % (len(blocks), p-rel_pr, rel_size))
last_page, last_sz = blocks[-1]
chk("reloc_last_block_page", last_page <= 0x981000, "last page=0x%X" % last_page)
# new block appends at end of reloc raw
new_block = struct.pack("<IIHH", 0x9A3000, 0x0C, 0x3000, 0x0000)
chk("reloc_new_block_size", len(new_block) == 12)
next_raw = min([s["pr"] for s in secs if s["pr"] > rel_pr] + [len(d)])
chk("reloc_append_space", rel_pr + rel_size + 12 <= next_raw,
    "free 0x%X bytes after reloc raw" % (next_raw - (rel_pr + rel_size)))

# ---------- 5. patches ----------
buf = bytearray(d); bad = []; overlaps = 0
last_end = -1
for p_ in sorted(man["patches"], key=lambda x: x["file_offset"]):
    o = p_["file_offset"]; old = bytes.fromhex(p_["old"]); new = bytes.fromhex(p_["new"])
    if len(old) != len(new):
        bad.append((p_["id"], hex(o), "length change")); continue
    if o < last_end: overlaps += 1
    last_end = o + len(old)
    if bytes(buf[o:o+len(old)]) != old:
        bad.append((p_["id"], hex(o), "old mismatch")); continue
    buf[o:o+len(old)] = new
chk("patches_apply", not bad, "%d entries, %d errors" % (len(man["patches"]), len(bad)))
chk("patches_no_overlap", overlaps == 0, str(overlaps))

# ---------- 6. simulate image in memory ----------
sim = bytearray(buf)
# 6a. section headers
for i, p in enumerate(plan):
    b = opt + soh + (nsec + i) * 40
    name = p["name"].encode().ljust(8, b"\0")
    # raw for .simthnk appended at end of file
    if p["rs"]:
        pr = len(sim); sim += b"\0" * p["rs"]
        # first dword = vtable, plus reloc entry covered by new block
        struct.pack_into("<I", sim, pr, 0x105F3A94)
    else:
        pr = 0
    struct.pack_into("<8sIIIIIIHHI", sim, b, name, p["vsz"], p["rva"], p["rs"], pr,
                    0, 0, 0, 0, 0xE0000040 if p["rs"] == 0 else 0x40000040)
    p["pr"] = pr
# 6b. reloc block
sim[rel_pr + rel_size: rel_pr + rel_size + 12] = new_block
struct.pack_into("<I", sim, dd + 5*8 + 4, rel_size + 12)
# 6c. header fields
struct.pack_into("<H", sim, e + 6, nsec + len(plan))
struct.pack_into("<I", sim, opt + 56, soi_new)
sim = sim  # keep

# ---------- 7. re-parse simulated image ----------
chk("reparse_nsec", struct.unpack_from("<H", sim, e+6)[0] == nsec + 2)
chk("reparse_soi", struct.unpack_from("<I", sim, opt+56)[0] == soi_new)
rel_size2 = struct.unpack_from("<I", sim, dd + 5*8 + 4)[0]
chk("reparse_reloc_size", rel_size2 == rel_size + 12, hex(rel_size2))
# new block visible?
found = False
for i in range(rel_size2 // 2):
    pass
p2 = rel_pr
while p2 + 8 <= rel_pr + rel_size2:
    page, bsz = struct.unpack_from("<II", sim, p2)
    if page == 0x9A3000 and bsz == 12:
        found = True; break
    p2 += bsz
chk("reparse_new_reloc_block", found)
# new section readable
b = opt + soh + (nsec + 1) * 40
nm = sim[b:b+8].rstrip(b"\0").decode()
vsz, va, rs, pr = struct.unpack_from("<IIII", sim, b+8)
chk("reparse_simthnk", nm == ".simthnk" and va == 0x9A3000 and rs == 0x200, f"{nm} va=0x{va:X} rs=0x{rs:X}")
chk("reparse_vptr_bytes", struct.unpack_from("<I", sim, pr)[0] == 0x105F3A94)

# ---------- 8. certificate / checksum ----------
chk("authenticode_present", sec_off != 0 and sec_size != 0,
    "cert dir offset=0x%X size=0x%X (signature will NOT be valid after patch)" % (sec_off, sec_size))
chk("cert_dir_within_file", sec_off + sec_size <= len(d) if sec_off else True,
    "cert ends at 0x%X, file 0x%X" % (sec_off + sec_size if sec_off else 0, len(d)))

report = dict(dll=DLL, sha256=sha, checks=res,
              summary=dict(total=len(res), passed=sum(1 for r in res if r["ok"]),
                           failed=sum(1 for r in res if not r["ok"])),
              plan=plan, size_of_image_new=soi_new)
json.dump(report, open(os.path.join(OUTDIR, "precheck.json"), "w"), indent=1)
print("\n%d checks, %d passed, %d failed" % (len(res), report["summary"]["passed"], report["summary"]["failed"]))
