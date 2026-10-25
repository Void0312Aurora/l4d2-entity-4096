#!/usr/bin/env python3
"""Bounded F2 consumer audit: classify old-offset operands in CClientFrame consumers."""
import csv, hashlib, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BIN = Path("/home/void0312/l4d2_server/bin/engine_srv.so")
EXPECTED_SHA = "5fa15f2820ab67b955ff227a20dbb3fda54d463f3799f33d71b6fd6f38e309b7"
F2 = ROOT/"data/linux/n27b_frame_member_sites.csv"
PATCH = ROOT/"data/linux/n27b_patch_sites.csv"

def symbols():
    out = subprocess.run(["readelf","-sW",str(BIN)],capture_output=True,text=True).stdout
    d = {}
    for line in out.splitlines():
        m = re.match(r"\s*\d+:\s*([0-9a-f]+)\s+(\d+)\s+FUNC\s+\S+\s+\S+\s+\S+\s+(\S+)", line)
        if m: d[m.group(3)] = (int(m.group(1),16), int(m.group(2)))
    return d

def main():
    if hashlib.sha256(BIN.read_bytes()).hexdigest() != EXPECTED_SHA:
        print("FAIL: unexpected pristine engine_srv.so sha256"); return 1
    out_path = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/"data/linux/n27d30_frame_audit.csv"
    f2 = {int(r["elf_addr"],16): r for r in csv.DictReader(open(F2))}
    patch = {}
    for r in csv.DictReader(open(PATCH)):
        try: patch[int(r["elf_addr"],16)] = r
        except (ValueError, KeyError): pass
    syms = symbols()
    funcs = [n for n in syms if any(k in n for k in ("ClientFrame","SendSnapshot","WriteDeltaEntities","ProcessBaselineAck"))]
    rows=[]
    for name in sorted(funcs):
        addr,size=syms[name]
        dis=subprocess.run(["objdump","-d",f"--start-address={addr}",f"--stop-address={addr+size}",str(BIN)],capture_output=True,text=True).stdout
        for line in dis.splitlines():
            m=re.match(r"\s*([0-9a-f]+):",line)
            if not m: continue
            ea=int(m.group(1),16)
            for off in ("10c","110","114","118"):
                if re.search(r"0x"+off+r"\(%e",line) and "-0x"+off not in line:
                    ins=line.split("\t",2)[-1].strip() if "\t" in line else line.strip()
                    if ea in f2: origin="f2_covered"
                    elif ea in patch: origin="c3_covered:"+str(patch[ea].get("group"))
                    elif "%ebp" in ins: origin="stack_local_excluded"
                    elif "ProcessBaselineAck" in name and "%esi" in ins: origin="cbaseclient_c3"
                    else: origin="unclassified"
                    rows.append(dict(function=name,elf_addr=hex(ea),old_disp="0x"+off.upper(),instruction=ins,origin=origin))
                    break
    # same instruction can be reported through multiple symbol aliases
    dedup = {}
    for r in rows:
        dedup.setdefault(r["elf_addr"], r)
    rows = list(dedup.values())
    out_path.parent.mkdir(parents=True,exist_ok=True)
    with open(out_path,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["function","elf_addr","old_disp","instruction","origin"]); w.writeheader(); w.writerows(rows)
    from collections import Counter
    counts=Counter(r["origin"] for r in rows)
    print("unique sites",len(rows),counts)
    bad=[r for r in rows if r["origin"]=="unclassified"]
    for r in bad: print("UNCLASSIFIED",r)
    if bad:
        print("FAIL: unclassified frame-consumer sites"); return 1
    print("PASS: every scanned old-offset operand is covered by F2 or C3")
    return 0

if __name__=="__main__": sys.exit(main())
