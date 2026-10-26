if ("d64_hunter_high_director_started" in getroottable()) { printl("D64_HUNTER_HIGH_ALREADY"); return }
::d64_hunter_high_director_started <- true
::d64_hunter_high_director_fillers <- []
printl("D64_HUNTER_HIGH_BEGIN")

while (::d64_hunter_high_director_fillers.len() == 0 || ::d64_hunter_high_director_fillers[::d64_hunter_high_director_fillers.len() - 1].GetEntityIndex() < 2047) {
    local filler = SpawnEntityFromTable("info_target", {origin = Vector(0, 0, -12000), targetname = "d64_hunter_high_filler"})
    if (!filler) {
        printl("D64_HUNTER_HIGH_FILLER_FAILED")
        return
    }
    ::d64_hunter_high_director_fillers.append(filler)
}

local last_index = ::d64_hunter_high_director_fillers[::d64_hunter_high_director_fillers.len() - 1].GetEntityIndex()
printl("D64_HUNTER_HIGH_FILLERS=" + ::d64_hunter_high_director_fillers.len() + " LAST_IDX=" + last_index)
local origin = Vector(0, 0, 64)
local spawnpoint = Entities.FindByClassname(null, "info_survivor_position")
if (spawnpoint) origin = spawnpoint.GetOrigin() + Vector(64, 0, 24)
local player = Entities.FindByClassname(null, "player")
if (player) origin = player.GetOrigin() + Vector(64, 0, 24)
try {
    local result = ZSpawn({type = 3, pos = origin, ang = QAngle(0, 0, 0)})
    printl("D64_HUNTER_HIGH_RETURN=" + result)
} catch (e) {
    printl("D64_HUNTER_HIGH_EXCEPTION=" + e)
}
printl("D64_HUNTER_HIGH_DONE")
