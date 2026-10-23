#!/usr/bin/env python3
"""Offline schema/counter tests for the N27-D19 declarative probe collector.

Runs with Python 3 stdlib only; gdb and the game are not required.

    python3 tools/n27d19/test_probe_schema.py

The test imports gdb_probe.py with N27_PROBE_IMPORT_ONLY=1 so the pure
collector data structures can be exercised without a live target.
"""

import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "probe_config.json"
SCRIPT_PATH = HERE / "gdb_probe.py"

os.environ.setdefault("N27_PROBE_IMPORT_ONLY", "1")


def load_collector():
    spec = importlib.util.spec_from_file_location("n27d19_gdb_probe", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G = load_collector()
PASSED = []
FAILED = []


def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print("PASS  %s" % name)
    else:
        FAILED.append((name, detail))
        print("FAIL  %s%s" % (name, (": " + detail) if detail else ""))


def check_equal(name, got, want):
    check(name, got == want, "got %r, want %r" % (got, want))


# ---------------------------------------------------------------------------
# 1. config
# ---------------------------------------------------------------------------

def test_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        config = json.load(handle)

    check_equal("config schema", config.get("schema"), G.CONFIG_SCHEMA)
    check_equal("config schema_version", config.get("schema_version"), 1)
    check_equal(
        "config jsonl schema",
        config.get("jsonl_schema_version"),
        G.SCHEMA_VERSION,
    )
    check_equal(
        "config preferred image base",
        G.as_int(config.get("preferred_image_base")),
        0x10000000,
    )

    modules = config.get("modules", {})
    check_equal("config module count", sorted(modules), ["client.dll", "engine.dll"])
    for name in ("engine.dll", "client.dll"):
        check("config module %s has env" % name, bool(modules[name].get("env")))
        check_equal(
            "config module %s PE image base" % name,
            G.as_int(modules[name].get("pe_image_base")),
            0x10000000,
        )

    full = config.get("full_state", {})
    check_equal("full_state mode", full.get("mode"), "signon")
    check_equal("full_state module", full.get("module"), "engine.dll")
    check_equal("full_state rva", G.as_int(full.get("rva")), 0x93140)
    check_equal("full_state state offset", full.get("state_offset"), 0x68)
    check_equal("full_state request offset", full.get("request_stack_offset"), 4)
    check_equal("full_state request value", full.get("request_value"), 6)
    check_equal("full_state full value", full.get("full_value"), 6)
    check("full_state requires return state", full.get("require_return_state") is True)
    check(
        "full_state expected bytes",
        bytes.fromhex(full.get("expected_bytes", "")) == bytes.fromhex("558bec81ec"),
    )

    raw_probes = config.get("probes", [])
    check_equal("probe count", len(raw_probes), 6)
    expected = {
        "callCond": {
            "module": "engine.dll",
            "rva": 0x1BC2E9,
            "phase": "both",
            "fields": ["edi"],
            "histogram": False,
            "pre": 4,
            "post": 8,
        },
        "afterCond": {
            "module": "engine.dll",
            "rva": 0x1BC2EE,
            "phase": "both",
            "fields": ["al"],
            "histogram": False,
            "pre": 4,
            "post": 8,
        },
        "jzCond": {
            "module": "engine.dll",
            "rva": 0x1BC2F0,
            "phase": "both",
            "fields": ["al", "eflags"],
            "histogram": False,
            "pre": 4,
            "post": 8,
        },
        "finalCall": {
            "module": "engine.dll",
            "rva": 0x1BC301,
            "phase": "both",
            "fields": ["eax", "edx", "esi", "edi"],
            "histogram": True,
            "pre": 0,
            "post": 2000,
        },
        "e56Entry": {
            "module": "engine.dll",
            "rva": 0x56E60,
            "phase": "both",
            "fields": ["return_address"],
            "histogram": False,
            "pre": 2,
            "post": 100,
        },
        "clientEventBranch": {
            "module": "client.dll",
            "rva": 0x1A0FBF,
            "phase": "post_full",
            "fields": ["return_address"],
            "histogram": False,
            "pre": 0,
            "post": 4,
        },
    }
    check_equal("probe ids", sorted(p["id"] for p in raw_probes), sorted(expected))

    for raw in raw_probes:
        pid = raw["id"]
        want = expected[pid]
        check("probe %s required keys" % pid, all(
            key in raw
            for key in (
                "id", "module", "rva", "phase", "sample_limits", "fields",
                "histogram_eax",
            )
        ))
        check_equal("probe %s module" % pid, raw.get("module"), want["module"])
        check_equal("probe %s rva" % pid, G.as_int(raw.get("rva")), want["rva"])
        check_equal("probe %s phase" % pid, raw.get("phase"), want["phase"])
        check_equal("probe %s fields" % pid, raw.get("fields"), want["fields"])
        check_equal(
            "probe %s histogram_eax" % pid,
            raw.get("histogram_eax"),
            want["histogram"],
        )
        limits = raw.get("sample_limits", {})
        check_equal("probe %s pre limit" % pid, limits.get("pre_full"), want["pre"])
        check_equal("probe %s post limit" % pid, limits.get("post_full"), want["post"])
        check_equal("probe %s stats every" % pid, limits.get("stats_every"), 200)
        check(
            "probe %s expected bytes" % pid,
            bool(raw.get("expected_bytes")),
            "missing expected_bytes",
        )
        try:
            expected_bytes = bytes.fromhex(raw.get("expected_bytes", ""))
            check(
                "probe %s expected bytes non-empty" % pid,
                len(expected_bytes) > 0,
            )
        except ValueError:
            check("probe %s expected bytes hex" % pid, False, "not hex")
        check(
            "probe %s verify bytes" % pid,
            raw.get("verify_bytes") is True,
        )

    final = next(p for p in raw_probes if p["id"] == "finalCall")
    target_check = final.get("target_check", {})
    check_equal("finalCall target_check kind", target_check.get("kind"), "eq_deref")
    check_equal("finalCall target_check left", target_check.get("left"), "eax")
    check_equal("finalCall target_check deref reg", target_check.get("deref_reg"), "edx")
    check_equal(
        "finalCall target_check deref offset",
        target_check.get("deref_offset"),
        0x0C,
    )
    check_equal(
        "finalCall target_check deref size",
        target_check.get("deref_size"),
        4,
    )
    check_equal(
        "finalCall target_check mismatch field",
        target_check.get("mismatch_field"),
        "mismatch",
    )

    client = next(p for p in raw_probes if p["id"] == "clientEventBranch")
    check_equal(
        "clientEventBranch expected post-FULL hits",
        client.get("expect_post_full_hits"),
        0,
    )

    # No host-absolute paths may leak from the config.
    check(
        "config has no host paths",
        not re.search(r"(?:/home/|/tmp/|/proc/|[A-Za-z]:\\)", CONFIG_PATH.read_text()),
    )

    # Build the runtime specs and validate the parsed view.
    defaults = config.get("defaults", {})
    specs = [G.ProbeSpec(raw, defaults) for raw in raw_probes]
    check_equal("parsed specs count", len(specs), 6)
    parsed = {spec.id: spec for spec in specs}
    check_equal("parsed finalCall pre limit", parsed["finalCall"].limits.pre_full, 0)
    check_equal("parsed finalCall post limit", parsed["finalCall"].limits.post_full, 2000)
    check_equal("parsed finalCall stats every", parsed["finalCall"].limits.stats_every, 200)
    check_equal(
        "parsed client phase",
        parsed["clientEventBranch"].phase,
        "post_full",
    )
    check_equal(
        "parsed client expected post-FULL hits",
        parsed["clientEventBranch"].expect_post_full_hits,
        0,
    )
    check_equal(
        "parsed final expected bytes",
        parsed["finalCall"].expected_bytes,
        bytes.fromhex("ffd0"),
    )
    check_equal(
        "parsed e56 expected bytes",
        parsed["e56Entry"].expected_bytes,
        bytes.fromhex("8bc1"),
    )
    return config, specs


# ---------------------------------------------------------------------------
# 2. JSONL schema and positive control
# ---------------------------------------------------------------------------

HIT_REQUIRED = (
    "schema_version",
    "run_id",
    "ts",
    "probe",
    "module",
    "rva",
    "phase",
    "full_state",
    "target_module",
    "target_rva",
    "edx",
    "esi",
    "al",
    "eflags",
    "mismatch",
)


def synthetic_events(specs):
    events = [
        {
            "event": "run_start",
            "schema_version": G.SCHEMA_VERSION,
            "run_id": "synthetic-run",
            "ts": "2026-10-24T00:00:00.000Z",
            "probe_count": len(specs),
            "module_bases": {"engine.dll": "0x79E00000", "client.dll": "0x74630000"},
        },
        {
            "event": "full_state_installed",
            "schema_version": G.SCHEMA_VERSION,
            "run_id": "synthetic-run",
            "ts": "2026-10-24T00:00:00.001Z",
            "mode": "signon",
            "module": "engine.dll",
            "rva": 0x93140,
            "breakpoint": 1,
            "bytes_verified": True,
        },
    ]
    for index, spec in enumerate(specs, start=2):
        events.append(
            {
                "event": "probe_installed",
                "schema_version": G.SCHEMA_VERSION,
                "run_id": "synthetic-run",
                "ts": "2026-10-24T00:00:00.002Z",
                "probe_id": spec.id,
                "module": spec.module,
                "rva": spec.rva,
                "phase_policy": spec.phase,
                "breakpoint": index,
                "first_bytes": (spec.expected_bytes or b"").hex(),
                "expected_bytes": (
                    spec.expected_bytes.hex() if spec.expected_bytes else None
                ),
                "bytes_verified": True,
                "sample_limits": spec.limits.as_dict(),
                "fields": list(spec.fields),
                "histogram_eax": spec.histogram_eax,
            }
        )
    events.append(
        {
            "event": "install_summary",
            "schema_version": G.SCHEMA_VERSION,
            "run_id": "synthetic-run",
            "ts": "2026-10-24T00:00:00.003Z",
            "ok": True,
            "expected_probes": len(specs),
            "installed_probes": len(specs),
            "probe_ids": [spec.id for spec in specs],
        }
    )

    hit = {
        "event": "hit",
        "schema_version": G.SCHEMA_VERSION,
        "run_id": "synthetic-run",
        "ts": "2026-10-24T00:00:01.000Z",
        "seq": 20,
        "probe": "finalCall",
        "module": "engine.dll",
        "rva": 0x1BC301,
        "phase": "both",
        "actual_phase": "post_full",
        "phase_policy": "both",
        "full_state": True,
        "target": 0x79E56E60,
        "target_module": "engine.dll",
        "target_rva": 0x56E60,
        "target_key": "engine.dll+0x56E60",
        "edx": 0x79E4E510,
        "edx_module": "engine.dll",
        "edx_rva": 0x4E510,
        "esi": 0x0B7F0018,
        "esi_module": None,
        "esi_rva": None,
        "al": 0x60,
        "eflags": 2097666,
        "mismatch": False,
        "deref": 0x79E56E60,
        "deref_module": "engine.dll",
        "deref_rva": 0x56E60,
        "captured": {
            "eax": 0x79E56E60,
            "edx": 0x79E4E510,
            "esi": 0x0B7F0018,
            "edi": 0x0B7F0020,
        },
        "counter": {"total_hits": 21, "post_full_hits": 13, "logged_hits": 8},
        "sample": {
            "pre_full": 0,
            "post_full": 8,
            "logged_pre_full": 0,
            "logged_post_full": 8,
        },
        "target_is_e56": True,
    }
    events.append(hit)
    events.append(
        {
            "event": "stats",
            "tag": "STATS",
            "schema_version": G.SCHEMA_VERSION,
            "run_id": "synthetic-run",
            "ts": "2026-10-24T00:00:02.000Z",
            "probe_id": "finalCall",
            "module": "engine.dll",
            "rva": 0x1BC301,
            "phase_policy": "both",
            "full_state": True,
            "counters": {
                "total_hits": 200,
                "post_full_hits": 192,
                "logged_hits": 8,
                "errors": 0,
            },
            "histogram": {
                "unique": 2,
                "hits": 200,
                "truncated": False,
                "targets": [
                    {"key": "engine.dll+0x56E60", "hits": 120},
                    {"key": "engine.dll+0x4EE80", "hits": 80},
                ],
            },
        }
    )
    events.append(
        {
            "event": "counts",
            "tag": "FINAL_COUNTS",
            "schema_version": G.SCHEMA_VERSION,
            "run_id": "synthetic-run",
            "ts": "2026-10-24T00:00:03.000Z",
            "full_state": True,
            "full_state_seen": True,
            "counters": {
                "finalCall": {
                    "total_hits": 347,
                    "post_full_hits": 347,
                    "logged_hits": 8,
                    "errors": 0,
                }
            },
            "histograms": {
                "finalCall": {
                    "unique": 2,
                    "hits": 347,
                    "targets": [
                        {"key": "engine.dll+0x56E60", "hits": 200},
                        {"key": "engine.dll+0x4EE80", "hits": 147},
                    ],
                }
            },
            "expectation_violations": [],
        }
    )
    events.append(
        {
            "event": "run_end",
            "schema_version": G.SCHEMA_VERSION,
            "run_id": "synthetic-run",
            "ts": "2026-10-24T00:00:04.000Z",
            "ok": True,
            "expectations_ok": True,
            "reason": "test",
            "full_state_seen": True,
        }
    )
    return events


def validate_hit(event):
    errors = []
    for key in HIT_REQUIRED:
        if key not in event:
            errors.append("missing %s" % key)
    if event.get("schema_version") != G.SCHEMA_VERSION:
        errors.append("bad schema_version")
    if event.get("event") != "hit":
        errors.append("bad event")
    if event.get("module") not in G.MODULE_NAMES:
        errors.append("bad module")
    if not isinstance(event.get("rva"), int):
        errors.append("rva not int")
    if event.get("phase") not in G.VALID_PHASES:
        errors.append("bad phase policy")
    if event.get("actual_phase") not in ("pre_full", "post_full"):
        errors.append("bad actual phase")
    if event.get("phase_policy") not in G.VALID_PHASES:
        errors.append("bad phase policy")
    if not isinstance(event.get("full_state"), bool):
        errors.append("full_state not bool")
    if event.get("target_module") is not None and event.get("target_module") not in G.MODULE_NAMES:
        errors.append("bad target_module")
    if event.get("target_rva") is not None and not isinstance(event.get("target_rva"), int):
        errors.append("target_rva not int")
    for key in ("edx", "esi"):
        if event.get(key) is not None and not isinstance(event.get(key), int):
            errors.append("%s not int" % key)
    for key in ("al", "eflags"):
        if event.get(key) is not None and not isinstance(event.get(key), int):
            errors.append("%s not int" % key)
    if event.get("mismatch") is not None and not isinstance(event.get("mismatch"), bool):
        errors.append("mismatch not bool/null")
    return errors


def install_ok(events, expected_count):
    installed = [event for event in events if event.get("event") == "probe_installed"]
    summary = [event for event in events if event.get("event") == "install_summary"]
    if len(installed) != expected_count:
        return False
    if not summary:
        return False
    last = summary[-1]
    return bool(last.get("ok")) and last.get("installed_probes") == expected_count


def test_jsonl(specs):
    events = synthetic_events(specs)
    hit = next(event for event in events if event.get("event") == "hit")
    errors = validate_hit(hit)
    check_equal("JSONL hit schema errors", errors, [])
    check_equal("JSONL hit required fields", set(HIT_REQUIRED) <= set(hit), True)
    check_equal(
        "JSONL finalCall target normalized",
        (hit["target_module"], hit["target_rva"]),
        ("engine.dll", 0x56E60),
    )
    check_equal("JSONL finalCall mismatch bool", hit["mismatch"], False)
    check_equal(
        "JSONL finalCall edx/esi raw ints",
        (isinstance(hit["edx"], int), isinstance(hit["esi"], int)),
        (True, True),
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "events.jsonl"
        with open(path, "w", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
        lines = [line for line in path.read_text().splitlines() if line.strip()]
        check_equal("JSONL one object per line", len(lines), len(events))
        parsed = []
        parse_ok = True
        for line in lines:
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                parse_ok = False
        check("JSONL every line parses", parse_ok)
        check_equal("JSONL parsed count", len(parsed), len(events))
        check(
            "JSONL no host paths",
            not re.search(
                r"(?:/home/|/tmp/|/proc/|[A-Za-z]:\\)",
                path.read_text(),
            ),
        )

    check_equal("positive control all probes installed", install_ok(events, 6), True)
    broken = [event for event in events if event.get("probe_id") != "clientEventBranch"]
    check_equal("positive control missing probe fails", install_ok(broken, 6), False)

    summary = next(event for event in events if event.get("event") == "install_summary")
    check_equal("install_summary expected count", summary["expected_probes"], 6)
    check_equal("install_summary installed count", summary["installed_probes"], 6)

    source = SCRIPT_PATH.read_text(encoding="utf-8")
    check("gdb script emits probe_installed", '"probe_installed"' in source)
    check("gdb script emits install_summary", '"install_summary"' in source)
    check("gdb script fails install with quit 1", 'gdb.execute("quit 1")' in source)
    check("gdb script has install failure path", "_fail_install" in source)
    check("gdb script sets scheduler-locking", 'set scheduler-locking on' in source)


# ---------------------------------------------------------------------------
# 3. counters (including the D18 cumulative-count regression)
# ---------------------------------------------------------------------------

def test_counters(specs):
    by_id = {spec.id: spec for spec in specs}
    call = G.ProbeCounters(by_id["callCond"])
    for _ in range(4):
        call.note_hit(False, "t")
    for _ in range(6):
        call.note_hit(True, "t")
    snapshot = call.snapshot()
    check_equal("callCond total_hits", snapshot["total_hits"], 10)
    check_equal("callCond pre_full_hits", snapshot["pre_full_hits"], 4)
    check_equal("callCond post_full_hits", snapshot["post_full_hits"], 6)
    check_equal("callCond logged_hits", snapshot["logged_hits"], 10)
    check_equal("callCond logged_pre", snapshot["logged_pre_full"], 4)
    check_equal("callCond logged_post", snapshot["logged_post_full"], 6)
    check_equal("callCond errors", snapshot["errors"], 0)

    # D18 regression: pre-FULL sample budget exhaustion must not block
    # post-FULL logging, because the gate is per-phase.
    raw = {
        "id": "cumulativeRegression",
        "module": "engine.dll",
        "rva": "0x1BC301",
        "phase": "both",
        "sample_limits": {"pre_full": 2, "post_full": 3, "stats_every": 200},
        "fields": ["eax"],
    }
    regression = G.ProbeCounters(G.ProbeSpec(raw))
    for _ in range(10):
        regression.note_hit(False, "t")
    for _ in range(6):
        regression.note_hit(True, "t")
    snapshot = regression.snapshot()
    check_equal("regression total_hits", snapshot["total_hits"], 16)
    check_equal("regression logged_pre", snapshot["logged_pre_full"], 2)
    check_equal("regression logged_post", snapshot["logged_post_full"], 3)
    check_equal("regression logged_hits", snapshot["logged_hits"], 5)
    check_equal("regression post hits still logged", snapshot["logged_post_full"], 3)
    check_equal("regression sample_limited", snapshot["sample_limited"], 11)

    # Phase filter: a post-FULL probe counts pre-FULL hits but does not log
    # them, then logs post-FULL hits normally.
    raw = {
        "id": "postOnly",
        "module": "client.dll",
        "rva": "0x1A0FBF",
        "phase": "post_full",
        "sample_limits": {"pre_full": 0, "post_full": 8, "stats_every": 200},
        "fields": [],
    }
    post_only = G.ProbeCounters(G.ProbeSpec(raw))
    for _ in range(5):
        post_only.note_hit(False, "t")
    for _ in range(5):
        post_only.note_hit(True, "t")
    snapshot = post_only.snapshot()
    check_equal("postOnly phase_filtered", snapshot["phase_filtered"], 5)
    check_equal("postOnly logged_hits", snapshot["logged_hits"], 5)
    check_equal("postOnly post_full_hits", snapshot["post_full_hits"], 5)

    # stats cadence
    stats = G.ProbeCounters(by_id["finalCall"])
    due_at = []
    for index in range(1, 401):
        stats.note_hit(True, "t")
        if stats.stats_due():
            due_at.append(index)
    check_equal("stats every 200 hits", due_at, [200, 400])

    stats.note_error()
    stats.note_error()
    check_equal("error counter", stats.snapshot()["errors"], 2)

    final = G.ProbeCounters(by_id["finalCall"])
    final.note_mismatch(True)
    final.note_mismatch(False)
    final.note_mismatch(None)
    snapshot = final.snapshot()
    check_equal("mismatch hits", snapshot["mismatch_hits"], 1)
    check_equal("mismatch unknown", snapshot["mismatch_unknown"], 1)

    for key in (
        "total_hits",
        "post_full_hits",
        "logged_hits",
        "errors",
    ):
        check("snapshot has %s" % key, key in snapshot)


# ---------------------------------------------------------------------------
# 4. histogram and module normalisation
# ---------------------------------------------------------------------------

def test_histogram_and_modules():
    histogram = G.Histogram()
    a = 0x79E00000 + 0x1BC301
    b = 0x74630000 + 0x1A0FBF
    module_a, rva_a = "engine.dll", 0x1BC301
    module_b, rva_b = "client.dll", 0x1A0FBF
    histogram.add(module_a, rva_a, a, 1)
    histogram.add(module_a, rva_a, a, 2)
    histogram.add(module_b, rva_b, b, 3)
    histogram.add(module_a, rva_a, a, 4)
    histogram.add(module_b, rva_b, b, 5)
    histogram.add(module_a, rva_a, a, 6)
    snapshot = histogram.snapshot()
    check_equal("histogram unique targets", snapshot["unique"], 2)
    check_equal("histogram total hits", snapshot["hits"], 6)
    check_equal("histogram one row per unique target", len(snapshot["targets"]), 2)
    rows = {row["key"]: row for row in snapshot["targets"]}
    check_equal(
        "histogram engine target key",
        rows["engine.dll+0x1BC301"]["hits"],
        4,
    )
    check_equal(
        "histogram client target key",
        rows["client.dll+0x1A0FBF"]["hits"],
        2,
    )
    check_equal(
        "histogram target raw address preserved",
        rows["engine.dll+0x1BC301"]["raw"],
        a,
    )
    top = histogram.snapshot(top=1)
    check_equal("histogram top truncation", top["truncated"], True)
    check_equal("histogram top unique", top["unique"], 2)
    check_equal("histogram top rows", len(top["targets"]), 1)
    check_equal(
        "histogram top target",
        top["targets"][0]["key"],
        "engine.dll+0x1BC301",
    )

    unknown = G.Histogram()
    unknown.add(None, None, 0x12345678, 1)
    check_equal(
        "histogram non-module target key",
        unknown.snapshot()["targets"][0]["key"],
        "abs:0x12345678",
    )

    modules = G.ModuleMap(
        bases={"engine.dll": 0x79E00000, "client.dll": 0x74630000},
        ranges={
            "engine.dll": [(0x79E00000, 0x7A600000)],
            "client.dll": [(0x74630000, 0x74EC9000)],
        },
        spans={"engine.dll": 0x800000, "client.dll": 0x900000},
    )
    check_equal(
        "normalize engine pointer",
        modules.normalize(0x79E00000 + 0x1BC301),
        ("engine.dll", 0x1BC301),
    )
    check_equal(
        "normalize client pointer",
        modules.normalize(0x74630000 + 0x1A0FBF),
        ("client.dll", 0x1A0FBF),
    )
    check_equal(
        "normalize non-module pointer",
        modules.normalize(0x12345678),
        (None, None),
    )
    check_equal("normalize zero pointer", modules.normalize(0), (None, None))
    check_equal("normalize None pointer", modules.normalize(None), (None, None))
    check(
        "module describe has no host paths",
        not re.search(
            r"(?:/home/|/tmp/|/proc/|[A-Za-z]:\\)",
            json.dumps(modules.describe()),
        ),
    )




# ---------------------------------------------------------------------------
# 4a. mapping parsing and env-base fallback (lead regression)
# ---------------------------------------------------------------------------

def test_mapping_parser_and_fallback():
    base_engine = 0x79E00000
    base_client = 0x74630000
    text = "\n".join([
        # /proc style, Wine path with spaces, multiple engine mappings.
        "79e00000-79e01000 r--p 00000000 08:01 123456 /home/u/Left 4 Dead 2/bin/engine.dll",
        "79e01000-7a000000 r-xp 00001000 08:01 123456 /home/u/Left 4 Dead 2/bin/engine.dll",
        "74630000-74f00000 r-xp 00001000 08:01 123456 /home/u/Left 4 Dead 2/left4dead2/bin/client.dll",
        "74630000-74f00000 r--p 00000000 08:01 123456 /home/u/Left 4 Dead 2/left4dead2/bin/client.dll",
        # gdb style, spaces in path.
        "0x7a000000 0x7a001000 0x1000 0x0 r--p /home/u/Left 4 Dead 2/bin/engine.dll",
        # Must not be mistaken for client.dll (D12's lsteamclient trap).
        "0x70000000 0x70010000 0x1000 0x0 r-xp /home/u/lsteamclient.dll",
    ])
    parsed = G.ModuleMap.parse_mappings(
        text,
        bases={"engine.dll": base_engine, "client.dll": base_client},
        spans={"engine.dll": 0x800000, "client.dll": 0x900000},
    )
    check_equal(
        "mapping parser engine range count",
        parsed.describe()["engine.dll"]["range_count"],
        3,
    )
    check_equal(
        "mapping parser client range count",
        parsed.describe()["client.dll"]["range_count"],
        2,
    )
    check(
        "mapping parser ignores lsteamclient.dll",
        all(
            row["start"] != "0x70000000"
            for row in parsed.describe()["client.dll"]["ranges"]
        ),
    )
    check_equal(
        "mapping parser engine target",
        parsed.normalize_detail(base_engine + 0x1BC2E9)[:2],
        ("engine.dll", 0x1BC2E9),
    )
    check_equal(
        "mapping parser engine source",
        parsed.normalize_detail(base_engine + 0x1BC2E9)[2],
        "mapped",
    )
    check_equal(
        "mapping parser client target",
        parsed.normalize_detail(base_client + 0x1A0FBF)[:2],
        ("client.dll", 0x1A0FBF),
    )
    check(
        "mapping parser no host paths",
        not re.search(
            r"(?:/home/|/tmp/|/proc/|[A-Za-z]:\\)",
            json.dumps(parsed.describe()),
        ),
    )

    # Partial/missing parsed ranges, but env bases are present.  The lead's
    # real run failed here: base+RVA must fall back to env_base_span, not
    # report "not in module mappings".
    partial = G.ModuleMap(
        bases={"engine.dll": base_engine, "client.dll": base_client},
        env_bases={"engine.dll": base_engine, "client.dll": base_client},
        ranges={
            "engine.dll": [(base_engine, base_engine + 0x1000)],
            "client.dll": [],
        },
        spans={"engine.dll": 0x800000, "client.dll": 0x900000},
    )
    engine_detail = partial.normalize_detail(base_engine + 0x1BC2E9)
    client_detail = partial.normalize_detail(base_client + 0x1A0FBF)
    check_equal(
        "fallback engine target",
        engine_detail[:2],
        ("engine.dll", 0x1BC2E9),
    )
    check_equal("fallback engine source", engine_detail[2], "env_base_span")
    check_equal(
        "fallback client target",
        client_detail[:2],
        ("client.dll", 0x1A0FBF),
    )
    check_equal("fallback client source", client_detail[2], "env_base_span")
    check_equal("fallback hit counter", partial.fallback_hits, 2)
    check_equal(
        "fallback describe mapped flag",
        partial.describe()["client.dll"]["mapped"],
        False,
    )
    check_equal(
        "fallback describe availability",
        partial.describe()["client.dll"]["fallback_available"],
        True,
    )


# ---------------------------------------------------------------------------
# 4b. end-to-end event construction with a fake target
# ---------------------------------------------------------------------------

def test_collector_simulation(config, specs):
    modules = G.ModuleMap(
        bases={"engine.dll": 0x79E00000, "client.dll": 0x74630000},
        ranges={
            "engine.dll": [(0x79E00000, 0x7A600000)],
            "client.dll": [(0x74630000, 0x74EC9000)],
        },
        spans={"engine.dll": 0x800000, "client.dll": 0x900000},
    )
    by_id = {spec.id: spec for spec in specs}
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "sim-events.jsonl"
        collector = G.Collector(
            config, specs, modules, str(out_path), "simulation-run"
        )
        collector.file_handle = open(out_path, "w", encoding="utf-8")
        collector.full_state = True
        collector.full_state_seen = True

        engine_base = 0x79E00000
        client_base = 0x74630000
        target_a = engine_base + 0x56E60
        target_b = engine_base + 0x4EE80
        vtable = engine_base + 0x4E510
        obj = 0x0B7F0018
        return_e56 = engine_base + 0x1BC303
        return_client = client_base + 0x1A0FBF
        state = {
            "target": target_a,
            "regs": {
                "eax": target_a,
                "edx": vtable,
                "esi": obj,
                "edi": obj + 8,
                "ecx": obj,
                "al": 0x60,
                "eflags": 0x200246,
                "esp": 0x1234,
            },
        }

        def fake_reg(name):
            return state["regs"].get(name)

        def fake_u32(addr):
            if addr == vtable + 0x0C:
                return state["target"]
            if addr == 0x1234:
                return return_e56
            if addr == 0x5678:
                return return_client
            return None

        original_reg = G.read_reg
        original_u32 = G.read_u32
        G.read_reg = fake_reg
        G.read_u32 = fake_u32
        try:
            # 4 pre-FULL + 8 post-FULL callCond hits.
            collector.full_state = False
            for _ in range(4):
                collector.on_hit(by_id["callCond"])
            collector.full_state = True
            for _ in range(8):
                collector.on_hit(by_id["callCond"])

            # 9 post-FULL finalCall hits: 8 with target A, the 9th with B.
            for index in range(9):
                state["target"] = target_a if index < 8 else target_b
                state["regs"]["eax"] = state["target"]
                collector.on_hit(by_id["finalCall"])

            # E56 entry return address is engine.dll+0x1BC303.
            state["regs"]["esp"] = 0x1234
            collector.on_hit(by_id["e56Entry"])

            # One unexpected client event branch hit (expectation is zero).
            state["regs"]["esp"] = 0x5678
            collector.on_hit(by_id["clientEventBranch"])

            # Push finalCall to 200 total hits so the STATS line is emitted.
            for _ in range(191):
                state["target"] = target_a
                state["regs"]["eax"] = target_a
                collector.on_hit(by_id["finalCall"])

            collector.finalize("simulation")
        finally:
            G.read_reg = original_reg
            G.read_u32 = original_u32

        events = []
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        hits = [event for event in events if event.get("event") == "hit"]
        final_hits = [event for event in hits if event.get("probe") == "finalCall"]
        call_hits = [event for event in hits if event.get("probe") == "callCond"]
        e56_hits = [event for event in hits if event.get("probe") == "e56Entry"]
        client_hits = [
            event for event in hits if event.get("probe") == "clientEventBranch"
        ]
        stats = [event for event in events if event.get("event") == "stats"]
        counts = [event for event in events if event.get("event") == "counts"]
        run_end = [event for event in events if event.get("event") == "run_end"]

        check_equal("simulation callCond hit lines", len(call_hits), 12)
        check_equal("simulation finalCall hit lines", len(final_hits), 200)
        check_equal("simulation e56 hit lines", len(e56_hits), 1)
        check_equal("simulation client hit lines", len(client_hits), 1)
        check_equal("simulation stats lines", len(stats), 1)
        check_equal("simulation counts lines", len(counts), 1)
        check_equal("simulation run_end lines", len(run_end), 1)
        check_equal(
            "simulation finalCall first target",
            (final_hits[0]["target_module"], final_hits[0]["target_rva"]),
            ("engine.dll", 0x56E60),
        )
        check_equal("simulation finalCall mismatch", final_hits[0]["mismatch"], False)
        check_equal(
            "simulation finalCall edx normalized",
            (final_hits[0]["edx_module"], final_hits[0]["edx_rva"]),
            ("engine.dll", 0x4E510),
        )
        check_equal(
            "simulation finalCall esi is heap",
            (final_hits[0]["esi_module"], final_hits[0]["esi_rva"]),
            (None, None),
        )
        check_equal(
            "simulation e56 return normalized",
            (e56_hits[0]["return_module"], e56_hits[0]["return_rva"]),
            ("engine.dll", 0x1BC303),
        )
        check_equal(
            "simulation client return normalized",
            (client_hits[0]["return_module"], client_hits[0]["return_rva"]),
            ("client.dll", 0x1A0FBF),
        )
        check_equal(
            "simulation client expectation violation",
            client_hits[0].get("expectation_violated"),
            True,
        )
        check_equal(
            "simulation stats cadence",
            stats[0]["counters"]["total_hits"],
            200,
        )
        check_equal("simulation stats tag", stats[0].get("tag"), "STATS")
        check_equal(
            "simulation counts expectation violation",
            counts[0]["expectation_violations"][0]["probe_id"],
            "clientEventBranch",
        )
        check(
            "simulation hit schema",
            all(not validate_hit(event) for event in hits),
        )
        check(
            "simulation no host paths",
            not re.search(
                r"(?:/home/|/tmp/|/proc/|[A-Za-z]:\\)",
                out_path.read_text(encoding="utf-8"),
            ),
        )
        histogram = counts[0]["histograms"]["finalCall"]
        check_equal("simulation histogram unique", histogram["unique"], 2)
        check_equal("simulation histogram hits", histogram["hits"], 200)
        rows = {row["key"]: row for row in histogram["targets"]}
        check_equal(
            "simulation histogram target A",
            rows["engine.dll+0x56E60"]["hits"],
            199,
        )
        check_equal(
            "simulation histogram target B",
            rows["engine.dll+0x4EE80"]["hits"],
            1,
        )




# ---------------------------------------------------------------------------
# 4c. install path with a fake gdb module
# ---------------------------------------------------------------------------

def test_install_with_fake_gdb(config, specs):
    class FakeInferior(object):
        pid = 4242

        def __init__(self, memory):
            self.memory = memory

        def read_memory(self, address, size):
            data = self.memory.get(int(address))
            if data is None:
                raise RuntimeError("unmapped")
            return data[:size]

    class FakeBreakpoint(object):
        _next = 1

        def __init__(self, *args, **kwargs):
            self.number = FakeBreakpoint._next
            FakeBreakpoint._next += 1

    class FakeExitEvent(object):
        def connect(self, callback):
            self.callback = callback

    class FakeGdb(object):
        VERSION = "fake-gdb"
        Breakpoint = FakeBreakpoint
        FinishBreakpoint = FakeBreakpoint

        def __init__(self, memory):
            self.selected = FakeInferior(memory)
            self.events = type("Events", (), {"exited": FakeExitEvent()})()

        def selected_inferior(self):
            return self.selected

    modules = G.ModuleMap(
        bases={"engine.dll": 0x79E00000, "client.dll": 0x74630000},
        env_bases={"engine.dll": 0x79E00000, "client.dll": 0x74630000},
        # Deliberately partial/overlapping: exactly the regression the lead
        # hit.  engine.dll has only its header page, while a too-wide
        # client.dll range even covers the engine address.  The expected
        # module must still resolve through the env-base span fallback.
        ranges={
            "engine.dll": [(0x79E00000, 0x79E01000)],
            "client.dll": [(0x74630000, 0x7A600000)],
        },
        spans={"engine.dll": 0x800000, "client.dll": 0x900000},
    )
    memory = {}
    for spec in specs:
        address = modules.base(spec.module) + spec.rva
        payload = (spec.expected_bytes or b"") + b"\x00" * 8
        memory[address] = payload

    old_gdb = G.gdb
    old_override = os.environ.get("N27_FULL_STATE")
    os.environ["N27_FULL_STATE"] = "1"
    G.gdb = FakeGdb(memory)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "install-events.jsonl"
            collector = G.Collector(
                config, specs, modules, str(out_path), "install-simulation"
            )
            ok = collector.install()
            collector.finalize("install-test")
            check_equal("fake install ok", ok, True)
            rows = [
                json.loads(line)
                for line in out_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            installed = [
                row for row in rows if row.get("event") == "probe_installed"
            ]
            summary = [
                row for row in rows if row.get("event") == "install_summary"
            ]
            check_equal("fake install probe lines", len(installed), 6)
            check_equal(
                "fake install probe ids",
                sorted(row["probe_id"] for row in installed),
                sorted(spec.id for spec in specs),
            )
            check_equal("fake install summary count", len(summary), 1)
            check_equal("fake install summary ok", summary[0].get("ok"), True)
            check_equal(
                "fake install summary installed",
                summary[0].get("installed_probes"),
                6,
            )
            check(
                "fake install bytes verified",
                all(row.get("bytes_verified") is True for row in installed),
            )
            check_equal(
                "fake install warns on fallback",
                len(summary[0].get("warnings", [])),
                5,
            )
            engine_rows = [
                row for row in installed if row["module"] == "engine.dll"
            ]
            client_rows = [
                row for row in installed if row["module"] == "client.dll"
            ]
            check_equal("fake install engine rows", len(engine_rows), 5)
            check_equal("fake install client rows", len(client_rows), 1)
            check(
                "fake install engine fallback source",
                all(
                    row.get("location_source") == "env_base_span"
                    for row in engine_rows
                ),
            )
            check_equal(
                "fake install client mapped source",
                client_rows[0].get("location_source"),
                "mapped",
            )
            check(
                "fake install fallback flag",
                all(row.get("fallback_used") is True for row in engine_rows)
                and client_rows[0].get("fallback_used") is False,
            )
            check_equal(
                "fake install env override",
                next(
                    row
                    for row in rows
                    if row.get("event") == "full_state_installed"
                ).get("mode"),
                "env",
            )
            counts = [row for row in rows if row.get("event") == "counts"]
            check_equal("fake install final counts", len(counts), 1)
    finally:
        G.gdb = old_gdb
        if old_override is None:
            os.environ.pop("N27_FULL_STATE", None)
        else:
            os.environ["N27_FULL_STATE"] = old_override


# ---------------------------------------------------------------------------
# 5. expected byte values from the shipped build
# ---------------------------------------------------------------------------

def test_expected_bytes():
    with open(CONFIG_PATH, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    expected = {
        "callCond": "e8c29cffff",
        "afterCond": "84c0",
        "jzCond": "0f8438020000",
        "finalCall": "ffd0",
        "e56Entry": "8bc1",
        "clientEventBranch": "8d4be8",
    }
    for raw in config["probes"]:
        check_equal(
            "expected bytes %s" % raw["id"],
            raw.get("expected_bytes"),
            expected[raw["id"]],
        )


# ---------------------------------------------------------------------------

def main():
    print("== N27-D19 probe schema tests ==")
    config, specs = test_config()
    test_jsonl(specs)
    test_counters(specs)
    test_histogram_and_modules()
    test_mapping_parser_and_fallback()
    test_collector_simulation(config, specs)
    test_install_with_fake_gdb(config, specs)
    test_expected_bytes()

    print("")
    print("checks: %d passed, %d failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        for name, detail in FAILED:
            print("FAILED: %s %s" % (name, detail))
        return 1
    print("ALL TESTS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
