# Research index

This index is the public map of the repository’s research history. Historical reports remain in place; the current user-facing result is maintained in the README and the D65/D66 reports.

| Phase | Problem or finding | Current status | Entry points |
| --- | --- | --- | --- |
| D1–D18 | Initial Windows storage and entity-list reverse engineering | REFERENCE | [early report](../reports/report.md), [D19 synthesis](../reports/n27d19/findings.md) |
| Network studies | Snapshot fields and protocol width mapping | REFERENCE | [reports directory](../reports/), [current architecture](architecture.md) |
| D19–D36 | Linux capacity, transmit and frame experiments | REFERENCE | [D19](../reports/n27d19/findings.md), [D36](../reports/n27d36/findings.md) |
| D43–D48 | Client loading and high-index sign-on failures | HISTORICAL; later client paths passed | [D43](../reports/n27d43/findings.md), [D48](../reports/n27d48/findings.md) |
| D49/D50 | Actual client lifecycle at 2048/2049/4095; disconnect still failed | Lifecycle observation retained; disconnect limitation SUPERSEDED by D62 | [D49/D50](../reports/n27d49/findings.md), [D62](../reports/n27d62/findings.md) |
| D56 | Non-network slots overlapped the new network range | Diagnosis retained; old candidate SUPERSEDED by D61 partition | [D56](../reports/n27d56/findings.md), [D61](../reports/n27d61/findings.md) |
| D61 | Linux candidate separated network/non-network ranges | Current partition basis | [D61](../reports/n27d61/findings.md) |
| D62 | Entity release, reuse and single-client reconnect baseline | Current single-client baseline | [D62](../reports/n27d62/findings.md) |
| D63 | Hunter pressure failure initially reported | Crash observation retained; expansion-root-cause claim SUPERSEDED | [D63](../reports/n27d63/findings.md) |
| D64 | Frida/original comparison isolated invalid Hunter VScript usage | Current correction; legal creation used in D65 | [D64](../reports/n27d64/findings.md) |
| D65 | Real ladder, index 4095, special infected, map transition and SourceMod probe | Current core P0 baseline; incomplete tests stay explicit | [D65](../reports/n27d65/findings.md) |
| D66 | Natural wire-serial wrap, release installer, gates and public documentation | Current release candidate | [D66](../reports/n27d66/findings.md) |

## How to read the evidence

The reports deliberately distinguish static inference, server-only observation, client observation, and formal end-to-end acceptance. A later runtime result can narrow or supersede an earlier static conclusion; the historical report remains available so the correction is auditable.

## Active entry points

- Public install: `tools/release/install.py` and `release/manifests/`.
- Release gate: `tools/release/check_rc.py`.
- Runtime evidence checker: `tools/linux/check_d65_evidence.py`.
- D65 lifecycle driver: `tools/linux/run_d65_lifecycle.py`.
- SourceMod compatibility probe: `tools/sourcemod/d65_probe.sp`.
