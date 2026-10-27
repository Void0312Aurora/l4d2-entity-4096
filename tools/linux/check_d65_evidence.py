#!/usr/bin/env python3
"""Check the lightweight D65 result record and selected raw snapshots.

This is deliberately an evidence checker, not a test runner. It fails when a
claimed PASS lacks its named raw evidence or when a module identity drifts.
"""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = {
    "patched_engine_sha256": "79b3966bd9752394beb2f29f0cf0244acedddde15112b4c037535994ecaf8014",
    "patched_server_sha256": "8575ed52f39b7c85ea776c83960e3ac08f07521b503109e639acdee1e53d5222",
    "patched_client_sha256": "3e5c3f2ee98c2bfa3f3672c654f7ae8b3ae401cc437a08ae1abbe57a6d363943",
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('record',type=Path)
    ap.add_argument('--evidence-root',type=Path,required=True)
    a=ap.parse_args()
    record=json.loads(a.record.read_text())
    failures=[]
    for key,want in EXPECTED.items():
        if record['identities'].get(key)!=want: failures.append(f'{key}: identity drift')
    for name,item in record['assertions'].items():
        if item['status']=='PASS':
            for ev in item.get('evidence',[]):
                if not (a.evidence_root/ev).exists(): failures.append(f'{name}: missing {ev}')
    ladder=record['ladder']
    if ladder != [16,64,128,256,512]: failures.append('ladder is not 16/64/128/256/512')
    if record['boundary']['index'] != 4095 or not record['boundary']['old_ref_invalid']:
        failures.append('4095 boundary lifecycle incomplete')
    out={'status':'PASS' if not failures else 'FAIL','failures':failures,
         'checked_record':str(a.record),'evidence_root':str(a.evidence_root)}
    print(json.dumps(out,indent=2))
    return 0 if not failures else 1
if __name__=='__main__': raise SystemExit(main())
