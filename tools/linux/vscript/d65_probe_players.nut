local p=null
while ((p=Entities.FindByClassname(p,"player"))!=null) {
    printl("D65_PLAYER idx="+p.GetEntityIndex()+" type="+p.GetZombieType()+" model="+p.GetModelName()+" health="+p.GetHealth())
}
