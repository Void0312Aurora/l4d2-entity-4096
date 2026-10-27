#!/usr/bin/env python3
"""Build byte-delta manifests for the supported private-copy targets.

The repository does not ship Valve binaries.  This tool is run by the
maintainer with a verified original and a verified candidate image and emits
only the old/new byte hunks plus their identities.  ``install.py`` consumes
the resulting JSON on a user's machine.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path


SCHEMA = "l4d2-4096-release-v1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hunks(source: bytes, target: bytes) -> list[dict]:
    """Return non-overlapping replacement hunks in source-coordinate order."""
    common = min(len(source), len(target))
    spans = []
    i = 0
    while i < common:
        if source[i] == target[i]:
            i += 1
            continue
        start = i
        i += 1
        while i < common and source[i] != target[i]:
            i += 1
        # Nearby four-byte relocations are cheaper and easier to audit as one
        # hunk. The unchanged gap is still checked byte-for-byte.
        while i < common:
            next_diff = i
            while next_diff < common and source[next_diff] == target[next_diff]:
                next_diff += 1
            if next_diff >= common or next_diff - i > 8:
                break
            i = next_diff + 1
        spans.append((start, i))
    if len(source) != len(target):
        # A size change is represented by a final insertion or truncation;
        # all overlapping bytes still receive ordinary sparse hunks.
        spans.append((common, len(source)))

    out = []
    for start, end in spans:
        new_end = end if start < common else len(target)
        old = source[start:end]
        new = target[start:new_end]
        out.append({
            "offset": start,
            "old_b64": base64.b64encode(old).decode("ascii"),
            "new_b64": base64.b64encode(new).decode("ascii"),
        })
    return out


def image(rel: str, source_path: Path, target_path: Path) -> dict:
    source = source_path.read_bytes()
    target = target_path.read_bytes()
    record = {
        "path": rel.replace("\\", "/"),
        "source_sha256": sha(source),
        "source_size": len(source),
        "output_sha256": sha(target),
        "output_size": len(target),
        "hunks": hunks(source, target),
    }
    # Exercise the same patch operation used by the installer before writing
    # the manifest.  A bad maintainer candidate must fail here.
    work = source
    for h in reversed(record["hunks"]):
        old = base64.b64decode(h["old_b64"])
        new = base64.b64decode(h["new_b64"])
        off = h["offset"]
        if work[off:off + len(old)] != old:
            raise SystemExit(f"generated hunk does not match {rel} at {off}")
        work = work[:off] + new + work[off + len(old):]
    if work != target:
        raise SystemExit(f"generated manifest does not reproduce {rel}")
    record["hunk_count"] = len(record["hunks"])
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", required=True, choices=["windows-client", "linux-server"])
    ap.add_argument("--source-root", type=Path, required=True,
                    help="verified original game root")
    ap.add_argument("--target-root", type=Path, required=True,
                    help="verified patched candidate root")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    if a.platform == "windows-client":
        paths = ["bin/engine.dll", "left4dead2/bin/client.dll"]
        notes = [
            "Windows client image; also usable by a Proton private copy.",
            "The matching patched Linux dedicated server is a separate manifest.",
        ]
    else:
        paths = ["bin/engine_srv.so", "left4dead2/bin/server_srv.so"]
        notes = [
            "Linux dedicated server image.",
            "Windows native dedicated server is not part of the tested support set.",
        ]

    files = []
    for rel in paths:
        src = a.source_root / rel
        dst = a.target_root / rel
        if src.is_symlink() or dst.is_symlink():
            raise SystemExit(f"refusing symlinked module: {rel}")
        if not src.is_file() or not dst.is_file():
            raise SystemExit(f"missing module: {rel}")
        files.append(image(rel, src, dst))

    record = {
        "schema": SCHEMA,
        "build": "23990068",
        "platform": a.platform,
        "files": files,
        "notes": notes,
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "manifest": str(a.output),
        "platform": a.platform,
        "files": [{"path": f["path"], "hunks": f["hunk_count"],
                    "source_sha256": f["source_sha256"],
                    "output_sha256": f["output_sha256"]} for f in files],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
