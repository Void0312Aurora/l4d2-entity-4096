const base = Process.findModuleByName("engine_srv.so").base;
function u32(p){ try { return p.readU32(); } catch(e){ return 0; } }
const C = {wde:0, send:0, gsf:0, alloc:0, signon:0, setsnap:0, netpkt:0,
           connect:0, freeclient:0, finishcert:0, authresp:0, authhelper:0, hook_errors:0};
function hook(off, name, handlers){
  try { Interceptor.attach(base.add(off), handlers); }
  catch(e){ C.hook_errors++; send({ev:"hook_error", name:name, err:String(e)}); }
}
hook(0x1DD830, "WDE", {
  onEnter(args){
    C.wde++;
    this.client=args[1]; this.fFrom=args[2]; this.fTo=args[3]; this.w=args[4];
    this.bits0 = this.w.isNull() ? 0 : u32(this.w.add(0xC));
  },
  onLeave(ret){
    if (C.wde<=3 || C.wde%100===0) {
      const w=this.w.isNull()?0:u32(this.w.add(0xC));
      send({ev:"WDE", n:C.wde, signon:u32(this.client.add(0xEC)),
        from:this.fFrom.toString(), from_tick:u32(this.fFrom.add(0x8)), from_snap:u32(this.fFrom.add(0x218)),
        to:this.fTo.toString(), to_tick:u32(this.fTo.add(0x8)), to_snap:u32(this.fTo.add(0x218)),
        bits:(w-this.bits0), total_bits:w});
    }
  }
});
hook(0xEA970, "SendSnapshot", { onEnter(args){
  C.send++;
  const th=args[0], fr=args[1];
  if (C.send<=3 || C.send%100===0)
    send({ev:"SendSnapshot", n:C.send, signon:u32(th.add(0xEC)), frame:fr.toString(), snap:u32(fr.add(0x218))});
}});
hook(0x1D9EB0, "GetSendFrame", { onEnter(){
  C.gsf++;
}});
hook(0x1058F0, "AllocateFrame", { onEnter(args){ C.alloc++; },
  onLeave(ret){ if (C.alloc<=3) send({ev:"AllocFrame", n:C.alloc, frame:ret.toString(), vt:u32(ret)}); }});
hook(0x105630, "SetSnapshot", { onEnter(args){ C.setsnap++;
  if (C.setsnap<=3) send({ev:"SetSnapshot", n:C.setsnap, frame:args[0].toString(), snap:args[1].toString()}); }});
hook(0xE73B0, "ProcessSignonState", {
  onEnter(args){
    C.signon++;
    this.th=args[0]; this.msg=args[1];
    this.before=u32(this.th.add(0xEC));
    this.requested=u32(this.msg.add(0x4C));
  },
  onLeave(ret){
    send({ev:"Signon", n:C.signon, client:this.th.toString(),
      before:this.before, requested:this.requested,
      after:u32(this.th.add(0xEC)), retval:ret.toInt32()});
  }
});
hook(0x0FAD80, "ConnectClient", { onEnter(){ C.connect++;
  if (C.connect<=4) send({ev:"ConnectClient", n:C.connect}); }});
hook(0x0FAB90, "GetFreeClientInternal", { onEnter(){ C.freeclient++; }});
hook(0x1EBBF0, "FinishCertificateCheck", { onEnter(){ C.finishcert++;
  if (C.finishcert<=4) send({ev:"FinishCert", n:C.finishcert}); }});
hook(0x2014D0, "OnValidateAuthTicketResponse", { onEnter(){ C.authresp++;
  if (C.authresp<=4) send({ev:"AuthResponse", n:C.authresp}); }});
hook(0x201040, "OnValidateAuthTicketResponseHelper", { onEnter(args){ C.authhelper++;
  if (C.authhelper<=6) send({ev:"AuthHelper", n:C.authhelper,
      client:args[1].toString(), code:args[2].toInt32()}); }});
let bigDumps=0;
hook(0x1B8200, "NET_SendPacket", { onEnter(args){ C.netpkt++;
  const size=args[4].toInt32();
  if (C.netpkt<=5 || C.netpkt%50===0) send({ev:"NetSend", n:C.netpkt, size:size});
  if (size>500 && bigDumps<3) {
    bigDumps++;
    let hex="";
    try { hex=Array.from(new Uint8Array(args[3].readByteArray(Math.min(size,64))))
      .map(x=>x.toString(16).padStart(2,'0')).join(''); } catch(e){ hex="err"; }
    send({ev:"BigPacket", n:C.netpkt, size:size, hex:hex});
  }
}});
setInterval(function(){ send({ev:"counts", c:C}); }, 5000);
send({ev:"loaded", base:base.toString(), counts:C});
