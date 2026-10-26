if ("d63_infected_only_started" in getroottable()) { printl("D63_INFECTED_ONLY_ALREADY"); return }
::d63_infected_only_started <- true
::d63_infected_only_fillers <- []
local p = Entities.FindByClassname(null, "player")
local o = p ? p.GetOrigin() + Vector(96,0,24) : Vector(0,0,64)
while (::d63_infected_only_fillers.len() == 0 || ::d63_infected_only_fillers[::d63_infected_only_fillers.len()-1].GetEntityIndex() < 2047) {
    local f = SpawnEntityFromTable("info_target", {origin=Vector(0,0,-12000), targetname="d63_infected_only_filler"})
    if (!f) { printl("D63_INFECTED_ONLY_FILLER_FAILED"); return }
    ::d63_infected_only_fillers.append(f)
}
printl("D63_INFECTED_ONLY_FILLERS=" + ::d63_infected_only_fillers.len())
try {
    ::d63_infected_only <- SpawnEntityFromTable("infected", {origin=o, targetname="d63_infected_only"})
    printl("D63_INFECTED_ONLY_CREATED idx=" + ::d63_infected_only.GetEntityIndex() + " valid=" + ::d63_infected_only.IsValid())
} catch (e) { printl("D63_INFECTED_ONLY_EXCEPTION=" + e) }
