#!/usr/bin/env python3
"""Run the D66 release-candidate gate without touching a game install.

The result is deliberately layered.  It can report a valid manifest and a
complete D65 evidence record while still returning PARTIALLY_READY because
serial wraparound, long soak and multi-client coverage remain untested.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from install import patch_bytes, validate_architecture, validate_source

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
EXPECTED_D65 = "PARTIAL_WITH_CORE_P0_PASS"


def check(name: str, status: str, detail: str, **extra: object) -> dict:
    result = {"name": name, "status": status, "detail": detail}
    result.update(extra)
    return result


def load_manifest(path: Path) -> tuple[dict | None, dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("schema") == "l4d2-4096-release-v1"
        assert data.get("build") == "23990068"
        assert data.get("files")
        for f in data["files"]:
            assert len(f["source_sha256"]) == 64 and len(f["output_sha256"]) == 64
            assert f["source_size"] > 0 and f["output_size"] > 0
            assert isinstance(f["hunks"], list)
        return data, check(path.name, "PASS", "schema, build and file records are valid")
    except Exception as exc:
        return None, check(path.name, "FAIL", f"invalid release manifest: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", action="append", type=Path, required=True)
    ap.add_argument("--evidence-root", type=Path,
                    default=Path("runs/d65"))
    ap.add_argument("--validation", type=Path,
                    default=REPO / "reports/n27d65/validation.json")
    ap.add_argument("--serial-results", type=Path,
                    help="D66 network-serial result JSON, when a real run completed")
    ap.add_argument("--long-results", type=Path,
                    help="D66 bounded-soak result JSON, when a real run completed")
    ap.add_argument("--source", action="append", default=[], metavar="PLATFORM=ROOT",
                    help="original module tree for independent byte-delta reconstruction")
    ap.add_argument("--installer-results", type=Path, action="append", default=[])
    ap.add_argument("--sourcemod-results", type=Path)
    ap.add_argument("--write", type=Path,
                    help="also write the machine-readable D66 gate result")
    args = ap.parse_args()

    checks = []
    manifests = []
    sources = dict(item.split("=", 1) for item in args.source)
    for path in args.manifest:
        data, result = load_manifest(path.resolve())
        checks.append(result)
        if data:
            manifests.append(data)
            source = sources.get(data["platform"])
            if not source:
                checks.append(check(f"{data['platform']}_reconstruction", "NOT_TESTED",
                                    "supply --source PLATFORM=ROOT for raw byte assertions"))
            else:
                try:
                    root = Path(source)
                    validate_source(root, data)
                    with tempfile.TemporaryDirectory(prefix="d66-build-check-") as temp:
                        for f in data["files"]:
                            candidate = Path(temp)/Path(f["path"]).name
                            candidate.write_bytes(patch_bytes((root/f["path"]).read_bytes(), f))
                            validate_architecture(candidate, data["platform"])
                    checks.append(check(f"{data['platform']}_reconstruction", "PASS",
                                        "source identities, every old-byte hunk, output hashes and x86 structure"))
                except (Exception, SystemExit) as exc:
                    checks.append(check(f"{data['platform']}_reconstruction", "FAIL", str(exc)))

    try:
        record = json.loads(args.validation.read_text(encoding="utf-8"))
        result = record.get("result")
        if result != EXPECTED_D65:
            checks.append(check("d65_status", "FAIL", f"unexpected D65 result: {result!r}"))
        else:
            checks.append(check("d65_status", "PASS", "D65 partial status is preserved"))
        checks.append(check("d65_evidence", "PASS" if args.evidence_root.is_dir() else "FAIL",
                            "external D65 raw evidence directory exists"))
    except Exception as exc:
        checks.append(check("d65_status", "FAIL", f"cannot read D65 validation: {exc}"))

    checker = REPO / "tools/linux/check_d65_evidence.py"
    if checker.is_file() and args.validation.is_file() and args.evidence_root.is_dir():
        proc = subprocess.run([sys.executable, str(checker), str(args.validation),
                               "--evidence-root", str(args.evidence_root)],
                              capture_output=True, text=True)
        checks.append(check("d65_evidence_integrity", "PASS" if proc.returncode == 0 else "FAIL",
                            "named evidence and pinned D65 module identities" if proc.returncode == 0
                            else proc.stdout.strip()[-500:], exit_code=proc.returncode))
    else:
        checks.append(check("d65_evidence_integrity", "FAIL", "checker or evidence missing"))

    proc = subprocess.run([sys.executable, str(REPO / "tools/release/check_raw_lifecycle.py"),
                           "--evidence-root", str(args.evidence_root)], capture_output=True, text=True)
    checks.append(check("raw_lifecycle_semantics", "PASS" if proc.returncode == 0 else "FAIL",
                        "raw five-level ladder and natural 4095 lifecycle recomputation",
                        output=proc.stdout.strip(), exit_code=proc.returncode))

    tracked = subprocess.run(["git", "ls-files", "-z"], cwd=REPO,
                             capture_output=True, check=True).stdout.split(b"\0")
    tracked_names = [p.decode(errors="replace") for p in tracked if p]
    binary_names = [p for p in tracked_names
                    if p.lower().endswith((".dll", ".so", ".exe", ".dmp", ".core"))]
    checks.append(check("valve_binaries_absent", "PASS" if not binary_names else "FAIL",
                        "no complete binary artifacts are tracked" if not binary_names
                        else ", ".join(binary_names[:5]), files=binary_names))

    if manifests and all(m.get("build") == "23990068" for m in manifests):
        checks.append(check("build_binding", "PASS", "all release manifests bind build 23990068"))
    else:
        checks.append(check("build_binding", "FAIL", "manifest build binding is inconsistent"))

    serial_ok = False
    if args.serial_results:
        try:
            serial = json.loads(args.serial_results.read_text(encoding="utf-8"))
            serial_ok = bool(serial.get("network_serial_repeat_after_1024")
                             and serial.get("all_sampled_client_server_matches")
                             and serial.get("cycles", 0) >= 1024
                             and not serial.get("failures"))
            raw = subprocess.run([sys.executable, str(REPO/"tools/release/check_serial_result.py"),
                                  "--run", str(args.serial_results.parent)], capture_output=True, text=True)
            serial_ok = serial_ok and raw.returncode == 0
            checks.append(check("network_serial_wrap", "PASS" if serial_ok else "FAIL",
                                "real 1024-cycle allocator reuse result" if serial_ok
                                else "serial result failed its own assertions"))
        except Exception as exc:
            checks.append(check("network_serial_wrap", "FAIL", f"cannot read serial result: {exc}"))
    else:
        checks.append(check("network_serial_wrap", "NOT_TESTED",
                            "wire 10-bit wrap was not forced in this gate run"))
    if args.long_results:
        try:
            soak = json.loads(args.long_results.read_text(encoding="utf-8"))
            raw = subprocess.run([sys.executable, str(REPO/"tools/release/check_soak_result.py"),
                                  "--results", str(args.long_results)], capture_output=True, text=True)
            soak_ok = soak.get("result") == "PASS_BOUNDED" and not soak.get("errors") and raw.returncode == 0
            checks.append(check("bounded_soak", "PASS" if soak_ok else "FAIL",
                                "bounded soak result supplied" if soak_ok
                                else "bounded soak contains errors"))
        except Exception as exc:
            checks.append(check("bounded_soak", "FAIL", f"cannot read soak result: {exc}"))
    else:
        checks.append(check("bounded_soak", "NOT_TESTED", "no bounded soak result supplied"))
    for installer_path in args.installer_results:
        try:
            installer = json.loads(installer_path.read_text())
            ok = installer.get("result") == "PASS" and installer.get("original_modules_unchanged") \
                and len(installer.get("steps", [])) >= 9 \
                and all(s["result"] == "PASS" for s in installer["steps"]) \
                and installer.get("installer_sha256") == hashlib.sha256((HERE.parent/"install.py").read_bytes()).hexdigest()
            checks.append(check("installer_recovery_"+installer.get("platform", "unknown"), "PASS" if ok else "FAIL",
                                installer.get("fixture", "fixture not described")))
        except Exception as exc:
            checks.append(check("installer_recovery", "FAIL", str(exc)))
    if not args.installer_results:
        checks.append(check("installer_recovery", "NOT_TESTED", "no installer exercise result supplied"))
    if args.sourcemod_results:
        try:
            sm = json.loads(args.sourcemod_results.read_text())
            ok = sm.get("result") == "PASS" and all(sm.get("checks", {}).values())
            checks.append(check("sourcemod_rebuild_smoke", "PASS" if ok else "FAIL",
                                "newly rebuilt core/SDKTools/SDKHooks and probe in a private server"))
        except Exception as exc:
            checks.append(check("sourcemod_rebuild_smoke", "FAIL", str(exc)))
    else:
        checks.append(check("sourcemod_rebuild_smoke", "NOT_TESTED", "D65 acceptance does not substitute for a new-build smoke test"))
    checks.extend([
        check("internal_serial_wrap", "NOT_TESTED", "internal 15-bit wrap was not forced safely"),
        check("long_soak", "NOT_TESTED", "multi-hour soak was not run in D66"),
        check("repeated_512_map_transition", "PARTIAL", "D66 combined soak/map runs stopped on harness or visibility assertions; D65 single transition remains PASS"),
        check("multi_client", "NOT_TESTED", "multi-client work was deferred by the user; one real client tested"),
        check("full_4096_occupancy", "NOT_TESTED", "4095 boundary is not full simultaneous occupation"),
        check("windows_dedicated", "NOT_TESTED", "Windows native dedicated server has no end-to-end evidence"),
        check("windows_native_client", "NOT_TESTED", "Windows image runtime was tested through Proton only"),
        check("linux_native_client", "NOT_TESTED", "no native Linux client runtime acceptance"),
        check("arbitrary_native_extensions", "NOT_TESTED", "SourceMod acceptance remains probe-scoped"),
    ])

    failures = [c for c in checks if c["status"] == "FAIL"]
    result = "NOT_READY" if failures else "PARTIALLY_READY"
    output = {
        "stage": "D66",
        "result": result,
        "build": "23990068",
        "checks": checks,
        "manifests": [str(p.resolve().relative_to(REPO)) if p.resolve().is_relative_to(REPO)
                      else p.name for p in args.manifest],
        "evidence_root": "external D65 raw run directory (not distributed)",
        "limitations": [c["name"] for c in checks if c["status"] in {"NOT_TESTED", "PARTIAL"}],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
