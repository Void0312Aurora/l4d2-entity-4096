# D65 SourceMod compatibility probe

The isolated build used SourceMod `3808e21eb842d8598cc8351a341dcbe661d21b58`,
Metamod:Source `cb47755826fad1483291e5dc00222aa64303d12f`, and the L4D2 SDK
at `2a31cd007b2d7d2f964dc093eedcf7a812cf9dd6`. The SDK copy changes only
`MAX_EDICT_BITS` from `11` to `12`; the repository does not ship the external
SourceMod binaries or Valve binaries.

The probe keeps SourceMod's real 15-bit serial semantics. It does not create an
index virtualization layer. The separate gamedata override changes the Linux
`EntityListeners` offset from `65572` to `131108`, matching the relocated list.
The tested scope is the core entity API, SDKTools, SDKHooks, and the D65 probe;
it is not a promise that arbitrary native extensions are compatible.

## Reproduce the D66 package

Use private source trees and a Linux x86-capable C/C++ toolchain (32-bit
development libraries are required). D66 used Python 3.13 and AMBuild 2.0.
The source repositories are:

- [SourceMod](https://github.com/alliedmodders/sourcemod), pinned above;
- [Metamod:Source](https://github.com/alliedmodders/metamod-source), pinned above;
- [HL2SDK L4D2](https://github.com/alliedmodders/hl2sdk), pinned above.

Check out each exact commit and run `git submodule update --init --recursive`.
Name the SDK directory `hl2sdk-l4d2`. Install AMBuild into a separate Python
environment; the same interpreter must run the following commands.

```bash
python tools/sourcemod/build_compat.py \
  --source /path/to/sourcemod-src \
  --metamod /path/to/metamod-source \
  --sdk /path/to/hl2sdk-l4d2 \
  --build /path/to/sm-build --check-only

python tools/sourcemod/build_compat.py \
  --source /path/to/sourcemod-src \
  --metamod /path/to/metamod-source \
  --sdk /path/to/hl2sdk-l4d2 \
  --build /path/to/sm-build
```

The builder rejects other source commits, unexpected tracked changes and
submodule drift. It applies only `public/const.h: MAX_EDICT_BITS 11 → 12`,
configures upstream for Linux x86/L4D2 without MySQL, builds the package,
compiles `d65_probe.sp`, and places the gamedata override at
`addons/sourcemod/gamedata/sdkhooks.games/custom/d65-entitylisteners.txt`.
It writes `l4d2-4096-compat.json` with source commits and artifact hashes.
Automatic upstream version metadata can change a core binary hash between
builds; the D66 ledger records the actual artifacts rather than assuming
bit-for-bit reproducibility.

## Private-server smoke test

Stop only your private test server before replacing its SourceMod files.
Back up that private `addons/sourcemod` tree. Copy the built package into
the private server, retaining your existing configuration. Metamod must
already be installed; the builder checks its source identity but does not
install or rebuild Metamod automatically.

In the private server console:

```text
meta list
sm exts list
sm plugins list
script_execute d65_load
script d65_create(16)
sm_d65_probe 2048
sm_d65_hook 2048
sm_d65_remember 2048
script d65_remove()
sm_d65_old
```

Require the rebuilt core, SDKTools and SDKHooks to be loaded, a real
`D65_SM_REF index=2048 ... resolved=2048`, and the old reference to resolve
to `-1` after the delete has completed. `d65_load.nut` comes from
`tools/linux/vscript/` and must be copied into the private server's
`left4dead2/scripts/vscripts/` first. The ordinary allocator may choose a
different high slot; use the actual `D65_CREATED idx=` value in that case.

The public compatibility claim remains limited to this core/API/hook scope.

`sm_d65_force <index>` is only a normal allocator smoke helper; SourceMod's
`CreateEntityByName` native does not accept a requested entity index. The probe
now reports the actual allocated index and skips `SDKHook` when the supplied
index is invalid. Use the VScript `d65_create` sequence above for a real
high-index allocation test.
