# N27-D19 declarative GDB probes

A declarative replacement for the hand-written breakpoint blocks in
`tools/linux/gdb/client_trace.py`. One JSON config describes the probes and one
gdb Python script installs them, normalises every module pointer to
`module.dll+0xRVA`, and emits versioned JSONL.

No database, no web service, no writes to the game: the script only installs
breakpoints, reads registers/memory, and detaches with gdb. The existing
`tools/linux/gdb/client_trace.py` is left untouched.

## Files

| File | Purpose |
|---|---|
| `probe_config.json` | Declarative probes, FULL-state detector, sample limits, expected bytes |
| `gdb_probe.py` | gdb Python collector (`import gdb`; also importable for tests) |
| `test_probe_schema.py` | Offline stdlib tests for config, JSONL, counters, histogram |
| `README.md` | This file |

`run_experiment.py` and `diff_traces.py` in the same directory are owned by the
runner/differential scope and are not modified here.

## Exact runner usage

The runner must attach to the **client** process (`left4dead2.exe`) and set
`N27_MODULE_BASE_ENGINE` / `N27_MODULE_BASE_CLIENT` from the first mapping of
`/bin/engine.dll` and `/bin/client.dll` in `/proc/<pid>/maps`. RVAs are added
to those runtime mapping bases; the PE preferred image base `0x10000000` is
documentation only and is **not** used for address arithmetic.

```sh
PID=...                                  # left4dead2.exe
ENGINE_BASE=0x79e00000                   # first /bin/engine.dll mapping
CLIENT_BASE=0x74630000                   # first /bin/client.dll mapping
OUT="$PWD/data/n27d19/run-001/events.jsonl"

sudo -n env \
  N27_PROBE_CONFIG="$PWD/tools/n27d19/probe_config.json" \
  N27_PROBE_OUT="$OUT" \
  N27_PROBE_RUN_ID="run-001" \
  N27_MODULE_BASE_ENGINE="$ENGINE_BASE" \
  N27_MODULE_BASE_CLIENT="$CLIENT_BASE" \
  timeout 55 gdb -q -batch \
    -ex "set pagination off" \
    -ex "set confirm off" \
    -ex "handle SIGUSR1 nostop noprint pass" \
    -ex "handle SIGUSR2 nostop noprint pass" \
    -ex "handle SIGCHLD nostop noprint pass" \
    -ex "handle SIGPIPE nostop noprint pass" \
    -ex "attach $PID" \
    -ex "python exec(open('$PWD/tools/n27d19/gdb_probe.py').read())" \
    -ex "continue"
```

`run_experiment.py` already launches the server/client and builds essentially
this command. It also sets `N27_RUN_ID` to the run directory name.

### Environment variables

| Variable | Required | Meaning |
|---|---|---|
| `N27_PROBE_CONFIG` | yes | `probe_config.json` path |
| `N27_PROBE_OUT` | yes | JSONL output path; truncated before install, written after all probes install |
| `N27_MODULE_BASE_ENGINE` | yes* | engine.dll mapping base (hex or decimal) |
| `N27_MODULE_BASE_CLIENT` | yes* | client.dll mapping base (hex or decimal) |
| `N27_PROBE_RUN_ID` | no | stable run id; default is timestamp+pid |
| `N27_FULL_STATE` | no | `0`/`1` override for late attach or replay |

\* If a base is absent, the collector falls back to the attached process's
mappings for that module, then to the configured `fallback_span`. The runner
should always pass both bases.

### Mapping fallback (Wine-safe)

`ModuleMap` accepts an address if either:

1. it falls in a parsed mapping range from `/proc/<pid>/maps` or
   `info proc mappings`, or
2. it falls in `N27_MODULE_BASE_<MODULE> .. base + fallback_span`.

