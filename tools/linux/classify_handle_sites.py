#!/usr/bin/env python3
"""Create the D63 risk-driven audit table for all 8,184 handle candidates."""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ida', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    rows = json.loads(a.ida.read_text())
    out = []
    for row in rows:
        fn = row.get('name','').lower()
        if any(x in fn for x in ('damage','event','firegameevent','gameevent')): category='events_damage'
        elif any(x in fn for x in ('sound','render','scene')): category='sound_render'
        elif any(x in fn for x in ('ai','nextbot','director','infected','terror')): category='ai_gameplay'
        elif any(x in fn for x in ('globalentitylist','entitylist','addentity','removeentity','free')): category='list_mutation'
        elif any(x in fn for x in ('network','edict','transmit','client','snapshot','baseline')): category='network_query'
        elif any(x in fn for x in ('handle','ehandle','getref','serverentity','entitybyindex')): category='handle_consumer'
        else: category='other_unknown'
        if row['kind']=='index_mask': semantics='index-mask candidate'
        elif row['kind']=='serial_shift': semantics='serial-shift candidate'
        else: semantics='unresolved candidate kind'
        # Candidate classification is not proof that a site ran. Dynamic and
        # boundary coverage must come from runtime instrumentation, never from
        # a function name that merely looks relevant.
        boundary = False
        dynamic = False
        risk = 'high' if category in {'events_damage','list_mutation','network_query','handle_consumer'} else 'medium' if category in {'ai_gameplay','sound_render'} else 'low'
        if 'unknown' in category: risk='review'
        out.append(dict(address=hex(row['va']), function_address=hex(row['function']), function=row['name'],
                         original_bytes=row['old'], patched_bytes=row['new'], instruction=row['instruction'],
                         semantics=semantics, category=category, dynamic_executed=bool(dynamic),
                         boundary_tested=bool(boundary), risk=risk, static_instruction_confirmed=True,
                         evidence='D63 IDA instruction table; static classification only; no per-site runtime evidence supplied'))
    counts={}
    for row in out: counts[row['category']]=counts.get(row['category'],0)+1
    result=dict(schema='d63-handle-audit-v1', source=str(a.ida), candidate_count=len(out),
                reviewed_instruction_count=sum(x['static_instruction_confirmed'] for x in out),
                dynamic_execution_count=sum(x['dynamic_executed'] for x in out),
                boundary_tested_count=sum(x['boundary_tested'] for x in out), categories=counts,
                assertions={'ALL_8184_HANDLE_SITES_CLASSIFIED': len(out)==8184 and all(x['category'] for x in out),
                            'STATIC_BYTES_AND_CANDIDATE_TAGS_PRESENT': all(x['original_bytes'] and x['patched_bytes'] and x['semantics'] for x in out),
                            'UNKNOWN_RETAINED': any(x['category']=='other_unknown' for x in out),
                            'NO_UNVERIFIED_DYNAMIC_CLAIMS': sum(x['dynamic_executed'] for x in out)==0 and sum(x['boundary_tested'] for x in out)==0},
                sites=out)
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('candidate_count','categories','assertions')},indent=2))


if __name__=='__main__': main()
