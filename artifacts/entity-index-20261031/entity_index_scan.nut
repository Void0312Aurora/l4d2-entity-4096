printl("ENTITY_INDEX_SCAN_LOAD")
::entity_index_scan <- function() {
    local e = null
    local count = 0
    local maxidx = -1
    local maxclass = ""
    local over2047 = 0
    local negative = 0
    local unique = {}
    local samples = []
    try {
        e = Entities.First()
        while (e) {
            if (e.IsValid()) {
                local idx = e.GetEntityIndex()
                ++count
                if (idx < 0) {
                    ++negative
                } else {
                    unique[idx.tostring()] <- true
                }
                if (idx > maxidx) { maxidx = idx; maxclass = e.GetClassname() }
                if (idx >= 2048) {
                    ++over2047
                    if (samples.len() < 32) samples.append(idx + ":" + e.GetClassname())
                }
            }
            e = Entities.Next(e)
        }
        printl("ENTITY_INDEX_SCAN count=" + count + " unique=" + unique.len() + " negative=" + negative + " max=" + maxidx + " maxclass=" + maxclass + " over2047=" + over2047)
        foreach (s in samples) printl("ENTITY_INDEX_HIGH " + s)
    } catch (err) { printl("ENTITY_INDEX_SCAN_EXCEPTION=" + err) }
}
