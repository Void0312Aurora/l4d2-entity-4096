import gdb, json, os, struct
from datetime import datetime, timezone
E = int(os.environ["N27_MODULE_BASE_ENGINE"], 16)
OUT = open(os.environ["N27_SIGNON_OUT"], "w", buffering=1)
RUN = os.environ.get("N27_RUN_ID", "?")
VT_NS = 0x3575CC
ENTRY = E + 0x93140
EXPECTED = bytes.fromhex("558bec81ec10010000")

def u32(a):
    try: return struct.unpack("<I", gdb.selected_inferior().read_memory(a,4).tobytes())[0]
    except Exception: return None
def u8(a):
    try: return gdb.selected_inferior().read_memory(a,1).tobytes()[0]
    except Exception: return None
def reg(n):
    try: return int(gdb.parse_and_eval("$"+n))
    except Exception: return None
def emit(**kw):
    kw.update(schema="n27d21.client.signon.v1", run_id=RUN,
              ts=datetime.now(timezone.utc).isoformat())
    OUT.write(json.dumps(kw, sort_keys=True)+"\n")

try:
    actual = bytes(gdb.selected_inferior().read_memory(ENTRY, len(EXPECTED)).tobytes())
except Exception as exc:
    emit(event="install_failed", stage="read_entry", error=str(exc)); raise SystemExit(1)
if actual != EXPECTED:
    emit(event="install_failed", stage="bytes", expected=EXPECTED.hex(), actual=actual.hex())
    raise SystemExit(1)

class SendFin(gdb.FinishBreakpoint):
    def __init__(self, clientstate, state):
        super().__init__(internal=True); self.clientstate=clientstate; self.state=state
    def stop(self):
        try: rv=int(self.return_value) & 0xff
        except Exception: rv=reg("eax")
        emit(event="send_signonstate_return", state=self.state, ret=rv,
             client_state=u32(self.clientstate+0x68) if self.clientstate else None)
        return False
    def out_of_scope(self):
        emit(event="send_signonstate_return", state=self.state, ret=None)

class SendBP(gdb.Breakpoint):
    def __init__(self, addr):
        super().__init__("*0x%x" % addr, internal=True)
    def stop(self):
        esp=reg("esp"); netchan=reg("ecx")
        msg=u32(esp+4) if esp else None
        vptr=u32(msg) if msg else None
        rva=(vptr-E) if vptr else None
        if rva == VT_NS:
            st=u32(msg+0x54); emit(event="send_signonstate_enter", state=st,
                spawn_count=u32(msg+0x58), netchan=netchan, msg=msg)
            SendFin(u32(netchan+8) if netchan else None, st)
        else:
            emit(event="send_other", vptr_rva=rva, netchan=netchan)
        return False

class SetFin(gdb.FinishBreakpoint):
    def __init__(self, cs, state):
        super().__init__(internal=True); self.cs=cs; self.state=state
    def stop(self):
        try: rv=int(self.return_value) & 0xff
        except Exception: rv=reg("eax")
        emit(event="set_signon_return", requested=self.state, ret=rv,
             client_state=u32(self.cs+0x68) if self.cs else None)
        return False
    def out_of_scope(self):
        emit(event="set_signon_return", requested=self.state, ret=None)

send_bp=None
class SetBP(gdb.Breakpoint):
    def __init__(self):
        super().__init__("*0x%x" % ENTRY, internal=True)
    def stop(self):
        global send_bp
        esp=reg("esp"); cs=reg("ecx")
        state=u32(esp+4) if esp else None
        netchan=u32(cs+16) if cs else None
        vt=u32(netchan) if netchan else None
        fn=u32(vt+0xA4) if vt else None
        emit(event="set_signon_enter", requested=state, clientstate=cs,
             current_state=u32(cs+0x68) if cs else None,
             netchan=netchan, send_fn=fn)
        if fn and send_bp is None:
            send_bp=SendBP(fn)
            emit(event="send_bp_installed", rva=fn-E)
        SetFin(cs, state)
        return False

SetBP()
emit(event="ready", entry=hex(ENTRY), bytes=actual.hex(), vt_ns=hex(E+VT_NS))
