# Compatibility

## Platform matrix

| Platform or component | Status | What was actually tested |
| --- | --- | --- |
| Linux dedicated server | Experimental | Patched engine/game DLLs, real high-index allocations and a Proton client |
| Windows client image | Experimental; native runtime NOT_TESTED | Patched module slots at 2048, 2049 and 4095 observed through Proton |
| Proton Windows client | Experimental | Sign-on, synchronized updates, deletion, reuse and map transition |
| Windows native dedicated server | NOT_TESTED | No end-to-end D66 evidence |
| Linux native client | NOT_TESTED | No client build or runtime evidence |
| Two real Steam users | NOT_TESTED | One local Steam account was available during D65 |
| Public matchmaking/VAC | NOT_TESTED | Private/insecure experiments only |

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

On 2026-10-27, a private copy combining the patched Linux server modules with
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
80-command `l4d2_specialammo` config. The private copy now loads the same 80
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
