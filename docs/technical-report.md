# L4D2-4096 technical report

## Abstract

The stock Left 4 Dead 2 build used by this project is build `23990068`. Its
engine allocates 2048 network edicts, indexed `0..2047`. The game module also
keeps a 4096-entry `CBaseEntityList`; the upper part of that list is used for
non-network entities. Raising one engine constant to 4096 therefore makes the
new network range overlap the old non-network pool.

L4D2-4096 changes the coupled storage, handle, snapshot and client paths. The
tested release candidate exposes network indices `0..4095`, an internal list
of 8192 entries, and a reserved internal slot at `4096`; non-network entries
use `4097..8191`. Client and server network paths use 12-bit entity indices,
while the internal handle index is 13 bits. The protocol's entity serial stays
10 bits; the internal handle serial stays 15 bits. These widths are deliberately
separate.

D65/D66 high-index client synchronization was tested with a Linux dedicated
server and patched Windows client through Proton. A native Windows client also
connected and played on the Linux server during the October 31 in-game test;
its server Logger reported `Networked: 2159` and VScript reached index `2158`.
Linux native-client gameplay has also been reported; its high-index support remains untested. D65 completed real create/update/delete
and allocator-reuse tests at `16/64/128/256/512` loads and at network index
`4095`, special-infected and one map-transition tests. D66 independently
recomputed the raw lifecycle records, completed one natural 1024-cycle wire
serial wrap at index `2229`, ran a 317.5-second bounded 512-entity test, and
repeated a limited SourceMod compatibility smoke test. A 2026-10-31 in-game test on `c6m1_riverbank` reached index `2158` (`infected`) with hidden filler entities. The release decision is
`PARTIALLY_READY` for a private single-client setup. It is not evidence of
full-slot occupation, multi-user operation, multi-hour stability, independent
native Windows high-index client-side verification, or arbitrary extension compatibility.

Evidence labels in this report are explicit:

| Label | Meaning |
| --- | --- |
| `STATIC_CONFIRMED` | Supported by binary, disassembly, manifest or data-layout analysis. |
| `RUNTIME_OBSERVED` | Seen in a real process, with a bounded experiment. |
| `END_TO_END_VERIFIED` | Server and patched client observed the behavior together. |
| `INFERRED` | Supported by several observations but not closed by a direct test. |
| `NOT_TESTED` | No qualifying experiment is recorded. |
| `SUPERSEDED` | A historical statement was corrected by later evidence. |

## Original engine architecture

The engine's edict array is the network-facing table. In the stock path,
`sv.max_edicts` is 2048 and an edict is selected by its position in the
`pEdicts` array. The stock allocator can reach indices `0..2047`; an attempt
to allocate beyond the configured limit follows the engine's no-free-edicts
error path. The D26 isolated storage test confirmed the analogous expanded
path can allocate through `4095`, but that test did not involve a client.

The game module has a separate `CBaseEntityList`. Each `CEntInfo` is 16 bytes:
an entity pointer, a serial, and two list links. The stock list has 4096
entries. Its network entries occupy `0..2047`; slot `2048` is skipped by the
non-network free-list constructor; the non-network free list starts at
`2049`. `AddEntityAtSlot` uses an edict-derived index directly, while
`AddNonNetworkableEntity` removes an entry from the same upper range. There is
no independent collision check in the old `AddEntityAtSlot` path.

An internal `CBaseHandle` combines an index and a serial. The stock layout is
an index mask of `0xFFF` (12 bits) and a 15-bit serial shifted by 12. This is
not the same as the network representation: the network snapshot carries a
10-bit serial field. A VScript entity index is also not a reliable internal
slot number for a non-network object; D62 observed a non-network relay in
internal slot `4416` whose public edict index was zero.

The client has additional storage that is coupled to the network width. The
stock client frame and related bitmap consumers use 256-byte (2048-bit)
bitmaps, 2048-entry baseline storage, and frame members at the original
offsets. The network serializer and parser contain separate index, count,
bitmap and serial fields. Treating every occurrence of `2048`, `0x7ff` or
`0x100` as the same constant is therefore unsafe.

## Expansion architecture

The final server partition is:

