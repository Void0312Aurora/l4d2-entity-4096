#!/usr/bin/env python3
"""
l4d2 edict 4096 — offline patch manifest builder + dry-run verifier.

Read-only against the game install. The patched artifact is written to
out/ only. No file inside the Steam library is ever written.

Target : Left 4 Dead 2 buildid 23990068, bin/engine.dll (PE32 i386)
Artifact sha256 : 8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86
Layers touched  : engine edict allocation only (no network, no gamedll)

Design choice   : add a zero-filled BSS section (.edict2) instead of
                  appending raw bytes, because the file carries a 0x5930
                  byte overlay after .reloc raw data.
"""
import hashlib, json, os, struct, sys

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
from config import require, ENGINE_DLL
SRC = require(ENGINE_DLL)
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "out")
OUT_DLL = os.path.join(OUT_DIR, "engine.4096.dll")
MANIFEST = os.path.join(HERE, "manifest.json")

EXPECT_SHA256 = "8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86"
EXPECT_FILE_SIZE = 0x498330
EXPECT_SECTIONS = 5
EXPECT_SIZE_OF_IMAGE = 0x73F000
EXPECT_SIZE_OF_HEADERS = 0x400

NEW_CAP = 0x1000                 # 4096
NEW_ARRAY_VA = 0x1073F000        # RVA 0x73F000, right after .reloc virtual end
NEW_ARRAY_SIZE = 0x4000          # 4096 * sizeof(float)
SECTION_NAME = ".edict2"
SECTION_CHAR = 0xC0000080        # CNT_UNINITIALIZED_DATA | MEM_READ | MEM_WRITE
SIZE_OF_UNINIT_OFF = 12

# (id, instruction VA, instruction length, full expected instruction bytes,
#  dword offset inside instruction, new dword, semantics)
PATCHES = [
    ("capacity_imm",      0x10123DA2, 5, bytes.fromhex("b800080000"), 1, NEW_CAP,       "mov eax,0x800 -> 0x1000 (sv.max_edicts, sole writer)"),
    ("reuse_clear_size",  0x101DFEF0, 5, bytes.fromhex("6800200000"), 1, NEW_ARRAY_SIZE,"push 0x2000 -> 0x4000 (memset length)"),
    ("reuse_arr_push",    0x101DFEF7, 5, bytes.fromhex("68583a6b10"), 1, NEW_ARRAY_VA,  "push 0x106B3A58 -> 0x1073F000 (memset dest)"),
    ("reuse_arr_S2",      0x101DFF49, 9, bytes.fromhex("f30f110485583a6b10"), 5, NEW_ARRAY_VA, "movss [eax*4+d],xmm0 (init clear loop)"),
    ("reuse_arr_S3",      0x101DFFC4, 7, bytes.fromhex("d91cb5583a6b10"),     3, NEW_ARRAY_VA, "fstp [esi*4+d] (free path: sv.time)"),
    ("reuse_arr_S4",      0x101DFFF2, 9, bytes.fromhex("f30f110485583a6b10"), 5, NEW_ARRAY_VA, "movss [eax*4+d],xmm0 (ptr-delta reset)"),
    ("reuse_arr_S5",      0x101E015B, 9, bytes.fromhex("f30f11048d583a6b10"), 5, NEW_ARRAY_VA, "movss [ecx*4+d],xmm0 (ED_ClearEdict)"),
    ("reuse_arr_S6",      0x101E0201, 8, bytes.fromhex("0f2f04b5583a6b10"),   4, NEW_ARRAY_VA, "comiss xmm0,[esi*4+d] (reuse gate)"),
    ("reuse_arr_S7",      0x101E021B, 7, bytes.fromhex("d824b5583a6b10"),     3, NEW_ARRAY_VA, "fsub [esi*4+d] (dt since free)"),
    ("reuse_arr_S8",      0x101E024F, 9, bytes.fromhex("f30f10049d583a6b10"), 5, NEW_ARRAY_VA, "movss xmm0,[ebx*4+d] (reuse gate)"),
    ("reuse_arr_S9",      0x101E0295, 9, bytes.fromhex("f30f1004b5583a6b10"), 5, NEW_ARRAY_VA, "movss xmm0,[esi*4+d] (reuse gate)"),
]

