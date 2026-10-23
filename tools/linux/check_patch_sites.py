#!/usr/bin/env python3
"""Fail when two patch groups claim the same instruction bytes.

Reads repository CSVs that carry elf_addr + old_bytes, decodes the byte length
from old_bytes and rejects overlapping ranges or duplicate addresses across
different groups. Frame-member rows carry only displacements and are checked
for duplicate addresses inside their own file.
"""
import csv, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

def parse_bytes(s):
    s = s.strip()
    if not s or s == "-":
        return None
    try:
        return bytes.fromhex(s)
    except ValueError:
        return None

def rows(path):
    with open(REPO / path, newline="") as f:
        for r in csv.DictReader(f):
            yield r

def main():
    spans = []
    for path in ("data/linux/n27b_patch_sites.csv", "data/linux/n27c_patch_sites.csv"):
        for r in rows(path):
            b = parse_bytes(r.get("old_bytes", ""))
            if not b:
                continue
            addr = int(r["elf_addr"], 16)
            spans.append((addr, addr + len(b), r.get("group", "?"), path, r["elf_addr"]))
    spans.sort()
    bad = False
    for i in range(len(spans) - 1):
        a0, a1, g0, p0, s0 = spans[i]
        a2, a3, g2, p2, s2 = spans[i + 1]
        if a2 < a1:
            print(f"OVERLAP {s0} ({g0}, {p0}) vs {s2} ({g2}, {p2})")
            bad = True
    seen = {}
    for path in ("data/linux/n27b_frame_member_sites.csv",):
        for r in rows(path):
            a = r["elf_addr"]
            if a in seen:
                print(f"DUPLICATE frame site {a} in {path}")
                bad = True
            seen[a] = True
    print("FAIL" if bad else "PASS: no duplicate or overlapping patch sites")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
