// Isolated D65 load. Call d65_create(count), then step/remove/reuse separately.
// Keep the low filler occupied so normal ED_Alloc can reuse the deleted high slots.
::d65_targets <- []
::d65_fillers <- []
::d65_old <- []
::d65_old_indices <- []
::d65_origin <- Vector(0, 0, 64)
local survivor = Entities.FindByClassname(null, "player")
if (survivor) ::d65_origin = survivor.GetOrigin() + Vector(96, 0, 24)
::d65_sequence <- 0
::d65_make_prop <- function() {
    return SpawnEntityFromTable("prop_dynamic_override", {
        model="models/props_c17/oildrum001.mdl", origin=Vector(0,0,-12000),
        solid=0, targetname="d65_target"
    })
}
::d65_create <- function(count) {
    if (count < 1 || count > 512) throw "D65 count outside 1..512"
    if (::d65_fillers.len() == 0) {
        local last = -1
        while (last < 2047) {
            local e = SpawnEntityFromTable("info_target", {origin=Vector(0,0,-12000), targetname="d65_filler"})
            if (!e) throw "D65 filler allocation failed"
            last = e.GetEntityIndex()
            ::d65_fillers.append(e)
            if (last > 2047) throw "D65 filler crossed 2047"
        }
    }
    while (::d65_targets.len() < count) {
        local e = ::d65_make_prop()
        if (!e) throw "D65 prop allocation failed"
        local idx = e.GetEntityIndex()
        if (idx < 2048) { ::d65_fillers.append(e); continue }
        if (idx >= 3072) throw "D65 pressure exceeded reserved headroom"
        e.SetOrigin(::d65_origin + Vector(((idx-2048)%16)*8, ((idx-2048)/16)*8, ::d65_sequence*4))
        ::d65_targets.append(e)
        printl("D65_CREATED idx=" + idx + " time=" + Time())
    }
    printl("D65_CREATE_DONE count=" + ::d65_targets.len())
}
::d65_step <- function(sequence) {
    ::d65_sequence = sequence
    foreach (e in ::d65_targets) {
        if (!e || !e.IsValid()) throw "D65 unexpected dead target"
        local idx = e.GetEntityIndex()
        e.SetOrigin(::d65_origin + Vector(((idx-2048)%16)*8, ((idx-2048)/16)*8, sequence*4))
    }
    printl("D65_STEP sequence=" + sequence + " count=" + ::d65_targets.len() + " time=" + Time())
}
::d65_remove <- function() {
    ::d65_old = []
    ::d65_old_indices = []
    local keep = []
    foreach (i,e in ::d65_targets) {
        if (i%2 == 0) { ::d65_old.append(e); ::d65_old_indices.append(e.GetEntityIndex()); e.Kill() }
        else keep.append(e)
    }
    ::d65_targets = keep
    printl("D65_REMOVE_REQUEST count=" + ::d65_old.len() + " time=" + Time())
}
::d65_report <- function() {
    foreach (e in ::d65_targets) printl("D65_TARGET idx="+e.GetEntityIndex()+" valid="+e.IsValid()+" origin="+e.GetOrigin())
    printl("D65_REPORT_DONE count="+::d65_targets.len())
}
::d65_reuse <- function() {
    local wanted = {}
    foreach (i in ::d65_old_indices) wanted[i] <- true
    local attempts=0
    while (wanted.len()) {
        if (++attempts>1024) throw "D65 reuse did not find deleted slots"
        local e=::d65_make_prop()
        if (!e || e.GetEntityIndex()>=3072) throw "D65 reuse exceeded headroom"
        local i=e.GetEntityIndex()
        if (i in wanted) {
            delete wanted[i]
            e.SetOrigin(::d65_origin+Vector(((i-2048)%16)*8,((i-2048)/16)*8,::d65_sequence*4))
            ::d65_targets.append(e)
            printl("D65_REUSED idx="+i)
        } else ::d65_fillers.append(e)
    }
    printl("D65_REUSE_DONE count="+::d65_targets.len()+" candidates="+attempts)
}
::d65_old_check <- function() {
    local valid = 0
    foreach (e in ::d65_old) if (e && e.IsValid()) ++valid
    printl("D65_OLD_CHECK total=" + ::d65_old.len() + " valid=" + valid + " time=" + Time())
}
::d65_free_fillers <- function() {
    local n=0
    while (::d65_fillers.len() && n<64) {
        local e=::d65_fillers.pop()
        if (e && e.IsValid()) e.Kill()
        ++n
    }
    printl("D65_FREE_FILLERS remaining=" + ::d65_fillers.len())
}
printl("D65_LOAD_READY origin=" + ::d65_origin)
