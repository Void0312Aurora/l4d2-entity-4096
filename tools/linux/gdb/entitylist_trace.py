"""GDB source file. D62_SESSION names an isolated session.json directory.

Run: sudo -E gdb -q -batch -ex 'attach PID' -x .../entitylist_trace.py
Records actual add/remove entry and completion, including empty-slot checks.
"""
import gdb
import json
import os
from pathlib import Path
import struct
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from read_server_entities import inspect

out = Path(os.environ['D62_SESSION'])
meta = json.loads((out/'session.json').read_text())
inferior = gdb.selected_inferior()
assert inferior.pid == meta['pid']
base = int(gdb.parse_and_eval('(unsigned int)&gEntList')) - 0x1060000
entlist = base + 0x1060000
log = (out/'entity-trace.jsonl').open('a', buffering=1)
pending_add = {}
pending_remove = {}
selected = {2047,2048,2049,2095,2096,4095}
selected_nonnet = int(os.environ.get('D62_NONNET_INDEX','0')) or None


def read(p,n):
    return bytes(inferior.read_memory(p,n))


def u32(p):
    return struct.unpack('<I',read(p,4))[0]


def slot(i):
    return struct.unpack('<IIII',read(entlist+4+16*i,16))


def emit(event, **fields):
    log.write(json.dumps(dict(event=event,time=time.time(),**fields))+'\n')


def snapshot(label):
    report=inspect(read,base)
    report.update(label=label,pid=inferior.pid,time=time.time(),server_base=base)
    (out/f'trace-{label}.json').write_text(json.dumps(report,indent=2)+'\n')
    emit('snapshot', label=label, assertions=report['assertions'],sky=report['sky'])


class Probe(gdb.Breakpoint):
    def __init__(self,offset,kind):
        self.kind=kind
        super().__init__(f'*{base+offset:#x}',internal=True)

    def stop(self):
        global selected_nonnet
        tid=gdb.selected_thread().global_num
        if self.kind=='add':
            sp=int(gdb.parse_and_eval('$esp'))
            result,this,obj,i,serial=struct.unpack('<IIIII',read(sp+4,20))
            assert this==entlist
            old=slot(i)
            caller=u32(sp)-base
            pending_add[tid]=dict(index=i,object=obj,result=result,old=old,caller=caller)
            emit('add_enter',**pending_add[tid],NO_SLOT_OVERWRITE=old[0]==0,
                 pool='network' if caller==0x43a54e else 'nonnetwork' if caller==0x43a5c7 else 'other',
                 stack=gdb.execute('bt 6',to_string=True) if old[0] else None)
        elif self.kind=='added':
            before=pending_add.pop(tid)
            i=before['index']; ptr,serial,prev,nxt=slot(i)
            if i>=4097 and selected_nonnet is None:
                selected_nonnet=i
            h=u32(before['result'])
            actual=u32(ptr+948)
            emit('add_done',index=i,pointer=ptr,serial=serial,handle=h,object_handle=actual,
                 HANDLE_ROUNDTRIP_OK=h==actual and h&8191==i and h>>13==serial)
            if i in selected or i==selected_nonnet:
                snapshot(f'add-{i}-{serial}')
        elif self.kind=='remove':
            sp=int(gdb.parse_and_eval('$esp'))
            this,i=struct.unpack('<II',read(sp+4,8))
            assert this==entlist
            old=slot(i)
            pending_remove[tid]=dict(index=i,old=old)
            emit('remove_enter',**pending_remove[tid],stack=gdb.execute('bt 8',to_string=True))
        else:
            before=pending_remove.pop(tid,None)
            if before:
                i=before['index']; now=slot(i)
                emit('remove_done',index=i,old=before['old'],now=now,
                     REMOVE_CONFIRMED=now[0]==0,
                     SERIAL_CONSISTENT=not before['old'][0] or now[1]==((before['old'][1]+1)&32767),
                     OLD_HANDLE_INVALID=now[0]==0 or now[1]!=before['old'][1])
                if i in selected or i==selected_nonnet:
                    snapshot(f'remove-{i}-{now[1]}')
        return False


class UtilityProbe(gdb.Breakpoint):
    def stop(self):
        sp=int(gdb.parse_and_eval('$esp'))
        i=u32(sp+4)
        if 2047<i<4096:
            emit('UTIL_EntityByIndex_high', index=i, slot=slot(i),
                 stack=gdb.execute('bt 5',to_string=True))
        return False


class SkyReturn(gdb.FinishBreakpoint):
    def stop(self):
        ptr=int(gdb.parse_and_eval('$eax'))
        emit('sky_return',pointer=ptr,handle=u32(ptr+948) if ptr else None)
        return False


class SkyProbe(gdb.Breakpoint):
    last=0
    def stop(self):
        if time.time()-self.last>1:
            self.last=time.time()
            SkyReturn(internal=True)
        return False


gdb.execute('set pagination off')
gdb.execute('set confirm off')
gdb.execute('set print thread-events off')
for sig in ['SIGPIPE','SIGUSR1','SIGUSR2','SIGCHLD']:
    gdb.execute(f'handle {sig} nostop noprint pass')
snapshot('initial')
for offset,kind in [(0x43a490,'add'),(0x43a50b,'added'),(0x43a620,'remove'),
                    (0x43a6c3,'removed'),(0x43a6ea,'removed')]:
    Probe(offset,kind)
UtilityProbe(f'*{base+0xb1b0b0:#x}',internal=True)
SkyProbe(f'*{base+0x812830:#x}',internal=True)
emit('ready',pid=inferior.pid,base=base)
try:
    gdb.execute('continue')
except KeyboardInterrupt:
    pass
if inferior.pid:
    emit('stopped',reason=gdb.execute('bt 20',to_string=True))
    (out/'stop-state.txt').write_text('\n'.join(
        gdb.execute(command,to_string=True) for command in
        ['info registers', 'p $_siginfo', 'x/20i $pc-24', 'bt 30', 'info proc mappings']))
    snapshot('final')
    gdb.execute('detach')
log.close()