| Range | Role | Evidence |
| --- | --- | --- |
| `0..4095` | Network edicts | `STATIC_CONFIRMED` by release manifests; `END_TO_END_VERIFIED` at selected indices. |
| `4096` | Reserved boundary slot | `RUNTIME_OBSERVED` in D62 list snapshots. |
| `4097..8191` | Non-network entity pool | `RUNTIME_OBSERVED` in D62 list and free-list checks. |

The entity list is relocated as an 8192-entry object (about `0x20038` in the
D62 runtime observation). Its consumers are updated for the new base, member
offsets, free-list limits and handle extraction. The reserved slot prevents a
network boundary value from being mistaken for a non-network allocation.

Only changing `MAX_EDICTS` is insufficient for three independent reasons:

1. A high edict would write into the stock non-network `CEntInfo` range.
2. A 12-bit handle index cannot represent internal slot `4096..8191`.
3. Snapshot, baseline, bitmap and client consumers still have 2048-sized
   storage or 11-bit assumptions.

The expansion leaves the internal serial at 15 bits. Network serial encoding
remains 10 bits, so it necessarily repeats after 1024 network reuse cycles.
D66 tested that repetition at one naturally reused high slot; it did not test
the internal 32768-cycle boundary.

## Engine binary modifications

The release manifests are the byte-level source of truth:

- `release/manifests/windows-client.json` contains the build-pinned Windows
  engine and game-module deltas.
- `release/manifests/linux-server.json` contains the Linux engine and server
  game-module deltas.
- `tools/release/install.py` verifies source hashes and old bytes before making
  an isolated copy, and verifies output hashes afterward.

The modifications fall into these groups:

1. **Capacity and storage.** Edict and change-info capacities are extended;
   reuse-time storage is relocated where the expanded array no longer fits.
2. **Entity-list migration.** The server list is moved to new writable storage;
   constructor counts, free-list boundaries, member offsets and 587 relative
   relocations are updated. D62 also fixed 20 missed object-tail operands and
   10 missed instance-method handle consumers.
3. **Handle encoding.** Index masks and shifts change from the stock internal
   layout to 13-bit indices. Sites are selected by semantic manifests, not by
   replacing every matching immediate.
4. **Snapshot and frame storage.** Client-frame bitmaps expand from 256 to
   512 bytes, baseline storage is expanded to 4096 entries, and the large
   stack bitmap is relocated to avoid overlapping `CEntityWriteInfo` locals.
   Associated frame pool sizes and member offsets are migrated together.
5. **Network encoding.** Entity index fields become 12 bits. PacketEntities
   count/entry sites that need the larger capacity use 13-bit handling. The
   network serial remains 10 bits. Writer and reader paths are patched as a
   pair; they are not one universal bit-width substitution.
6. **Compatibility consumers.** The tested SourceMod build changes the SDK
   `MAX_EDICT_BITS` definition from 11 to 12 and uses a relocated Linux
   SDKHooks `EntityListeners` gamedata offset.

The manifests identify the precise offsets and old/new byte assertions. This
report intentionally does not reproduce thousands of machine-code hunks; see
[the patch map](patch-map.md). No complete Valve DLL or SO is distributed.

## Network protocol and snapshot processing

The network entity index is a 12-bit value after the change, covering
`0..4095`. The internal entity-list index is 13 bits, covering `0..8191`.
They are related by the server's entity mapping but are not interchangeable.

The network serial is a 10-bit field. It identifies a network incarnation in
the snapshot stream and is compared with the low ten bits of the internal
serial. D62 observed this truncation directly, and D66 observed the sequence
`1023 -> 0 -> 1` on both server and patched client at index `2229` after 1024
ordinary allocator cycles.

The D65 validation record deliberately marked `WIRE_SERIAL_WRAP` as
`NOT_TESTED`. The later D66 record is the separate runtime result that changes
only this conclusion; it does not retroactively upgrade the D65 experiment.

`PacketEntities` has both entity-index fields and count/entry fields. A count
describes how many records or groups are present; it is not an entity index.
The manifest therefore records separate sites: index readers/writers use the
12-bit representation, while sites whose count or entry capacity crosses the
old limit use 13-bit handling. The D25/N27 reports document why the stack
bitmap, frame bitmap, and count fields cannot be changed by a single constant
replacement.

