if ("d64_hunter_director_started" in getroottable()) { printl("D64_HUNTER_DIRECTOR_ALREADY"); return }
::d64_hunter_director_started <- true
printl("D64_HUNTER_DIRECTOR_BEGIN")
local origin = Vector(0, 0, 64)
local spawnpoint = Entities.FindByClassname(null, "info_survivor_position")
if (spawnpoint) origin = spawnpoint.GetOrigin() + Vector(64, 0, 24)
local player = Entities.FindByClassname(null, "player")
if (player) origin = player.GetOrigin() + Vector(64, 0, 24)
try {
    local result = ZSpawn({type = 3, pos = origin, ang = QAngle(0, 0, 0)})
    printl("D64_HUNTER_DIRECTOR_RETURN=" + result)
} catch (e) {
    printl("D64_HUNTER_DIRECTOR_EXCEPTION=" + e)
}
printl("D64_HUNTER_DIRECTOR_DONE")
