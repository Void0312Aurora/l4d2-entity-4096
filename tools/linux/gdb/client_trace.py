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
edb = os.environ.get("ENGINE_DLL_BASE")
if edb:
    ebase = int(edb, 16)
    def _mk_entry(off, name):
        class _E(gdb.Breakpoint):
            n = 0
            post = 0
            def __init__(self):
                super().__init__("*0x%x" % (ebase + off), internal=True)
            def stop(self):
                _E.n += 1
                if full["ptr"] is not None and _E.post < 3:
                    _E.post += 1
                    try: ra = int(gdb.parse_and_eval("*(unsigned int*)$esp"))
                    except Exception: ra = 0
                    w("ENTRYPOST %s n=%d t=%.3f ra=0x%x" % (name, _E.n, time.time()-t0, ra))
                return False
        _E()
    def _mk_probe(off, name, regs):
        class _P(gdb.Breakpoint):
            total = 0
            post = 0
            def __init__(self):
                super().__init__("*0x%x" % (ebase + off), internal=True)
            def stop(self):
                _P.total += 1
                if full["ptr"] is not None:
                    _P.post += 1
                    if name == "finalCall":
                        try: tgt = int(gdb.parse_and_eval("$eax"))
                        except Exception: tgt = 0
                        TGT[tgt] = TGT.get(tgt, 0) + 1
                        if TGT[tgt] == 1:
                            try: edx = int(gdb.parse_and_eval("$edx")); esi = int(gdb.parse_and_eval("$esi"))
                            except Exception: edx, esi = 0, 0
                            w("TARGET new tgt=0x%x edx=0x%x esi=0x%x" % (tgt, edx, esi))
                    if _P.post <= 8:
                        vals = []
                        for r in regs:
                            try: vals.append("%s=%d" % (r, int(gdb.parse_and_eval("$"+r))))
                            except Exception: vals.append(r+"=?")
                        try: ra = int(gdb.parse_and_eval("*(unsigned int*)$esp"))
                        except Exception: ra = 0
                        w("PROBE %s post=%d total=%d ra=0x%x %s" %
                          (name, _P.post, _P.total, ra, " ".join(vals)))

                    elif _P.total % 200 == 0:
                        w("PROBE %s post=%d total=%d" % (name, _P.post, _P.total))
                return False
        _P()
    TGT = {}
    _mk_probe(0x1BC2E9, "callCond", ["edi"])
    _mk_probe(0x1BC2EE, "afterCond", ["al"])
    _mk_probe(0x1BC2F0, "jzCond", ["al","eflags"])
    _mk_probe(0x1BC301, "finalCall", ["eax","edx","esi","edi"])
    for _o,_n in ((0x1CDDF0,"CDDF0"),(0x1BCA20,"BCA20"),(0x1BC800,"BC800"),(0x1BBCF0,"BBCF0")):
        _mk_entry(_o,_n)
    class E56IN(gdb.Breakpoint):
        n = 0
        post = 0
        def __init__(self):
            super().__init__("*0x%x" % (ebase + 0x56E60), internal=True)
        def stop(self):
            E56IN.n += 1
            if full["ptr"] is not None and E56IN.post < 3:
                E56IN.post += 1
                try:
                    ra = int(gdb.parse_and_eval("*(unsigned int*)$esp"))
                    bt = gdb.execute("bt 6", to_string=True).replace("\n", " | ")[:500]
                except Exception:
                    ra, bt = 0, ""
                w("ENTRYPOST E56E60 n=%d t=%.3f ra=0x%x bt=%s" % (E56IN.n, time.time()-t0, ra, bt))
            elif E56IN.n <= 3:
                w("ENTRY E56E60 n=%d t=%.3f afterfull=False" % (E56IN.n, time.time()-t0))
            return False
    E56IN()
    for _off,_name in ((0x56E6B,"E56E60"),(0x1EC292,"E1EC1D0"),(0xD32F6,"E0D3210")):
        class EB(gdb.Breakpoint):
            def __init__(self, off, name):
                super().__init__("*0x%x" % (ebase + off), internal=True)
                self.bname = name
            def stop(self):
                if full["ptr"] is not None:
                    w("POSTFULL %s t=%.3f" % (self.bname, time.time()-t0))
                return False
        EB(_off, _name)
    w("TRACE engine_dll_base=0x%x" % ebase)
cdb = os.environ.get("CLIENT_DLL_BASE")
if cdb:
    cbase = int(cdb, 16)
    class LIPE(gdb.Breakpoint):
        n = 0
        def __init__(self):
            super().__init__("*0x%x" % (cbase + 0x179DB0), internal=True)
        def stop(self):
            LIPE.n += 1
            w("ENT levelinit t=%.3f n=%d" % (time.time()-t0, LIPE.n))
            return False
    LIPE()
    class LEVFI(gdb.Breakpoint):
        n = 0
        def __init__(self):
            super().__init__("*0x%x" % (cbase + 0x1A0FBF), internal=True)
        def stop(self):
            LEVFI.n += 1
            try:
                bt = gdb.execute("bt 8", to_string=True).replace("\n", " | ")[:600]
            except Exception:
                bt = ""
            w("EVT levelfinished t=%.3f n=%d bt=%s" % (time.time()-t0, LEVFI.n, bt))
            return False
    LEVFI()
    w("TRACE client_dll_base=0x%x" % cbase)
w("TRACE base=0x%x" % base)
