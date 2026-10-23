# N27-D19 independent review (Agent E)

Scope: audited `tools/n27d19/{probe_config.json,gdb_probe.py,test_probe_schema.py,README.md}`,
`tools/n27d19/{run_experiment.py,diff_traces.py}`, `reports/n27d19/{static-analysis.md,auto-diff.md}`,
`data/n27d19/{static.json,auto-diff.json}`, and the raw runs
`/tmp/n27d19-runs/{pristine-2,frameonly-2}`. The Lead also pointed at the `-3` runs, which I
used as corroboration (same artifacts, same pattern; shorter post-FULL windows).

Method: independent PE parsing of the shipped Windows `engine.dll`, independent recomputation
from `events.jsonl`/`counts.json`, log inspection, code reading, and the offline suite. I did not
run the game/server and did not modify binaries. No claim below relies on the Lead's prose.

## Verdicts

| # | Claim | Verdict |
|---|---|---|
| 1 | Per-phase sampling fix, no D17/D18 cumulative gate | **PASS** (with scheduler caveat) |
| 2 | Fallback/address validation; bytes verified; lsteamclient not mistaken | **PASS (qualified)** |
| 3 | frameonly post-FULL only `0x4E510`/`0x53FE0`; pristine also `0x4EE80`/`0x56E60`/others; no histogram truncation | **PASS** |
| 4 | `0x56E60` is `SVC_UserMessage` (vtable `0x358EEC`), not a frame/loading function | **PASS** |
| 5 | Missing UserMessage/GameEvent may be consequence, not cause | **PASS as a caution; causality INCONCLUSIVE** |

Bottom line: the central D19 factual result is reproducible from raw events. The prior
D15–D18 framing of `0x56E60` is indeed invalid. The main open issue is not the differential
table but causality and runner validation: the client-side stream difference is broad (many SVCs,
not just two), and the current harness cannot tell "server did not send" from "client did not
receive/dispatch" or "client was not active yet."

## Claim 1 — per-phase sampling

**PASS.** `ProbeCounters.note_hit` gates on `logged_pre_full` / `logged_post_full`, never on
lifetime `total_hits` (`gdb_probe.py:539-598`). The offline regression at
`test_probe_schema.py:568-610` exercises exactly the D18 failure mode and passes. Raw evidence:

| run | probe | pre hits | post hits | logged pre | logged post | post limit |
|---|---|---|---|---|---|---|
| pristine-2 | callCond | 53 | 910 | 4 | 8 | 8 |
| pristine-2 | finalCall | 53 | 910 | 0 | 910 | 2000 |
| frameonly-2 | callCond | 53 | 778 | 4 | 8 | 8 |
| frameonly-2 | finalCall | 53 | 778 | 0 | 778 | 2000 |
| pristine-3 | callCond | 53 | 644 | 4 | 8 | 8 |
| frameonly-3 | callCond | 53 | 652 | 4 | 8 | 8 |

If the D18 gate were still present, the four pre-FULL logs would suppress the post-FULL logs;
they do not. `sample_limited` on `finalCall` is 53 (the pre-FULL hits, limit 0), not post-FULL
loss. No `probe_error` occurred in either run.

Caveats:

* The runs did **not** execute with `scheduler-locking on`, despite the README calling it
  mandatory. `run_experiment.py` never sets `N27_SCHEDULER_LOCKING` and never passes
  `-ex "set scheduler-locking on"`; `gdb_probe.py:1485` defaults the variable to `"off"` and
  `:1488` applies that value. The README/test assertion is therefore not backed by the runner
  (see "Tests" below). This did not visibly corrupt these counts, but the documented
  serialization guarantee is absent.
* The FULL latch is instrument-derived (`engine.dll+0x93140`, request=6, `[this+0x68]` 5→6).
  It is self-consistent (`before=5, after=6` in all four runs) but its function identity is
  not covered by `static.json` and was not independently re-verified here.

## Claim 2 — address validation and fallback

