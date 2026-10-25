local n = 0
local mn = -1
local mx = -1
for (local i = 0; i < 64; i++) {
    local e = SpawnEntityFromTable("info_target", { origin = Vector(0, 0, 0) })
    if (e) {
        local idx = e.GetEntityIndex()
        if (mn < 0 || idx < mn) mn = idx
        if (idx > mx) mx = idx
        n++
    }
}
printl("D37_BATCH n=" + n + " min=" + mn + " max=" + mx)
