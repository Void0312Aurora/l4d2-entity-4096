# Verification model

D66 keeps build, integrity, raw semantics, installation and runtime checks separate. A release candidate is only as strong as the weakest layer needed for the claimed use.

| Layer | Entry point | Meaning |
| --- | --- | --- |
| Static build checks | existing `engine/verify_pe.py`, `tools/precheck_server.py`, manifest checks | Source identity, structure, expected old bytes and output hashes |
| Evidence integrity | `tools/linux/check_d65_evidence.py` | Named D65 raw snapshots exist and match the recorded module identities |
| Raw lifecycle semantics | `tools/release/check_raw_lifecycle.py` | Recomputes actual indices, wire serial, handles, origins, deletion and reuse across 54 raw snapshots |
| Installer checks | `tools/release/install.py` | Source hashes, hunk assertions, output hashes, private-copy and recovery behavior |
| Runtime acceptance | D65/D66 raw run directories | Real server/client lifecycle, Frida observation, map transition and D66 serial wrap |

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

## Evidence rules

- A static manifest does not prove runtime behavior.
- A server-side snapshot does not prove client visibility.
- A natural index-4095 run does not prove full 4096-slot occupation.
- A finite serial observation does not prove wraparound safety.
- A compatibility probe does not prove arbitrary third-party extension compatibility.

The raw evidence is external to the repository because it contains large process snapshots and private paths. The repository stores the compact D65 ledger, validation record, generated charts and the scripts needed to re-run the checks.
