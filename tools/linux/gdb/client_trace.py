import gdb, os, time
base = int(os.environ["CLIENT_BASE"], 16)
def w(s):
    print(s, flush=True)
t0 = time.time()
full = {"ptr": None}
class Ret(gdb.FinishBreakpoint):
    def __init__(self, tag, this, req, cur):
        super().__init__(internal=True)
        self.tag, self.this, self.req, self.cur = tag, this, req, cur
    def stop(self):
        after = None
        try: after = int(gdb.parse_and_eval("*(unsigned int*)(%d+0x68)" % self.this))
        except Exception: pass
        rv = None
        try: rv = int(self.return_value)
        except Exception: pass
        w("RET %s t=%.3f this=0x%x before=%s req=%s after=%s rv=%s" %
          (self.tag, time.time()-t0, self.this, self.cur, self.req, after, rv))
        if self.tag == "signon" and self.req == 6 and after == 6:
            full["ptr"] = self.this
            w("FULL_CACHED t=%.3f this=0x%x" % (time.time()-t0, self.this))
        return False
class SS(gdb.Breakpoint):
    def __init__(self):
        super().__init__("*0x%x" % (base + 0x93140), internal=True)
    def stop(self):
        try:
            this = int(gdb.parse_and_eval("$ecx"))
            req = int(gdb.parse_and_eval("*(unsigned int*)$esp + 0")) if False else int(gdb.parse_and_eval("*(unsigned int*)($esp+4)"))
            cur = int(gdb.parse_and_eval("*(unsigned int*)(%d+0x68)" % this))
            w("ENT signon t=%.3f this=0x%x before=%d req=%d" % (time.time()-t0, this, cur, req))
            Ret("signon", this, req, cur)
        except Exception as e:
            w("ERR signon %s" % e)
        return False
class PPE(gdb.Breakpoint):
    n = 0
    def __init__(self):
        super().__init__("*0x%x" % (base + 0x77140), internal=True)
    def stop(self):
        PPE.n += 1
        try:
            ecx = int(gdb.parse_and_eval("$ecx"))
            a0 = int(gdb.parse_and_eval("*(unsigned int*)($esp+4)"))
            st = -1
            if full["ptr"] is not None:
                try: st = int(gdb.parse_and_eval("*(unsigned int*)(%d+0x68)" % full["ptr"]))
                except Exception: pass
            if PPE.n <= 5 or PPE.n % 100 == 0:
                w("ENT ppe t=%.3f n=%d ecx=0x%x arg0=0x%x state=%d ecx_is_client=%s" %
                  (time.time()-t0, PPE.n, ecx, a0, st, ecx == full["ptr"]))
            if PPE.n <= 5:
                Ret("ppe", full["ptr"] or a0, -1, -1)
        except Exception as e:
            w("ERR ppe %s" % e)
        return False
SS(); PPE()
w("TRACE base=0x%x" % base)
