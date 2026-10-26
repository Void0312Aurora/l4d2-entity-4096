foreach (t in ::n27_d55_targets) {
    local before = t.GetOrigin()
    t.SetOrigin(before + Vector(0, 96, 32))
    printl("D55_UPDATE idx=" + t.GetEntityIndex() + " before=" + before + " after=" + t.GetOrigin())
}
