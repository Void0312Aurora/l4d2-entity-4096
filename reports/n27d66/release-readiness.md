# D66 release readiness

## Decision

`PARTIALLY_READY`

This is a usable experimental release candidate for a **private single-client** setup. It is not a general multiplayer release and it is not a claim of complete platform or plugin compatibility.

## Ready within the declared scope

- Windows client image and Proton client byte-delta manifests are bound to build `23990068`; native Windows runtime remains untested.
- Linux dedicated-server manifest covers the dynamically used patched engine and game DLLs.
- Source SHA-256 mismatch stops before copying.
- Dry-run, isolated target, output SHA-256, marked receipt, backup and restore paths exist.
- D65 evidence checker remains green for the real ladder, index 4095, special infected, map transition and limited SourceMod probe.
- D66 independently recomputes the raw five-level/4095 lifecycle and the network 10-bit wrap at index 2229.
- A 317.5-second single-map bounded run passed 10 full 512-entity samples and 3 delete/recreate rounds; it is not a multi-hour claim.
- A newly rebuilt pinned SourceMod core, SDKTools, SDKHooks and probe loaded in a private server and passed the 2048 reference/hook/delete smoke test.
- README, Chinese landing page, compatibility table, architecture diagrams, benchmark data and research index are available.

## Blocking or excluded items

| Item | Status | Release effect |
| --- | --- | --- |
| Network 10-bit serial wrap | PASS for one natural high-index slot | Does not prove internal 15-bit wrap or all network slots |
| Internal 15-bit serial wrap | NOT_TESTED | No claim at the 32768-cycle boundary |
| Bounded soak | PASS_BOUNDED | No multi-hour leak/stability claim |
| Repeated map changes with 512 props | PARTIAL | Harness/visibility assertions stopped combined runs; D65 single transition stays PASS |
| Multi-hour soak | NOT_TESTED | No long-term leak/stability claim |
| Two real Steam clients | NOT_TESTED | Single-client scope only |
| Full simultaneous 4096 occupation | NOT_TESTED | Index 4095 is a natural boundary result |
| Windows native dedicated server | NOT_TESTED | Linux dedicated server only |
| Windows native client runtime | NOT_TESTED | Runtime evidence is Proton-only |
| Arbitrary native extensions | NOT_TESTED | SourceMod result is probe-scoped |
| Public Release/VAC/matchmaking | NOT_TESTED | No public distribution claim |

## Evidence and gate

The machine-readable gate is [validation.json](validation.json). The detailed D66 records are [network-serial.json](network-serial.json), [bounded-soak.json](bounded-soak.json), [sourcemod-smoke.json](sourcemod-smoke.json), and [raw-lifecycle.json](raw-lifecycle.json). D65’s runtime evidence remains the source of truth for the core P0 result; D66 adds installer and documentation checks without rewriting prior evidence. Use `tools/release/check_rc.py` after any new boundary or soak result.
