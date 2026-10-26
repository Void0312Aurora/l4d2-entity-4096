foreach (t in ::n27_d55_targets) {
    local idx = t.GetEntityIndex()
    t.Kill()
    printl("D55_DELETE idx=" + idx)
}
