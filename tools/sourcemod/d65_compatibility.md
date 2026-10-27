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
