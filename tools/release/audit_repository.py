#!/usr/bin/env python3
"""Classify tracked repository paths for the D66 information-architecture audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import re
from collections import Counter


def classify(path: str) -> tuple[str, str]:
    p = Path(path)
    parts = p.parts
    if path == ".gitignore":
        return "REFERENCE", "repository hygiene rules"
    if path in {"reports/n27d66/repository-inventory.json", "reports/n27d66/repository-inventory.md"}:
        return "GENERATED", "derived inventory, regenerated from current paths and references"
    if path in {"README.md", "README.zh-CN.md"} or parts[:1] in {("docs",), ("release",)}:
        if parts[:2] == ("docs", "assets"):
            return "GENERATED", "generated public diagrams and benchmark assets"
        return "ACTIVE", "public entry point or release documentation"
    if parts[:2] == ("tools", "release"):
        return "ACTIVE", "D66 release and audit entry point"
    if path in {"tools/linux/run_d66_serial.py", "tools/linux/run_d66_soak.py",
                "tools/linux/vscript/d66_wrap.nut", "tools/linux/d65_runtime.py",
                "tools/linux/check_d65_evidence.py", "tools/linux/run_d65_lifecycle.py"} \
            or parts[:2] == ("tools", "sourcemod"):
        return "ACTIVE", "invoked D66 verification or pinned SourceMod integration workflow"
    if parts[:2] == ("reports", "n27d66"):
        return "ACTIVE", "current D66 result"
    if parts[:2] == ("reports", "n27d65") or path.startswith("tools/linux/d65"):
        return "ACTIVE", "current D65 runtime baseline"
    if parts[:1] == ("out",) or "__pycache__" in parts:
        return "GENERATED", "local build or interpreter output"
    if path == "tools/dyn/restart_and_launch.sh":
        return "DEPRECATED", "globally restarts Steam and launches the Steam tree; replaced by bounded private-copy runner"
    if parts[:1] == ("reports",) or parts[:1] == ("data",) or parts[:2] in {
        ("tools", "n27d19"), ("tools", "n27d20"), ("tools", "windows")
    }:
        return "HISTORICAL", "immutable experiment record or data; current status is resolved by the research index"
    if parts[:1] in {( "engine",), ("manifests",), ("evidence",), ("samples",)} or parts[:1] == ("tools",):
        return "REFERENCE", "active lower-level analysis or evidence input"
    return "UNKNOWN", "no explicit D66 rule; review before changing"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument("--output", type=Path,
                    default=Path(__file__).resolve().parents[2] / "reports/n27d66/repository-inventory.json")
    args = ap.parse_args()
    raw = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=args.root,
                         capture_output=True, check=True).stdout.split(b"\0")
    rows = []
    names = sorted({item.decode() for item in raw if item})
    references = {name: set() for name in names}
    for name in names:
        source = args.root/name
        if source.suffix not in {".md", ".py", ".sh", ".json"} or source.stat().st_size > 2_000_000 \
                or name.startswith("reports/n27d66/repository-inventory"):
            continue
        contents = source.read_text(errors="replace")
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", contents):
            if "://" in target:
                continue
            try:
                resolved = str((source.parent/target).resolve().relative_to(args.root.resolve()))
                if resolved in references:
                    references[resolved].add(name)
            except ValueError:
                pass
        for target in re.findall(r"(?:tools|reports|data|manifests|engine)/[A-Za-z0-9_./-]+", contents):
            if target in references and target != name:
                references[target].add(name)
    for path in names:
        category, reason = classify(path)
        rows.append({"path": path, "category": category, "reason": reason,
                     "referenced_by": sorted(references[path])})
    counts = Counter(r["category"] for r in rows)
    output = {"schema": "l4d2-d66-repository-inventory-v1", "counts": dict(sorted(counts.items())), "files": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = args.output.with_suffix(".md")
    lines = ["# D66 repository inventory", "", "Classification uses actual public entry points, references and provenance rules; D/Dates alone are not treated as a deletion signal.", "", "| Category | Files | Meaning |", "| --- | ---: | --- |"]
    meanings = {
        "ACTIVE": "current user or developer entry point",
        "REFERENCE": "retained active analysis input or lower-level tool",
        "HISTORICAL": "prior experiment retained for auditability",
        "DEPRECATED": "retained but no longer a public workflow",
        "GENERATED": "derived build or visual output",
        "UNKNOWN": "requires review before removal or refactor",
    }
    for category in ["ACTIVE", "REFERENCE", "HISTORICAL", "DEPRECATED", "GENERATED", "UNKNOWN"]:
        lines.append(f"| `{category}` | {counts.get(category, 0)} | {meanings[category]} |")
    lines += ["", "## Unknown paths", ""]
    unknown = [r["path"] for r in rows if r["category"] == "UNKNOWN"]
    lines += [f"- `{p}`" for p in unknown] or ["None."]
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "markdown": str(md), "counts": dict(counts)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
