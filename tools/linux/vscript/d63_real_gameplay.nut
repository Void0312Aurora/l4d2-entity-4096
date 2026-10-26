// Real gameplay coverage with a bounded high-index reservation.  Fillers are
// kept out of the PVS; representative game entities remain near the survivor.
if ("d63_real_gameplay_done" in getroottable()) {
    printl("D63_REAL_ALREADY_RUNNING")
    return
}
::d63_real_gameplay_done <- true
::d63_real_fillers <- []
::d63_real_entities <- []
::d63_real_player <- Entities.FindByClassname(null, "player")
::d63_real_origin <- d63_real_player ? d63_real_player.GetOrigin() + Vector(96, 0, 24) : Vector(0, 0, 64)

local function marker(text) { printl("D63_REAL_" + text) }
local function remember(label, e) {
    if (e) {
        ::d63_real_entities.append(e)
        marker(label + " idx=" + e.GetEntityIndex() + " class=" + e.GetClassname())
    } else marker(label + " FAILED")
    return e
}

local highest = 2047
while (::d63_real_fillers.len() == 0 || ::d63_real_fillers[::d63_real_fillers.len()-1].GetEntityIndex() < highest) {
    local filler = SpawnEntityFromTable("info_target", {origin=Vector(0,0,-12000), targetname="d63_real_filler"})
    if (!filler) { marker("FILLER_FAILED"); return }
    ::d63_real_fillers.append(filler)
}
marker("FILLERS count=" + ::d63_real_fillers.len() + " last=" + ::d63_real_fillers[::d63_real_fillers.len()-1].GetEntityIndex())

local infected = null
local hunter = null
try { infected = remember("INFECTED", SpawnEntityFromTable("infected", {origin=::d63_real_origin, targetname="d63_real_infected"})) } catch (e) { marker("INFECTED_EXCEPTION=" + e) }
try { hunter = remember("SPECIAL_HUNTER", SpawnEntityFromTable("hunter", {origin=::d63_real_origin + Vector(64,0,0), targetname="d63_real_hunter"})) } catch (e) { marker("SPECIAL_HUNTER_EXCEPTION=" + e) }
try { remember("PHYSICS_PROP", SpawnEntityFromTable("prop_physics", {model="models/props_junk/gascan001a.mdl", origin=::d63_real_origin + Vector(128,0,0), targetname="d63_real_physics"})) } catch (e) { marker("PHYSICS_EXCEPTION=" + e) }
try { remember("WEAPON", SpawnEntityFromTable("weapon_pistol_spawn", {origin=::d63_real_origin + Vector(160,0,0), targetname="d63_real_weapon"})) } catch (e) { marker("WEAPON_EXCEPTION=" + e) }
try { remember("PROJECTILE", SpawnEntityFromTable("pipe_bomb_projectile", {origin=::d63_real_origin + Vector(192,0,0), targetname="d63_real_projectile"})) } catch (e) { marker("PROJECTILE_EXCEPTION=" + e) }
try { remember("LOGIC", SpawnEntityFromTable("logic_relay", {targetname="d63_real_logic"})) } catch (e) { marker("LOGIC_EXCEPTION=" + e) }
try { remember("SOUND", SpawnEntityFromTable("ambient_generic", {message="UI/menu_countdown.wav", health=10, spawnflags=48, targetname="d63_real_sound"})) } catch (e) { marker("SOUND_EXCEPTION=" + e) }
try { remember("TRIGGER", SpawnEntityFromTable("trigger_once", {spawnflags=1, origin=::d63_real_origin, mins="-32 -32 -32", maxs="32 32 32", targetname="d63_real_trigger"})) } catch (e) { marker("TRIGGER_EXCEPTION=" + e) }

if (infected && ::d63_real_player) {
    try { infected.TakeDamage(10.0, 2, ::d63_real_player); marker("INFECTED_DAMAGE_RETURNED idx=" + infected.GetEntityIndex()) } catch (e) { marker("INFECTED_DAMAGE_EXCEPTION=" + e) }
}
if (hunter && ::d63_real_player) {
    try { hunter.TakeDamage(10.0, 2, ::d63_real_player); marker("HUNTER_DAMAGE_RETURNED idx=" + hunter.GetEntityIndex()) } catch (e) { marker("HUNTER_DAMAGE_EXCEPTION=" + e) }
}

::d63_real_tick <- 0
::d63_real_heartbeat <- function() {
    ++::d63_real_tick
    local live = 0
    foreach (e in ::d63_real_entities) if (e && e.IsValid()) ++live
    marker("HEARTBEAT tick=" + ::d63_real_tick + " live=" + live)
    if (::d63_real_tick == 8 && infected && infected.IsValid()) {
        try { infected.TakeDamage(10000.0, 2, ::d63_real_player); marker("INFECTED_FATAL_DAMAGE_RETURNED") } catch (e) { marker("INFECTED_FATAL_EXCEPTION=" + e) }
    }
    if (::d63_real_tick == 12) {
        foreach (e in ::d63_real_entities) {
            if (e && e.IsValid() && e.GetClassname() != "logic_relay" && e.GetClassname() != "ambient_generic") {
                try { e.Kill(); marker("KILL_REQUEST idx=" + e.GetEntityIndex() + " class=" + e.GetClassname()) } catch (x) { marker("KILL_EXCEPTION=" + x) }
            }
        }
    }
    if (::d63_real_tick < 20) return 1.0
    marker("DONE")
    return -1
}
local relay = SpawnEntityFromTable("logic_relay", {targetname="d63_real_heartbeat_relay"})
if (relay) relay.SetContextThink("d63_real_heartbeat", ::d63_real_heartbeat, 1.0)
marker("STARTED")
