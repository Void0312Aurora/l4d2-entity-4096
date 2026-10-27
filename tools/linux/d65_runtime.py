#!/usr/bin/env python3
"""Small D65 console/memory helpers for pinned, isolated D62 builds.

Run the driver with sudo for /proc/PID/mem. No inferior calls or memory writes.
Server origin +0x2e0 was identified by a coordinate scan and verified by moves;
client complete-object origin +0x124 is pinned by the existing D62 reader.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import struct
import time

from read_server_entities import inspect, verify_relocations


def console(session, commands, delay=.25):
    s = socket.socket(socket.AF_UNIX)
    s.connect(str(Path(session)/'console.sock'))
    s.sendall(('\n'.join(commands)+'\n').encode())
    s.settimeout(delay)
    chunks=[]
    while True:
        try:
            chunk=s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
        except TimeoutError:
            break
    s.close()
    return b''.join(chunks).decode(errors='replace')


def module(pid, suffix):
    lines=Path(f'/proc/{pid}/maps').read_text().splitlines()
    row=next(l.split(maxsplit=5) for l in lines if l.endswith(suffix) and l.split()[2]=='00000000')
    return int(row[0].split('-')[0],16), Path(row[5])


def snapshot(server_pid, client_pid, indices, out, label, observer_session=None):
    # Caller must supply an owned isolated process; protected port 27073 is rejected.
    cmd=Path(f'/proc/{server_pid}/cmdline').read_bytes().split(b'\0')
    if any(port in cmd for port in [b'27073', b'27074']):
        raise ValueError('protected server')
    if int(Path(f'/proc/{server_pid}/status').read_text().split('TracerPid:')[1].split()[0]):
        raise ValueError('detach the debugger before a SIGSTOP memory snapshot')
    sb, serverfile=module(server_pid,'/server_srv.so')
    eb, enginefile=module(server_pid,'/engine_srv.so')
    fd=os.open(f'/proc/{server_pid}/mem',os.O_RDONLY)
    def read(p,n):
        return os.pread(fd,n,p)
    def u32(p):
        return struct.unpack('<I',read(p,4))[0]
    try:
        os.kill(server_pid,signal.SIGSTOP)
        for _ in range(100):
            if Path(f'/proc/{server_pid}/status').read_text().split('State:')[1].lstrip().startswith('T'):
                break
            time.sleep(.005)
        else:
            raise RuntimeError('server did not stop')
        full=inspect(read,sb)
        edict_base=u32(eb+0x3a8174)
        rows=[]
        for i in indices:
            r=dict(full['slots'][i])
            p=r['pointer']
            if p:
                r.update(handle=u32(p+948),edict_pointer=u32(p+48),
                         origin=struct.unpack('<fff',read(p+0x2e0,12)))
                r['rtti']=next(x['rtti'] for x in full['occupied'] if x['index']==i)
                if r['edict_pointer']:
                    r['edict_words']=struct.unpack('<IIII',read(r['edict_pointer'],16))
                    r['edict_expected']=edict_base+i*16
            rows.append(r)
        server=dict(pid=server_pid, time=time.time(),base=sb,engine_base=eb,edict_base=edict_base,
                    num_edicts=u32(eb+0x3a816c),max_edicts=u32(eb+0x3a8170),slots=rows,
                    assertions=full['assertions'],errors=full['errors'],handle_errors=full['handle_errors'],
                    sky=full['sky'],relocations=verify_relocations(read,sb,serverfile.read_bytes()),
                    nonnet_occupied=sum(r['index']>4096 for r in full['occupied']),
                    network_occupied=sum(r['index']<4096 for r in full['occupied']),
                    nonnet_free=len(full['nonnetwork_free']['indices']))
    finally:
        os.close(fd)
        try:
            os.kill(server_pid,signal.SIGCONT)
        except ProcessLookupError:
            pass
    client=None
    if client_pid:
        cb, clientfile=module(client_pid,'/left4dead2/bin/client.dll')
        fd=os.open(f'/proc/{client_pid}/mem',os.O_RDONLY)
        try:
            # Read-only client sampling: each slot is re-read after its object.
            def read(p,n): return os.pread(fd,n,p)
            def u32(p): return struct.unpack('<I',read(p,4))[0]
            table=u32(cb+0x6c50ac)
            if table!=cb+0x963000:
                raise ValueError('unexpected client entity table')
            rows=[]
            for i in indices:
                raw=read(table+4+i*16,16)
                p,serial,_,_=struct.unpack('<IIII',raw)
                r=dict(index=i,pointer=p,serial=serial)
                if p:
                    vt=u32(p); col=u32(vt-4); complete=p-u32(col+4)
                    r.update(rtti=read(u32(col+12)+8,160).split(b'\0',1)[0].decode(errors='replace'),
                             complete_object=complete,origin=struct.unpack('<fff',read(complete+0x124,12)))
                    # DT_TerrorPlayer RecvProp registrations, verified in IDA.
                    if any(n in r['rtti'] for n in ['TerrorPlayer','Hunter','Spitter','Smoker','Boomer','Charger','Jockey']):
                        r['zombie_class']=u32(complete+7312)
                        r['life_state']=read(complete+0x147,1)[0]
                        r['health']=u32(complete+236)
                r['stable_slot']=raw==read(table+4+i*16,16)
                rows.append(r)
            engine_base, _ = module(client_pid, '/bin/engine.dll')
            # CL_ProcessPacketEntities reads CClientState +196, returned by
            # engine+82ca0 as *(engine+4268ec)+8. Sampled tick, not an ACK.
            observation_tick = u32(u32(engine_base+0x4268ec)+8+196)
            client=dict(pid=client_pid,time=time.time(),base=cb,slots=rows,
                        observation_tick=observation_tick)
        finally:
            os.close(fd)
    observer=None
    observer_dir = Path(observer_session) if observer_session else Path(out)/'server'
    sock=observer_dir/'frida.sock'
    meta = observer_dir/'session.json'
    if sock.exists() and meta.exists() and json.loads(meta.read_text())['pid'] == server_pid:
        s=socket.socket(socket.AF_UNIX);s.settimeout(2)
        s.connect(str(sock));s.sendall(json.dumps(indices).encode())
        chunks=[]
        while chunk:=s.recv(65536): chunks.append(chunk)
        s.close();observer=json.loads(b''.join(chunks))
    report=dict(label=label,time=time.time(),server=server,client=client,frida=observer)
    path=Path(out)/f'{label}.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    return report


def identity(pid, suffixes):
    result=dict(pid=pid,time=time.time(),cmdline=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode(),modules=[])
    for suffix in suffixes:
        base,path=module(pid,suffix)
        result['modules'].append(dict(path=str(path),base=base,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return result