The second path is the Wine/Proton safety net: `info proc mappings` can be
partial, and a missing range must not turn a correct base+RVA into
`address ... not in ... mappings`. Parsed mapping lines are matched by the
whole basename `engine.dll` / `client.dll` (so `lsteamclient.dll` does not
match, the D12 trap), so paths containing spaces (`Left 4 Dead 2`) work; only
the first two hex tokens (start/end) are used.
Acceptance through the fallback is recorded as `location_source:
"env_base_span"`, `fallback_used: true`, and a per-probe warning; the expected
byte prefix is still verified. The failure record includes
`modules.describe()` with `base`, `env_base`, parsed `ranges`, `mapped`,
`range_count`, `fallback_span`, and `fallback_hits`.

### scheduler-locking is off by default

The command sequence must attach **before** the Python script and include:

```gdb
# default: off (all game threads run; probes fire across threads)
# only for single-stepping / `record full`:
# set scheduler-locking on
```

The script also executes this idempotently and warns if it cannot. GDB stops all
threads on attach; with scheduler-locking on, probe hits are serviced one at a
time so per-probe counters and the JSONL write order are not interleaved by
multiple Wine threads. Do not move the Python install before the lock.

### Late attach / replay

If the client was already at signon state 6 when gdb attached, the
`SetSignonState(5→6)` transition will not be observed. Pass
`N27_FULL_STATE=1` to start in the post-FULL phase. Do not use the override for
a normal early-attach run: the script then emits
`full_state_installed.mode = "env"` instead of latching the real transition.

## Positive control: install must fail loudly

Every configured probe produces a `probe_installed` line after:

1. the module base resolves,
2. `module_base + rva` normalises back to the same `module`/`rva`,
3. the optional expected-byte prefix matches, and
4. `gdb.Breakpoint()` succeeds.

A `probe_installed` line carries `first_bytes`, `expected_bytes`,
`bytes_verified`, the breakpoint number and the sample limits. After all
probes, `install_summary` has `ok`, expected/installed counts and the probe ids.
The FULL-state detector is reported separately as `full_state_installed`.

If any required install step fails, the collector writes
`$N27_PROBE_OUT.install.json`, prints `N27_PROBE_INSTALL_FAILED ...`, writes a
single `install_failed` JSONL record (including `modules.describe()`,
`failures` and `warnings`), and quits gdb with status 1. It does not write any
`hit` lines. The runner must treat a non-zero gdb exit status as a failed run
and must also check the install summary:

```sh
python3 - "$OUT" <<'PY'
import json, sys
path = sys.argv[1] + ".install.json"
try:
    with open(path) as f:
        bad = json.load(f)
except FileNotFoundError:
    bad = None
if bad is not None:
    raise SystemExit("probe install failed: %r" % bad["failures"])
rows = [json.loads(line) for line in open(sys.argv[1]) if line.startswith("{")]
assert not [r for r in rows if r.get("event") == "install_failed"], rows
installed = [r["probe_id"] for r in rows if r.get("event") == "probe_installed"]
summary = [r for r in rows if r.get("event") == "install_summary"]
assert len(installed) == 6, installed
assert summary and summary[-1]["ok"], summary
PY
```

`run_experiment.py` currently sets `ok` from `connect_ok and event_lines > 0`
and does not inspect gdb's return code. Because a failed install now emits one
diagnostic `install_failed` line, the runner must explicitly reject
`install_failed` and require a successful `install_summary` (as in the snippet
above). Add the check, or an equivalent `returncode`/`probe_installed` count
check, so a never-installed probe cannot be reported as a valid run.

## JSONL schema

`schema_version` is fixed at `n27d19.probe.v1`. Every line is one compact JSON
object; every line has `schema_version`, `run_id`, `ts` (UTC ISO-8601), and a
monotonic `seq`. No host-absolute path is emitted for a module address.

| `event` | Meaning |
|---|---|
| `run_start` | Config/schema versions, pid, module bases, override |
| `full_state_installed` | Signon detector or env override was installed |
| `probe_installed` | One per configured probe, with byte/address verification |
| `install_summary` | Aggregate positive-control result |
| `full_state` | Once, when the post-FULL latch is set |
| `hit` | One logged hit (subject to phase and sample limits) |
| `stats` | Periodic `STATS` line every `stats_every` total hits |
| `probe_error` | A hit handler raised; the probe continues |
| `full_state_error` | FULL detector/FinishBreakpoint error |
| `counts` | Final per-probe counters and full histograms |
| `run_end` | Final ok/expectation summary |