**PASS, qualified.** For all six probes in both `-2` runs and both `-3` runs:
`probe_installed.bytes_verified = true`, `install_summary.ok = true`, 6/6 probes; the FULL
detector also reports `bytes_verified = true`. The fallback is not silent: every probe records
`location_source = "env_base_span"`, `fallback_used = true`, a per-probe warning, and the
warning is repeated in `run_start`, `install_summary` and `counts`.

Independent checks:

* Runner base discovery uses exact path suffixes `/bin/engine.dll` and `/bin/client.dll`
  (`run_experiment.py:module_base`); `lsteamclient.dll` cannot satisfy those suffixes.
* `ModuleMap.parse_mappings` matches a whole basename with a negative lookbehind
  (`gdb_probe.py:216-267`), so `lsteamclient.dll` is not read as `client.dll`; the offline test
  at `test_probe_schema.py:754-860` passes.
* I re-read the actual PE: SHA-256 matches `static.json`, imagebase `0x10000000`; all
  `static.json` sequence/target bytes and vtable slot entries match; all probe prefixes match
  the installed-client `engine.dll` and `client.dll` bytes at the recorded addresses.

Qualification / correction: the absolute "cannot silently accept a wrong module base" is too
strong. `resolve_for_module` constructs the address from the same env base it then "validates",
so the meaningful guard is the expected-byte check. Three probes use only a 2-byte prefix
(`afterCond=84c0`, `finalCall=ffd0`, `e56Entry=8bc1`); `verify_bytes` is configurable, and a probe
with no `expected_bytes` would install with `bytes_verified = null`. In this config a wrong base
would have to match all six checks, which is practically unlikely but not a cryptographic
guarantee. The all-probes `env_base_span` fallback also means parsed mappings were never able to
confirm the code region in these runs; the env bases are accepted on the runner's word plus the
byte checks.

## Claim 3 — post-FULL dispatch target sets

**PASS.** Recomputed from raw `hit` events (not from the summary). `finalCall` post-FULL sets:

| target | pristine-2 | frameonly-2 | pristine-3 | frameonly-3 |
|---|---:|---:|---:|---:|
| `engine.dll+0x4E510` NET_Tick | 372 | 389 | 256 | 326 |
| `engine.dll+0x53FE0` SVC_PacketEntities | 372 | 389 | 256 | 326 |
| `engine.dll+0x53EF0` SVC_Sounds | 82 | 0 | 54 | 0 |
| `engine.dll+0x4EE80` SVC_GameEvent | 29 | 0 | 28 | 0 |
| `engine.dll+0x56E60` SVC_UserMessage | 26 | 0 | 24 | 0 |
| `engine.dll+0x53E40` SVC_UpdateStringTable | 13 | 0 | 15 | 0 |
| `engine.dll+0x26E0` unidentified forwarder | 5 | 0 | 4 | 0 |
| `engine.dll+0x4E440` NET_StringCmd | 3 | 0 | 3 | 0 |
| `engine.dll+0x53890` SVC_SetView | 2 | 0 | 1 | 0 |
| `engine.dll+0x53900` SVC_FixAngle | 2 | 0 | 1 | 0 |
| `engine.dll+0x53B20` SVC_TempEntities | 2 | 0 | 0 | 0 |
| `engine.dll+0x53970` SVC_CrosshairAngle | 1 | 0 | 1 | 0 |
| `engine.dll+0x4FFA0` NET_SetConVar | 1 | 0 | 1 | 0 |

`data/n27d19/auto-diff.json` matches the raw `-2` post-FULL counts exactly. The extra classes
above were identified independently from the PE vtable/RTTI (slot 3 of each class vtable), not
from the Lead's report.

No sample truncation of the frameonly histogram:

* `frameonly-2` `finalCall`: `post_full_hits = 778`, `logged_post_full = 778`, configured
  `post_full = 2000`. All 778 post-FULL hits were logged; 389 + 389 = 778.
