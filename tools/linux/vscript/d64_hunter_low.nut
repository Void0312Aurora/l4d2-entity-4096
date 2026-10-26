if ("d64_hunter_low_started" in getroottable()) { printl("D64_HUNTER_LOW_ALREADY"); return }
::d64_hunter_low_started <- true
local p = Entities.FindByClassname(null, "player")
local origin = p ? p.GetOrigin() + Vector(64, 0, 24) : Vector(0, 0, 64)
printl("D64_HUNTER_LOW_BEGIN")
try {
    local hunter = SpawnEntityFromTable("hunter", {origin=origin, targetname="d64_hunter_low"})
    if (!hunter) {
        printl("D64_HUNTER_LOW_NULL")
    } else {
        printl("D64_HUNTER_LOW_CREATED idx=" + hunter.GetEntityIndex() + " valid=" + hunter.IsValid())
    }
} catch (e) {
    printl("D64_HUNTER_LOW_EXCEPTION=" + e)
}
printl("D64_HUNTER_LOW_DONE")
