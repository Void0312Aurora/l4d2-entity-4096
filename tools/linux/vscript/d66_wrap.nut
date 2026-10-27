// D66 controlled serial-wrap probe.  It uses ordinary allocation and never
// writes an entity-table slot or a serial value directly.
::d66_fillers <- []
::d66_slot <- null
::d66_old <- null
::d66_cycle <- 0
::d66_origin <- Vector(0, 0, 64)

local player = Entities.FindByClassname(null, "player")
if (player) ::d66_origin = player.GetOrigin() + Vector(96, 0, 24)

::d66_prepare <- function() {
    if (::d66_fillers.len() != 0) return
    local last = -1
    while (last < 2047) {
        local e = SpawnEntityFromTable("info_target", {origin=Vector(0,0,-12000), targetname="d66_filler"})
        if (!e) throw "D66 filler allocation failed"
        last = e.GetEntityIndex()
        ::d66_fillers.append(e)
        if (last > 2047) throw "D66 filler crossed 2047"
    }
    printl("D66_WRAP_READY fillers=" + ::d66_fillers.len() + " last=" + last)
}

::d66_spawn <- function() {
    if (::d66_slot && ::d66_slot.IsValid()) throw "D66 slot still alive"
    local e = SpawnEntityFromTable("prop_dynamic_override", {
        model="models/props_c17/oildrum001.mdl", origin=::d66_origin,
        solid=0, targetname="d66_wrap_target"
    })
    if (!e) throw "D66 wrap allocation failed"
    local i = e.GetEntityIndex()
    if (i < 2048 || i >= 3072) throw "D66 wrap left high-index range"
    e.SetOrigin(::d66_origin + Vector(::d66_cycle % 32, 0, 0))
    ::d66_slot = e
    ::d66_cycle += 1
    printl("D66_WRAP_CREATE idx=" + i + " cycle=" + ::d66_cycle + " time=" + Time())
}

::d66_kill <- function() {
    if (!::d66_slot || !::d66_slot.IsValid()) throw "D66 wrap target missing"
    local i = ::d66_slot.GetEntityIndex()
    ::d66_old = ::d66_slot
    ::d66_slot.Kill()
    ::d66_slot = null
    printl("D66_WRAP_DELETE idx=" + i + " cycle=" + ::d66_cycle + " time=" + Time())
}

::d66_old_check <- function() {
    local valid = (::d66_old && ::d66_old.IsValid()) ? 1 : 0
    printl("D66_WRAP_OLD valid=" + valid + " cycle=" + ::d66_cycle + " time=" + Time())
}

::d66_cleanup <- function() {
    if (::d66_slot && ::d66_slot.IsValid()) ::d66_slot.Kill()
    while (::d66_fillers.len()) {
        local e = ::d66_fillers.pop()
        if (e && e.IsValid()) e.Kill()
    }
    printl("D66_WRAP_CLEANUP_DONE")
}

printl("D66_WRAP_SCRIPT_READY")