* `counts.histograms.finalCall`: `hits = 831`, `unique = 15`, `truncated = false`.
  `831 − 778 = 53` is exactly the pre-FULL hit count (pre-FULL detail is disabled, but the
  histogram still records those targets).
* Same for `-3` (`652` post, `705` histogram, `truncated=false`).

Corrections/clarifications:

* `README.md` and the `finalCall` config note say only the first 8 post-FULL hits are logged;
  the actual config is `post_full: 2000`, and 910/778/644/652 hits were logged. The e56Entry
  table in the README also says 8, config says 100. The docs are stale; the run data follows
  the config.
* `counts.histograms.finalCall` is **not** phase-filtered. Pristine-2 reports 375 `0x4E510`
  and 29 `0x56E60` in the histogram versus 372/26 in the post-FULL event table; the difference
  is pre-FULL hits. The frameonly histogram contains three pre-FULL `0x56E60` hits. Do not read
  the all-phase histogram as a post-FULL table.
* Consequently, "frameonly never calls `0x56E60`" is false as a whole-run statement; the
  correct statement is "zero post-FULL." `reports/n27d19/findings.md` says frameonly had
  "12" pre-FULL `0x56E60` hits; the raw count is **3** (finalCall histogram and e56Entry entry
  count both agree). `static-analysis.md`'s "frameonly 观察不到 0x56E60" also needs the
  post-FULL qualifier.
* `0x26E0` is not resolvable as a static vtable slot in this PE; it is reported as
  unidentified rather than guessed.

## Claim 4 — `0x56E60` is `SVC_UserMessage`

**PASS.** Independent PE verification (SHA-256 `8a6d4680…`):

* vtable RVA `0x358EEC`, byte offset `+0xC` (slot 3) contains `0x10056E60`.
* The RTTI type descriptor behind that vtable is `.?AVSVC_UserMessage@@`; vtable slot 8
  functions are `mov eax, 0x17` (type 23) and `mov eax, 0x10358F28` → `"svc_UserMessage"`.
* `0x56E60` is exactly `8B C1 8B 48 50 8B 11 50 8B 42 54 FF D0 C3`: a 14-byte forwarder to
  `[msg+0x50]->vtable[0x54]`. It contains no `CClientFrame` access.
* The dispatch target `0x1EC1D0` contains an immediate reference to
  `"Couldn't dispatch user message (%i)"` at `0x101EC29D`, consistent with user-message
  dispatch.
* The four `0x4E510/0x4EE80/0x56E60/0x53FE0` vtable slot-3 entries, type IDs and target bytes
  all match `static.json`; the static report's bytes are correct.

The D15–D18 framing is invalid. Nuance that should be preserved: the
`OnEngineLevelLoadingFinished` event itself is delivered as a UserMessage that traverses
`0x1EC1D0` and `0x56E60` (D14 stack). `0x56E60` is therefore not a loading-specific function,
but its post-FULL hits are a proxy for "some UserMessage was dispatched," including the
loading-finished one. The missing `0x56E60` says "no UserMessage in this window", not "the
loading path was skipped."

## Claim 5 — causality

**The caution is correct; causality is INCONCLUSIVE.** Current evidence cannot distinguish:

1. frameonly server never sent GameEvent/UserMessage (e.g. client not active/signon-limited);
2. server sent them but the client's receive/lookup/dispatch rejected them;
3. the client was still loading and the server correctly suppressed gameplay messages.

What the evidence shows:

* The difference is much broader than GameEvent/UserMessage: pristine also dispatches
  SVC_Sounds (82/54), SVC_UpdateStringTable (13/15), SVC_TempEntities, SVC_SetView,
  SVC_FixAngle, SVC_CrosshairAngle, NET_StringCmd and NET_SetConVar; frameonly dispatches none
  of them post-FULL. This looks like a client that is connected and receiving snapshots
  (`NET_Tick` + `SVC_PacketEntities`) but not in an active/spawned game state, not a selective
  failure of two message types.
