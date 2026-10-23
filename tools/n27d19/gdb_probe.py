#!/usr/bin/env python3
"""Declarative GDB probe collector for the L4D2 Windows client under Proton.

This file is executed *inside gdb* by the runner:

    set scheduler-locking on
    python exec(open("tools/n27d19/gdb_probe.py").read())
    continue

It reads a JSON probe description (N27_PROBE_CONFIG) and writes one compact
JSON object per line to N27_PROBE_OUT.  Module addresses are normalised to a
module basename plus RVA (for example ``engine.dll+0x1BC301``); host paths are
never emitted.

Environment:
    N27_PROBE_CONFIG          required, probe_config.json path
    N27_PROBE_OUT             required, JSONL output path
    N27_MODULE_BASE_ENGINE    mapping base of engine.dll (hex)
    N27_MODULE_BASE_CLIENT    mapping base of client.dll (hex)
    N27_PROBE_RUN_ID          optional stable run id
    N27_FULL_STATE            optional 0/1 override for replay/attach-late runs

The script is also importable for offline tests.  Set
N27_PROBE_IMPORT_ONLY=1 before importing it to suppress ``main()``.
"""

from __future__ import print_function

import atexit
import json
import os
import re
import struct
import sys
import time
from datetime import datetime, timezone

try:  # gdb is absent when the schema tests import this module.
    import gdb  # type: ignore
except Exception:  # pragma: no cover - exercised by gdb unlike offline tests
    gdb = None


SCHEMA_VERSION = "n27d19.probe.v1"
CONFIG_SCHEMA = "n27d19.probe.config.v1"
MODULE_NAMES = ("engine.dll", "client.dll")
VALID_PHASES = ("pre_full", "post_full", "both")
VALID_FIELDS = (
    "eax", "edx", "esi", "edi", "ecx", "al", "eflags", "return_address"
)
DEFAULT_SPANS = {"engine.dll": 0x800000, "client.dll": 0x900000}
SIDECAR_EVERY_HITS = 25


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------

