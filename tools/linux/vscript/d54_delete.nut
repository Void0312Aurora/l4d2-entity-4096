local t = ::n27_d52_target
if (!t) {
    printl("D54_DELETE missing")
} else {
    local idx = t.GetEntityIndex()
    t.Kill()
    local live = Entities.FindByName(null, "n27_d52_target")
    printl("D54_DELETE idx=" + idx + " alive=" + (live != null))
}
