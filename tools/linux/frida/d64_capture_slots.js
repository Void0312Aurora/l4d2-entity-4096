// D64: observe the legal Hunter player allocator and the NUM_FOR_EDICT call
// used by SetFakeClientConVarValue. Run against an isolated srcds process.
const engine = Process.getModuleByName('engine_srv.so');
const server = Process.getModuleByName('server_srv.so');
const alloc = server.enumerateSymbols().find(s => s.name === '_ZN6Hunter20AllocatePlayerEntityEP7edict_tPKc');
const num = engine.enumerateSymbols().find(s => s.name === '_Z13NUM_FOR_EDICTPK7edict_t');

function state() {
  const edictBase = engine.base.add(0x3a8174).readPointer();
  return {
    engine_base: engine.base.toString(),
    edict_base: edictBase.toString(),
    num_edicts: engine.base.add(0x3a816c).readU32(),
    max_edicts: engine.base.add(0x3a8170).readU32(),
    stride: 16
  };
}

if (!alloc || !num) throw new Error('D64 symbols unavailable');
send({event: 'hooks-ready', pid: Process.id, arch: Process.arch, ...state()});

Interceptor.attach(alloc.address, {
  onEnter(args) {
    const s = state();
    const p = args[0];
    send({
      event: 'Hunter_AllocatePlayerEntity',
      edict: p.toString(),
      index: p.sub(ptr(s.edict_base)).toInt32() / s.stride,
      classname: args[1].readCString(),
      ...s
    });
  }
});

Interceptor.attach(num.address, {
  onEnter(args) {
    this.p = args[0];
    this.caller = DebugSymbol.fromAddress(this.returnAddress).toString();
    this.report = this.caller.includes('SetFakeClientConVarValue');
    if (this.report) {
      const s = state();
      send({
        event: 'NUM_FOR_EDICT_SetFake_enter',
        edict: this.p.toString(),
        index: this.p.isNull() ? null : this.p.sub(ptr(s.edict_base)).toInt32() / s.stride,
        ...s,
        caller: this.caller
      });
    }
  },
  onLeave(rv) {
    if (this.report) send({event: 'NUM_FOR_EDICT_SetFake_return', index: rv.toInt32()});
  }
});
