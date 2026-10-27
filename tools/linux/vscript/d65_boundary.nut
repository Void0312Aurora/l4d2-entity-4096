// Use normal ED_Alloc's one-second free-edict cooldown to grow the high-water
// mark without filling the live pool. First kill our low fillers and allow one
// frame to complete; invoke this script within one second of that removal.
// Game time must already exceed two seconds. Existing high props stay alive.
// No index/serial/count writes and no forced-index factory calls.
::d65_edge_fillers <- []
local last = -1
while (last < 4094) {
    local e=SpawnEntityFromTable("info_target", {origin=Vector(0,0,-12000),targetname="d65_edge_filler"})
    if (!e) throw "D65 boundary filler failed"
    last=e.GetEntityIndex()
    d65_edge_fillers.append(e)
    if (last>4094 || d65_edge_fillers.len()>2200) throw "D65 boundary missed cooldown window"
}
::d65_edge <- SpawnEntityFromTable("prop_dynamic_override", {
    model="models/props_c17/oildrum001.mdl",origin=d65_origin,solid=0,targetname="d65_edge"
})
if (!d65_edge || d65_edge.GetEntityIndex()!=4095) throw "D65 boundary wrong target"
printl("D65_BOUNDARY_CREATED index="+d65_edge.GetEntityIndex()+" fillers="+d65_edge_fillers.len()+" time="+Time())
