#!/usr/bin/env python3
"""Read a pinned D61+ server list; stop briefly for a consistent snapshot.

The same inspect() function is used inside GDB at completed add/remove stops.
No inferior function calls, binary writes, or Steam installation changes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import time


def verify_relocations(read, base, image):
    """Compare the relocated live ELF words with their file-backed addends."""
    phoff=struct.unpack_from('<I',image,28)[0]
    phsize,phnum=struct.unpack_from('<HH',image,42)
    segments=[struct.unpack_from('<IIIIIIII',image,phoff+i*phsize) for i in range(phnum)]
    shoff=struct.unpack_from('<I',image,32)[0]
    shsize,shnum=struct.unpack_from('<HH',image,46)
    failures=[]
    checked=0
    for i in range(shnum):
        sec=struct.unpack_from('<IIIIIIIIII',image,shoff+i*shsize)
        if sec[1]!=9:  # SHT_REL
            continue
        for off in range(sec[4],sec[4]+sec[5],sec[9]):
            target,info=struct.unpack_from('<II',image,off)
            if info&255!=8:
                continue
            for typ,fileoff,va,_,filesz,*_ in segments:
                if typ==1 and va<=target<va+filesz:
                    addend=struct.unpack_from('<I',image,fileoff+target-va)[0]
                    if 0x1060000<=addend<0x1080038:
                        actual=struct.unpack('<I',read(base+target,4))[0]
                        checked+=1
                        if actual!=base+addend:
                            failures.append(dict(target=target,addend=addend,actual=actual))
                    break
    return dict(checked=checked,failures=failures,passed=checked==587 and not failures)


def inspect(read, base):
    def u32(p):
        return struct.unpack('<I', read(p, 4))[0]

    entlist = base + 0x1060000
    data = read(entlist, 0x20038)
    slots = [struct.unpack_from('<IIII', data, 4 + i*16) for i in range(8192)]
    errors = []

    def chain(offset, occupied):
        head, tail = struct.unpack_from('<II', data, offset)
        node, prev, indices = head, 0, []
        seen = set()
        while node:
            delta = node - entlist - 4
            if delta % 16 or not 0 <= delta//16 < 8192 or node in seen:
                errors.append(f'bad/cyclic node {node:#x} at {offset:#x}')
                break
            seen.add(node)
            i = delta//16
            ptr, serial, back, nxt = slots[i]
            if back != prev or bool(ptr) != occupied:
                errors.append(f'link/occupancy mismatch #{i} at {offset:#x}')
            indices.append(i)
            prev, node = node, nxt
        if prev != tail:
            errors.append(f'tail mismatch at {offset:#x}')
        return dict(head=head, tail=tail, indices=indices)

    active = chain(0x20004, True)
    free = chain(0x2000c, False)
    occupied = {i for i,s in enumerate(slots) if s[0]}
    nonnet = {i for i in occupied if i > 4096}
    if set(active['indices']) != occupied:
        errors.append('active list omits/duplicates occupied slots')
    if set(free['indices']) != set(range(4097,8192))-nonnet:
        errors.append('non-network free list has missing or foreign nodes')
    if slots[4096][0] or slots[4096][2:] != (entlist+4+4096*16,)*2:
        errors.append('reserved slot is occupied or linked')
    rows = []
    handle_errors = []
    for i in sorted(occupied):
        ptr, serial, prev, nxt = slots[i]
        row = dict(index=i, pointer=ptr, serial=serial, prev=prev, next=nxt)
        try:
            vt = u32(ptr)
            ti = u32(vt-4)
            namep = u32(ti+4)
            row['rtti'] = read(namep,160).split(b'\0',1)[0].decode('ascii','replace')
            handle = u32(ptr+237*4)
            row['handle'] = handle
            row['handle_valid'] = handle != 0xffffffff and handle&0x1fff == i and handle>>13 == serial
            row['networkable'] = u32(ptr+48)
            if not row['handle_valid']:
                handle_errors.append(i)
        except (OSError, ValueError, RuntimeError) as e:
            row['error'] = str(e)
            handle_errors.append(i)
        rows.append(row)
    sky = [r for r in rows if 'CSkyCamera' in r.get('rtti','')]
    return dict(entity_list=entlist, array_start=entlist+4, array_end=entlist+0x20004,
                active=active, nonnetwork_free=free, occupied=rows,
                slots=[dict(index=i,pointer=p,serial=s,prev=b,next=n) for i,(p,s,b,n) in enumerate(slots)],
                sky=sky, errors=errors, handle_errors=handle_errors,
                assertions=dict(FREELIST_INTEGRITY_OK=not errors,
                    HANDLE_ROUNDTRIP_OK=not handle_errors,
                    SKYCAMERA_HANDLE_VALID=bool(sky) and all(r.get('handle_valid') for r in sky),
                    NON_NETWORK_SLOT_IN_RANGE=all(r['index']>4096 for r in rows if not r.get('networkable',1)),
                    NETWORK_SLOT_IN_RANGE=all(r['index']<4096 for r in rows if r.get('networkable',0))))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pid',type=int)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    proc=Path(f'/proc/{a.pid}')
    if (proc/'comm').read_text().strip() != 'srcds_linux':
        ap.error('expected isolated srcds_linux')
    maps=(proc/'maps').read_text()
    module=next(l.split(maxsplit=5) for l in maps.splitlines()
                if l.endswith('/server_srv.so') and l.split()[2]=='00000000')
    base=int(module[0].split('-')[0],16)
    fd=os.open(proc/'mem',os.O_RDONLY)
    stopped=False
    try:
        os.kill(a.pid,signal.SIGSTOP)
        stopped=True
        for _ in range(100):
            if (proc/'status').read_text().split('State:')[1].lstrip().startswith('T'):
                break
            time.sleep(.01)
        else:
            raise RuntimeError('process did not stop')
        report=inspect(lambda p,n:os.pread(fd,n,p),base)
        report['relocations']=verify_relocations(lambda p,n:os.pread(fd,n,p),base,Path(module[5]).read_bytes())
        report.update(pid=a.pid,time=time.time(),server_base=base,
                      server_sha256=hashlib.sha256(Path(module[5]).read_bytes()).hexdigest(),maps=maps)
    finally:
        os.close(fd)
        if stopped:
            os.kill(a.pid,signal.SIGCONT)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['pid','entity_list','sky','errors','handle_errors','assertions']},indent=2))


if __name__=='__main__':
    main()
