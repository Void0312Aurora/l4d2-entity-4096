// Only for the pinned D62 Linux server in a private experiment.
// Redirect one legal factory request's existing force-edict argument. No table
// or serial writes; the engine allocates/attaches/spawns the object normally.
const server = Process.getModuleByName('server_srv.so');
const engine = Process.getModuleByName('engine_srv.so');
let requested = null;
Interceptor.attach(server.base.add(0x6dfee0), {
  onEnter(args) {
    if (requested !== null && args[0].readCString() === 'prop_dynamic_override') {
      this.index = requested;
      args[1] = ptr(requested);
      requested = null;
      send({event:'forced_factory_enter', index:this.index, time_ms:Date.now()});
    }
  },
  onLeave(result) {
    if (this.index !== undefined) send({event:'forced_factory_return', index:this.index,
      entity:result.toString(), time_ms:Date.now()});
  }
});
rpc.exports = {
  arm(index) {
    if (index !== 4095) throw new Error('only the isolated boundary slot is allowed');
    if (!server.base.add(0x1060004+16*index).readPointer().isNull())
      throw new Error('boundary slot is occupied');
    // ED_Alloc(index) only reuses an existing free edict below num_edicts.
    // A never-created high slot is not a legal forced-allocation request.
    if (engine.base.add(0x3a816c).readU32() <= index)
      throw new Error('boundary slot has not been reached by normal allocation');
    const edict = engine.base.add(0x3a8174).readPointer().add(index*16);
    if ((edict.readU32() & 2) === 0) throw new Error('edict is not free');
    requested = index;
    return {pid:Process.id, index, armed:true};
  }
};
