import gdb, json, os, struct
from datetime import datetime, timezone
E = int(os.environ["N27_MODULE_BASE_ENGINE"], 16)
OUT = open(os.environ["N27_SIGNON_OUT"], "w", buffering=1)
RUN = os.environ.get("N27_RUN_ID", "?")
VT_NS = 0x3575CC  # ??_7NET_SignonState@@6B@

def u32(a):
    try: return struct.unpack("<I", gdb.selected_inferior().read_memory(a,4).tobytes())[0]
    except Exception: return None

def reg(n):
    try: return int(gdb.parse_and_eval("$"+n))
    except Exception: return None

def emit(**kw):
    kw.update(schema="n27d21.client.signon.v1", run_id=RUN,
              ts=datetime.now(timezone.utc).isoformat())
    OUT.write(json.dumps(kw, sort_keys=True)+"\n")

class SendBP(gdb.Breakpoint):
    def __init__(self, addr):
        super().__init__("*0x%x" % addr, internal=True)
    def stop(self):
        esp = reg("esp"); netchan = reg("ecx")
        msg = u32(esp+4) if esp else None
        vptr = u32(msg) if msg else None
        rva = (vptr - E) if vptr else None
        rec = dict(event="send_netmsg", netchan=netchan, msg=msg, vptr_rva=rva)
        if rva == VT_NS:
            rec.update(event="send_signonstate", state=u32(msg+0x54), spawn_count=u32(msg+0x58))
        emit(**rec)
        return False

class Finish(gdb.FinishBreakpoint):
    def __init__(self, tag):
        super().__init__(internal=True); self.tag = tag
    def stop(self):
        try: rv = int(self.return_value)
        except Exception: rv = None
        emit(event="set_signon_return", tag=self.tag, ret=rv)
        return False
    def out_of_scope(self):
        emit(event="set_signon_return", tag=self.tag, ret=None)

send_bp = None
class SetBP(gdb.Breakpoint):
    def __init__(self):
        super().__init__("*0x%x" % (E + 0x93140), internal=True)
    def stop(self):
        global send_bp
        esp = reg("esp"); this = reg("ecx")
        state = u32(esp+4) if esp else None
        netchan = u32(this+16) if this else None
        vt = u32(netchan) if netchan else None
        fn = u32(vt+0xA4) if vt else None
        emit(event="set_signon_entry", clientstate=this, state=state,
             netchan=netchan, send_fn=fn,
             send_fn_rva=(fn-E) if fn else None,
             current_state=u32(this+0x68) if this else None)
        if fn and send_bp is None and 0 <= fn-E < 0x600000:
            send_bp = SendBP(fn)
            emit(event="send_bp_installed", addr=fn, rva=fn-E)
        Finish(state)
        return False

SetBP()
emit(event="ready", engine=hex(E), vt_ns=hex(E+VT_NS))
