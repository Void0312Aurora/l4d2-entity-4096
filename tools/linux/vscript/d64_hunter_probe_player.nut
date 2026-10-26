if ("d64_hunter_probe_player_started" in getroottable()) { printl("D64_HUNTER_PROBE_ALREADY"); return }
::d64_hunter_probe_player_started <- true
printl("D64_HUNTER_PROBE_BEGIN")
local p = Entities.FindByClassname(null, "player")
local count = 0
while (p) {
    ++count
    printl("D64_HUNTER_PLAYER idx=" + p.GetEntityIndex() + " valid=" + p.IsValid() + " class=" + p.GetClassname())
    try { printl("D64_HUNTER_PLAYER_TEAM idx=" + p.GetEntityIndex() + " team=" + p.GetTeamNumber()) } catch (e) { printl("D64_HUNTER_TEAM_EXCEPTION=" + e) }
    try { printl("D64_HUNTER_PLAYER_HEALTH idx=" + p.GetEntityIndex() + " health=" + p.GetHealth()) } catch (e) { printl("D64_HUNTER_HEALTH_EXCEPTION=" + e) }
    try { printl("D64_HUNTER_PLAYER_ALIVE idx=" + p.GetEntityIndex() + " alive=" + p.IsAlive()) } catch (e) { printl("D64_HUNTER_ALIVE_EXCEPTION=" + e) }
    try { printl("D64_HUNTER_PLAYER_ZOMBIE_TYPE idx=" + p.GetEntityIndex() + " type=" + p.GetZombieType()) } catch (e) { printl("D64_HUNTER_TYPE_EXCEPTION=" + e) }
    if (count == 1) {
        try {
            p.TakeDamage(10.0, 2, p)
            printl("D64_HUNTER_DAMAGE_SMALL_RETURNED idx=" + p.GetEntityIndex() + " health=" + p.GetHealth())
        } catch (e) { printl("D64_HUNTER_DAMAGE_SMALL_EXCEPTION=" + e) }
    }
    p = Entities.FindByClassname(p, "player")
}
printl("D64_HUNTER_PLAYER_COUNT=" + count)
printl("D64_HUNTER_PROBE_DONE")
