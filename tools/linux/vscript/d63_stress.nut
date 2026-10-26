// One-variable entity stress stage. Set d63_count and d63_rate in separate
// console script statements before executing this file. Repeated step calls
// are driven externally so the requested rate is measurable and bounded.
local count = ("d63_count" in getroottable()) ? ::d63_count : 64
local rate = ("d63_rate" in getroottable()) ? ::d63_rate : 10
if (count < 1 || count > 512 || rate < 1 || rate > 20) { printl("D63_STRESS_BAD_PARAMETERS count=" + count + " rate=" + rate); return }
if (!("d63_stress_targets" in getroottable())) ::d63_stress_targets <- []
if (!("d63_stress_target_ordinals" in getroottable())) ::d63_stress_target_ordinals <- []
if (!("d63_stress_fillers" in getroottable())) ::d63_stress_fillers <- []
if (!("d63_stress_lowfillers" in getroottable())) ::d63_stress_lowfillers <- []
if (!("d63_stress_origin" in getroottable())) {
    local player = Entities.FindByClassname(null, "player")
    ::d63_stress_origin <- player ? player.GetOrigin() + Vector(96, 0, 24) : Vector(0,0,64)
}
if (count < ::d63_stress_targets.len()) { printl("D63_STRESS_CANNOT_SHRINK existing=" + ::d63_stress_targets.len() + " requested=" + count); return }
local last = 2047
while (::d63_stress_fillers.len() == 0 || ::d63_stress_fillers[::d63_stress_fillers.len()-1].GetEntityIndex() < last) {
    local filler = SpawnEntityFromTable("info_target", {origin=Vector(0,0,-12000), targetname="d63_stress_filler"})
    if (!filler) { printl("D63_STRESS_FILLER_FAILED"); return }
    ::d63_stress_fillers.append(filler)
}
while (::d63_stress_targets.len() < count) {
    local i = ::d63_stress_targets.len()
    local attempts = 0
    while (true) {
        local e = SpawnEntityFromTable("prop_dynamic_override", {
            model="models/props_c17/oildrum001.mdl", origin=Vector(0,0,-12000), solid=0,
            targetname="d63_stress_candidate"
        })
        if (!e) { printl("D63_STRESS_TARGET_FAILED i=" + i); return }
        local idx = e.GetEntityIndex()
        if (idx >= 2048 && idx <= 4095) {
            e.SetOrigin(::d63_stress_origin + Vector((i%16)*48, (i/16)*48, 0))
            ::d63_stress_targets.append(e)
            ::d63_stress_target_ordinals.append(i)
            printl("D63_STRESS_TARGET i=" + i + " idx=" + idx)
            break
        }
        ::d63_stress_lowfillers.append(e)
        ++attempts
        if (attempts > 4096) { printl("D63_STRESS_NO_HIGH_SLOT i=" + i); return }
    }
}
::d63_stress_updates <- 0
::d63_stress_phase <- false
::d63_stress_step <- function() {
    ::d63_stress_phase = !::d63_stress_phase
    local delta = ::d63_stress_phase ? 32 : 0
    local target_slot = 0
    foreach (e in ::d63_stress_targets) {
        if (e && e.IsValid()) {
            local i = ::d63_stress_target_ordinals[target_slot]
            e.SetOrigin(::d63_stress_origin + Vector((i%16)*48, (i/16)*48, delta))
        }
        ++target_slot
    }
    ++::d63_stress_updates
    if (::d63_stress_updates % 10 == 0) printl("D63_STRESS_HEARTBEAT count=" + count + " rate=" + rate + " updates=" + ::d63_stress_updates + " live=" + ::d63_stress_targets.len())
}
printl("D63_STRESS_BEGIN count=" + count + " rate=" + rate + " fillers=" + ::d63_stress_fillers.len() + " lowfillers=" + ::d63_stress_lowfillers.len() + " targets=" + ::d63_stress_targets.len())
