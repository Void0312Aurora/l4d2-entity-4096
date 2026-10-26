foreach (e in ::d62_targets) {
    if (!e.IsValid()) throw "D62 target invalid before update"
    e.SetOrigin(e.GetOrigin()+Vector(0,96,32))
    printl("D62_UPDATE idx="+e.GetEntityIndex()+" origin="+e.GetOrigin())
}
