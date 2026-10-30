# Research index

This index keeps the historical D1–D66 timeline while adding a topic-first
route to the final technical explanation. Historical reports remain available;
the current result is defined by the technical report, manifests, D65/D66
records and the separately scoped 2026-10-31 gameplay-assisted observation.

## Start with the final explanation

- [Technical report](technical-report.md) — complete architecture, protocol,
  lifecycle, compatibility and evidence boundaries.
- [Patch map](patch-map.md) — why the manifest groups exist and how to trace
  them to analysis and validation.
- [Evidence and reproduction](evidence-and-reproduction.md) — public records,
  private raw evidence and reproducible checks.
- [Architecture](architecture.md) — compact width and storage overview.
- [Verification model](verification.md) — checker layers and commands.

## Browse by technical topic

| Topic | Final explanation | Key analysis | Current implementation | Main validation |
| --- | --- | --- | --- | --- |
| Windows engine reverse engineering | [technical report](technical-report.md#engine-binary-modifications) | [reports/report.md](../reports/report.md) | [Windows manifest](../release/manifests/windows-client.json) | [D66 gate](../reports/n27d66/validation.json) |
| Linux engine and entity storage | [expansion architecture](technical-report.md#expansion-architecture) | [D56](../reports/n27d56/findings.md), [D61](../reports/n27d61/findings.md) | [Linux manifest](../release/manifests/linux-server.json) | [D62 validation](../reports/n27d62/validation.json) |
| Entity table and handles | [lifecycle](technical-report.md#entity-lifecycle-and-failure-analysis) | [D30 correction](../reports/n27d30/correction.md), [D62](../reports/n27d62/findings.md) | [handle data](../data/handle_ops.csv) | [raw lifecycle gate](../tools/release/check_raw_lifecycle.py) |
| Network widths and PacketEntities | [protocol chapter](technical-report.md#network-protocol-and-snapshot-processing) | [N25](../reports/network-n25.md), [N27 reports](../reports/network-n27b.md) | [width sites](../data/netproto_width_sites.csv) | [D65 validation](../reports/n27d65/validation.json) |
| Client initialization and synchronization | [protocol chapter](technical-report.md#network-protocol-and-snapshot-processing) | [N27-D6–D9](../reports/network-n27d6.md) | [client manifest](../release/manifests/windows-client.json) | [D65 findings](../reports/n27d65/findings.md) |
| Entity lifecycle | [lifecycle chapter](technical-report.md#entity-lifecycle-and-failure-analysis) | [D49/D50](../reports/n27d49/findings.md), [D62](../reports/n27d62/findings.md) | [D65 lifecycle runner](../tools/linux/run_d65_lifecycle.py) | [D66 raw checks](../reports/n27d66/raw-lifecycle.json) |
| Corrected assumptions | [failure analysis](technical-report.md#entity-lifecycle-and-failure-analysis) | [D30](../reports/n27d30/correction.md), [D63](../reports/n27d63/findings.md), [D64](../reports/n27d64/findings.md) | [D65 legal probes](../tools/linux/vscript/d65_special.nut) | [D65/D66 records](../reports/n27d65/validation.json) |
| Dynamic and load testing | [experimental validation](technical-report.md#experimental-validation) | [D65](../reports/n27d65/findings.md), [D66](../reports/n27d66/findings.md) | [Linux runners](../tools/linux/), [2026-10-31 filler](../artifacts/entity-index-20261031/entity_index_fill.nut) | [D66 validation](../reports/n27d66/validation.json), [gameplay-assisted scan](../artifacts/entity-index-20261031/runtime-index-scan.txt) |
| SourceMod compatibility | [compatibility chapter](technical-report.md#sourcemod-and-extension-compatibility) | [D65 compatibility](../tools/sourcemod/d65_compatibility.md) | [compatibility builder](../tools/sourcemod/build_compat.py) | [D66 smoke](../reports/n27d66/sourcemod-smoke.json) |
| Installer and release engineering | [patch map](patch-map.md), [evidence](evidence-and-reproduction.md) | [D66 findings](../reports/n27d66/findings.md) | [installer](../tools/release/install.py), [release manifests](../release/manifests/) | [release gate](../tools/release/check_rc.py) |

The labels in each report distinguish STATIC_CONFIRMED, RUNTIME_OBSERVED,
END_TO_END_VERIFIED, INFERRED, NOT_TESTED and SUPERSEDED. A later runtime
result can narrow or supersede an earlier static conclusion; the historical
report remains available so that correction is auditable.

## Historical timeline

| Phase | Finding | Current status | Entry points |
| --- | --- | --- | --- |
| D1–D18 | Initial Windows storage and entity-list reverse engineering | REFERENCE | [early report](../reports/report.md), [D19 synthesis](../reports/n27d19/findings.md) |
| Network N1–N24 | Snapshot fields, protocol widths and client frame paths | REFERENCE; individual corrections retained | [network reports](../reports/) |
| D19–D36 | Linux capacity, transmit and frame experiments | REFERENCE | [D19](../reports/n27d19/findings.md), [D36](../reports/n27d36/findings.md) |
| D43–D48 | Client loading and high-index sign-on failures | HISTORICAL; later client paths passed | [D43](../reports/n27d43/findings.md), [D48](../reports/n27d48/findings.md) |
| D49/D50 | Actual client lifecycle at 2048/2049/4095; disconnect still failed | Lifecycle observation retained; disconnect limitation SUPERSEDED by D62 | [D49/D50](../reports/n27d49/findings.md), [D62](../reports/n27d62/findings.md) |
| D56 | Non-network slots overlapped the new network range | Diagnosis retained; old candidate SUPERSEDED by D61 partition | [D56](../reports/n27d56/findings.md), [D61](../reports/n27d61/findings.md) |
| D61 | Linux candidate separated network/non-network ranges | Current partition basis; early client run remained incomplete | [D61](../reports/n27d61/findings.md) |
| D62 | Entity release, reuse and single-client reconnect baseline | Current single-client lifecycle basis | [D62](../reports/n27d62/findings.md) |
| D63 | Hunter pressure failure initially reported | Crash retained; expansion-root-cause claim SUPERSEDED | [D63](../reports/n27d63/findings.md) |
| D64 | Frida/original comparison isolated invalid Hunter VScript usage | Current correction; legal creation used in D65 | [D64](../reports/n27d64/findings.md) |
| D65 | Real ladder, index 4095, special infected, map transition and SourceMod probe | Current core runtime baseline; incomplete tests remain explicit | [D65](../reports/n27d65/findings.md) |
| D66 | Natural wire-serial wrap, bounded run, release installer and public evidence gates | Current release candidate | [D66](../reports/n27d66/findings.md) |
| 2026-10-31 gameplay observation | Hidden filler props during `c6m1_riverbank` gameplay led to high-index ordinary infected (max 2158) | `RUNTIME_OBSERVED` server-side only; not natural-only, client-traced or sustained high-load acceptance | [runtime artifact and scripts](../artifacts/entity-index-20261031/README.md) |

## Active entry points

- Public installation: [tools/release/install.py](../tools/release/install.py)
  and [release manifests](../release/manifests/).
- Release gate: [tools/release/check_rc.py](../tools/release/check_rc.py).
- Repository audit: [tools/release/audit_repository.py](../tools/release/audit_repository.py).
- Runtime evidence checker: [tools/linux/check_d65_evidence.py](../tools/linux/check_d65_evidence.py).
- D65 lifecycle driver: [tools/linux/run_d65_lifecycle.py](../tools/linux/run_d65_lifecycle.py).
- D66 serial and bounded-run drivers: [run_d66_serial.py](../tools/linux/run_d66_serial.py), [run_d66_soak.py](../tools/linux/run_d66_soak.py).
- SourceMod compatibility probe: [d65_probe.sp](../tools/sourcemod/d65_probe.sp).

Historical files are not removed merely because their D number is old. The
inventory in [reports/n27d66/repository-inventory.md](../reports/n27d66/repository-inventory.md)
records the current classification and preserves superseded experiments.