def utc_now():
    """ISO-8601 UTC timestamp with millisecond precision."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def as_int(value, default=None):
    """Parse an int, a decimal string, or a ``0x`` hex string."""
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        text = str(value).strip()
        if not text:
            return default
        if text.lower().startswith("0x"):
            return int(text, 16)
        return int(text, 10)
    except Exception:
        return default


def as_u32(value):
    parsed = as_int(value, None)
    return None if parsed is None else (parsed & 0xFFFFFFFF)


def hex32(value):
    parsed = as_u32(value)
    return None if parsed is None else "0x%X" % parsed


def sanitize_text(value, limit=400):
    """Strip host-absolute paths from diagnostic text.

    Module pointers are emitted as module+RVA, never as a path.  This helper
    also keeps gdb/Wine exception text from leaking a host path into JSONL.
    """
    text = str(value)
    text = re.sub(
        r"[A-Za-z]:\\[^\s]+",
        lambda m: os.path.basename(m.group(0).replace("\\", "/")),
        text,
    )
    text = re.sub(r"/(?:[^/\s]+/)+([^/\s]+)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def parse_bool_env(value):
    """Return True/False for common boolean env spellings, or None."""
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on", "full", "post_full"):
        return True
    if text in ("0", "false", "no", "off", "pre", "pre_full"):
        return False
    return None


def target_pid():
    if gdb is None:
        return 0
    try:
        return int(gdb.selected_inferior().pid)
    except Exception:
        return 0


def read_memory_bytes(addr, size):
    """Read target memory; return bytes or None.  Never raises."""
    if gdb is None or addr is None or size <= 0:
        return None
    try:
        inferior = gdb.selected_inferior()
        data = inferior.read_memory(int(addr), int(size))
        if isinstance(data, memoryview):
            data = data.tobytes()
        elif not isinstance(data, (bytes, bytearray)):
            data = bytes(data)
        return bytes(data)
    except Exception:
        return None


def read_u32(addr):
    data = read_memory_bytes(addr, 4)
    if data is None or len(data) != 4:
        return None
    return struct.unpack("<I", data)[0]


def read_reg(name):
    """Read a 32-bit register by gdb name; return int or None."""
    if gdb is None:
        return None
    try:
        value = gdb.parse_and_eval("(unsigned int)$" + str(name))
        return int(value) & 0xFFFFFFFF
    except Exception:
        pass
    try:
        # A few gdb/arch combinations reject the explicit cast for $al or
        # $eflags; the raw convenience variable still converts.
        value = gdb.parse_and_eval("$" + str(name))
        return int(value) & 0xFFFFFFFF
    except Exception:
        return None


# ---------------------------------------------------------------------------
# module normalisation
# ---------------------------------------------------------------------------

class ModuleMap(object):
    """Map a raw target address to ``(module, rva)``.

    Two sources are used:

    1. parsed mappings from the attached process (/proc/<pid>/maps, then
       ``info proc mappings``), and
    2. the env-supplied mapping base as a fallback span.

    The fallback matters under Proton/Wine: ``info proc mappings`` can be
    partial or formatted differently, and a missing/partial range must not
    make a correct base+RVA probe look unmapped.  Addresses accepted through
    the fallback are recorded as ``env_base_span`` so the install record can
    show a warning.  The expected-byte prefix is always verified separately.
    """

    def __init__(self, bases=None, spans=None, ranges=None, env_bases=None):
        self.bases = dict(bases or {})
        self.spans = dict(spans or {})
        self.env_bases = dict(
            env_bases if env_bases is not None else self.bases
        )
        self.ranges = {name: [] for name in MODULE_NAMES}
        self.fallback_hits = 0
        if ranges:
            for name, items in ranges.items():
                if name in self.ranges:
                    self.ranges[name] = sorted(items)
        for name in MODULE_NAMES:
            if name not in self.spans:
                self.spans[name] = DEFAULT_SPANS[name]

    @staticmethod
    def _mapping_tokens(line):
        """Return the first two address-like tokens on a mapping line."""
        return re.findall(r"0x[0-9a-fA-F]+|[0-9a-fA-F]{6,}", line)

    @classmethod
    def parse_mappings(cls, text, bases=None, spans=None):
        """Parse /proc or gdb-style mapping text.

        Detection is by the literal module basename in the line, so Wine paths
        containing spaces work.  Only the first two address-like tokens are
        used (start/end); path, permissions and inode differences are ignored.
        """
        env_bases = dict(bases or {})
        bases = dict(env_bases)
        spans = dict(spans or {})
        for name in MODULE_NAMES:
            if name not in spans:
                spans[name] = DEFAULT_SPANS[name]

        ranges = {name: [] for name in MODULE_NAMES}
        for line in (text or "").splitlines():
            lower = line.lower()
            module = None
            for name in MODULE_NAMES:
                # Require a whole basename.  A plain substring test would
                # match lsteamclient.dll as client.dll (D12's known trap).
                pattern = r"(?<![A-Za-z0-9._-])" + re.escape(name) + r"(?=$|[\s\),])"
                if re.search(pattern, lower):
                    module = name
                    break
            if module is None:
                continue
            tokens = cls._mapping_tokens(line)
            if len(tokens) < 2:
                continue
            try:
                # Mapping addresses are hex; /proc omits "0x", gdb includes it.
                start = int(tokens[0], 16)
                end = int(tokens[1], 16)
            except ValueError:
                continue
            if end <= start:
                continue
            ranges[module].append((start, end))

        for name in MODULE_NAMES:
            if ranges[name]:
                ranges[name].sort()
                if name not in bases:
                    bases[name] = ranges[name][0][0]
        return cls(
            bases=bases,
            spans=spans,
            ranges=ranges,
            env_bases=env_bases,
        )

    @classmethod
    def discover(cls, bases=None, spans=None):
        pid = target_pid()
        text = ""
        if pid:
            try:
                with open("/proc/%d/maps" % pid, "r", errors="ignore") as handle:
                    text = handle.read()
            except Exception:
                text = ""
        if not text and gdb is not None:
            try:
                text = gdb.execute("info proc mappings", to_string=True)
            except Exception:
                text = ""
        return cls.parse_mappings(text, bases=bases, spans=spans)

    def base(self, name):
        if name in self.bases:
            return self.bases[name]
        if self.ranges.get(name):
            return self.ranges[name][0][0]
        return None

    def normalize_detail(self, address):
        """Return ``(module, rva, source)``.

        ``source`` is ``mapped`` for a parsed mapping, ``env_base_span`` for
        the base+fallback-span path, or ``unmapped``.
        """
        raw = as_u32(address)
        if raw is None or raw == 0:
            return (None, None, "unmapped")

        # Parsed ranges first.
        for name in MODULE_NAMES:
            base = self.base(name)
            if base is None:
                continue
            for start, end in self.ranges.get(name, []):
                if start <= raw < end and raw >= base:
                    return (name, raw - base, "mapped")

        # Env base + span fallback.  This is deliberately limited to the
        # configured span and only used when no parsed range matched.
        for name in MODULE_NAMES:
            base = self.env_bases.get(name)
            if base is None:
                continue
            span = self.spans.get(name, DEFAULT_SPANS[name])
            if base <= raw < base + span:
                self.fallback_hits += 1
                return (name, raw - base, "env_base_span")
        return (None, None, "unmapped")

    def normalize(self, address):
        """Return ``(module_name, rva)`` or ``(None, None)``."""
        module, rva, _source = self.normalize_detail(address)
        return (module, rva)

    def resolve_for_module(self, name, address):
        """Resolve an address for a *specific* expected module.

        Parsed ranges are still preferred, but if they are partial (or
        mis-attributed) and the configured env base contains the address, the
        expected module is accepted through ``env_base_span``.  This is the
        install-time path that keeps a correct base+RVA from being rejected.
        """
        module, rva, source = self.normalize_detail(address)
        if module == name:
            return (module, rva, source)
        raw = as_u32(address)
        base = self.env_bases.get(name)
        if raw is not None and base is not None:
            span = self.spans.get(name, DEFAULT_SPANS[name])
            if base <= raw < base + span:
                self.fallback_hits += 1
                return (name, raw - base, "env_base_span")
        return (module, rva, source)

    def describe(self):
        """Small JSON-safe module summary (no host paths)."""
        out = {}
        for name in MODULE_NAMES:
            base = self.base(name)
            ranges = self.ranges.get(name, [])
            out[name] = {
                "base": hex32(base),
                "env_base": hex32(self.env_bases.get(name)),
                "mapped": bool(ranges),
                "range_count": len(ranges),
                "ranges": [
                    {"start": hex32(start), "end": hex32(end)}
                    for start, end in ranges
                ],
                "fallback_span": hex32(self.spans.get(name)),
                "fallback_available": self.env_bases.get(name) is not None,
                "fallback_hits": self.fallback_hits,
            }
        return out


def format_target_key(module, rva, raw):
    if module is not None and rva is not None:
        return "%s+0x%X" % (module, rva)
    raw = as_u32(raw)
    return None if raw is None else ("abs:0x%X" % raw)


# ---------------------------------------------------------------------------
# histogram / counters (pure Python; used by the offline tests)
# ---------------------------------------------------------------------------

class Histogram(object):
    """One row per unique target; each row also carries a hit count.

    ``unique`` is the number of distinct targets in the run.  A target is
    inserted exactly once (first sighting), so the final snapshot contains
    one row per unique target; ``hits`` counts every occurrence.
    """

    def __init__(self):
        self.rows = {}
        self.order = []

    def add(self, module, rva, raw, seq=None):
        raw = as_u32(raw)
        if raw is None:
            return None
        key = format_target_key(module, rva, raw)
        row = self.rows.get(key)
        if row is None:
            row = {
                "key": key,
                "module": module,
                "rva": rva,
                "raw": raw,
                "hits": 0,
                "first_seq": seq,
                "last_seq": seq,
            }
            self.rows[key] = row
            self.order.append(key)
        row["hits"] += 1
        row["last_seq"] = seq
        return key

    @property
    def unique(self):
        return len(self.rows)

    @property
    def total_hits(self):
        return sum(row["hits"] for row in self.rows.values())

    def snapshot(self, top=None):
        rows = sorted(
            self.rows.values(), key=lambda row: (-row["hits"], row["key"])
        )
        total = len(rows)
        if top is not None and top >= 0:
            rows = rows[:top]
        return {
            "unique": self.unique,
            "hits": self.total_hits,
            "truncated": len(rows) < total,
            "targets": rows,
        }


class SampleLimits(object):
    def __init__(self, pre_full, post_full, stats_every):
        self.pre_full = pre_full
        self.post_full = post_full
        self.stats_every = stats_every

    def as_dict(self):
        return {
            "pre_full": self.pre_full,
            "post_full": self.post_full,
            "stats_every": self.stats_every,
        }


class ProbeSpec(object):
    def __init__(self, raw, defaults=None):
        defaults = defaults or {}
        raw = dict(raw or {})
        if not raw.get("id"):
            raise ValueError("probe missing id")
        self.id = str(raw["id"])
        self.module = str(raw.get("module", "")).lower()
        if self.module not in MODULE_NAMES:
            raise ValueError("%s: unknown module %r" % (self.id, self.module))
        self.rva = as_int(raw.get("rva"), None)
        if self.rva is None or self.rva < 0 or self.rva > 0xFFFFFFFF:
            raise ValueError("%s: invalid rva %r" % (self.id, raw.get("rva")))
        self.phase = str(raw.get("phase", defaults.get("phase", "both")))
        if self.phase not in VALID_PHASES:
            raise ValueError("%s: invalid phase %r" % (self.id, self.phase))

        limits = dict(defaults.get("sample_limits", {}))
        limits.update(raw.get("sample_limits", {}))
        pre_full = as_int(limits.get("pre_full"), 4)
        post_full = as_int(limits.get("post_full"), 8)
        stats_every = as_int(limits.get("stats_every"), 200)
        if pre_full < 0 or post_full < 0 or stats_every < 0:
            raise ValueError("%s: sample limits must be non-negative" % self.id)
        self.limits = SampleLimits(pre_full, post_full, stats_every)

        fields = raw.get("fields", [])
        if not isinstance(fields, list):
            raise ValueError("%s: fields must be a list" % self.id)
        self.fields = [str(field) for field in fields]
        for field in self.fields:
            if field not in VALID_FIELDS:
                raise ValueError("%s: unsupported field %r" % (self.id, field))

        self.histogram_eax = bool(raw.get("histogram_eax", False))
        self.expect_post_full_hits = as_int(
            raw.get("expect_post_full_hits", raw.get("expect_hits")), None
        )
        self.expected_bytes = self._parse_hex(
            raw.get("expected_bytes", defaults.get("expected_bytes"))
        )
        self.verify_bytes = bool(
            raw.get("verify_bytes", defaults.get("verify_bytes", True))
        )
        self.target_check = raw.get("target_check")
        if self.target_check is not None and not isinstance(
            self.target_check, dict
        ):
            raise ValueError("%s: target_check must be an object" % self.id)
        self.note = str(raw.get("note", ""))

    def _parse_hex(self, value):
        if value in (None, ""):
            return None
        text = str(value).replace(" ", "").replace(":", "").strip().lower()
        if len(text) % 2:
            raise ValueError("%s: expected_bytes has odd length" % self.id)
        try:
            return bytes.fromhex(text)
        except ValueError:
            raise ValueError("%s: expected_bytes is not hex" % self.id)

    def phase_allows(self, full_state):
        if self.phase == "both":
            return True
        if self.phase == "post_full":
            return bool(full_state)
        return not bool(full_state)

    def as_dict(self):
        return {
            "id": self.id,
            "module": self.module,
            "rva": self.rva,
            "phase": self.phase,
            "sample_limits": self.limits.as_dict(),
            "fields": list(self.fields),
            "histogram_eax": self.histogram_eax,
            "expect_post_full_hits": self.expect_post_full_hits,
            "expected_bytes": (
                self.expected_bytes.hex() if self.expected_bytes else None
            ),
            "verify_bytes": self.verify_bytes,
            "target_check": self.target_check,
        }


class ProbeCounters(object):
    """Per-probe counters.

    Sampling is gated on *per-phase logged* counters, never on the lifetime
    total.  This is the fix for the D18 cumulative-count bug: exhausting the
    pre-FULL sample budget cannot stop post-FULL samples.
    """

    def __init__(self, spec):
        self.spec = spec
        self.total_hits = 0
        self.pre_full_hits = 0
        self.post_full_hits = 0
        self.logged_hits = 0
        self.logged_pre_full = 0
        self.logged_post_full = 0
        self.sample_limited = 0
        self.phase_filtered = 0
        self.errors = 0
        self.mismatch_hits = 0
        self.mismatch_unknown = 0
        self.deref_errors = 0
        self.first_hit_ts = None
        self.last_hit_ts = None
        self.histogram = Histogram()

    def note_hit(self, full_state, ts=None):
        self.total_hits += 1
        actual_phase = "post_full" if full_state else "pre_full"
        if full_state:
            self.post_full_hits += 1
        else:
            self.pre_full_hits += 1
        self.first_hit_ts = self.first_hit_ts or ts
        self.last_hit_ts = ts

        if not self.spec.phase_allows(full_state):
            self.phase_filtered += 1
            return (False, actual_phase)

        limit = (
            self.spec.limits.post_full
            if full_state
            else self.spec.limits.pre_full
        )
        logged = (
            self.logged_post_full if full_state else self.logged_pre_full
        )
        if logged >= limit:
            self.sample_limited += 1
            return (False, actual_phase)

        if full_state:
            self.logged_post_full += 1
        else:
            self.logged_pre_full += 1
        self.logged_hits += 1
        return (True, actual_phase)

    def note_error(self):
        self.errors += 1

    def note_mismatch(self, mismatch):
        if mismatch is True:
            self.mismatch_hits += 1
        elif mismatch is None and self.spec.target_check is not None:
            self.mismatch_unknown += 1

    def stats_due(self):
        every = self.spec.limits.stats_every
        return bool(every) and self.total_hits > 0 and self.total_hits % every == 0

    def sample_snapshot(self):
        return {
            "pre_full": self.spec.limits.pre_full,
            "post_full": self.spec.limits.post_full,
            "logged_pre_full": self.logged_pre_full,
            "logged_post_full": self.logged_post_full,
        }

    def snapshot(self):
        data = {
            "total_hits": self.total_hits,
            "pre_full_hits": self.pre_full_hits,
            "post_full_hits": self.post_full_hits,
            "logged_hits": self.logged_hits,
            "logged_pre_full": self.logged_pre_full,
            "logged_post_full": self.logged_post_full,
            "sample_limited": self.sample_limited,
            "phase_filtered": self.phase_filtered,
            "errors": self.errors,
            "mismatch_hits": self.mismatch_hits,
            "mismatch_unknown": self.mismatch_unknown,
            "deref_errors": self.deref_errors,
            "histogram_unique": self.histogram.unique,
            "histogram_hits": self.histogram.total_hits,
            "first_hit_ts": self.first_hit_ts,
            "last_hit_ts": self.last_hit_ts,
        }
        if self.spec.expect_post_full_hits is not None:
            data["expect_post_full_hits"] = self.spec.expect_post_full_hits
        return data


# ---------------------------------------------------------------------------
# full-state detector
# ---------------------------------------------------------------------------

class SignonFullStateDetector(object):
    """Latch FULL when SetSignonState(6) returns with state==6.

    Declarative replacement for the hand-written FinishBreakpoint logic in
    tools/linux/gdb/client_trace.py.  The breakpoint is not a probe and is
    reported separately as ``full_state_installed``.
    """

    def __init__(self, config, collector):
        self.config = dict(config or {})
        self.collector = collector
        self.bp = None
        self.installed = False
        self.pending = False
        self.attempts = 0
        self.rejections = 0
        self.errors = 0

    def install(self):
        if gdb is None:
            raise RuntimeError("gdb module unavailable")
        module = str(self.config.get("module", "engine.dll")).lower()
        if module not in MODULE_NAMES:
            raise ValueError("full_state: unknown module %r" % module)
        rva = as_int(self.config.get("rva"), None)
        if rva is None:
            raise ValueError("full_state: invalid rva")
        base = self.collector.modules.base(module)
        if base is None:
            raise RuntimeError("full_state: %s base unavailable" % module)
        address = base + rva
        expected = self.config.get("expected_bytes")
        expected_verified = None
        if expected and bool(self.config.get("verify_bytes", True)):
            expected_bytes = bytes.fromhex(str(expected).replace(" ", ""))
            actual = read_memory_bytes(address, len(expected_bytes))
            expected_verified = actual == expected_bytes
            if not expected_verified:
                raise RuntimeError(
                    "full_state byte mismatch at %s+0x%X (expected %s got %s)"
                    % (
                        module,
                        rva,
                        expected_bytes.hex(),
                        actual.hex() if actual is not None else "unreadable",
                    )
                )

        detector = self
        state_offset = as_int(self.config.get("state_offset"), 104)
        request_offset = as_int(self.config.get("request_stack_offset"), 4)
        request_value = as_int(self.config.get("request_value"), 6)
        full_value = as_int(self.config.get("full_value"), 6)
        require_return = bool(self.config.get("require_return_state", True))

        class Finish(gdb.FinishBreakpoint):
            def __init__(self, this_ptr, request, before):
                super(Finish, self).__init__(internal=True)
                self.this_ptr = this_ptr
                self.request = request
                self.before = before

            def stop(self):
                detector.pending = False
                after = read_u32(self.this_ptr + state_offset)
                detector.attempts += 1
                if after == full_value:
                    detector.collector.set_full_state(
                        mode="signon",
                        signon_this=self.this_ptr,
                        request=self.request,
                        before=self.before,
                        after=after,
                    )
                else:
                    detector.rejections += 1
                return False

        class Entry(gdb.Breakpoint):
            def __init__(self):
                super(Entry, self).__init__("*0x%x" % address, internal=True)

            def stop(self):
                try:
                    this_ptr = read_reg("ecx")
                    esp = read_reg("esp")
                    request = read_u32(esp + request_offset) if esp else None
                    before = (
                        read_u32(this_ptr + state_offset)
                        if this_ptr is not None
                        else None
                    )
                    if (
                        request == request_value
                        and this_ptr is not None
                        and not detector.collector.full_state
                        and not detector.pending
                    ):
                        detector.pending = True
                        if require_return:
                            try:
                                Finish(this_ptr, request, before)
                            except Exception as exc:
                                detector.pending = False
                                detector.errors += 1
                                detector.collector.note_full_state_error(exc)
                        else:
                            detector.pending = False
                            detector.collector.set_full_state(
                                mode="signon-entry",
                                signon_this=this_ptr,
                                request=request,
                                before=before,
                                after=None,
                            )
                except Exception as exc:
                    detector.errors += 1
                    detector.collector.note_full_state_error(exc)
                return False

        self.bp = Entry()
        self.installed = True
        return {
            "event": "full_state_installed",
            "mode": "signon",
            "module": module,
            "rva": rva,
            "breakpoint": int(self.bp.number),
            "expected_bytes": expected,
            "bytes_verified": expected_verified,
            "state_offset": state_offset,
            "request_stack_offset": request_offset,
            "request_value": request_value,
            "full_value": full_value,
        }


# ---------------------------------------------------------------------------
# collector
# ---------------------------------------------------------------------------

class Collector(object):
    def __init__(self, config, specs, modules, out_path, run_id):
        self.config = config
        self.specs = list(specs)
        self.modules = modules
        self.out_path = out_path
        self.run_id = run_id
        self.counters = {spec.id: ProbeCounters(spec) for spec in self.specs}
        self.breakpoints = {}
        self.installed = []
        self.failures = []
        self.warnings = []
        self.full_state = False
        self.full_state_seen = False
        self.full_override = None
        self.full_detector = None
        self.full_record = None
        self.seq = 0
        self.file_handle = None
        self.finalized = False
        self.sidecar_errors = 0

    # -- event plumbing -----------------------------------------------------
    def _write(self, event):
        if self.file_handle is None:
            raise RuntimeError("output is not open")
        payload = dict(event)
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload.setdefault("run_id", self.run_id)
        payload.setdefault("ts", utc_now())
        self.seq += 1
        payload["seq"] = self.seq
        line = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        self.file_handle.write(line + "\n")
        self.file_handle.flush()

    def _write_sidecar(self):
        if not self.out_path:
            return
        path = self.out_path + ".counts.json"
        tmp = path + ".tmp.%d" % os.getpid()
        try:
            payload = self.snapshot_counts("sidecar")
            payload["schema_version"] = SCHEMA_VERSION
            payload["run_id"] = self.run_id
            payload["ts"] = utc_now()
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(tmp, path)
        except Exception:
            self.sidecar_errors += 1

    # -- install ------------------------------------------------------------
    def install(self):
        self._install_full_state()
        for spec in self.specs:
            self._install_probe(spec)
        if self.failures:
            self._fail_install()
            return False
        try:
            self._open_output()
        except Exception as exc:
            self.failures.append("output: " + sanitize_text(exc))
            self._fail_install()
            return False

        self._write(
            {
                "event": "run_start",
                "config_schema": CONFIG_SCHEMA,
                "jsonl_schema_version": SCHEMA_VERSION,
                "probe_count": len(self.specs),
                "probe_ids": [spec.id for spec in self.specs],
                "target_pid": target_pid(),
                "module_bases": {
                    name: hex32(self.modules.base(name))
                    for name in MODULE_NAMES
                },
                "modules": self.modules.describe(),
                "full_state_override": self.full_override,
                "warnings": list(self.warnings),
                "gdb_version": getattr(gdb, "VERSION", None) if gdb else None,
            }
        )
        if self.full_record:
            self._write(self.full_record)
        for record in self.installed:
            self._write(record)
        self._write(
            {
                "event": "install_summary",
                "ok": True,
                "expected_probes": len(self.specs),
                "installed_probes": len(self.installed),
                "probe_ids": [record["probe_id"] for record in self.installed],
                "full_state": self.full_record,
                "warnings": list(self.warnings),
            }
        )
        self._write_sidecar()

        try:
            atexit.register(self.finalize, "atexit")
        except Exception:
            pass
        if gdb is not None:
            try:
                gdb.events.exited.connect(
                    lambda event: self.finalize("inferior_exited")
                )
            except Exception:
                pass
        print(
            "N27_PROBE_READY run_id=%s probes=%d engine=%s client=%s full_state=%s"
            % (
                self.run_id,
                len(self.installed),
                hex32(self.modules.base("engine.dll")),
                hex32(self.modules.base("client.dll")),
                self.full_state,
            ),
            flush=True,
        )
        return True

    def _open_output(self):
        if not self.out_path:
            raise RuntimeError("N27_PROBE_OUT is not set")
        parent = os.path.dirname(os.path.abspath(self.out_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        self.file_handle = open(self.out_path, "w", encoding="utf-8")

    def _install_full_state(self):
        config = self.config.get("full_state") or {}
        override_name = str(config.get("env_override", "N27_FULL_STATE"))
        override = parse_bool_env(os.environ.get(override_name))
        self.full_override = override
        if override is not None:
            self.full_state = override
            self.full_state_seen = bool(override)
            self.full_record = {
                "event": "full_state_installed",
                "mode": "env",
                "env_var": override_name,
                "installed": True,
                "full_state": bool(override),
                "breakpoint": None,
            }
            return
        mode = str(config.get("mode", "signon")).lower()
        if mode in ("none", "off", "disabled"):
            self.full_record = {
                "event": "full_state_installed",
                "mode": mode,
                "installed": False,
                "full_state": False,
                "breakpoint": None,
            }
            self.failures.append("full_state: disabled but no env override")
            return
        if mode != "signon":
            self.failures.append("full_state: unsupported mode %r" % mode)
            return
        try:
            detector = SignonFullStateDetector(config, self)
            record = detector.install()
            self.full_detector = detector
            self.full_record = record
        except Exception as exc:
            self.failures.append("full_state: " + sanitize_text(exc))

    def _install_probe(self, spec):
        base = self.modules.base(spec.module)
        if base is None:
            self.failures.append("%s: %s base unavailable" % (spec.id, spec.module))
            return
        address = base + spec.rva
        module, rva, location_source = self.modules.resolve_for_module(
            spec.module, address
        )
        if module != spec.module or rva != spec.rva:
            self.failures.append(
                "%s: address %s not in %s mappings"
                % (spec.id, hex32(address), spec.module)
            )
            return
        fallback_used = location_source == "env_base_span"
        if fallback_used:
            message = (
                "%s: accepted %s+0x%X via env-base fallback "
                "(parsed mapping range missing/partial)"
                % (spec.id, spec.module, spec.rva)
            )
            self.warnings.append(message)
            print("N27_PROBE_WARNING: " + message, file=sys.stderr, flush=True)

        first_bytes = read_memory_bytes(address, 8)
        bytes_verified = None
        if spec.expected_bytes:
            actual = read_memory_bytes(address, len(spec.expected_bytes))
            bytes_verified = actual == spec.expected_bytes
            if spec.verify_bytes and not bytes_verified:
                self.failures.append(
                    "%s: byte mismatch at %s+0x%X expected=%s got=%s"
                    % (
                        spec.id,
                        spec.module,
                        spec.rva,
                        spec.expected_bytes.hex(),
                        actual.hex() if actual is not None else "unreadable",
                    )
                )
                return

        collector = self

        class ProbeBreakpoint(gdb.Breakpoint):
            def __init__(self):
                super(ProbeBreakpoint, self).__init__(
                    "*0x%x" % address, internal=True
                )

            def stop(self):
                try:
                    collector.on_hit(spec)
                except Exception as exc:
                    collector.counters[spec.id].note_error()
                    try:
                        collector._write(
                            {
                                "event": "probe_error",
                                "probe_id": spec.id,
                                "module": spec.module,
                                "rva": spec.rva,
                                "error": sanitize_text(exc),
                            }
                        )
                    except Exception:
                        pass
                return False

        try:
            bp = ProbeBreakpoint()
            self.breakpoints[spec.id] = bp
        except Exception as exc:
            self.failures.append("%s: breakpoint failed: %s" % (spec.id, sanitize_text(exc)))
            return

        record = {
            "event": "probe_installed",
            "probe_id": spec.id,
            "module": spec.module,
            "rva": spec.rva,
            "phase": spec.phase,
            "phase_policy": spec.phase,
            "breakpoint": int(bp.number),
            "location_source": location_source,
            "fallback_used": fallback_used,
            "first_bytes": first_bytes.hex() if first_bytes is not None else None,
            "expected_bytes": (
                spec.expected_bytes.hex() if spec.expected_bytes else None
            ),
            "bytes_verified": bytes_verified,
            "sample_limits": spec.limits.as_dict(),
            "fields": list(spec.fields),
            "histogram_eax": spec.histogram_eax,
            "expect_post_full_hits": spec.expect_post_full_hits,
        }
        self.installed.append(record)

    def _fail_install(self):
        payload = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "ts": utc_now(),
            "event": "install_failed",
            "ok": False,
            "failures": list(self.failures),
            "warnings": list(self.warnings),
            "probe_ids": [spec.id for spec in self.specs],
            "modules": self.modules.describe(),
            "full_state": self.full_record,
        }
        if self.out_path:
            path = self.out_path + ".install.json"
            tmp = path + ".tmp.%d" % os.getpid()
            try:
                with open(tmp, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, indent=2, sort_keys=True)
                    handle.write("\n")
                os.replace(tmp, path)
            except Exception:
                pass
        if self.out_path:
            try:
                record = dict(payload)
                record["seq"] = 1
                with open(self.out_path, "a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(
                            record,
                            sort_keys=True,
                            separators=(",", ":"),
                            ensure_ascii=True,
                        )
                        + "\n"
                    )
                    handle.flush()
            except Exception:
                pass
        print(
            "N27_PROBE_INSTALL_FAILED "
            + json.dumps(payload, sort_keys=True, separators=(",", ":")),
            file=sys.stderr,
            flush=True,
        )
        # Fail the gdb process before any JSONL hit can be written.  The
        # runner must treat a non-zero gdb exit status as a failed run.
        if gdb is not None:
            try:
                gdb.execute("set confirm off")
                gdb.execute("quit 1")
            except Exception:
                pass
        os._exit(1)

    # -- runtime ------------------------------------------------------------
    def set_full_state(self, mode, signon_this=None, request=None, before=None, after=None):
        if self.full_state:
            return
        self.full_state = True
        self.full_state_seen = True
        try:
            self._write(
                {
                    "event": "full_state",
                    "full_state": True,
                    "mode": mode,
                    "signon_this": signon_this,
                    "request": request,
                    "before": before,
                    "after": after,
                }
            )
            self._write_sidecar()
        except Exception:
            pass

    def note_full_state_error(self, exc):
        try:
            self._write(
                {
                    "event": "full_state_error",
                    "error": sanitize_text(exc),
                }
            )
        except Exception:
            pass

    def on_hit(self, spec):
        counters = self.counters[spec.id]
        ts = utc_now()
        full_state = bool(self.full_state)
        log_allowed, actual_phase = counters.note_hit(full_state, ts)

        captured = {}
        for field in spec.fields:
            if field == "return_address":
                esp = read_reg("esp")
                captured[field] = read_u32(esp) if esp is not None else None
            else:
                captured[field] = read_reg(field)

        al = read_reg("al")
        eflags = read_reg("eflags")

        wants_edx = "edx" in spec.fields or spec.target_check is not None
        wants_esi = "esi" in spec.fields
        edx = captured.get("edx") if "edx" in captured else (read_reg("edx") if wants_edx else None)
        esi = captured.get("esi") if "esi" in captured else (read_reg("esi") if wants_esi else None)

        target = captured.get("eax") if "eax" in captured else None
        if spec.histogram_eax and target is None:
            target = read_reg("eax")

        target_module = target_rva = None
        histogram_key = None
        if spec.histogram_eax and target is not None:
            target_module, target_rva = self.modules.normalize(target)
            histogram_key = counters.histogram.add(
                target_module, target_rva, target, self.seq + 1
            )

        edx_module, edx_rva = (
            self.modules.normalize(edx) if edx is not None else (None, None)
        )
        esi_module, esi_rva = (
            self.modules.normalize(esi) if esi is not None else (None, None)
        )

        return_address = captured.get("return_address")
        return_module, return_rva = (
            self.modules.normalize(return_address)
            if return_address is not None
            else (None, None)
        )

        mismatch = None
        deref = None
        deref_module = deref_rva = None
        if spec.target_check is not None and target is not None:
            deref_reg = spec.target_check.get("deref_reg", "edx")
            deref_offset = as_int(spec.target_check.get("deref_offset"), 12)
            deref_size = as_int(spec.target_check.get("deref_size"), 4)
            base_value = captured.get(deref_reg)
            if base_value is None:
                base_value = read_reg(deref_reg)
            if base_value is None:
                counters.note_error()
                counters.mismatch_unknown += 1
            else:
                if deref_size == 4:
                    deref = read_u32(base_value + deref_offset)
                else:
                    raw = read_memory_bytes(base_value + deref_offset, deref_size)
                    deref = int.from_bytes(raw, "little") if raw else None
                if deref is None:
                    counters.note_error()
                    counters.deref_errors += 1
                    counters.mismatch_unknown += 1
                else:
                    mismatch = deref != target
                    counters.note_mismatch(mismatch)
                    deref_module, deref_rva = self.modules.normalize(deref)

        expectation_violated = None
        if spec.expect_post_full_hits is not None:
            expectation_violated = (
                counters.post_full_hits > spec.expect_post_full_hits
            )

        if log_allowed:
            event = {
                "event": "hit",
                "probe": spec.id,
                "module": spec.module,
                "rva": spec.rva,
                "phase": spec.phase,
                "actual_phase": actual_phase,
                "phase_policy": spec.phase,
                "full_state": full_state,
                "target": target,
                "target_module": target_module,
                "target_rva": target_rva,
                "target_key": histogram_key,
                "edx": edx,
                "edx_module": edx_module,
                "edx_rva": edx_rva,
                "esi": esi,
                "esi_module": esi_module,
                "esi_rva": esi_rva,
                "al": al,
                "eflags": eflags,
                "mismatch": mismatch,
                "deref": deref,
                "deref_module": deref_module,
                "deref_rva": deref_rva,
                "captured": captured,
                "counter": {
                    "total_hits": counters.total_hits,
                    "post_full_hits": counters.post_full_hits,
                    "logged_hits": counters.logged_hits,
                },
                "sample": counters.sample_snapshot(),
            }
            if "edi" in captured:
                event["edi"] = captured["edi"]
            if "ecx" in captured:
                event["ecx"] = captured["ecx"]
            if "return_address" in captured:
                event["return_addr"] = return_address
                event["return_module"] = return_module
                event["return_rva"] = return_rva
            if target is not None:
                event["target_is_e56"] = (
                    target_module == "engine.dll" and target_rva == 0x56E60
                )
            if expectation_violated is not None:
                event["expectation_violated"] = expectation_violated
            self._write(event)

        if counters.stats_due():
            self.emit_stats(spec, counters)
            self._write_sidecar()
        elif counters.total_hits % SIDECAR_EVERY_HITS == 0:
            # The runner may kill gdb with SIGTERM (timeout); keep a recent
            # counts snapshot on disk even when atexit/finalize never runs.
            self._write_sidecar()

    def emit_stats(self, spec, counters):
        event = {
            "event": "stats",
            "tag": "STATS",
            "probe_id": spec.id,
            "module": spec.module,
            "rva": spec.rva,
            "phase": spec.phase,
            "phase_policy": spec.phase,
            "full_state": bool(self.full_state),
            "counters": counters.snapshot(),
            "sample_limits": spec.limits.as_dict(),
        }
        if spec.histogram_eax:
            event["histogram"] = counters.histogram.snapshot(top=10)
        self._write(event)

    def snapshot_counts(self, reason="final"):
        counters = {}
        histograms = {}
        violations = []
        for spec in self.specs:
            state = self.counters[spec.id]
            counters[spec.id] = state.snapshot()
            if spec.histogram_eax:
                histograms[spec.id] = state.histogram.snapshot()
            if (
                spec.expect_post_full_hits is not None
                and state.post_full_hits > spec.expect_post_full_hits
            ):
                violations.append(
                    {
                        "probe_id": spec.id,
                        "expect_post_full_hits": spec.expect_post_full_hits,
                        "actual_post_full_hits": state.post_full_hits,
                    }
                )
        return {
            "event": "counts",
            "tag": "FINAL_COUNTS",
            "reason": reason,
            "full_state": bool(self.full_state),
            "full_state_seen": bool(self.full_state_seen),
            "counters": counters,
            "histograms": histograms,
            "expectation_violations": violations,
            "warnings": list(self.warnings),
            "install": {
                "expected_probes": len(self.specs),
                "installed_probes": len(self.installed),
                "ok": not self.failures and len(self.installed) == len(self.specs),
            },
        }

    def finalize(self, reason="final"):
        if self.finalized or self.file_handle is None:
            return
        self.finalized = True
        try:
            snapshot = self.snapshot_counts(reason)
            self._write(snapshot)
            self._write(
                {
                    "event": "run_end",
                    "ok": snapshot["install"]["ok"],
                    "expectations_ok": not snapshot["expectation_violations"],
                    "reason": reason,
                    "full_state_seen": bool(self.full_state_seen),
                    "full_state": bool(self.full_state),
                    "counters": snapshot["counters"],
                    "expectation_violations": snapshot[
                        "expectation_violations"
                    ],
                    "warnings": snapshot["warnings"],
                }
            )
        except Exception:
            pass
        finally:
            try:
                self._write_sidecar()
            except Exception:
                pass
            try:
                self.file_handle.flush()
                self.file_handle.close()
            except Exception:
                pass
            self.file_handle = None


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def _prepare_output(out_path):
    """Truncate the event log and remove stale sidecars before install.

    A failed install must not leave a previous run's JSONL behind for the
    runner to mistake as this run's evidence.
    """
    parent = os.path.dirname(os.path.abspath(out_path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8"):
        pass
    for suffix in (".counts.json", ".install.json"):
        try:
            os.unlink(out_path + suffix)
        except FileNotFoundError:
            pass
        except OSError:
            pass


def _load_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    if config.get("schema") != CONFIG_SCHEMA:
        raise ValueError(
            "unsupported config schema %r (expected %r)"
            % (config.get("schema"), CONFIG_SCHEMA)
        )
    defaults = config.get("defaults", {})
    probes = []
    seen = set()
    for raw in config.get("probes", []):
        spec = ProbeSpec(raw, defaults)
        if spec.id in seen:
            raise ValueError("duplicate probe id %r" % spec.id)
        seen.add(spec.id)
        probes.append(spec)
    if not probes:
        raise ValueError("config contains no probes")
    modules = config.get("modules") or {}
    for name in MODULE_NAMES:
        if name not in modules:
            raise ValueError("config missing module %r" % name)
    return config, probes


def _read_bases(config):
    bases = {}
    for name in MODULE_NAMES:
        meta = (config.get("modules") or {}).get(name) or {}
        env_name = meta.get("env")
        value = os.environ.get(env_name) if env_name else None
        if value:
            bases[name] = as_int(value, None)
    return bases


def main():
    if gdb is None:
        raise RuntimeError("gdb_probe.py must be executed inside gdb")
    config_path = os.environ.get("N27_PROBE_CONFIG")
    out_path = os.environ.get("N27_PROBE_OUT")
    run_id = os.environ.get("N27_PROBE_RUN_ID") or (
        "n27d19-%s-%d"
        % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), os.getpid())
    )
    if not config_path or not out_path:
        print(
            "N27_PROBE_CONFIG and N27_PROBE_OUT must be set",
            file=sys.stderr,
            flush=True,
        )
        try:
            gdb.execute("quit 1")
        except Exception:
            pass
        os._exit(1)

    try:
        _prepare_output(out_path)
    except Exception as exc:
        print(
            "N27_PROBE_OUTPUT_ERROR " + sanitize_text(exc),
            file=sys.stderr,
            flush=True,
        )
        try:
            gdb.execute("quit 1")
        except Exception:
            pass
        os._exit(1)

    # The runner sets this before the Python script; make it explicit and
    # idempotent so a manual attach cannot silently interleave threads.
    try:
        lock_mode = os.environ.get("N27_SCHEDULER_LOCKING", "off").strip().lower()
        if lock_mode not in ("on", "off", "step", "replay"):
            lock_mode = "off"
        gdb.execute("set scheduler-locking %s" % lock_mode)
    except Exception:
        print(
            "N27_PROBE_WARNING: could not set scheduler-locking on",
            file=sys.stderr,
            flush=True,
        )

    try:
        config, specs = _load_config(config_path)
    except Exception as exc:
        print(
            "N27_PROBE_CONFIG_ERROR " + sanitize_text(exc),
            file=sys.stderr,
            flush=True,
        )
        try:
            gdb.execute("quit 1")
        except Exception:
            pass
        os._exit(1)

    spans = {}
    for name in MODULE_NAMES:
        spans[name] = as_int(
            ((config.get("modules") or {}).get(name) or {}).get("fallback_span"),
            DEFAULT_SPANS[name],
        )
    modules = ModuleMap.discover(_read_bases(config), spans)
    missing = [name for name in MODULE_NAMES if modules.base(name) is None]
    if missing:
        print(
            "N27_PROBE_MODULE_BASE_MISSING " + ",".join(missing),
            file=sys.stderr,
            flush=True,
        )
        try:
            gdb.execute("quit 1")
        except Exception:
            pass
        os._exit(1)

    collector = Collector(config, specs, modules, out_path, run_id)
    collector.install()


if (
    os.environ.get("N27_PROBE_IMPORT_ONLY") != "1"
    and gdb is not None
    and __name__ == "__main__"
):
    main()
