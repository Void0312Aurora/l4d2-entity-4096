#!/usr/bin/env python3
"""Bounded F2 consumer audit: classify old-offset operands in CClientFrame consumers."""
import csv, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BIN = Path("/home/void0312/l4d2_server/bin/engine_srv.so")
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
    out_path.parent.mkdir(parents=True,exist_ok=True)
    with open(out_path,"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["function","elf_addr","old_disp","instruction","origin"]); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print("sites",len(rows),Counter(r["origin"] for r in rows))
    for r in rows:
        if r["origin"]=="unclassified": print("UNCLASSIFIED",r)

if __name__=="__main__": main()
