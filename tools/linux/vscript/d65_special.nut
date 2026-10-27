// Set d65_type to a runtime-verified ZOMBIE_* constant before each invocation.
local origin = ::d65_origin + Vector(0, 128, 0)
local ok = ZSpawn({type=::d65_type, pos=origin, ang=QAngle(0,0,0)})
printl("D65_SPECIAL_REQUEST type=" + ::d65_type + " result=" + ok + " time=" + Time())
::d65_special <- null
local p=null
while ((p=Entities.FindByClassname(p,"player")) != null) {
    if (p.GetZombieType()==::d65_type && p.GetHealth()>0) {
        ::d65_special = p
        printl("D65_SPECIAL_FOUND idx="+p.GetEntityIndex()+" type="+p.GetZombieType()+" model="+p.GetModelName()+" health="+p.GetHealth()+" valid="+p.IsValid())
        p.TakeDamage(10.0, 2, null)
        printl("D65_SPECIAL_DAMAGED idx="+p.GetEntityIndex()+" health="+p.GetHealth())
        break
    }
}
if (::d65_special == null) throw "D65 requested infected type not present"
