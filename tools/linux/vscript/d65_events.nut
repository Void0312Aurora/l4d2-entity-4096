::d65_events <- {
    OnGameEvent_player_death = function(p) {
        printl("D65_PLAYER_DEATH userid="+p.userid+" time="+Time())
    },
    OnGameEvent_player_hurt = function(p) {
        printl("D65_PLAYER_HURT userid="+p.userid+" health="+p.health+" time="+Time())
    },
    OnGameEvent_infected_death = function(p) {
        printl("D65_INFECTED_DEATH time="+Time())
    }
}
__CollectGameEventCallbacks(::d65_events)
printl("D65_EVENTS_READY")
