// Keep references across successive 2048, 2095 and 4095 boundary steps.
local first = ::n27_first_index
local count = (first == 4095) ? 1 : 2
local player = Entities.FindByClassname(null, "player")
if (!("d62_fillers" in getroottable())) ::d62_fillers <- []
if (!("d62_targets" in getroottable())) ::d62_targets <- []
printl("D62_BEGIN first=" + first)
local last = -1
while (last < first-1) {
    local e = SpawnEntityFromTable("info_target", {origin=Vector(0,0,-12000)})
    if (!e) throw "D62 filler allocation failed"
    last=e.GetEntityIndex()
    d62_fillers.append(e)
    if (last >= first) throw "D62 crossed requested target"
}
for (local n=0; n<count; ++n) {
    local pos = player ? player.GetOrigin()+Vector(96+96*n,0,24) : Vector(0,0,0)
    local e = SpawnEntityFromTable("prop_dynamic_override", {
        model="models/props_c17/oildrum001.mdl", origin=pos, solid=0,
        targetname="n27_d62_"+(first+n)
    })
    if (!e || e.GetEntityIndex()!=first+n) throw "D62 wrong target index"
    d62_targets.append(e)
    printl("D62_TARGET idx="+e.GetEntityIndex()+" origin="+e.GetOrigin())
}
printl("D62_DONE first="+first)
