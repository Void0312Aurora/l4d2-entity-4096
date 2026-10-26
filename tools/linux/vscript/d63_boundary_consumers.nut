// Actual VScript consumers, including valid high, partition hole, non-network,
// and upper-bound lookups. Results are deliberately separate from arithmetic.
local indices = [0, 1, 2048, 4095, 4096, 4097, 8191, -1]
foreach (i in indices) {
    try {
        local by = EntIndexToHScript(i)
        printl("D63_BOUNDARY idx=" + i + " valid=" + (by != null && by.IsValid()) + " class=" + (by ? by.GetClassname() : "NULL"))
    } catch (err) { printl("D63_BOUNDARY idx=" + i + " EXCEPTION=" + err) }
}
printl("D63_BOUNDARY_DONE")
