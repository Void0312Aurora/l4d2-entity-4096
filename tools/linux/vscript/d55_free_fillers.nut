local count = 0
foreach (e in ::n27_d55_fillers) {
    if (e && e.IsValid()) {
        e.Kill()
        count++
    }
}
::n27_d55_fillers.clear()
printl("D55_FREE_FILLERS count=" + count)
