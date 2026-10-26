::d62_nonnet <- SpawnEntityFromTable("logic_relay", {targetname="n27_d62_nonnet"})
if (!d62_nonnet) throw "D62 non-network allocation failed"
// Non-network objects have edict index 0; their internal slot is read by GDB.
printl("D62_NONNET_CREATE edict_index="+d62_nonnet.GetEntityIndex()+" valid="+d62_nonnet.IsValid())
