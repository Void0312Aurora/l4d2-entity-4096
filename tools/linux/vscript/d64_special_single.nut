if ("d64_special_single_started" in getroottable()) { printl("D64_SPECIAL_SINGLE_ALREADY"); return }
::d64_special_single_started <- true
local ztype = 4
local origin = Vector(256, 256, 64)
local spawnpoint = Entities.FindByClassname(null, "info_survivor_position")
if (spawnpoint) origin = spawnpoint.GetOrigin() + Vector(96, 0, 24)
try {
    local result = ZSpawn({type = ztype, pos = origin, ang = QAngle(0, 0, 0)})
    printl("D64_SPECIAL_SINGLE_RETURN type=" + ztype + " result=" + result)
} catch (e) {
    printl("D64_SPECIAL_SINGLE_EXCEPTION type=" + ztype + " error=" + e)
}
local p = Entities.FindByClassname(null, "player")
while (p) {
    local t = -1
    local health = -1
    try { t = p.GetZombieType() } catch (e) {}
    try { health = p.GetHealth() } catch (e) {}
    printl("D64_SPECIAL_SINGLE_PLAYER idx=" + p.GetEntityIndex() + " type=" + t + " health=" + health + " valid=" + p.IsValid())
    p = Entities.FindByClassname(p, "player")
}
printl("D64_SPECIAL_SINGLE_DONE")
