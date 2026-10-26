if ("d64_special_high_spitter_started" in getroottable()) { printl("D64_SPECIAL_HIGH_SPITTER_ALREADY"); return }
::d64_special_high_spitter_started <- true
::d64_special_high_spitter_fillers <- []
while (::d64_special_high_spitter_fillers.len() == 0 || ::d64_special_high_spitter_fillers[::d64_special_high_spitter_fillers.len() - 1].GetEntityIndex() < 2047) {
    local filler = SpawnEntityFromTable("info_target", {origin = Vector(0, 0, -12000), targetname = "d64_special_high_filler"})
    if (!filler) { printl("D64_SPECIAL_HIGH_SPITTER_FILLER_FAILED"); return }
    ::d64_special_high_spitter_fillers.append(filler)
}
local last = ::d64_special_high_spitter_fillers[::d64_special_high_spitter_fillers.len() - 1].GetEntityIndex()
local origin = Vector(256, 256, 64)
local spawnpoint = Entities.FindByClassname(null, "info_survivor_position")
if (spawnpoint) origin = spawnpoint.GetOrigin() + Vector(96, 0, 24)
printl("D64_SPECIAL_HIGH_SPITTER_FILLERS=" + ::d64_special_high_spitter_fillers.len() + " LAST_IDX=" + last)
try {
    local result = ZSpawn({type = 4, pos = origin, ang = QAngle(0, 0, 0)})
    printl("D64_SPECIAL_HIGH_SPITTER_RETURN=" + result)
} catch (e) { printl("D64_SPECIAL_HIGH_SPITTER_EXCEPTION=" + e) }
local p = Entities.FindByClassname(null, "player")
while (p) {
    local t = -1
    local health = -1
    try { t = p.GetZombieType() } catch (e) {}
    try { health = p.GetHealth() } catch (e) {}
    printl("D64_SPECIAL_HIGH_PLAYER idx=" + p.GetEntityIndex() + " type=" + t + " health=" + health + " valid=" + p.IsValid())
    p = Entities.FindByClassname(p, "player")
}
printl("D64_SPECIAL_HIGH_SPITTER_DONE")
