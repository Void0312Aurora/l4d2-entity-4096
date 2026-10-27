// Build 23990068 / D62 pinned Linux image. Observe only an isolated process.
const engine = Process.getModuleByName('engine_srv.so');
const server = Process.getModuleByName('server_srv.so');
let snapshot = null;
let last = 0;
Interceptor.attach(engine.base.add(0x1dd830), {
  onEnter(args) {
    snapshot = {tick: args[2].add(8).readU32(), time_ms: Date.now()};
    if (Date.now() - last > 1000) {
      last = Date.now();
      send({event:'write_delta_entities', ...snapshot});
    }
  }
});
Process.setExceptionHandler(details => {
  send({event:'native_exception', details:details,
    stack:Thread.backtrace(details.context, Backtracer.ACCURATE).map(DebugSymbol.fromAddress).map(String)});
  return false;
});
rpc.exports = {
  capture(indices) {
    const table = server.base.add(0x1060000);
    const edictBase = engine.base.add(0x3a8174).readPointer();
    return {pid:Process.id, time_ms:Date.now(), snapshot,
      engine_base:engine.base.toString(), server_base:server.base.toString(),
      edict_base:edictBase.toString(), num_edicts:engine.base.add(0x3a816c).readU32(),
      max_edicts:engine.base.add(0x3a8170).readU32(),
      slots:indices.map(i => {
        const slot=table.add(4+i*16), entity=slot.readPointer();
        const row={entity_index:i,entity_pointer:entity.toString(),serial:slot.add(4).readU32()};
        if (!entity.isNull()) {
          const edict=entity.add(48).readPointer();
          row.handle=entity.add(948).readU32();
          row.edict_pointer=edict.toString();
          row.edict_expected=i<4096?edictBase.add(i*16).toString():null;
          row.rtti=entity.readPointer().sub(4).readPointer().add(4).readPointer().readCString();
          if (!edict.isNull()) row.edict_words=[0,4,8,12].map(n=>edict.add(n).readU32());
        }
        return row;
      })};
  }
};
send({event:'d65_observer_ready',pid:Process.id,arch:Process.arch});
