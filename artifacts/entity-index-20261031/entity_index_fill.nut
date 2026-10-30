// Temporary, reversible entity-index stress helper.
// It keeps spawned props alive so the edict allocator cannot immediately reuse
// their slots for short-lived infected.
if (!("entity_index_fill_store" in getroottable()))
    ::entity_index_fill_store <- []

::entity_index_fill <- function(count = 64) {
    local model = "models/props_junk/garbage_metalcan001a.mdl"
    PrecacheModel(model)
    local created = 0
    for (local i = 0; i < count; ++i) {
        local ent = SpawnEntityFromTable("prop_dynamic_override", {
            model = model,
            origin = "0 0 -10000",
            angles = "0 0 0",
            solid = "0",
            rendermode = "10",
            disableshadows = "1",
            targetname = "codex_entity_index_fill"
        })
        if (ent != null) {
            entity_index_fill_store.append(ent)
            ++created
        }
    }
    printl("ENTITY_INDEX_FILL created=" + created + " stored=" + entity_index_fill_store.len())
}

::entity_index_fill_cleanup <- function() {
    local killed = 0
    foreach (ent in entity_index_fill_store) {
        if (ent != null && ent.IsValid()) {
            EntFireByHandle(ent, "Kill", "", 0.0, null, null)
            ++killed
        }
    }
    entity_index_fill_store.clear()
    printl("ENTITY_INDEX_FILL_CLEANUP killed=" + killed)
}
