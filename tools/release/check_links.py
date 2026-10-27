#!/usr/bin/env python3
"""Check relative Markdown links without fetching external URLs."""
from __future__ import annotations

import argparse
from pathlib import Path
import re


LINK = re.compile(r"(?<![A-Za-z0-9_])\[[^\]]+\]\(([^)\s]+)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = ap.parse_args()
    failures = []
    checked = 0
    for doc in args.root.rglob("*.md"):
        if ".git" in doc.parts:
            continue
        for raw in LINK.findall(doc.read_text(encoding="utf-8", errors="replace")):
            if raw.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = raw.split("#", 1)[0]
            if not target:
                continue
            checked += 1
            if not (doc.parent / target).exists():
                failures.append(f"{doc.relative_to(args.root)} -> {raw}")
    print(f"checked relative Markdown links: {checked}")
    if failures:
        print("broken links:")
        print("\n".join(failures))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
