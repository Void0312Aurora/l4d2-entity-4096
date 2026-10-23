const base = Process.findModuleByName("engine_srv.so").base;
function u32(p){ try { return p.readU32(); } catch(e){ return 0; } }
const N = {wde:0, send:0, gsf:0, alloc:0, signon:0, setsnap:0};
function log(o){ send(o); }
function hook(off, name, handlers){
  try { Interceptor.attach(base.add(off), handlers); }
  catch(e){ log({ev:"hook_error", name:name, err:String(e)}); }
}
hook(0x1DD830, "WDE", {
  onEnter(args){
    N.wde++;
    const client=args[1], fr=args[3];
    if (N.wde<=5 || N.wde%200===0)
      log({ev:"WDE", n:N.wde, client:client.toString(), signon:u32(client.add(0xEC)),
           frame:fr.toString(), snap:u32(fr.add(0x218))});
  }
});
hook(0xEA970, "SendSnapshot", {
  onEnter(args){
    N.send++;
    const th=args[0], fr=args[1];
    if (N.send<=5 || N.send%100===0)
      log({ev:"SendSnapshot", n:N.send, th:th.toString(), signon:u32(th.add(0xEC)),
           frame:fr.toString(), snap:u32(fr.add(0x218)), tick:u32(fr.add(0x8))});
  }
});
hook(0x1D9EB0, "GetSendFrame", {
  onEnter(){
    N.gsf++;
    const th=this.context.ebx;
    if (N.gsf<=5 || N.gsf%500===0)
      log({ev:"GetSendFrame", n:N.gsf, th:th.toString(), signon:u32(th.add(0xEC))});
  }
});
hook(0x1058F0, "AllocateFrame", {
  onEnter(args){ N.alloc++; this.th=args[0]; },
  onLeave(ret){ if (N.alloc<=5 || N.alloc%200===0) log({ev:"AllocFrame", n:N.alloc, mgr:this.th.toString(), frame:ret.toString(), vt:u32(ret), snap:u32(ret.add(0x218))}); }
});
hook(0x105630, "SetSnapshot", {
  onEnter(args){ N.setsnap++; if (N.setsnap<=5 || N.setsnap%100===0) log({ev:"SetSnapshot", n:N.setsnap, frame:args[0].toString(), snap:args[1].toString(), old:u32(args[0].add(0x218))}); }
});
hook(0xE73B0, "ProcessSignonState", {
  onEnter(args){ N.signon++; if (N.signon<=8) log({ev:"SignonState", n:N.signon, client:args[0].toString(), cur:u32(args[0].add(0xEC)), msg:args[1].toString()}); }
});
log({ev:"loaded", base:base.toString()});
