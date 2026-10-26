// Leave at least 64 high edicts free while retaining the low-index fillers.
// Exercises the high entityid lookup in PlayerReporter::FireGameEvent.
local player=Entities.FindByClassname(null,"player")
::d62_infected <- SpawnEntityFromTable("infected", {
    origin=player.GetOrigin()+Vector(1024,0,0), targetname="n27_d62_infected"
})
if (!d62_infected || d62_infected.GetEntityIndex()<2048) throw "D62 infected is not high-index"
printl("D62_INFECTED_CREATED idx="+d62_infected.GetEntityIndex())
d62_infected.TakeDamage(100000.0,2,player)
printl("D62_INFECTED_DAMAGE_RETURNED")