On the server, `WriteDeltaEntities` selects a target and baseline frame,
builds the entity delta stream, and writes the snapshot bit fields. On the
client, the corresponding reader processes the packet, updates baseline and
frame state, and materializes or removes client entities. The patch must keep
these paths symmetric: an unmodified client cannot decode an index at or above
`2048`, even if the server can allocate it.

The historical N27 reports retain several corrections. Early frame-only
experiments were initially attributed to snapshot layout, then Frida and
client-side traces showed that some runs failed before signon or after FULL;
the final D65/D66 runtime evidence is the authoritative scope for the release
claim. The old `0x1DDE90` interpretation was corrected in D30: it is a client
bitmap consumer, while the nearby `CClientFrame` access is a separate site.

## Entity lifecycle and failure analysis

The intended lifecycle is:

1. The normal allocator returns an edict and the server creates a networkable
   entity at its actual index.
2. The entity list assigns an internal handle with a 13-bit index and a
   15-bit serial; snapshot code sends the network index and low 10 serial bits.
3. The patched client receives the delta, creates or updates its corresponding
   object, and advances its observation state.
4. Removal clears the pointer, increments the internal serial modulo 15 bits,
   invalidates the old handle, and makes the slot eligible for normal reuse.
5. A later allocation may reuse the slot with a new internal serial and a
   possibly repeated network serial.

D56 supplied the original failure model: the old 4096-entry entity list let a
high network edict overwrite a non-network slot such as the old sky-camera
range. The final release does not rely on a null check in
`ClientData_Update`; D61/D62 move the pool and observe the list invariants
at runtime.

D62 observed network slots `2048`, `2049`, `2095`, `2096`, and `4095` together
with a real sky-camera at internal index `4143`. It recorded actual removal,
serial increment, free-list integrity, normal reuse and invalid old handles.
The same server/client loop covered update, disconnect, reconnect, update
again and final deletion for one client. This is `END_TO_END_VERIFIED` for the
declared single-client scenario, not for every disconnect variant.

D63 retained a real Hunter pressure failure but did not establish that the
expansion caused it. D64 compared the original game path and identified an
invalid Hunter VScript usage in the experiment. Legal creation paths were used
in D65, where six special infected coexisted with 512 high-index props and
their damage/death events completed. The D63 expansion-root-cause statement is
therefore `SUPERSEDED`; the crash observation remains historical evidence.

## SourceMod and extension compatibility

Stock SourceMod core and stock SDKHooks do not form a general compatibility
layer for this expansion. D65 observed invalid high-index results from the
stock core API and a stock SDKHooks crash at the old Linux `EntityListeners`
offset. D66 rebuilt pinned sources:

- SourceMod `1.12.0.7259`, commit
  `3808e21eb842d8598cc8351a341dcbe661d21b58`;
- Metamod:Source `1.12.0-dev+1228`, commit
  `cb47755826fad1483291e5dc00222aa64303d12f`;
- L4D2 SDK commit `2a31cd007b2d7d2f964dc093eedcf7a812cf9dd6`.

The compatibility build changes only the SDK `MAX_EDICT_BITS` header value
from 11 to 12 and applies the tested SDKHooks gamedata offset `131108`. The
rebuilt core, SDKTools, SDKHooks and D65 probe loaded; reference round trips at
`0/2047/2048/2049`, a 4095 callback, and post-delete old-reference invalidation
passed. This is `END_TO_END_VERIFIED` for that probe scope. DHooks, left4dhooks,
L4DToolZ and arbitrary third-party native extensions are `NOT_TESTED`.

## Windows single-player / in-process listen-server boundary

The project's **single-client** end-to-end claim refers to one Windows/Proton client and a **separate patched Linux dedicated server**. It is not acceptance of L4D2's Windows client-hosted **single-player/listen-server** path. In the latter, the game process also runs local game-server logic, which must agree with the client's entity range and packet/snapshot handling. A dedicated-server success is insufficient to certify this distinct execution arrangement.

The current [Windows release manifest](../release/manifests/windows-client.json) contains `bin/engine.dll` and `left4dead2/bin/client.dll` only; the local Windows game-server module `left4dead2/bin/server.dll` is not in the supported release patch set. The [Linux release manifest](../release/manifests/linux-server.json) instead covers `engine_srv.so` and `server_srv.so`. **Expanded Windows single-player is not implemented or runtime-validated in the current release.** Neither the result of ordinary low-index single-player with these patched client modules nor the precise first failing stage is recorded.

