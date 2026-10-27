#pragma semicolon 1
#pragma newdecls required
#include <sourcemod>
#include <sdktools>
#if defined D65_CORE_ONLY
 #undef AUTOLOAD_EXTENSIONS
 #undef REQUIRE_EXTENSIONS
#endif
#include <sdkhooks>

public Plugin myinfo = {
    name = "D65 isolated compatibility probe", author = "L4D2-4096",
    description = "Separate native calls and log their actual results", version = "1"
};
bool g_SpawnHooks;
int g_OldRef = INVALID_ENT_REFERENCE;
public APLRes AskPluginLoad2(Handle myself, bool late, char[] error, int errmax) {
#if defined D65_CORE_ONLY
    MarkNativeAsOptional("SDKHook");
#endif
    return APLRes_Success;
}
public void OnPluginStart() {
    RegServerCmd("sm_d65_probe", Probe);
    RegServerCmd("sm_d65_force", Force);
    RegServerCmd("sm_d65_hook", Hook);
    RegServerCmd("sm_d65_spawnhooks", SpawnHooks);
    RegServerCmd("sm_d65_remember", Remember);
    RegServerCmd("sm_d65_old", Old);
    PrintToServer("D65_SM_READY maxentities=%d", GetMaxEntities());
}
public Action Remember(int argc) {
    char arg[32]; GetCmdArg(1,arg,sizeof(arg));
    int index=StringToInt(arg);
    g_OldRef=EntIndexToEntRef(index);
    PrintToServer("D65_SM_REMEMBER index=%d ref=%d",index,g_OldRef);
    return Plugin_Handled;
}
public Action Old(int argc) {
    PrintToServer("D65_SM_OLD ref=%d resolved=%d",g_OldRef,EntRefToEntIndex(g_OldRef));
    return Plugin_Handled;
}
public Action Probe(int argc) {
    char arg[32], classname[128]; GetCmdArg(1,arg,sizeof(arg));
    int index=StringToInt(arg);
    PrintToServer("D65_SM_PROBE_BEGIN index=%d max=%d",index,GetMaxEntities());
    bool valid=IsValidEntity(index);
    PrintToServer("D65_SM_VALID index=%d valid=%d",index,valid);
    if (valid) {
        int ref=EntIndexToEntRef(index);
        PrintToServer("D65_SM_REF index=%d ref=%d resolved=%d",index,ref,EntRefToEntIndex(ref));
        GetEntityClassname(index,classname,sizeof(classname));
        PrintToServer("D65_SM_CLASS index=%d classname=%s",index,classname);
    }
    PrintToServer("D65_SM_PROBE_END index=%d",index);
    return Plugin_Handled;
}
public Action Force(int argc) {
    char arg[32]; GetCmdArg(1,arg,sizeof(arg)); int index=StringToInt(arg);
    PrintToServer("D65_SM_FORCE_BEGIN requested=%d",index);
    int entity=CreateEntityByName("prop_dynamic_override",index);
    PrintToServer("D65_SM_FORCE_RETURN requested=%d entity=%d",index,entity);
    if (entity != -1) {
        DispatchKeyValue(entity,"model","models/props_c17/oildrum001.mdl");
        DispatchKeyValue(entity,"solid","0");
        DispatchKeyValue(entity,"targetname","d65_sm_target");
        DispatchSpawn(entity);
        PrintToServer("D65_SM_SPAWNED index=%d",entity);
    }
    return Plugin_Handled;
}
public Action Hook(int argc) {
    char arg[32];GetCmdArg(1,arg,sizeof(arg));int entity=StringToInt(arg);
    PrintToServer("D65_SM_HOOK_BEGIN index=%d",entity);
    SDKHook(entity,SDKHook_OnTakeDamage,Damage);
    PrintToServer("D65_SM_HOOK_END index=%d",entity);
    return Plugin_Handled;
}
public Action SpawnHooks(int argc) {
    g_SpawnHooks=!g_SpawnHooks;PrintToServer("D65_SM_SPAWNHOOKS enabled=%d",g_SpawnHooks);
    return Plugin_Handled;
}
public void OnEntityCreated(int entity,const char[] classname) {
    if (entity>=2047) PrintToServer("D65_SM_CREATED index=%d classname=%s",entity,classname);
    if (g_SpawnHooks && entity>=2047) SDKHook(entity,SDKHook_SpawnPost,SpawnPost);
}
public void OnEntityDestroyed(int entity) {
    if (entity>=2047) PrintToServer("D65_SM_DESTROYED index=%d",entity);
}
public void SpawnPost(int entity) {
    PrintToServer("D65_SM_SPAWNPOST index=%d",entity);
}
public Action Damage(int victim,int &attacker,int &inflictor,float &damage,int &damagetype) {
    PrintToServer("D65_SM_DAMAGE index=%d amount=%.1f",victim,damage);
    return Plugin_Continue;
}
