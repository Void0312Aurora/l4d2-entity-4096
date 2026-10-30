# L4D2 Entity Limit Expansion — 2048 to 4096

L4D2-4096 is an unofficial, build-pinned expansion of the **Left 4 Dead 2** network entity limit. It raises the network range from `0..2047` to `0..4095` and the internal entity table from 4096 to 8192 slots while keeping the original Source entity semantics.

This is an experimental release candidate for private testing environments. It is not a Valve product, does not bypass Steam ownership or authentication, and does not include Valve binaries. The client and dedicated server must use matching patched images.

## Current release status

**PARTIALLY_READY — single-client experimental testing.** The runtime-tested path is a Linux dedicated server plus the Windows client through Proton. The same Windows module manifest is provided for native Windows testing; that runtime has not been independently accepted. D65 evidence covers real `16/64/128/256/512` entity ladders, index `4095`, six special infected, client synchronization, and one map transition. D66 adds a real 1024-cycle wire-serial wrap test, a 317.5-second bounded 512-entity run, in-place module installer, reproducible SourceMod build and independent raw-evidence gates. A separate 2026-10-31 gameplay-assisted runtime test on `c6m1_riverbank` observed indices beyond the vanilla boundary while the game was running, including a common infected at index `2158`. This is a bounded server-side observation, not a new client-sync or long-duration acceptance test.

The following remain outside the release claim: internal 15-bit serial wraparound, multi-hour soak, two real Steam users, full simultaneous occupation of all 4096 network slots, native Windows runtime acceptance, Linux native client, and arbitrary native extensions.

## What is supported

| Component | Status | Evidence boundary |
| --- | --- | --- |
| Linux dedicated server | Experimental | Real D65 Proton/client sessions; patched `engine_srv.so` and `server_srv.so` |
| Windows client image | Experimental; native runtime unverified | Real patched module observations at 2048, 2049 and 4095 through Proton |
| Proton Windows client | Experimental | End-to-end connection, updates, deletion, reuse and map transition |
| Windows native dedicated server | Not tested | Do not list as supported |
| Linux native client | Not tested | Do not list as supported |
| SourceMod core / SDKTools / SDKHooks | Limited compatible build | Only the API and callbacks in the D65 probe are covered |

## Install the release modules

Use a Python 3 interpreter and a legally installed build `23990068`. The
installer verifies the source hashes, backs up only the manifest-listed DLLs
next to the originals, and replaces those modules in the existing Steam game
directory. It does not copy the game tree or addons.

Check a Windows or Proton client source:

```bash
python3 tools/release/install.py check \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

Preview the source without changing files:

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2" \
  --dry-run

python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

For a Linux dedicated server, use `release/manifests/linux-server.json` with
the server root. The installer writes `*.l4d2-4096.bak` beside each patched
module and stores `l4d2-4096-install.json` in the game directory. Restore the
original modules with:

```bash
python3 tools/release/install.py restore \
  --receipt "/path/to/Left 4 Dead 2/l4d2-4096-install.json"