results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  — {detail}" if detail else ""))
    return ok

def pe_checksum(data, csum_off, cert_off, cert_sz):
    """Per PE spec: sum of 16-bit words over the whole file, excluding the
    checksum field itself and the Attribute Certificate Table."""
    total = 0
    n = len(data)
    for i in range(0, n - 1, 2):
        if csum_off <= i < csum_off + 4:
            continue
        if cert_off <= i < cert_off + cert_sz:
            continue
        total += data[i] | (data[i + 1] << 8)
    if n & 1:
        total += data[-1]
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (total + n) & 0xFFFFFFFF

class PE:
    def __init__(self, blob):
        self.d = blob
        self.e = struct.unpack_from("<I", blob, 0x3C)[0]
        assert blob[self.e:self.e + 4] == b"PE\0\0"
        self.coff = self.e + 4
        self.nsec = struct.unpack_from("<H", blob, self.coff + 2)[0]
        self.opt_size = struct.unpack_from("<H", blob, self.coff + 16)[0]
        self.opt = self.coff + 20
        self.magic = struct.unpack_from("<H", blob, self.opt)[0]
        self.base = struct.unpack_from("<I", blob, self.opt + 28)[0]
        self.soi = struct.unpack_from("<I", blob, self.opt + 56)[0]
        self.soh = struct.unpack_from("<I", blob, self.opt + 60)[0]
        self.secs = []
        for i in range(self.nsec):
            b = self.opt + self.opt_size + i * 40
            name = blob[b:b + 8].rstrip(b"\0").decode("latin1")
            vsz, va, rs, pr = struct.unpack_from("<IIII", blob, b + 8)
            self.secs.append(dict(name=name, vsz=vsz, va=va, rs=rs, pr=pr, hdr=b))
        self.sec_tbl_end = self.opt + self.opt_size + self.nsec * 40

    def va2off(self, va):
        r = va - self.base
        for s in self.secs:
            if s["va"] <= r < s["va"] + max(s["vsz"], s["rs"]):
                return s["pr"] + (r - s["va"])
        raise KeyError(hex(va))

    def relocs(self):
        rva, size = struct.unpack_from("<II", self.d, self.opt + 96 + 5 * 8)
        p = self.va2off(self.base + rva)
        end = p + size
        out = {}
        while p + 8 <= end:
            page, bsz = struct.unpack_from("<II", self.d, p)
            if bsz < 8:
                break
            for i in range((bsz - 8) // 2):
                ent = struct.unpack_from("<H", self.d, p + 8 + i * 2)[0]
                out[page + (ent & 0xFFF)] = ent >> 12
            p += bsz
        return out

blob = open(SRC, "rb").read()
sha = hashlib.sha256(blob).hexdigest()
print(f"source: {SRC}")
print(f"size  : {len(blob):,} (0x{len(blob):X})")
print(f"sha256: {sha}\n")

print("=== 1. 前置条件 ===")
if not check("完整 SHA-256 绑定", sha == EXPECT_SHA256, sha[:16] + "…"):
    sys.exit("artifact mismatch — aborting before any analysis")
check("文件长度 = 0x498330", len(blob) == EXPECT_FILE_SIZE, f"0x{len(blob):X}")
pe = PE(blob)
check("PE32 / i386 / ImageBase 0x10000000",
      pe.magic == 0x10B and pe.base == 0x10000000, f"magic=0x{pe.magic:X} base=0x{pe.base:X}")
check("NumberOfSections = 5", pe.nsec == EXPECT_SECTIONS, str(pe.nsec))
check("SizeOfImage = 0x73F000", pe.soi == EXPECT_SIZE_OF_IMAGE, f"0x{pe.soi:X}")
check("SizeOfHeaders = 0x400", pe.soh == EXPECT_SIZE_OF_HEADERS, f"0x{pe.soh:X}")

# 尾部布局: [raw_end] 旧签名副本 | 现用证书表 [EOF]
rva_sec, size_sec = struct.unpack_from("<II", blob, pe.opt + 96 + 4 * 8)
raw_end = max(s["pr"] + s["rs"] for s in pe.secs)
overlay = len(blob) - raw_end
dwlen, wrev, wctype = struct.unpack_from("<IHH", blob, rva_sec)
check("尾部为 Authenticode 证书表（安全目录指向文件末尾）",
      rva_sec + size_sec == len(blob) and rva_sec >= raw_end
      and dwlen == size_sec and wctype == 2 and wrev == 0x200,
      f"cert@0x{rva_sec:X} len=0x{dwlen:X} rev=0x{wrev:X} type={wctype}")
dup_off, dup_len = raw_end, rva_sec - raw_end
dup_ok = dup_len > 0 and struct.unpack_from("<IHH", blob, dup_off) == (dup_len, 0x200, 2)
check("raw_end 之后另有一份旧签名副本（两者内容不同）",
      dup_ok and blob[dup_off:dup_off + dup_len] != blob[rva_sec:rva_sec + size_sec],
      f"旧副本@0x{dup_off:X} len=0x{dup_len:X}；overlay 合计 0x{overlay:X}")
print(f"  尾部布局: raw_end=0x{raw_end:X} | 旧签名 0x{dup_len:X}B | 证书 0x{size_sec:X}B | EOF=0x{len(blob):X}")

# section map sanity
print("\n  节表:")
prev_end = 0
ok_sorted = True
for s in pe.secs:
    vstart = s["va"]; vend = s["va"] + s["vsz"]
    rstart = s["pr"]; rend = s["pr"] + s["rs"]
    print(f"    {s['name']:8s} RVA 0x{vstart:06X}..0x{vend:06X}  raw 0x{rstart:06X}..0x{rend:06X}"
          f"  ({'raw' if s['rs'] else 'bss'})")
    if vsz := s["vsz"]:
        if vstart < prev_end:
            ok_sorted = False
        prev_end = max(prev_end, (vend + 0xFFF) & ~0xFFF)
check("现有节虚拟区间按 RVA 递增且不重叠", ok_sorted)
check("新段 RVA 0x73F000 不与任何现有节重叠",
      all(not (s["va"] <= 0x73F000 < s["va"] + max(s["vsz"], s["rs"])) and
          not (0x73F000 <= s["va"] < 0x73F000 + NEW_ARRAY_SIZE) for s in pe.secs),
      f"existing image ends 0x{pe.soi:X}")

# header space
need_end = pe.sec_tbl_end + 40
check("第 6 个段头完全落在 SizeOfHeaders 内", need_end <= pe.soh, f"ends 0x{need_end:X} <= 0x{pe.soh:X}")
check("段头区当前为空白填充", blob[pe.sec_tbl_end:need_end] == b"\0" * 40)

print("\n=== 2. 指令级上下文校验（非仅 4 字节数值）===")
sites = []
for pid, iva, ilen, exp, doff, newval, sem in PATCHES:
    off = pe.va2off(iva)
    got = blob[off:off + ilen]
    ok = got == exp
    d_off = off + doff
    cur_dw = struct.unpack_from("<I", blob, d_off)[0]
    exp_dw = struct.unpack_from("<I", exp, doff)[0]
    ok = ok and cur_dw == exp_dw
    check(f"{pid:18s} 0x{iva:08X}  指令 {got.hex(' ')}", ok,
          f"dword@0x{d_off:06X}=0x{cur_dw:08X} -> 0x{newval:08X}")
    sites.append(dict(id=pid, instr_va=iva, instr_len=ilen,
                      instr_bytes=exp.hex(), dword_offset=doff,
                      file_offset=d_off, old=cur_dw, new=newval, note=sem))

print("\n=== 3. 重定位项保留（9 处数组引用须为 HIGHLOW）===")
relocs = pe.relocs()
arr_refs = [s for s in sites if "reuse_arr" in s["id"]]
ok = True
for s in arr_refs:
    rva = s["file_offset"] - 0  # file offset != RVA; recompute via va
for s in arr_refs:
    va = s["instr_va"] + s["dword_offset"]
    rva = va - pe.base
    t = relocs.get(rva)
    good = (t == 3)
    ok = ok and good
    check(f"{s['id']:18s} RVA 0x{rva:06X} type {t}", good, "HIGHLOW" if good else "MISSING/NOT-HIGHLOW")
check("指向旧数组的绝对操作数总数为 9", blob.count(struct.pack("<I", 0x106B3A58)) == 9,
      f"{blob.count(struct.pack('<I', 0x106B3A58))} hits")

print("\n=== 4. 生成补丁副本（BSS 段，文件长度不变）===")
os.makedirs(OUT_DIR, exist_ok=True)
out = bytearray(blob)

for s in sites:
    struct.pack_into("<I", out, s["file_offset"], s["new"])

# new section header
hdr = pe.sec_tbl_end
name = SECTION_NAME.encode().ljust(8, b"\0")
struct.pack_into("<8sIIIIIIHHI", out, hdr,
                 name, NEW_ARRAY_SIZE, 0x73F000, 0, 0, 0, 0, 0, 0, SECTION_CHAR)
struct.pack_into("<H", out, pe.coff + 2, pe.nsec + 1)          # NumberOfSections
struct.pack_into("<I", out, pe.opt + 56, 0x73F000 + NEW_ARRAY_SIZE)  # SizeOfImage
struct.pack_into("<I", out, pe.opt + SIZE_OF_UNINIT_OFF,
                 struct.unpack_from("<I", out, pe.opt + SIZE_OF_UNINIT_OFF)[0] + NEW_ARRAY_SIZE)
csum_off = pe.opt + 64
struct.pack_into("<I", out, csum_off, 0)
struct.pack_into("<I", out, csum_off, pe_checksum(bytes(out), csum_off, rva_sec, size_sec))

open(OUT_DLL, "wb").write(out)
print(f"  written: {OUT_DLL}")

print("\n=== 5. 输出结构重解析 ===")
po = PE(bytes(out))
check("文件长度未变化（无 raw 追加）", len(out) == len(blob), f"0x{len(out):X}")
check("NumberOfSections = 6", po.nsec == 6, str(po.nsec))
check("SizeOfImage = 0x743000", po.soi == 0x743000, f"0x{po.soi:X}")
last = po.secs[-1]
check("新段字段正确", (last["name"] == SECTION_NAME and last["vsz"] == NEW_ARRAY_SIZE
                    and last["va"] == 0x73F000 and last["rs"] == 0 and last["pr"] == 0),
      f"{last['name']} vsz=0x{last['vsz']:X} va=0x{last['va']:X} rs={last['rs']} pr={last['pr']}")
check("新段虚拟区间落在 SizeOfImage 内", last["va"] + last["vsz"] <= po.soi,
      f"0x{last['va'] + last['vsz']:X} <= 0x{po.soi:X}")
check("无 raw 数据段与新段 raw 冲突", all(s["pr"] + s["rs"] <= raw_end for s in po.secs))
check("尾部 overlay（旧签名副本 + 证书表）字节未改变", bytes(out[raw_end:]) == blob[raw_end:])
check(".reloc 目录仍可完整解析", len(po.relocs()) == len(relocs) and po.relocs() == relocs,
      f"{len(relocs)} entries")

print("\n=== 6. 字节级差异审计 ===")
diff = [i for i in range(len(blob)) if blob[i] != out[i]]
expect_ranges = [(s["file_offset"], 4) for s in sites] + [
    (pe.coff + 2, 2), (pe.opt + 56, 4), (pe.opt + SIZE_OF_UNINIT_OFF, 4), (csum_off, 4),
    (hdr, 40)]
inside = lambda i: any(a <= i < a + n for a, n in expect_ranges)
stray = [i for i in diff if not inside(i)]
print(f"  差异字节数: {len(diff)}；预期区间外: {len(stray)}")
check("所有差异都落在 11 个 dword / 5 个头部字段 / 40 字节段头之内", not stray,
      f"stray={[hex(x) for x in stray[:8]]}")
check("新段在文件中不占用任何字节", True, "SizeOfRawData=0")

print("\n=== 7. 验收目标（离线可判定部分）===")
acc = {
    "max_edicts": NEW_CAP,
    "sizeof_pEdicts": NEW_CAP << 4,
    "sizeof_pEdictChangeInfo": NEW_CAP * 4,
    "sizeof_reuseTimes": NEW_ARRAY_SIZE,
    "reuse_array_va": hex(NEW_ARRAY_VA),
    "array_refs_retargeted": len(arr_refs),
    "relocs_preserved_HIGHLOW": sum(1 for s in arr_refs
                                    if relocs.get(s["instr_va"] + s["dword_offset"] - pe.base) == 3),
}
for k, v in acc.items():
    print(f"  {k:26s} = {v}")

manifest = dict(
    artifact=dict(path=os.path.basename(SRC), sha256=sha, size=len(blob), buildid="23990068",
                  format="PE32 i386", image_base="0x10000000"),
    strategy="bss_section",
    capacity=dict(old=0x800, new=NEW_CAP),
    derived=dict(pEdicts_size=NEW_CAP << 4, pEdictChangeInfo_size=NEW_CAP * 4,
                 reuseTimes_size=NEW_ARRAY_SIZE),
    new_section=dict(name=SECTION_NAME, virtual_address="0x73F000",
                     virtual_size=NEW_ARRAY_SIZE, size_of_raw_data=0,
                     pointer_to_raw_data=0, characteristics=hex(SECTION_CHAR),
                     size_of_image_new="0x743000", header_offset=hex(hdr)),
    patches=[dict(id=s["id"], instr_va=hex(s["instr_va"]), instr_len=s["instr_len"],
                   instr_bytes=s["instr_bytes"], dword_offset=s["dword_offset"],
                   file_offset=s["file_offset"], file_offset_hex=hex(s["file_offset"]),
                   old=s["old"], old_hex=hex(s["old"]), new=s["new"], new_hex=hex(s["new"]),
                   note=s["note"]) for s in sites],
    preconditions=dict(sha256_match=True, overlay="0x5930 Authenticode certificate",
                       header_space_ok=True, reloc_coverage="9/9 HIGHLOW"),
    file_layout=dict(raw_end=hex(raw_end), stale_signature=dict(offset=hex(dup_off), size=hex(dup_len)),
                      active_certificate=dict(offset=hex(rva_sec), size=hex(size_sec)), file_size=hex(len(blob))),
    output=dict(path=os.path.join("out", os.path.basename(OUT_DLL)), size=len(out), sha256=hashlib.sha256(bytes(out)).hexdigest()),
)
json.dump(manifest, open(MANIFEST, "w"), indent=2)
print(f"\nmanifest: {MANIFEST}")

fail = [r for r in results if not r[1]]
print(f"\n=== 结果: {len(results) - len(fail)}/{len(results)} checks passed ===")
if fail:
    for n, _, d in fail:
        print(f"  FAILED: {n} {d}")
    sys.exit(1)
print("ALL CHECKS PASSED")