There **is** prior Windows `server.dll` work: the [historical research report](../reports/report.md) (sections 75, 176–177), [manifest](../manifests/server.json), and [builder](../tools/build_server.py) describe static layout/handle research, an isolated experimental server-module image and a later 808-site candidate with 30/30 PE checks. That work is not equivalent to a current build-pinned release artifact or a three-module listen-server runtime test. Its assumptions and binary identity require re-audit before any integration.

The [N26 loopback baseline](../reports/network-n26-baseline.md) investigated `127.0.0.1` between **separate processes**, where process-local `NET_SendLoopPacket` prevented a reply reaching the independent client; the LAN-address control worked. This does not prove the in-process Listen Server loopback path is broken. The local initialization, edict partition, loopback transport, snapshot serialization and entity lifecycle have not been jointly measured in the expanded Windows single-player configuration. Their failure mechanisms remain **undetermined**, not diagnosed.

Acceptance should proceed by comparing original and patched low-index single-player startup, auditing and integrating Windows game-server support where needed, capturing the actual local-server connection path, and finally observing high-index entity creation, client state, deletion/reuse and map transition. See the [compatibility notes](compatibility.md#single-player-and-listen-server-scope) and [verification model](verification.md).

## Experimental validation

| Objective | Result | Evidence level and boundary |
| --- | --- | --- |
| Static capacity, manifest and byte identity | PASS | `STATIC_CONFIRMED`; build `23990068` only. |
| Linux edict storage through 4095 | PASS | `RUNTIME_OBSERVED`; D26 had no client. |
| Real 16/64/128/256/512 ladder | PASS | `END_TO_END_VERIFIED`; one client and bounded sessions. |
| Normal allocator index 4095 | PASS | `END_TO_END_VERIFIED`; not all 4096 slots occupied. |
| High-index update/delete/reuse | PASS | `END_TO_END_VERIFIED`; selected slots and raw lifecycle checks. |
| Six special infected with high-index load | PASS | `END_TO_END_VERIFIED`; infected players remained in their normal player range. |
| One map transition and recreation | PASS | `END_TO_END_VERIFIED`; corrected private startup order. |
| Disconnect and reconnect | PASS | `END_TO_END_VERIFIED`; single-client E/G loop, not all variants. |
| Network 10-bit serial wrap | PASS | `RUNTIME_OBSERVED`/dual-end at index 2229, 1024 cycles. |
| Internal 15-bit serial wrap | NOT_TESTED | No safe 32768-cycle live run. |
| Bounded 512-entity run | PASS_BOUNDED | 317.5 seconds, 10 samples, three recycle rounds; no multi-hour claim. |
| 512-entity repeated map transitions | PARTIAL | Visibility/harness failures retained; possible PVS effect is unresolved. |
| SourceMod compatibility | PASS | Rebuilt components and probe only. |
| Native Windows client gameplay | TESTED (basic) | Connected to Linux server and played during Oct 31 server-side high-index observation (`Networked: 2159`); native client-side index trace pending. |
| Native Linux client gameplay | TESTED (basic) | Connected to server and played; high-index synchronization untested. |
| Native Linux client loading/rendering | UNTRIAGED | Occasional glitches during gameplay; investigation pending. |
| Windows single-player / listen server with 4096 edicts | NOT_IMPLEMENTED / NOT_TESTED | No Windows `server.dll` in the current release manifest; historical static prototype exists but no integrated or runtime-accepted local-server path. |
| Active gameplay with filler-assisted indices >=2048 | PASS_BOUNDED | `RUNTIME_OBSERVED` on patched Linux server; VScript max index 2158 (`infected`), Logger `Networked: 2159`; no independent high-index client trace in this run. |

### Gameplay-assisted high-index observation (2026-10-31)

A separate `c6m1_riverbank` session on the patched Linux 4096 server set `z_common_limit=500` and spawned persistent, invisible `prop_dynamic_override` fillers below the map through VScript. Holding the fillers alive reduced immediate reuse of low indices while normal gameplay continued. The published Entity Limits Logger report records `All: 2374` and `Networked: 2159`. A direct VScript scan recorded `count=2397`, `unique=2127`, `negative=0`, `max=2158`, `maxclass=infected`, and `over2047=105`. The last value is the scan's count of observations at indices >=2048; it is not an independently deduplicated count. In particular, `count` and `unique` differ, so neither `count` nor the Logger total independently establishes the number of simultaneously occupied *distinct* network edicts.

The [published evidence directory](../artifacts/entity-index-20261031/README.md) includes the [Logger log](../artifacts/entity-index-20261031/entity_limit_2026-10-31_00-20-00.log), [scan output](../artifacts/entity-index-20261031/runtime-index-scan.txt), [fill/cleanup helper](../artifacts/entity-index-20261031/entity_index_fill.nut), and [scanner](../artifacts/entity-index-20261031/entity_index_scan.nut). This is `RUNTIME_OBSERVED` for gameplay-assisted server allocation of a common infected beyond index 2047, not evidence that an unassisted horde exceeded the limit. The report's 28-minute snapshot interval is not a measurement of sustained time above the threshold. There is no new client-side index/snapshot trace for this session; D65/D66 end-to-end evidence is separate.

The compact records are linked from [evidence and reproduction](evidence-and-reproduction.md).
The D65 and D66 machine-readable records are kept unchanged as historical
inputs to the current report.

## Known limitations

- The manifests and byte assertions are tied to build `23990068`. A later
  Steam update requires a new audit and reconstruction.
- Two real Steam clients were not available and remain `NOT_TESTED`.
- Client-hosted Windows single-player/listen-server expansion is `NOT_IMPLEMENTED` in the current release and `NOT_TESTED` as an integrated configuration. Historical `server.dll` static work exists but is not a validated release component; process-local loopback is not a diagnosed fault.
- Native Windows client gameplay was tested, but a same-run native Windows
  client-side high-index trace is pending. Windows dedicated server remains
  `NOT_TESTED`. Linux native-client gameplay was tested; its high-index support
  remains unverified and occasional loading/rendering issues are under review.
- Internal 15-bit serial wrap is `NOT_TESTED`; the network 10-bit wrap result
  covers one naturally reused slot.
- Multi-hour stability and full simultaneous occupation of all 4096 network
  slots are `NOT_TESTED`.
- The 2026-10-31 gameplay-assisted crossing does not test natural-only
  saturation of the old limit, duration above 2047, or independent client
  synchronization of the high-index infected in that same session.
- Repeated 512-entity map transitions remain `PARTIAL`. The continuous
  missing-client-object pattern is recorded, but its PVS/visibility cause is
  not established.
- Third-party native extensions, VAC behavior, public matchmaking and public
  distribution are `NOT_TESTED`.
- The raw D65/D66 process snapshots and logs are outside the repository. The
  repository contains compact records, hashes and checkers, not a claim that
  an external reader can replay every historical run without the original
  private game files.

## Future work

The useful next steps include auditing the historical Windows `server.dll` candidate and validating client-hosted single-player/listen-server separately from the proven dedicated-server setup. Other planned work includes a second legal Steam client, native Windows client-side and
Linux-native high-index acceptance (if claimed), a separately designed long-duration run, explicit
full-slot occupancy testing, unassisted horde-pressure sampling, a paired
client/server gameplay trace above 2047, and extension-by-extension compatibility work.
Each needs new evidence; none should be inferred from the current 4095 or
single-client results. Supporting a later L4D2 build requires re-analysis and
new manifests. An 8192-network-edict expansion is only a future research
direction: the current 8192 value is the internal entity-table capacity, not
8192 network edicts.

## AI-assisted research and development

Most reverse-engineering passes, static analyses, patch-generation scripts and
runtime harnesses were produced with AI coding agents. Human direction covered
the research questions, engineering choices, experiment coordination, result
review and scope decisions. AI output was treated as a hypothesis: the project
used original-binary comparisons, byte assertions, real process observation,
independent raw-evidence checkers and bounded end-to-end tests before assigning
the labels above. Historical corrections remain visible because generated
analysis is not accepted merely because it is plausible.

## Primary references

- [Architecture](architecture.md)
- [Patch map](patch-map.md)
- [Evidence and reproduction](evidence-and-reproduction.md)
- [Research index](research-index.md)
- [D62 lifecycle report](../reports/n27d62/findings.md)
- [D65 validation report](../reports/n27d65/findings.md)
- [D66 release report](../reports/n27d66/findings.md)
