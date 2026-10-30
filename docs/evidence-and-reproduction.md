# Evidence and reproduction

This document separates what is public in the repository from what was used
in the private game runs. The compact JSON records are evidence summaries and
hash ledgers; they do not imply that the original process snapshots are
published.

## Evidence levels

| Level | Repository example | What it supports |
| --- | --- | --- |
| Static | release manifests, engine/manifest*.json, data/*.csv, disassembly notes | Expected bytes, widths, layout and artifact identity |
| Runtime observation | D26/D61/D62 reports and compact snapshots, [2026-10-31 gameplay-assisted scan](../artifacts/entity-index-20261031/README.md) | A bounded behavior in the named process and environment; does not by itself establish client delivery |
| End-to-end | D65 validation and D66 smoke records | Patched server and patched client observed together |
| Recomputed | check_d65_evidence.py, check_raw_lifecycle.py, check_serial_result.py | The compact/raw inputs satisfy explicit invariants |
| Missing | external raw run directories | Cannot be independently replayed from the repository alone |

The checkers are not historical replay by themselves. A checker result is only
as strong as the inputs it receives, and a script that can be run without raw
inputs is not proof that the old experiment has been replayed.

## Public evidence matrix

| Conclusion | Public summary | Public raw or compact record | Checker / entry point | Independent replay boundary |
| --- | --- | --- | --- | --- |
| Entity-list partition and 4095 lifecycle | D62 findings | reports/n27d62/validation.json, reports/n27d65/entity-ledger.json | tools/linux/check_d62_evidence.py, tools/release/check_raw_lifecycle.py | Compact records are public; original memory snapshots are local |
| 16/64/128/256/512 ladder | D65 findings | reports/n27d65/validation.json | tools/linux/check_d65_evidence.py, tools/release/check_raw_lifecycle.py | Requires original D65 evidence root and legal build-matched files |
| Normal allocator boundary 4095 | D65/D66 findings | D65 validation and D66 raw-lifecycle record | tools/release/check_raw_lifecycle.py | Public result and hashes; full snapshots are not bundled |
| Wire serial wrap | D66 findings | reports/n27d66/network-serial.json | tools/release/check_serial_result.py against original run | JSON summary is public; raw snapshots and event log are local |
| Bounded 512-entity run | D66 findings | reports/n27d66/bounded-soak.json | tools/release/check_soak_result.py against raw samples | Sample files are local; result is bounded, not multi-hour |
| SourceMod compatibility | D66 findings | reports/n27d66/sourcemod-build.json, sourcemod-smoke.json | tools/sourcemod/build_compat.py --check-only; smoke record | Source commits and artifact hashes are public; raw private log is hashed only |
| Map transition | D65 validation and findings | D65 compact record | D65 evidence checker | One corrected private transition; repeated 512 transitions remain partial |
| Gameplay-assisted indices beyond 2047 | [2026-10-31 evidence overview](../artifacts/entity-index-20261031/README.md) | [Logger log](../artifacts/entity-index-20261031/entity_limit_2026-10-31_00-20-00.log), [VScript scan](../artifacts/entity-index-20261031/runtime-index-scan.txt) | [fill/cleanup](../artifacts/entity-index-20261031/entity_index_fill.nut), [scan](../artifacts/entity-index-20261031/entity_index_scan.nut), [SHA256SUMS](../artifacts/entity-index-20261031/SHA256SUMS) | Patched Linux server in gameplay, max index 2158 (`infected`); no same-run independent client-side trace, no natural-only saturation or sustained threshold duration |

## What is published

The repository publishes source-side manifests, byte assertions, compact
validation ledgers, selected assembly notes, scripts, generated diagrams and
hashes. The source commit pins for the compatibility build are public. The
two historical references mentioned in the audit remain real files:
archive/gen_manifest.py.broken and reports/precheck/precheck.json; they are
retained historical inputs, not recreated placeholders. The latter contains
historical machine-specific paths, so it should be read as an old audit record,
not as a portable current installation path.

The repository does not publish Valve's complete original or modified DLL/SO,
Steam credentials, process dumps, cores, raw memory snapshots, unfiltered
Proton logs, or the large private Workshop cache. D62–D66 reports intentionally
refer to those files by compact names and hashes where appropriate.

## Gameplay-assisted index evidence (2026-10-31)

The published run occurred on `c6m1_riverbank` with the patched Linux server. `z_common_limit=500` raised the permitted infected population; it does **not** establish that 500 infected were simultaneously alive. The fill helper spawned invisible `prop_dynamic_override` entities at `0 0 -10000`, retained handles to keep them alive, and offered `entity_index_fill_cleanup()` for removal. The scan helper used `Entities.First()` / `Entities.Next()` and `GetEntityIndex()`.

- Entity Limits Logger: `All: 2374`, `Networked: 2159`.
- VScript: `count=2397`, `unique=2127`, `negative=0`, `max=2158`, `maxclass=infected`, `over2047=105`.
- Interpretation: the observed maximum is an ordinary infected entity above the old 2047 maximum under filler-assisted in-game load. Because the traversal returned more observations than distinct indices, scan counts must not be reported as exact simultaneous distinct network-edict occupancy. The Logger totals are presented as reported, without equating them to an independently audited allocator occupancy.
- Boundaries: the saved report spans a 28-minute snapshot interval, **not** a measured 28-minute run above the threshold; no paired high-index client packet/visibility trace for this session is published. Natural-only horde saturation and long-duration stability remain unverified.

The published scripts and records can be inspected, and the helper can be used in a matching private test to collect a **new** observation. This does not replay the historical game session or establish what the client received. Keep the original log and scan unchanged; record any future client traces and time-above-threshold measurements separately.

## Reproduce static and compact checks

Run these from the repository root with Python 3:

    python3 tools/release/check_links.py --root .
    python3 tools/release/audit_repository.py --root .
    python3 tools/release/check_serial_arithmetic.py
    python3 tools/release/check_rc.py \
      --manifest release/manifests/windows-client.json \
      --manifest release/manifests/linux-server.json
    python3 -m py_compile tools/release/*.py tools/linux/*.py tools/sourcemod/*.py

The release gate can perform source reconstruction when legal original module
trees are supplied. It should be run against private copies, for example:

    python3 tools/release/check_rc.py \
      --manifest release/manifests/windows-client.json \
      --manifest release/manifests/linux-server.json \
      --source windows-client=/path/to/original-client \
      --source linux-server=/path/to/original-server \
      --installer-results reports/n27d66/installer-results.json \
      --installer-results reports/n27d66/installer-linux-results.json

Without the external D65 raw directory, the gate must report runtime evidence
as unavailable rather than turning it into a pass. With the original run
directory present, the named checkers recompute hashes, slot pointers, serial
increments, old-reference invalidation and client/server observations.

## Reproduce the compatibility build

Use the exact SourceMod, Metamod:Source and L4D2 SDK commits in
tools/sourcemod/d65_compatibility.md. The builder rejects commit or submodule
drift and applies only the documented SDK bit-width change plus the tested
gamedata file:

    python3 tools/sourcemod/build_compat.py \
      --source /path/to/sourcemod-src \
      --metamod /path/to/metamod-source \
      --sdk /path/to/hl2sdk-l4d2 \
      --build /path/to/sm-build --check-only

The private-server smoke sequence is documented in
tools/sourcemod/d65_compatibility.md. It requires a legal, build-matched
game installation and a separately backed-up private server.

## Raw evidence export protocol

The original D65/D66 runs remain outside the repository. A future public
export should be a small, filtered dataset, not a process dump:

1. Copy the named JSON snapshots, event records and run metadata into a new
   export directory.
2. Remove absolute personal paths, credentials, tokens, core data and
   unrelated Workshop files.
3. Recompute SHA-256 values and compare them with the compact ledger.
4. Run the corresponding checker from a clean checkout.
5. Record which files were omitted and whether the checker result is a replay
   of the historical run or a new run.

Until that export is done, claims should use “public summary with local raw
evidence”, not “fully reproducible historical experiment”. No raw evidence is
manufactured when the original directory is absent.

## Evidence gaps

The following remain open: natural-only gameplay saturation above 2047, independently traced client delivery in the 2026-10-31 gameplay-assisted run, measured time-above-threshold, two real Steam clients, native Windows runtime,
native Linux client, internal 15-bit serial wrap, multi-hour soak, full
simultaneous 4096-slot occupation, repeated 512-entity map transitions, and
arbitrary native extensions. D66's repeated-transition visibility pattern is
preserved as unresolved; it is not assigned a root cause without a matching
PVS/visibility control experiment.
