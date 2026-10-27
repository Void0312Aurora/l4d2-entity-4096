#!/usr/bin/env python3
"""Install or restore the L4D2-4096 modules in the Steam game tree.

The installer changes only the files listed by the release manifest. Before
the first replacement it keeps an adjacent ``.l4d2-4096.bak`` copy of every
module, so the normal Steam game directory remains the only launch location
and restore does not require a second game installation.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile
import time


SCHEMA = "l4d2-4096-release-v1"
RECEIPT_SCHEMA = "l4d2-4096-install-receipt-v2"
RECEIPT = "l4d2-4096-install.json"
BACKUP_SUFFIX = ".l4d2-4096.bak"


def format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{value} B"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise SystemExit(f"unsupported manifest schema: {data.get('schema')!r}")
    if data.get("build") != "23990068":
        raise SystemExit("this installer is bound to L4D2 build 23990068")
    if data.get("platform") not in {"windows-client", "linux-server"}:
        raise SystemExit("manifest platform is not supported")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise SystemExit("manifest has no files")
    for item in files:
        for key in ("path", "source_sha256", "source_size", "output_sha256",
                    "output_size", "hunks"):
            if key not in item:
                raise SystemExit(f"manifest file entry misses {key}")
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise SystemExit("manifest paths must stay inside the game tree")
        prev = -1
        for hunk in item["hunks"]:
            old = base64.b64decode(hunk["old_b64"])
            base64.b64decode(hunk["new_b64"])
            if hunk["offset"] < prev:
                raise SystemExit(f"hunks are not ordered: {item['path']}")
            prev = hunk["offset"] + len(old)
    return data


def validate_architecture(path: Path, platform: str) -> None:
    with path.open("rb") as f:
        head = f.read(4096)
    if platform == "linux-server":
        if head[:6] != b"\x7fELF\x01\x01" or struct.unpack_from("<H", head, 18)[0] != 3:
            raise SystemExit(f"expected an x86 little-endian ELF module: {path}")
    else:
        if head[:2] != b"MZ":
            raise SystemExit(f"expected an x86 PE module: {path}")
        pe = struct.unpack_from("<I", head, 60)[0]
        if head[pe:pe+4] != b"PE\0\0" or struct.unpack_from("<H", head, pe+4)[0] != 0x14C:
            raise SystemExit(f"expected an x86 PE module: {path}")


def reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise SystemExit(f"refusing symlinked game module: {path}")


def reject_module_links(root: Path, relative: str) -> None:
    path = root
    for part in Path(relative).parts:
        path = path / part
        reject_symlink(path)


def backup_path(path: Path) -> Path:
    return path.with_name(path.name + BACKUP_SUFFIX)


def validate_source(game: Path, manifest: dict, progress: bool = False) -> list[dict]:
    """Verify an unpatched game tree and return source identities."""
    results = []
    total = len(manifest["files"])
    for number, item in enumerate(manifest["files"], 1):
        if progress:
            print(f"[1/2] verify source {number}/{total}: {item['path']}", flush=True)
        path = game / item["path"]
        reject_module_links(game, item["path"])
        if not path.is_file():
            raise SystemExit(f"missing required file: {path}")
        actual_size = path.stat().st_size
        actual_sha = sha(path)
        if actual_size != item["source_size"] or actual_sha != item["source_sha256"]:
            raise SystemExit(
                f"unsupported original at {item['path']}: "
                f"size={actual_size} sha256={actual_sha}; expected "
                f"size={item['source_size']} sha256={item['source_sha256']}"
            )
        validate_architecture(path, manifest["platform"])
        results.append({"path": item["path"], "source_sha256": actual_sha,
                        "source_size": actual_size})
        if progress:
            print(f"      verified {format_bytes(actual_size)}", flush=True)
    return results


def patch_bytes(blob: bytes, item: dict) -> bytes:
    pieces = []
    cursor = 0
    for hunk in item["hunks"]:
        off = int(hunk["offset"])
        old = base64.b64decode(hunk["old_b64"])
        new = base64.b64decode(hunk["new_b64"])
        if off < cursor or off > len(blob) or blob[off:off + len(old)] != old:
            raise SystemExit(f"source byte assertion failed: {item['path']} +0x{off:x}")
        pieces.extend((blob[cursor:off], new))
        cursor = off + len(old)
    pieces.append(blob[cursor:])
    out = b"".join(pieces)
    if len(out) != item["output_size"] or hashlib.sha256(out).hexdigest() != item["output_sha256"]:
        raise SystemExit(f"candidate hash assertion failed: {item['path']}")
    return out


def current_state(game: Path, manifest: dict, progress: bool = False) -> tuple[str, list[dict]]:
    """Return source, patched, or reject a mixed/unknown module state."""
    states = []
    records = []
    total = len(manifest["files"])
    for number, item in enumerate(manifest["files"], 1):
        if progress:
            print(f"[1/2] verify current {number}/{total}: {item['path']}", flush=True)
        path = game / item["path"]
        reject_module_links(game, item["path"])
        if not path.is_file():
            raise SystemExit(f"missing required file: {path}")
        actual_size = path.stat().st_size
        actual_sha = sha(path)
        if actual_size == item["source_size"] and actual_sha == item["source_sha256"]:
            state = "source"
        elif actual_size == item["output_size"] and actual_sha == item["output_sha256"]:
            state = "patched"
        else:
            raise SystemExit(
                f"unsupported current file at {item['path']}: "
                f"size={actual_size} sha256={actual_sha}"
            )
        validate_architecture(path, manifest["platform"])
        states.append(state)
        records.append({"path": item["path"], "state": state,
                        "sha256": actual_sha, "size": actual_size})
        if progress:
            print(f"      {state}: {format_bytes(actual_size)}", flush=True)
    if all(state == "source" for state in states):
        return "source", records
    if all(state == "patched" for state in states):
        return "patched", records
    raise SystemExit("mixed module state; restore or repair the listed files before installing")


def atomic_write(path: Path, data: bytes) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def ensure_backup(path: Path, item: dict) -> Path:
    backup = backup_path(path)
    reject_symlink(backup)
    if backup.exists():
        if not backup.is_file() or backup.stat().st_size != item["source_size"] or sha(backup) != item["source_sha256"]:
            raise SystemExit(f"backup does not match the release source: {backup}")
    else:
        shutil.copy2(path, backup)
        if sha(backup) != item["source_sha256"]:
            backup.unlink(missing_ok=True)
            raise SystemExit(f"backup verification failed: {backup}")
    return backup


def install(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest.resolve())
    game = args.game.resolve()
    if not game.is_dir():
        raise SystemExit(f"game root is not a directory: {game}")

    state, _ = current_state(game, manifest, progress=True)
    print(f"game:             {game}", flush=True)
    print(f"platform:         {manifest['platform']}", flush=True)
    if state == "patched":
        for item in manifest["files"]:
            ensure_backup(game / item["path"], item)
        print("already installed: release module hashes match", flush=True)
        return 0
    if args.dry_run:
        print("DRY-RUN: source verified; no files or backups were written", flush=True)
        return 0

    source_info = [{"path": item["path"], "source_sha256": item["source_sha256"],
                    "source_size": item["source_size"]} for item in manifest["files"]]
    backups = []
    candidates = []
    item_by_path = {item["path"]: item for item in manifest["files"]}
    try:
        for item in manifest["files"]:
            path = game / item["path"]
            backups.append(ensure_backup(path, item))
            candidates.append((path, item, patch_bytes(path.read_bytes(), item)))

        print(f"[2/2] patch and verify {len(candidates)} module(s)", flush=True)
        applied = []
        try:
            for path, item, candidate in candidates:
                if sha(path) != item["source_sha256"]:
                    raise SystemExit(f"source changed while preparing install: {path}")
                atomic_write(path, candidate)
                applied.append((path, item))
                print(f"      ready {item['path']}: {format_bytes(len(candidate))}", flush=True)
        except BaseException:
            for path, item in reversed(applied):
                atomic_write(path, backup_path(path).read_bytes())
            raise

        for item in manifest["files"]:
            path = game / item["path"]
            if sha(path) != item["output_sha256"]:
                raise SystemExit(f"output hash verification failed: {item['path']}")

        receipt = {
            "schema": RECEIPT_SCHEMA,
            "manifest": str(args.manifest.resolve()),
            "build": manifest["build"],
            "platform": manifest["platform"],
            "game": str(game),
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_files": source_info,
            "output_files": [{"path": i["path"], "sha256": i["output_sha256"],
                              "size": i["output_size"]} for i in manifest["files"]],
            "backup_files": [{"path": str(b.relative_to(game)).replace("\\", "/"),
                              "sha256": item["source_sha256"], "size": item["source_size"]}
                             for b, item in zip(backups, manifest["files"])],
        }
        atomic_write(game / RECEIPT, (json.dumps(receipt, indent=2) + "\n").encode())
    except BaseException:
        # Verified backups are deliberately retained if a later step fails.
        raise
    print(f"installed in place: {game}", flush=True)
    print(f"backups: {', '.join(str(b) for b in backups)}", flush=True)
    print(f"receipt: {game / RECEIPT}", flush=True)
    return 0


def restore(args: argparse.Namespace) -> int:
    receipt_path = args.receipt.resolve()
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    if data.get("schema") != RECEIPT_SCHEMA:
        raise SystemExit("unsupported install receipt (expected an in-place install receipt)")
    game = Path(data["game"]).resolve()
    if receipt_path != game / RECEIPT:
        raise SystemExit("receipt must be in the patched game directory")
    manifest = load_manifest(Path(data["manifest"]).resolve())
    state, _ = current_state(game, manifest)
    if state == "source":
        print("already restored: source module hashes match", flush=True)
        return 0
    for item in manifest["files"]:
        path = game / item["path"]
        backup = backup_path(path)
        if not backup.is_file() or sha(backup) != item["source_sha256"]:
            raise SystemExit(f"backup hash mismatch or missing: {backup}")
        atomic_write(path, backup.read_bytes())
        if sha(path) != item["source_sha256"]:
            raise SystemExit(f"restore verification failed: {item['path']}")
        print(f"restored {item['path']}", flush=True)
    print(f"restored original modules in place: {game}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("check", "install"):
        p = sub.add_parser(name, help="check or install the release modules in the game tree")
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--game", type=Path, required=True)
        if name == "install":
            p.add_argument("--dry-run", action="store_true",
                           help="verify the source without creating backups or changing files")
    p = sub.add_parser("restore", help="restore the .l4d2-4096.bak module backups")
    p.add_argument("--receipt", type=Path, required=True)
    args = ap.parse_args()
    if args.command == "check":
        m = load_manifest(args.manifest.resolve())
        state, _ = current_state(args.game.resolve(), m)
        if state == "source":
            print("PASS: original file identities match the release manifest")
        else:
            print("PASS: patched file identities match the release manifest")
        return 0
    if args.command == "install":
        return install(args)
    return restore(args)


if __name__ == "__main__":
    raise SystemExit(main())
