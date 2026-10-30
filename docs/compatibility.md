# Compatibility

## Platform matrix

| Platform or component | Status | What was actually tested |
| --- | --- | --- |
| Linux dedicated server | Experimental | Patched engine/game DLLs, real high-index allocations and a Proton client |
| Windows client image | Experimental; native runtime NOT_TESTED | Patched module slots at 2048, 2049 and 4095 observed through Proton |
| Proton Windows client | Experimental | Sign-on, synchronized updates, deletion, reuse and map transition |
| Windows native dedicated server | NOT_TESTED | No end-to-end D66 evidence |
| Linux native client | NOT_TESTED | No client build or runtime evidence |
| Windows client-hosted single-player / listen server | **NOT_IMPLEMENTED / NOT_VALIDATED** | No Windows `server.dll` in the release manifest, and no accepted single-player local-server experiment |
| Two real Steam users | NOT_TESTED | One local Steam account was available during D65 |
| Public matchmaking/VAC | NOT_TESTED | Private/insecure experiments only |

## Single-player and listen-server scope

**Single-client** in D65/D66 means one Windows game client (run through Proton) connected to a **separate Linux dedicated server**. It does **not** mean the game's single-player menu or an in-process Windows **listen server**. A client-hosted single-player game must run the local game-server logic and the client-side networking/snapshot path within the game process; success against a dedicated server does not automatically validate this arrangement.

The current [Windows release manifest](../release/manifests/windows-client.json) lists only `bin/engine.dll` and `left4dead2/bin/client.dll`; it omits `left4dead2/bin/server.dll`. The [Linux server release manifest](../release/manifests/linux-server.json) patches `bin/engine_srv.so` and `left4dead2/bin/server_srv.so` instead. Consequently, **the published Windows client patch is not a complete 4096-edict listen-server implementation**. The effect of installing it on ordinary low-index single-player startup has not been established by a dedicated control test; do not claim that ordinary single-player necessarily fails.

This gap does **not** mean Windows `server.dll` was never studied. The historical [Windows reverse-engineering report](../reports/report.md) (notably sections 75 and 177), [static patch manifest](../manifests/server.json), and [experimental builder](../tools/build_server.py) document an isolated patched `server.dll` prototype with **808 patch sites and 30/30 PE preflight checks**. Those are historical **static/structural** results, not a current release manifest, not a verified three-module listen-server build, and not a runtime acceptance result. They must be audited against the current release and build identity before reuse.

The historical [N26 loopback baseline](../reports/network-n26-baseline.md) observed that **an out-of-process** client connecting to a separate server on `127.0.0.1` could trigger the engine's process-local `NET_SendLoopPacket` path; using a non-loopback LAN address worked for that experiment. This does **not** establish a defect in an in-process listen server, or prove that its loopback implementation requires modification. That question, along with local game-server initialization, edict allocation, snapshot and client observation paths, remains untested for the patched Windows single-player mode.

Required acceptance work: reproduce baseline single-player startup with original modules; test ordinary low-index single-player startup with the current Windows patch; re-audit and integrate the historical server-module changes where needed; record loaded modules, server capacity and local connection path; then test indices `2047/2048/2049/4095` with server allocation, client creation/update/delete/reuse and map transitions. Diagnose the first observed failure rather than assigning a loopback or `server.dll` root cause in advance.

## SourceMod compatibility

D65 tested a separate compatibility tree with:

- SourceMod `1.12.0.7259`, source commit `3808e21eb842d8598cc8351a341dcbe661d21b58`;
- Metamod:Source `1.12.0-dev+1228`, source commit `cb47755826fad1483291e5dc00222aa64303d12f`;
- L4D2 SDK commit `2a31cd007b2d7d2f964dc093eedcf7a812cf9dd6`, with the tested `MAX_EDICT_BITS 11 → 12` header change;
- SDKHooks Linux gamedata override `EntityListeners=131108`.

The rebuilt SourceMod core, SDKTools and SDKHooks loaded. The D65 probe verified entity reference round trips at `0`, `2047`, `2048` and `2049`, and recorded SDKHooks callbacks at `4095`.

The stock core high-index API returned invalid indices. Stock SDKHooks crashed while reading the old Linux `EntityListeners=65572` offset. The compatibility result therefore means **compatible for the tested probe scope**, not “all plugins work”.

The reproducible source notes and probe are in [`tools/sourcemod/d65_compatibility.md`](../tools/sourcemod/d65_compatibility.md) and [`tools/sourcemod/d65_probe.sp`](../tools/sourcemod/d65_probe.sp).

D66 adds `tools/sourcemod/build_compat.py`, which checks the three pinned
repositories and recursive submodules before building and packaging the
minimal SDK/gamedata changes. See [the recorded artifact hashes](../reports/n27d66/sourcemod-build.json).

## Production plugin-stack smoke test

On 2026-10-27, a temporary staging tree combining the patched Linux server modules with
the host's production SourceMod tree was tested before touching the live
server. The stock SDKHooks extension crashed during its entity-listener
initialization because it still used the original Linux `EntityListeners`
layout. Replacing the SourceMod core, SDKTools and SDKHooks with the rebuilt
compatibility package allowed the same stack to load 46 plugins, nine
extensions, and the maps `c1m1_hotel → c8m1_apartment`. This is a deployment
requirement for the patched server, not evidence that arbitrary native
extensions are compatible at high entity indices.

The full plugin stack also exposed a command-buffer interaction. The first
rejected command was `witch_shock_ammo_drop` while SourceMod executed the
80-command `l4d2_specialammo` config. That staging tree now loads the same 80
commands in eight small files; command order and values are unchanged, and
the two-map run recorded zero `Cbuf_AddText: buffer overflow` warnings. The
L4D2-incompatible `nextmap.smx` remains disabled.

Nine workshop VPKs contained malformed mission definitions. Private copies
were repaired in place at the VPK directory entry, with the originals kept
for rollback; all 84 VPKs then loaded with zero mission parse errors. The
repair record and hashes are in
[`reports/compat-production-20261027/mission-vpk-repairs.json`](../reports/compat-production-20261027/mission-vpk-repairs.json).

This is a startup/configuration and map-transition acceptance. It does not
cover two real Steam users, public/VAC operation, or high-index behavior of
each production plugin.