* Pristine-2's `clientEventBranch` (`OnEngineLevelLoadingFinished` branch) fires exactly once
  at FULL+3.329 s; frameonly-2 has zero. Pristine-3 also has one, frameonly-3 zero. This is
  consistent with frameonly not completing the loading/active transition.
* But that branch is itself a UserMessage dispatched through `0x56E60` (D14 stack), so it is
  not independent evidence: zero UserMessages implies zero loading-finished UserMessages.

What is missing:

* no server-side netchan send log (message type + target client), so "not sent" vs "not
  received" is unknown;
* no client-side `FindNetMessage`/`ReadFromBuffer`/dispatch-entry log, so a receive-side
  rejection is unknown;
* no client active/spawn/signon state probe beyond FULL, and no clean evidence that frameonly's
  client was still on the loading screen at kill time.

The current D19 wording ("may be a consequence") is appropriately cautious. It should not be
upgraded to a causal claim without the server-send experiment proposed in `findings.md` §9.

## Runner validity

Both `-2` and `-3` runs are install-valid: 6/6 probes, `install_summary.ok=true`,
`install_failed=false`, no `probe_error`, `full_state_seen=true`, `bytes_verified=true`, and
`run_end`/`counts` present. **No run was marked ok despite an install/probe failure.**

But `metadata.ok` is not a strong validity verdict:

* `connect_ok` is `"Connected to" in client.console.log`. That file is copied from the shared
  Steam `console.log` and **accumulates across runs**: `pristine-1/client.console.log` is a
  strict prefix of `pristine-2/client.console.log`, and `frameonly-1` of `frameonly-2`. The
  `-2` files contain 16/17 `Connecting to public` blocks and 6 `Server connection timed out`
  lines, many from earlier runs. A stale "Connected to" can satisfy `connect_ok` even if the
  current client never connected. The gdb events independently show the probed client reached
  FULL, but the runner's check is not run-scoped.
* `event_lines > 0` only requires any JSONL line (including install lines); the runner does not
  require `run_end`, `counts`, `full_state_seen`, `install_summary.installed_probes == 6`, or
  `expectations_ok`.
* gdb's return code is not recorded or checked. A gdb that exits non-zero after install would
  still pass if the JSONL is non-empty and `install_summary` is present.
* `--duration 30` produces a `timeout 45` gdb kill; the post-FULL observation window is only
  ~19.5 s in `pristine-2`/`frameonly-2` (13.8-16.3 s in `-3`), not 30 s. `run_end.reason` is
  `"inferior_exited"` while `gdb.log` ends with `[Inferior … detached]`, so the termination
  semantics are not recorded; this is a harness timeout, not a clean client exit.
* Pristine-2 and pristine-3 both have a `clientEventBranch` expectation violation
  (`expect_post_full_hits: 0`, actual 1); `run_end.expectations_ok=false`, but `metadata.ok=true`
  and `auto-diff.json` reports `ok: true`. The expectation is image-specific in spirit but global
  in the config; it should either be removed for pristine or surfaced in the run verdict.
* `run_experiment.py` verifies the source image hash, but the frameonly entry uses a 16-hex
  prefix (`89152442f624339b`) rather than the full SHA; the metadata full hash does match the
  file, but the runner would accept any file sharing that prefix. The image provenance/build
  command is not in the run artifacts.

## Offline tests

`python3 tools/n27d19/test_probe_schema.py` → **225 passed, 0 failed, exit 0** (twice).
`python3 -m py_compile` on all four Python tools → OK.

One test is a false positive worth fixing: `test_probe_schema.py:564` asserts the literal
`"set scheduler-locking on"` appears in `gdb_probe.py`. It appears only in the module docstring
(line 6); the implementation defaults to `off` and the runner never sets `on`. Thus the test
"passes" while the documented mandatory property is not implemented. The expected-byte test
(`test_expected_bytes`) only compares config to hard-coded constants; it does not read the game
binary. My separate PE check does verify the real bytes.

## Concrete corrections

