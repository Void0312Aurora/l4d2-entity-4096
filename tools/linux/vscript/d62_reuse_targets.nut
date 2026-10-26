// Run after actual deletion of the five targets, with only the final 64
// fillers removed. The normal edict allocator must return the released slots.
::d62_oldtargets <- d62_targets
::d62_targets = []
local player=Entities.FindByClassname(null,"player")
foreach (idx in [2048,2049,2095,2096,4095]) {
    if (idx==4095) {
        local last=-1
        while (last<4094) {
            local f=SpawnEntityFromTable("info_target", {origin=Vector(0,0,-12000)})
            if (!f) throw "D62 reuse filler failed"
            last=f.GetEntityIndex()
            d62_fillers.append(f)
            if (last>=4095) throw "D62 reuse crossed target"
        }
    }
    local e=SpawnEntityFromTable("prop_dynamic_override", {
        model="models/props_c17/oildrum001.mdl", solid=0,
        origin=player.GetOrigin()+Vector(96,0,24), targetname="n27_d62_reused_"+idx
    })
    if (!e || e.GetEntityIndex()!=idx) throw "D62 wrong reused index"
    d62_targets.append(e)
    printl("D62_REUSED idx="+idx)
}
foreach (old in d62_oldtargets) printl("D62_REUSED_OLD_VALID="+old.IsValid())
printl("D62_REUSE_DONE")