### `hit` fields

Required fields, always present (non-applicable values are `null`):

```
schema_version, run_id, ts, seq, event, probe, module, rva,
phase, full_state, target_module, target_rva,
edx, esi, al, eflags, mismatch
```

Additional fields:

| Field | Meaning |
|---|---|
| `phase` | Configured policy: `pre_full`, `post_full`, `both` |
| `actual_phase` | **Actual** phase at the hit: `pre_full` or `post_full` |
| `phase_policy` | Configured policy (same value as `phase`, kept for readers) |
| `target` | Raw EAX target (local correlation only) |
| `target_key` | `engine.dll+0x56E60` style histogram key |
| `edx_module`, `edx_rva`, `esi_module`, `esi_rva` | Normalised module pointers |
| `deref`, `deref_module`, `deref_rva` | `*(u32*)(EDX+0x0C)` for `finalCall` |
| `target_is_e56` | Whether the target is exactly `engine.dll+0x56E60` |
| `return_addr`, `return_module`, `return_rva` | `[esp]` for `e56Entry`/`clientEventBranch` |
| `captured` | The probe's configured fields |
| `counter` | Lifetime/phase/logged counters at this hit |
| `sample` | Per-phase sample limits and logged counts |
| `expectation_violated` | Present when a probe has an expected-hit count |

`edx`/`esi` are raw integers for the differential script. Their module+RVA
views are the explicit `*_module`/`*_rva` fields. `target_module`/`target_rva`
are `null` when the target is outside `engine.dll`/`client.dll` or absent.

`finalCall` also records `mismatch`:

```
expected = *(u32*)(edx + 0x0C)
mismatch = (eax != expected)
```

If the dereference is unreadable, `mismatch` is `null`, `deref_errors`
increments, and the hit is still logged. `mismatch_hits` /
`mismatch_unknown` are in the final counters.

### Counters

Per probe: `total_hits`, `pre_full_hits`, `post_full_hits`, `logged_hits`,
`logged_pre_full`, `logged_post_full`, `sample_limited`, `phase_filtered`,
`errors`, `mismatch_hits`, `mismatch_unknown`, `deref_errors`,
`histogram_unique`, `histogram_hits`, `first_hit_ts`, `last_hit_ts`.

`logged_hits` counts detailed `hit` lines only. It is not `total_hits`: a run
can legitimately have hundreds of hits; the D19 finalCall config raises the
post-FULL detailed limit to 2000 so the phase-correct target histogram is complete.

### Histogram

Only `finalCall` has `histogram_eax: true`. Every hit updates the histogram,
including hits whose detailed line was sampled out. The final `counts` event
contains one row per **unique** target:

```json
{"key":"engine.dll+0x56E60","module":"engine.dll","rva":355936,"raw":2045079136,
 "hits":199,"first_seq":1,"last_seq":198}
```

`unique` is the number of distinct targets; `hits` is the total occurrence
count. The `stats` event carries the top 10 targets plus `truncated`; `counts`
carries the complete table. A unique target is inserted once and then only its
`hits` counter changes.

### Sample limits and STATS

`sample_limits` are per phase:

* `pre_full` — maximum detailed hit lines before FULL,
* `post_full` — maximum detailed hit lines after FULL,
* `stats_every` — emit a `STATS` line every N **total** hits.

The configured limits are:

| Probe | phase | pre | post | histogram |
|---|---|---|---|---|
| `callCond` | both | 4 | 8 | no |
| `afterCond` | both | 4 | 8 | no |
| `jzCond` | both | 4 | 8 | no |
| `finalCall` | both | 0 | 8 | **yes** |
| `e56Entry` | both | 2 | 8 | no |
| `clientEventBranch` | post_full | 0 | 4 | no |

`finalCall` therefore logs only the first 8 post-FULL detailed hits; all targets
are histogrammed and a `STATS` line appears at 200/400/... total hits.
`clientEventBranch` expects zero post-FULL hits (`expect_post_full_hits: 0`);
any hit is logged, has `expectation_violated: true`, and appears in the final
`expectation_violations`.

