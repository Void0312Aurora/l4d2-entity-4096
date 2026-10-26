printl("D50_BEGIN")
local n = 0
local last = -1
while (n < 2500) {
    local e = SpawnEntityFromTable("info_target", { origin = Vector(0, 0, -12000) })
    if (!e) break
    last = e.GetEntityIndex()
    n++
    if (last >= 2047) break
}
printl("D50_FILL n=" + n + " last=" + last)
local t = SpawnEntityFromTable("prop_dynamic", {
    model = "models/props_c17/oildrum001.mdl",
    origin = Vector(0, 0, 64),
    targetname = "n27_d50_target"
})
if (t) {
    local idx = t.GetEntityIndex()
    t.__KeyValueFromString("targetname", "n27_d50_target")
    printl("D50_NAME name=" + t.GetName())
    local live = Entities.FindByName(null, "n27_d50_target")
    printl("D50_TARGET idx=" + idx)
    if (live && live.GetEntityIndex() == idx) {
        printl("D50_ALIVE idx=" + idx + " valid=1")
    } else {
        printl("D50_ALIVE idx=" + idx + " valid=0")
    }
    printl("D50_DONE idx=" + idx)
} else {
    printl("D50_TARGET failed")
    printl("D50_ALIVE valid=0")
    printl("D50_DONE failed")
}
