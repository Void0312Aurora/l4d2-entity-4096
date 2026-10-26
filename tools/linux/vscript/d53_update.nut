local t = ::n27_d52_target
if (!t) {
    printl("D53_UPDATE missing")
} else {
    local idx = t.GetEntityIndex()
    local before = t.GetOrigin()
    local after = before + Vector(96, 0, 0)
    t.SetOrigin(after)
    printl("D53_UPDATE idx=" + idx + " before=" + before + " after=" + t.GetOrigin())
}
