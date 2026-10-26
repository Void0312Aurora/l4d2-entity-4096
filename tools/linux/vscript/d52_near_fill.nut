printl("D52_BEGIN")
local p = Entities.FindByClassname(null, "player")
if (!p) {
    printl("D52_PLAYER failed")
    printl("D52_DONE failed")
} else {
    local origin = p.GetOrigin()
    local e = null
    local moved = 0
    while ((e = Entities.FindByClassname(e, "info_target")) != null) {
        e.SetOrigin(origin + Vector(24, 0, 8))
        moved++
    }
    printl("D52_MOVED existing=" + moved)
    local n = 0
    local first = -1
    local last = -1
    while (n < 3000 && last < 2047) {
        local e = SpawnEntityFromTable("info_target", {
            origin = origin + Vector(32, 0, 8)
        })
        if (!e) break
        last = e.GetEntityIndex()
        if (first < 0) first = last
        n++
    }
    printl("D52_FILL n=" + n + " first=" + first + " last=" + last)
    local t = SpawnEntityFromTable("prop_dynamic", {
        model = "models/props_c17/oildrum001.mdl",
        origin = origin + Vector(96, 0, 24),
        solid = 0,
        targetname = "n27_d52_target"
    })
    if (!t) {
        printl("D52_TARGET failed")
        printl("D52_DONE failed")
    } else {
        ::n27_d52_target <- t
        local idx = t.GetEntityIndex()
        t.__KeyValueFromString("targetname", "n27_d52_target")
        local live = Entities.FindByName(null, "n27_d52_target")
        printl("D52_TARGET idx=" + idx + " name=" + t.GetName() + " origin=" + t.GetOrigin())
        if (live && live.GetEntityIndex() == idx) {
            printl("D52_ALIVE idx=" + idx + " valid=1")
        } else {
            printl("D52_ALIVE idx=" + idx + " valid=0")
        }
        printl("D52_DONE idx=" + idx)
    }
}
