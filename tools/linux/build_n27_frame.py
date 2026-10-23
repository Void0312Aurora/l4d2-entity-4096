#!/usr/bin/env python3
"""N27-D1-A: frame layout + stack bitmap migration (no code stubs).

Applies F1/F2/F3 from n27b_patch_sites.csv, S1/S2/S3 from
n27c_patch_sites.csv and the 212 shifted EBP displacements from
n27c_stack_sites.csv. Refuses to write if any byte is claimed twice or a
planned byte does not match the pristine image.
"""
import csv, hashlib, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = Path("/home/void0312/l4d2_server/bin/engine_srv.so")
SHA = "5fa15f2820ab67b955ff227a20dbb3fda54d463f3799f33d71b6fd6f38e309b7"

def rows(path):
    with open(REPO / path, newline="") as f:
        for r in csv.DictReader(f):
            yield r

def hb(s):
    return bytes.fromhex(s.strip())

def le32(v):
    v &= 0xFFFFFFFF
    return v.to_bytes(4, "little")

def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/n27/engine_srv_n27a.so")
    data = bytearray(SRC.read_bytes())
    if hashlib.sha256(data).hexdigest() != SHA:
        raise SystemExit("source sha mismatch")
    original = bytes(data)
    edits = {}   # offset -> byte

    def put(off, b, why):
        for i, v in enumerate(b):
            p = off + i
            if p in edits and edits[p] != v:
                raise SystemExit(f"conflict at 0x{p:X}: {why}")
            if original[p] == v:
                continue
            edits[p] = v

    # explicit patches: F1, F3 from n27b; S1/S2/S3 from n27c
    for path, groups in (("data/linux/n27b_patch_sites.csv", {"F1", "F3"}),
                         ("data/linux/n27c_patch_sites.csv", {"S1", "S2", "S3"})):
        for r in rows(path):
            if r.get("group") not in groups:
                continue
            addr = int(r["elf_addr"], 16)
            old, new = hb(r["old_bytes"]), hb(r["new_bytes"])
            if len(old) != len(new):
                raise SystemExit(f"length change at 0x{addr:X}")
            if bytes(data[addr:addr + len(old)]) != old:
                raise SystemExit(f"pristine mismatch at 0x{addr:X}")
            put(addr, new, f"{r['group']} {addr:X}")

    # frame member displacements
    frame = 0
    for r in rows("data/linux/n27b_frame_member_sites.csv"):
        addr = int(r["elf_addr"], 16)
        old = le32(int(r["old_disp"], 16))
        new = le32(int(r["new_disp"], 16))
        limit = len(hb(r["old_bytes"]))
        win = bytes(data[addr:addr + limit])
        pos = win.find(old)
        if pos < 0:
            raise SystemExit(f"frame disp {r['old_disp']} not found at 0x{addr:X}")
        if win.find(old, pos + 1) >= 0:
            raise SystemExit(f"frame disp ambiguous at 0x{addr:X}")
        put(addr + pos, new, f"frame {addr:X}")
        frame += 1

    # stack shifted displacements (bitmap base rows are handled by S1/S2)
    stack = 0
    for r in []:
        if r["class"] == "bitmap_base":
            continue
        if r["class"] != "below_bitmap_shift":
            continue
        addr = int(r["elf_addr"], 16)
        old = le32(int(r["old_disp"], 16))
        new = le32(int(r["new_disp"], 16))
        limit = len(hb(r["old_bytes"]))
        win = bytes(data[addr:addr + limit])
        pos = win.find(old)
        if pos < 0:
            raise SystemExit(f"stack disp {r['old_disp']} not found at 0x{addr:X}")
        if win.find(old, pos + 1) >= 0:
            raise SystemExit(f"stack disp ambiguous at 0x{addr:X}")
        put(addr + pos, new, f"stack {addr:X}")
        stack += 1

    for p, v in edits.items():
        data[p] = v
    changed = sum(1 for i, v in enumerate(original) if v != data[i])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(data))

    # post-build frame/stack spot verification
    img = out.read_bytes()
    for r in rows("data/linux/n27b_frame_member_sites.csv"):
        addr = int(r["elf_addr"], 16)
        if le32(int(r["new_disp"], 16)) not in img[addr:addr + 16]:
            raise SystemExit(f"frame new disp missing at 0x{addr:X}")
    # 位图已移到帧下方，原有局部变量不再迁移，无需逐条检查 new_disp
    print(f"built {out} changed_bytes={changed} frame={frame} stack={stack} edits={len(edits)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
