#!/usr/bin/env python3
"""GDB Python probe for the Linux srcds engine: activation + outbound messages.

Environment:
  N27_SERVER_OUT       JSONL output path
  N27_SERVER_BASE      engine_srv.so mapping base (hex)
  N27_SERVER_VTABLES   JSON map {hex rva: class name}
  N27_RUN_ID           run id
"""
import gdb, json, os, struct, time
from datetime import datetime, timezone

BASE = int(os.environ["N27_SERVER_BASE"], 16)
OUT = open(os.environ["N27_SERVER_OUT"], "w", buffering=1)
RUN = os.environ.get("N27_RUN_ID", "?")
try:
    VT = {int(k, 16): v for k, v in json.load(open(os.environ["N27_SERVER_VTABLES"])).items()}
except Exception:
    VT = {}

def u32(addr):
    try:
        return struct.unpack("<I", gdb.selected_inferior().read_memory(addr, 4).tobytes())[0]
    except Exception:
        return None

def u8(addr):
    try:
        return gdb.selected_inferior().read_memory(addr, 1).tobytes()[0]
    except Exception:
        return None

def emit(**kw):
    kw.update({"schema_version": "n27d20.server.v1", "run_id": RUN, "ts": datetime.now(timezone.utc).isoformat()})
    OUT.write(json.dumps(kw, sort_keys=True) + "\n")

def reg(name):
    try: return int(gdb.parse_and_eval("$" + name))
    except Exception: return None

def stack(i):
    esp = reg("esp")
    return u32(esp + 4 * i) if esp is not None else None

def cls_of(vptr):
    if vptr is None: return None, None
    rva = vptr - 8 - BASE
    return VT.get(rva), rva

class ReadFin(gdb.FinishBreakpoint):
    def __init__(self, obj):
        super().__init__(internal=True); self.obj=obj
    def stop(self):
        try: rv=int(self.return_value) & 0xff
        except Exception: rv=reg("eax")
        vals = {hex(o): u32(self.obj+o) for o in (0x4c,0x50,0x54,0x58)} if self.obj else None
        emit(event="read_signonstate_return", ret=rv, obj=self.obj, fields=vals,
             state=u32(self.obj+0x54) if self.obj else None)
        return False
    def out_of_scope(self):
        emit(event="read_signonstate_return", ret=None)

class BP(gdb.Breakpoint):
    def __init__(self, addr, name, kind):
        super().__init__("*0x%x" % (BASE + addr), internal=True)
        self.name = name; self.kind = kind
    def stop(self):
        # GCC i386 C++ passes `this` as the first stack argument.
        this = stack(1)
        if self.kind == "sendmsg":
            msg = stack(2); vptr = u32(msg) if msg else None
            cls, vrva = cls_of(vptr)
            emit(event="sendmsg", client=this, msg=msg, vptr=vptr,
                 vptr_rva=vrva, msg_class=cls)
        elif self.kind == "signonmsg":
            emit(event="signonmsg", client=this, state=stack(2), old=stack(3),
                 signon_state=u8(this + 0xEC) if this else None)
        elif self.kind == "readstore":
            emit(event="read_state_store", value=reg("eax"), site=self.name)
        elif self.kind == "readsignon":
            ebp = reg("ebp"); this_ebp = u32(ebp+8) if ebp else None
            emit(event="read_signonstate_enter", object=this, object_ebp=this_ebp,
                 ebp=ebp, eip=reg("eip"), bfread=stack(2))
            ReadFin(this_ebp or this)
        elif self.kind == "procmsg":
            self.n = getattr(self, "n", 0) + 1
            if self.n % 100 == 0:
                emit(event="processmessages_tick", count=self.n)
        elif self.kind == "setsignon":
            emit(event="setsignon", client=this, requested=stack(2),
                 before=u8(this + 0xEC) if this else None)
        else:
            emit(event=self.name, client=this,
                 signon_state=u8(this + 0xEC) if this else None)
        return False

for addr, name, kind in (
    (0xEA5C0, "sendmsg", "sendmsg"),
    (0xEA1A0, "signonmsg", "signonmsg"),
    (0xE96D0, "setsignon", "setsignon"),
    (0xE9740, "activateplayer", "plain"),
    (0xEBA70, "spawnplayer", "plain"),
    (0xEBD50, "sendsignondata", "plain"),
    (0xA8083, "readsignon2", "readsignon"),
    (0x1A6460, "procmsg", "procmsg"),
    (0xA81E5, "store_a", "readstore"),
    (0xA836E, "store_b", "readstore"),
):
    BP(addr, name, kind)

emit(event="ready", base=hex(BASE), vtables=len(VT))
