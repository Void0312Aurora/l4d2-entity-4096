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

The stock core high-index API returned invalid indices. Stock SDKHooks crashed while reading the old Linux `EntityListeners=65572` offset. The compatibility result therefore means **compatible for the tested probe scope**, not “all plugins work”. Other native extensions, including DHooks, left4dhooks and L4DToolZ, remain untested.

The reproducible source notes and probe are in [`tools/sourcemod/d65_compatibility.md`](../tools/sourcemod/d65_compatibility.md) and [`tools/sourcemod/d65_probe.sp`](../tools/sourcemod/d65_probe.sp).

D66 adds `tools/sourcemod/build_compat.py`, which checks the three pinned
repositories and recursive submodules before building and packaging the
minimal SDK/gamedata changes. See [the recorded artifact hashes](../reports/n27d66/sourcemod-build.json).
