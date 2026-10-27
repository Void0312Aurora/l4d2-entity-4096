# Patch map

This map explains the technical purpose of the byte manifests. The manifests
remain the machine-readable source of truth for offsets, old bytes, new bytes,
hashes and file sizes. A row below can summarize many sites; it is not a claim
that every hunk has received an independent dynamic test.

## Build identity and artifact scope

| Target module | Manifest | Build | Output role | Current status |
| --- | --- | --- | --- | --- |
| Windows bin/engine.dll | release/manifests/windows-client.json | 23990068 | Client capacity, frame, snapshot and protocol consumers | Static reconstruction PASS; runtime through Proton only |
| Windows left4dead2/bin/client.dll | same | 23990068 | Client game-module consumers and layout companions | Static reconstruction PASS; runtime through Proton only |
| Linux bin/engine_srv.so | release/manifests/linux-server.json | 23990068 | Server edicts, reuse arrays and network paths | Static reconstruction PASS; real private server PASS in tested scope |
| Linux left4dead2/bin/server_srv.so | same | 23990068 | Entity list, handles, game-module consumers | Static reconstruction PASS; real private server PASS in tested scope |

The Windows manifest contains 95 engine hunks and 1605 client-module hunks;
the Linux manifest contains 142 engine hunks and 8792 server-module hunks.
Those counts describe manifest entries, not individually completed dynamic
tests. Complete Valve binaries are intentionally absent.

## Mapping by subsystem

| Target module(s) | Original behavior | Expansion need | Modification category | Implementation source | Analysis and validation | Residual risk |
| --- | --- | --- | --- | --- | --- | --- |
| Windows/Linux engine | max_edicts, edict and change-info arrays stop at 2048 | Permit network indices 0..4095 | Capacity constants, array allocation and reuse storage | engine/manifest.json; platform release manifests | N26 storage run; D65/D66 real sessions | Other build paths and later builds require new analysis |
| Linux server game module | 4096 CEntInfo entries, upper range is non-network pool | Separate 4096 network entries from non-network entries | Object relocation, member offsets, free-list bounds, relative relocations | Linux manifest; D61/D62 builders and reports | D62 list, sky-camera, free-list and reuse snapshots | Not every one of 8184 candidate handle sites has independent runtime coverage |
| Windows/Linux client and server | CBaseHandle index mask and serial shift use stock layout | Represent internal slots through 8191 | Semantic mask, shift, compare and packing edits | manifests/*.json; data/*handle*; tools/linux/patch_entitylist_linux.py | D62 handle round trips; D65/D66 raw lifecycle checks | Invalid-handle consumers outside tested paths remain possible |
| Client/server network code | Entity index fields are 11 bits | Encode/decode 0..4095 | 11→12-bit writer/reader edits | data/netproto_width_sites.csv; reports/network-n*.md | D65 real synchronization; D66 wire-wrap | Not all packet shapes and third-party clients tested |
| PacketEntities count/entry sites | Some count fields cap the number of entries | Carry expanded counts where required | Site-specific 11/12→13-bit changes | data/netproto_width_sites.csv; N25/N27 reports | Static and selected runtime paths | Count fields must not be confused with entity indices |
| Client frame and baselines | 256-byte bitmaps and 2048 baseline entries | Store 4096 network entries | Frame-size, bitmap, pool and baseline migrations | data/linux/migration_sites.csv; N25–N27 reports | D65 real client path; raw lifecycle checks | Earlier frame-only failures show fixed-layout consumers are sensitive |
| WriteDeltaEntities stack state | 2048-bit local bitmap overlaps unrelated locals if grown in place | Keep local object layout valid | Move bitmap, change stack frame and cleanup paths | N27-D2/D3/D4 reports; engine manifest | D65/D66 sessions | Future compiler/build variants need new layout analysis |
| SourceMod SDK/API | MAX_EDICT_BITS=11; stock callbacks use old layout | Expose tested high-index API and callback range | Header rebuild and Linux gamedata override | tools/sourcemod/build_compat.py; d65-entitylisteners.txt | D66 SourceMod smoke record | Other native extensions are untested |

## Protocol and frame site classes

The network reports classify sites rather than applying a global textual
replacement:

- entity index masks and read/write widths map to 12 bits;
- count fields that can exceed the old range map to their independently
  verified wider form;
- network serial remains 10 bits;
- internal handle serial remains 15 bits;
- 256-byte frame and client bitmaps become 512 bytes where the owning object
  requires it;
- stack bitmap growth includes stack-frame relocation and matching early
  returns.

The D30 correction is part of this map: the 0x1DDE90 client bitmap consumer
is not the adjacent CClientFrame member access. The historical report
reports/n27d30/correction.md remains the audit trail.

## Relocation and verification rules

Each release hunk has an input hash and an old-byte assertion. The installer
rejects a source mismatch before replacing the listed module and verifies the
output hash after patching. tools/release/check_rc.py separately checks
manifest identity, reconstruction, D65 evidence integrity and raw lifecycle
semantics. A passing hunk assertion proves that the expected file was patched;
it does not prove the resulting code path was exercised dynamically.

The D61 report records 587 relative relocations for the moved Linux entity-list
object. D62 observes those relocations in memory and checks list invariants,
but the result remains bounded to build 23990068 and the tested server paths.

## Cross-version portability

The method is not shown to be impossible on another build, but no other build
has a validated manifest. Addresses, old bytes, object layouts and relocation
sets are version-specific. Porting requires a fresh static audit, new
manifests, reconstruction checks and client/server regression tests.