## Config schema

Top level: `schema`, `schema_version`, `jsonl_schema_version`,
`preferred_image_base`, `modules`, `full_state`, `defaults`, `probes`.

Each probe:

```json
{
  "id": "finalCall",
  "module": "engine.dll",
  "rva": "0x1BC301",
  "phase": "both",
  "sample_limits": {"pre_full": 0, "post_full": 8, "stats_every": 200},
  "fields": ["eax", "edx", "esi", "edi"],
  "histogram_eax": true,
  "expected_bytes": "ffd0",
  "verify_bytes": true,
  "target_check": {
    "kind": "eq_deref",
    "left": "eax",
    "deref_reg": "edx",
    "deref_offset": 12,
    "deref_size": 4,
    "mismatch_field": "mismatch"
  }
}
```

* `rva` accepts `0x` hex strings; output is a decimal integer RVA.
* `phase` is `pre_full`, `post_full`, or `both`.
* `fields` can be `eax`, `edx`, `esi`, `edi`, `ecx`, `al`, `eflags`,
  `return_address`.
* `histogram_eax: true` records the EAX target histogram.
* `expected_bytes` is an optional hex prefix. With `verify_bytes: true` a
  mismatch is an install failure. Set `verify_bytes: false` when probing a
  different client build; `first_bytes` is still recorded.
* `expect_post_full_hits` is an optional expected count; a mismatch is reported
  in `expectation_violations` but the run is still a valid observation.

### FULL-state detector

The config's `full_state` block is not a probe. It installs one internal
breakpoint at `CClientState::SetSignonState` (`engine.dll+0x93140`, verified
bytes `55 8b ec 81 ec`):

1. at entry, `ECX` is `this`, `[esp+4]` is the requested state and
   `[this+0x68]` is the current state;
2. for request 6, a `FinishBreakpoint` reads `[this+0x68]` after return;
3. if the returned state is 6, `full_state` is latched and a `full_state` event
   is emitted once.

`N27_FULL_STATE=1` bypasses the detector for late attach/replay and records
`mode: "env"`.

## Why the D18 cumulative-count bug cannot recur

D18's `COND.n` counted process-lifetime hits. Once the pre-FULL sample budget
was used, post-FULL hits stopped being logged and looked like zero hits.

This collector keeps `total_hits` and `post_full_hits` separately, plus
`logged_pre_full` and `logged_post_full`. The sample gate is:

```
logged_in_this_phase < sample_limit_for_this_phase
```

It never uses `total_hits` as a sample gate. The offline regression test
simulates 10 pre-FULL hits (limit 2) followed by 6 post-FULL hits (limit 3) and
asserts the post-FULL samples are still logged. `stats_due()` is the only
consumer of `total_hits`, and it emits a separate `STATS` line rather than
suppressing a hit.

A `counts` snapshot is also written to `$N27_PROBE_OUT.counts.json` at install,
every 25 hits, at every `STATS`, and at finalization. If the runner kills gdb
with `timeout` before `atexit`/`gdb.events.exited` can emit the final `counts`
line, the sidecar still contains a recent snapshot.

## Offline tests

```sh
python3 tools/n27d19/test_probe_schema.py
```

Expected tail:

```
checks: 225 passed, 0 failed
ALL TESTS PASS
```

The tests use only the Python standard library. `gdb_probe.py` is imported with
`N27_PROBE_IMPORT_ONLY=1`; a fake target supplies registers/memory for an
end-to-end 200-hit simulation, so no game or gdb target is required.

## Operational notes

* Run under the same privilege as the existing gdb runner (`sudo -n` for
  attaching to the Proton process).
* Keep `set handoff` off; the script returns `False` from every breakpoint
  callback and never stops the inferior.
* The collector truncates the JSONL and removes stale `*.counts.json` /
  `*.install.json` sidecars before installing. A failed install leaves a single
  `install_failed` JSONL record plus `events.jsonl.install.json`; it never
  leaves a previous run's hit lines for the runner to mistake as this run's
  evidence.
* This script reads target memory only at probe points; it does not patch code
  or write target memory.