```

The game must be closed while modules are replaced. Steam may overwrite a
patched module during a game update; run `check` and `install` again after an
update. See [installation](docs/installation.md) for recovery details.

## Verified behavior

![Entity capacity before and after](docs/assets/diagrams/capacity.svg)

![Network path and width boundaries](docs/assets/diagrams/protocol.svg)

![High-index entity lifecycle](docs/assets/diagrams/lifecycle.svg)

![D65 real entity ladder](docs/assets/benchmark/d65-ladder.svg)

![Boundary coverage](docs/assets/benchmark/d65-boundary.svg)

| Boundary or load | Result |
| --- | --- |
| `2047` | Vanilla ceiling and API control |
| `2048` | First added index; client create/update/delete |
| `2049` | High-index client observation and reuse |
| `16/64/128/256/512` | Create, six updates, delete, reuse in real sessions |
| `4095` | Normal allocator boundary; create, six updates, delete, reuse, SDKHooks callbacks |
| Special infected | Hunter, Spitter, Smoker, Boomer, Charger and Jockey under 512 live high-index props |
| Map transition | `c1m1_hotel → c1m2_streets`, then high-index recreation and synchronization |
| Wire serial wrap | Index 2229, 1024 ordinary reuse cycles, client/server `1023 → 0 → 1` and return to initial wire serial |
| Gameplay-assisted crossing of 2048 | `c6m1_riverbank`: Logger `All: 2374`, `Networked: 2159`; VScript `max=2158`, `maxclass=infected`, `over2047=105` after persistent hidden prop fill. Server-side only; not natural-only load or a fresh client-sync trace |

The [2026-10-31 in-game evidence](artifacts/entity-index-20261031/README.md) includes the [Logger report](artifacts/entity-index-20261031/entity_limit_2026-10-31_00-20-00.log), [VScript scan](artifacts/entity-index-20261031/runtime-index-scan.txt), [fill/cleanup helper](artifacts/entity-index-20261031/entity_index_fill.nut), and [scan helper](artifacts/entity-index-20261031/entity_index_scan.nut). The scan reported `count=2397` but `unique=2127`; these do not count the same thing and must not be equated with distinct occupied network slots. The snapshot interval does not measure time above index 2047.

The machine-readable D65 record is [reports/n27d65/validation.json](reports/n27d65/validation.json), with the narrative in [reports/n27d65/findings.md](reports/n27d65/findings.md). D66’s release decision and test boundaries are in [reports/n27d66/release-readiness.md](reports/n27d66/release-readiness.md); the final gate is [reports/n27d66/validation.json](reports/n27d66/validation.json), with [wire serial](reports/n27d66/network-serial.json), [bounded soak](reports/n27d66/bounded-soak.json), and [SourceMod smoke](reports/n27d66/sourcemod-smoke.json) records.

## Architecture and verification

- [Technical report](docs/technical-report.md)
- [Patch map](docs/patch-map.md)
- [Evidence and reproduction](docs/evidence-and-reproduction.md)
- [Architecture and bit-widths](docs/architecture.md)
- [Installation and recovery](docs/installation.md)
- [Compatibility matrix](docs/compatibility.md)
- [Verification model](docs/verification.md)
- [Limitations](docs/limitations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development and reproducible builds](docs/development.md)
- [Research index](docs/research-index.md)
- [Demo storyboard and capture script](docs/demo/storyboard.md)

Run the release-candidate gate against the local D65 evidence:

```bash
python3 tools/release/check_rc.py \
  --manifest release/manifests/windows-client.json \
  --manifest release/manifests/linux-server.json \
  --evidence-root /path/to/runs/d65
```

The gate reports static identity, manifest, evidence-integrity, and end-to-end scope separately. A `PASS` for a checked layer never turns an untested layer into a pass.

## Important limits

- All addresses and byte assertions are bound to build `23990068`; a Steam update invalidates them.
- Vanilla clients cannot decode network indices at or above `2048`.
- Wire serial repeats after 1024 reuse cycles as expected. The internal 15-bit wrap remains `NOT_TESTED`.
- The gameplay-assisted >2047 observation used hidden filler entities. Natural-only saturation, full simultaneous 4096-slot occupation and sustained high-load stability are unverified. This run has no separate high-index client packet/visibility trace; D65/D66 client evidence remains distinct.
- VAC safety, public matchmaking, and public release distribution are unverified.
- Third-party SourceMod native extensions are not covered by the limited compatibility build.
- The installer touches only the manifest-listed modules; addons and the rest of the Steam tree are left in place.

## Provenance

The repository contains research data, patch manifests, scripts and documentation. It does not contain Valve’s original or modified game binaries. See [research-index](docs/research-index.md) for the historical evidence chain and the reports that were superseded by later runtime observations.
