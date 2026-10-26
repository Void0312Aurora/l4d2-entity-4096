printl("D51_BEGIN")
local p = Entities.FindByClassname(null, "player")
if (!p) {
    printl("D51_PLAYER failed")
    printl("D51_DONE failed")
} else {
    local origin = p.GetOrigin()
    printl("D51_PLAYER idx=" + p.GetEntityIndex() + " origin=" + origin)
    local t = SpawnEntityFromTable("prop_dynamic", {
        model = "models/props_c17/oildrum001.mdl",
        origin = origin + Vector(48, 0, 16),
        solid = 0,
        targetname = "n27_d51_target"
    })
    if (!t) {
        printl("D51_TARGET failed")
        printl("D51_DONE failed")
    } else {
        local idx = t.GetEntityIndex()
        t.__KeyValueFromString("targetname", "n27_d51_target")
        local live = Entities.FindByName(null, "n27_d51_target")
        printl("D51_TARGET idx=" + idx)
        if (live && live.GetEntityIndex() == idx) {
            printl("D51_ALIVE idx=" + idx + " valid=1")
        } else {
            printl("D51_ALIVE idx=" + idx + " valid=0")
        }
        printl("D51_DONE idx=" + idx)
    }
}
