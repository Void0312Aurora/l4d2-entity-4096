local e = SpawnEntityFromTable("prop_dynamic", { model = "models/props_c17/oildrum001.mdl", origin = Vector(0, 0, 64) })
if (e) printl("D41_TARGET idx=" + e.GetEntityIndex())
else printl("D41_TARGET failed")