1. README: runner is no longer "connect_ok and event_lines only" — it does check
   `install_failed` and `install_summary.ok`; it still does not check gdb's return code. Update
   the stale statement. Also update sample-limit table (`finalCall` 2000, `e56Entry` 100) and
   remove "only the first 8 post-FULL hits" from README/config note.
2. Scheduler-locking: either set `N27_SCHEDULER_LOCKING=on` (and/or pass
   `-ex "set scheduler-locking on"`) in `run_experiment.py`, or drop the "mandatory" claim and
   change the test to assert the effective setting, not a docstring literal.
3. `findings.md`: frameonly pre-FULL `0x56E60` count is 3, not 12. `static-analysis.md` and
   `findings.md` should say "zero post-FULL" everywhere they currently say "never/not observed".
4. `auto-diff`/`counts`: annotate that the auto-diff counts are post-FULL logged hits while
   `counts.histograms` is all-phase; otherwise the 375/29 vs 372/26 mismatch looks like a bug.
5. `clientEventBranch`: make `expect_post_full_hits` image-specific or informational; do not
   let `metadata.ok=true` coexist with `expectations_ok=false` silently.
6. Runner: reset/rotate `client.console.log` before launching the client, or make `connect_ok`
   event-based (e.g. FULL + first PacketEntities + no disconnect in the run window). Require
   `run_end`, `counts`, `full_state_seen`, 6 installed probes and gdb return code 0.
7. `run_experiment.py`: record full image hash for frameonly and the build/provenance command;
   record gdb return code and termination reason; state the actual post-FULL window duration.

## Remaining threats to validity

* **Causality**: no server-send or client-receive instrumentation; the observed missing message
  types are consistent with both server suppression and client-side rejection/loading.
* **Single build per image, two runs**: `-2` and `-3` reproduce the target-set pattern, but
  there is no alternating/repeated same-image control, and the post-FULL windows differ
  (~19.5 s vs 13.8-16.3 s). Counts are not directly comparable across runs.
* **Phase boundary**: FULL is detected at one prologue-verified address; the function identity
  and the exact latch point relative to map loading/spawn are not independently established.
* **Address safety**: all probes used the env-base fallback because parsed mappings did not
  cover the code region; safety rests on short expected-byte prefixes (three are 2 bytes).
* **Harness contamination**: `client.console.log` accumulates across runs; the "ok" flag is
  install+stale-connect, not a clean-run guarantee.
* **Termination**: harness `timeout 45` kills gdb; `run_end.reason=inferior_exited` with a
  detached inferior is ambiguous. Post-FULL windows are ~14-19 s, not 30 s.
* **Build provenance**: frameonly is a `/tmp` artifact verified by a 16-hex prefix in the
  runner; the actual patch set is not recorded in the run directory.
* **Static scope**: `0x26E0` remains unidentified; the static report's claim that only
  SVC_PacketEntities touches `CClientFrame` is plausible but the deep chain is not fully
  closed. `0x10053440`'s 2048 hardcode is an observation, not a proven member.
* **Config expectation**: `clientEventBranch`'s global zero-hit expectation is wrong for
  pristine and is currently ignored by the run verdict.

## Evidence index

* Raw post-FULL histograms: `/tmp/n27d19-runs/{pristine-2,frameonly-2,pristine-3,frameonly-3}/events.jsonl`;
  counts in `events.jsonl.counts.json`.
* PE verification: `/home/void0312/.steam/debian-installation/steamapps/common/Left 4 Dead 2/bin/engine.dll`
  (SHA-256 `8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86`).
* Static byte/vtable cross-check: `data/n27d19/static.json` (all sequence bytes and vtable
  slots matched the PE; RTTI name `.?AVSVC_UserMessage@@`; type 23; name pointer
  `0x10358F28` → `svc_UserMessage`; user-message failure string referenced at `0x101EC29D`).
* Test run: 225/225 pass; scheduler assertion false positive at `test_probe_schema.py:564`.
