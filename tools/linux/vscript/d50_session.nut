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
local t = SpawnEntityFromTable("prop_dynamic", { model = "models/props_c17/oildrum001.mdl", origin = Vector(0, 0, 64) })
if (t) {
    printl("D50_TARGET idx=" + t.GetEntityIndex())
    printl("D50_DONE idx=" + t.GetEntityIndex())
} else {
    printl("D50_TARGET failed")
    printl("D50_DONE failed")
}
