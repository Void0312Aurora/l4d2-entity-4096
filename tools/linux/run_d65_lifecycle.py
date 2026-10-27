#!/usr/bin/env python3
"""Record D65 actual-index prop lifecycles against a private, connected server.

First execute d65_load.nut and position d65_origin near the connected player.
Run as a user allowed to read both process memories. No debugger may be attached.
"""
import argparse
import json
from pathlib import Path
import re
import time

from d65_runtime import console, snapshot

def synchronized(frame, indices):
    server={s['index']:s for s in frame['server']['slots']}
    client={s['index']:s for s in frame['client']['slots']}
    return all(server[i]['pointer'] and client[i]['pointer'] and client[i]['stable_slot']
               and client[i]['serial']==(server[i]['serial']&1023)
               and all(abs(a-b)<.13 for a,b in zip(server[i]['origin'],client[i]['origin']))
               for i in indices)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--session',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--client-pid',type=int,required=True)
    ap.add_argument('--counts',type=int,nargs='+',default=[16,64,128,256,512])
    ap.add_argument('--prefix',default='load')
    a=ap.parse_args()
    if any(n not in [16,64,128,256,512] for n in a.counts):ap.error('unsupported load')
    pid=json.loads((a.session/'session.json').read_text())['pid']
    a.out.mkdir(parents=True,exist_ok=True)
    log=(a.out/f'{a.prefix}-commands.log').open('w',buffering=1)
    def cmd(s):
        t=console(a.session,[s],.15);log.write(t);return t
    results=[]
    for count in a.counts:
        stage=f'{a.prefix}{count}'
        cmd(f'script d65_create({count})');time.sleep(.8)
        ids=[int(i) for i in re.findall(r'D65_TARGET idx=(\d+)',cmd('script d65_report()'))]
        if len(ids)!=count or len(set(ids))!=count:raise RuntimeError('wrong live target set')
        def snap(label):return snapshot(pid,a.client_pid,ids,a.out,f'{stage}-{label}',a.session)
        row=dict(count=count,indices=ids,create_sync=synchronized(snap('created'),ids))
        for seq in range(1,7):
            cmd(f'script d65_step({seq})');time.sleep(.45)
            before=snap(f'seq{seq}');row[f'seq{seq}']=synchronized(before,ids)
        cmd('script d65_remove()');time.sleep(.8)
        empty=snap('deleted')
        deleted=[s['index'] for s in empty['server']['slots'] if not s['pointer']]
        old={s['index']:s for s in before['server']['slots']}
        client={s['index']:s for s in empty['client']['slots']}
        row['removed_count']=len(deleted)
        row['remove_sync']=len(deleted)==count//2 and all(not client[i]['pointer'] for i in deleted)
        row['old_before_reuse']=cmd('script d65_old_check()')
        time.sleep(1.1);cmd('script d65_reuse()');time.sleep(.8)
        after=snap('reused');row['reuse_sync']=synchronized(after,ids)
        row['serial_increment']=all(s['serial']==((old[s['index']]['serial']+1)&32767)
                                    for s in after['server']['slots'] if s['index'] in deleted)
        row['old_after_reuse']=cmd('script d65_old_check()')
        results.append(row)
        (a.out/f'{a.prefix}-results.json').write_text(json.dumps(results,indent=2)+'\n')
        if not all(v for v in row.values() if isinstance(v,bool)):
            raise RuntimeError('first failed load; evidence saved, stop pressure')
        print(f'{stage}: create/update/delete/reuse passed',flush=True)

if __name__=='__main__':main()
