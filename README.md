# L4D2 Entity Limit Expansion — 2048 to 4096

L4D2-4096 is an unofficial, build-pinned expansion of the **Left 4 Dead 2** network entity limit. It raises the network range from `0..2047` to `0..4095` and the internal entity table from 4096 to 8192 slots while keeping the original Source entity semantics.

This is an experimental release candidate for private copies. It is not a Valve product, does not bypass Steam ownership or authentication, and does not include Valve binaries. The client and dedicated server must use matching patched images.

## Current release status

**PARTIALLY_READY — single-client experimental testing.** The runtime-tested path is a Linux dedicated server plus the Windows client through Proton. The same Windows module manifest is provided for native Windows testing; that runtime has not been independently accepted. D65 evidence covers real `16/64/128/256/512` entity ladders, index `4095`, six special infected, client synchronization, and one map transition. D66 adds a real 1024-cycle wire-serial wrap test, a 317.5-second bounded 512-entity run, private-copy installer, reproducible SourceMod build and independent raw-evidence gates.

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

## Install a private copy

Use a Python 3 interpreter and a legally installed build `23990068`. The installer reads the original tree, verifies every source hash, applies only byte deltas from `release/manifests/`, verifies the output hash, and writes to a separate private directory outside the source tree. It never modifies the source tree.

Check a Windows or Proton client source:

```bash
python3 tools/release/install.py check \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

Preview and create the private copy:

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2" \
  --target "$HOME/L4D2-4096-client" --dry-run

python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2" \
  --target "$HOME/L4D2-4096-client"
```

For a Linux dedicated server, use `release/manifests/linux-server.json` with the server root. The receipt in the private target records source and output hashes. Restore a previous marked target with:

```bash
python3 tools/release/install.py restore \
  --receipt "$HOME/L4D2-4096-client/l4d2-4096-install.json"
```

If the target was newly created and has no backup, add `--remove-created` to remove that marked private copy. See [installation](docs/installation.md) for source paths, launch notes, and failure recovery.

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

The machine-readable D65 record is [reports/n27d65/validation.json](reports/n27d65/validation.json), with the narrative in [reports/n27d65/findings.md](reports/n27d65/findings.md). D66’s release decision and test boundaries are in [reports/n27d66/release-readiness.md](reports/n27d66/release-readiness.md); the final gate is [reports/n27d66/validation.json](reports/n27d66/validation.json), with [wire serial](reports/n27d66/network-serial.json), [bounded soak](reports/n27d66/bounded-soak.json), and [SourceMod smoke](reports/n27d66/sourcemod-smoke.json) records.

## Architecture and verification

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
- VAC safety, public matchmaking, and public release distribution are unverified.
- Third-party SourceMod native extensions are not covered by the limited compatibility build.
- Do not copy patched images into the Steam library. Use an isolated private copy and keep the receipt.

## Provenance

The repository contains research data, patch manifests, scripts and documentation. It does not contain Valve’s original or modified game binaries. See [research-index](docs/research-index.md) for the historical evidence chain and the reports that were superseded by later runtime observations.
