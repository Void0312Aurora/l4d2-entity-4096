// Run after signon so the props are in the real player's PVS.
local first = ("n27_first_index" in getroottable()) ? ::n27_first_index : 2048
local count = (first == 4095) ? 1 : 2
local player = ("n27_test_userid" in getroottable()) ? GetPlayerFromUserID(::n27_test_userid) : Entities.FindByClassname(null, "player")
if (!player) throw "D55 requires a player"
printl("D55_BEGIN first=" + first)
::n27_d55_fillers <- []
local last = -1
while (last < first - 1 && n27_d55_fillers.len() < 4096) {
    local e = SpawnEntityFromTable("info_target", { origin = Vector(0, 0, -12000) })
    if (!e) throw "D55 filler allocation failed"
    last = e.GetEntityIndex()
    n27_d55_fillers.append(e)
}
printl("D55_FILL count=" + n27_d55_fillers.len() + " last=" + last)
::n27_d55_targets <- []
for (local n = 0; n < count; n++) {
    local pos = player.GetOrigin() + Vector(96 + 96*n, 0, 24)
    local t = SpawnEntityFromTable("prop_dynamic_override", {
        model = "models/props_c17/oildrum001.mdl", origin = pos,
        solid = 0, targetname = "n27_d55_target_" + n
    })
    if (!t) throw "D55 target allocation failed"
    t.__KeyValueFromString("targetname", "n27_d55_target_" + n)
    n27_d55_targets.append(t)
    local idx = t.GetEntityIndex()
    printl("D55_TARGET idx=" + idx + " class=" + t.GetClassname() + " origin=" + t.GetOrigin())
    if (idx != first + n) throw "D55 unexpected target index"
}
printl("D55_DONE first=" + first + " count=" + count)
