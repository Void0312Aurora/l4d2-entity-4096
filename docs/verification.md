# Verification model

D66 keeps build, integrity, raw semantics, installation and runtime checks separate. A release candidate is only as strong as the weakest layer needed for the claimed use.

| Layer | Entry point | Meaning |
| --- | --- | --- |
| Static build checks | existing `engine/verify_pe.py`, `tools/precheck_server.py`, manifest checks | Source identity, structure, expected old bytes and output hashes |
| Evidence integrity | `tools/linux/check_d65_evidence.py` | Named D65 raw snapshots exist and match the recorded module identities |
| Raw lifecycle semantics | `tools/release/check_raw_lifecycle.py` | Recomputes actual indices, wire serial, handles, origins, deletion and reuse across 54 raw snapshots |
| Installer checks | `tools/release/install.py` | Source hashes, hunk assertions, output hashes, in-place module backup and recovery behavior |
| Runtime acceptance | D65/D66 raw run directories | Real **separate Linux dedicated-server plus Windows/Proton client** lifecycle, Frida observation, map transition and D66 serial wrap; **not** client-hosted single-player |
| In-game high-index server observation | [2026-10-31 Logger/scan](../artifacts/entity-index-20261031/README.md) | Native Windows client was connected and playing; Linux server reached `Networked: 2159`, VScript index `2158`. Server-side evidence, not a native Windows client index trace |
| Windows native-client gameplay | Gameplay observation / Oct 31 Logger | Connected to Linux server and played during assisted high-index server test; native client-side trace pending |
| Linux native-client gameplay | Gameplay observation | Connected and played; high-index sync untested, occasional visual glitches to investigate |

Run the evidence and release gates:

```bash
python3 tools/linux/check_d65_evidence.py \
  reports/n27d65/validation.json \
  --evidence-root /path/to/runs/d65

python3 tools/release/check_rc.py \
  --manifest release/manifests/windows-client.json \
  --manifest release/manifests/linux-server.json \
  --evidence-root /path/to/runs/d65 \
  --source windows-client=/path/to/original-client \
  --source linux-server=/path/to/original-server \
  --serial-results /path/to/runs/d66/serial-wrap6/serial-wrap-results.json \
  --long-results /path/to/runs/d66/soak-stable/soak-results.json \
  --installer-results reports/n27d66/installer-results.json \
  --installer-results reports/n27d66/installer-linux-results.json
```

The D65 record is `PARTIAL_WITH_CORE_P0_PASS`. Its `PASS` entries cover the tested scope; D66 adds a real wire-serial result and a bounded single-map soak, while internal serial wrap, two-client concurrency and multi-hour soak remain explicit `NOT_TESTED` entries. The D66 gate preserves that distinction.

D65 is kept unchanged as a historical record. D66's wire-wrap result is
separate: `check_serial_result.py --run /path/to/serial-wrap6` recomputes
1025 create events, 1024 deletes/invalid-old-reference events and 13 raw
snapshots, including wire serial `1023 → 0 → 1`. The internal 15-bit wrap
remains untested. On an empty client slot, the local cached serial may be
1024 immediately after deleting 1023; the pointer is null, and the next
created object's serial is exactly 0.

Supplying `--source` makes the gate reconstruct every candidate in a
temporary directory: source size/hash, every old-byte assertion, output
size/hash and x86 PE/ELF structure are checked separately from runtime
evidence. Without source trees, reconstruction is `NOT_TESTED`.

`tools/release/check_serial_arithmetic.py` produces `reports/n27d66/serial-arithmetic.json`. It proves only the documented 10-bit/15-bit encode-decode arithmetic and marks `runtime_claim` as `NONE`; it is not a substitute for the live serial runner.

## Single-player/listen-server validation (not yet implemented)

The published Windows [release manifest](../release/manifests/windows-client.json) patches `engine.dll` and `client.dll` but **does not** include `server.dll`. A historical [Windows game-server manifest](../manifests/server.json), [builder](../tools/build_server.py) and [static research report](../reports/report.md) record an experimental 808-site candidate with 30/30 PE preflight; these are not release or runtime acceptance evidence. The [N26 process-local loopback finding](../reports/network-n26-baseline.md) concerns two **separate** processes using `127.0.0.1`, not an in-process listen-server failure.

To claim Windows client-hosted single-player with 4096 edicts, independently record: (1) original Windows single-player startup as baseline; (2) current patched client startup while remaining below 2048, to detect regressions without presuming their cause; (3) loaded module identity, server initialization and local transport/loopback trace; (4) a re-audited and integrated Windows game-server implementation; (5) live allocation and paired client observations at `2047`, `2048`, `2049` and `4095`, including creation, updates, deletion/reuse and map transition. A PASS for the dedicated-server path cannot substitute for these tests. No listen-server acceptance result or root-cause trace is recorded by the current release.

## 2026-10-31 gameplay-assisted crossing

The separately published [run log](../artifacts/entity-index-20261031/entity_limit_2026-10-31_00-20-00.log) records `All: 2374` and `Networked: 2159`; the [VScript scan](../artifacts/entity-index-20261031/runtime-index-scan.txt) records max index `2158` as `infected` and `over2047=105`. The [fill script](../artifacts/entity-index-20261031/entity_index_fill.nut) generated persistent hidden props to force high-index allocation, and the [scan script](../artifacts/entity-index-20261031/entity_index_scan.nut) captured the server-side result. Assign `RUNTIME_OBSERVED` / `PASS_BOUNDED` to this crossing only. The different `count=2397` and `unique=2127` scan values rule out equating traversal count with exact distinct active edicts. The 28-minute Logger interval does not quantify time above 2047.

This is **not** an additional D65/D66 client synchronization pass, a natural-only horde threshold test, or a 4096-slot occupancy test. No raw gameplay/client trace was added to the release gate by this documentation update.

## Linux native-client verification

The native Linux client has been used for normal server-connected gameplay. High-index synchronization (`2048+`) has not been tested; occasional loading/rendering glitches remain uninvestigated. A dedicated high-index client trace is needed if claiming full 4096-index support.

## Evidence rules

- A static manifest does not prove runtime behavior.
- One client connected to a Linux dedicated server does not validate Windows client-hosted single-player/listen-server mode; neither historical `server.dll` preflight nor an unrelated out-of-process loopback observation changes this.
- A server-side snapshot does not prove client visibility.
- A filler-assisted high-index infected observation does not prove an unassisted horde reaches that index, or that a long snapshot interval was spent above the threshold.
- A natural index-4095 run does not prove full 4096-slot occupation.
- A finite serial observation does not prove wraparound safety.
- A compatibility probe does not prove arbitrary third-party extension compatibility.

The raw evidence is external to the repository because it contains large process snapshots and private paths. The repository stores the compact D65 ledger, validation record, generated charts and the scripts needed to re-run the checks.
