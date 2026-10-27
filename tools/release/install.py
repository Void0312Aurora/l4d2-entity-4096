#!/usr/bin/env python3
"""Install or restore an L4D2-4096 private copy from a byte-delta manifest.

The original game tree is read-only.  ``install`` creates a private home-directory
private copy unless ``--target`` names another destination.  It validates
every source hash before copying, patches temporary files, verifies the final
hashes, and only then swaps the destination into place.  ``restore`` uses the
receipt written by install and never needs IDA, GDB, or a hex editor.
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
MARKER = ".l4d2-4096-private-copy"
RECEIPT = "l4d2-4096-install.json"


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
        for h in item["hunks"]:
            if h["offset"] < prev:
                raise SystemExit(f"hunks are not ordered: {item['path']}")
            prev = h["offset"] + len(base64.b64decode(h["old_b64"]))
            base64.b64decode(h["old_b64"])
            base64.b64decode(h["new_b64"])
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
        if head[pe:pe+4] != b"PE\0\0" or struct.unpack_from("<H", head, pe+4)[0] != 0x14c:
            raise SystemExit(f"expected an x86 PE module: {path}")


def reject_symlink(path: Path) -> None:
    if path.is_symlink():
        raise SystemExit(f"refusing symlinked game module: {path}")


def reject_module_links(root: Path, relative: str) -> None:
    path = root
    for part in Path(relative).parts:
        path = path/part
        reject_symlink(path)


def validate_source(game: Path, manifest: dict) -> list[dict]:
    results = []
    for item in manifest["files"]:
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
    return results


def patch_bytes(blob: bytes, item: dict) -> bytes:
    pieces = []
    cursor = 0
    # Hunk coordinates refer to the source, including insertions/truncations.
    for h in item["hunks"]:
        off = int(h["offset"])
        old = base64.b64decode(h["old_b64"])
        new = base64.b64decode(h["new_b64"])
        if off < cursor or off > len(blob) or blob[off:off + len(old)] != old:
            raise SystemExit(f"source byte assertion failed: {item['path']} +0x{off:x}")
        pieces.extend((blob[cursor:off], new))
        cursor = off + len(old)
    pieces.append(blob[cursor:])
    out = b"".join(pieces)
    if len(out) != item["output_size"] or hashlib.sha256(out).hexdigest() != item["output_sha256"]:
        raise SystemExit(f"candidate hash assertion failed: {item['path']}")
    return out


def is_under(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def private_default(game: Path) -> Path:
    return Path.home() / f"{game.name}-l4d2-4096"


def install(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest.resolve())
    game = args.game.resolve()
    if not game.is_dir():
        raise SystemExit(f"game root is not a directory: {game}")
    target = (args.target or private_default(game)).resolve()
    if target == game or is_under(target, game) or is_under(game, target):
        raise SystemExit("target must be a separate sibling/private tree")
    if ".steam" in game.parts and target == game:
        raise SystemExit("refusing to modify a Steam library")

    source_info = validate_source(game, manifest)
    existing = target.exists()
    if existing:
        if not target.is_dir() or not (target / MARKER).is_file():
            raise SystemExit(f"existing target is not a marked private copy: {target}")
        if not args.replace:
            raise SystemExit(f"target exists; pass --replace after checking it: {target}")
    destination_parent = target.parent
    print(f"source verified: {game}")
    print(f"private target:  {target}")
    print(f"platform:        {manifest['platform']}")
    for item in manifest["files"]:
        print(f"  {item['path']}: {item['source_sha256'][:12]} -> {item['output_sha256'][:12]}")
    if args.dry_run:
        print("DRY-RUN: no files copied or modified")
        return 0

    destination_parent.mkdir(parents=True, exist_ok=True)
    backup = None
    backup_files = []
    if existing:
        for item in manifest["files"]:
            prior = target / item["path"]
            reject_module_links(target, item["path"])
            backup_files.append({"path": item["path"], "sha256": sha(prior)})
    temp = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=str(destination_parent)))
    try:
        shutil.rmtree(temp)
        shutil.copytree(game, temp, symlinks=True)
        reject_symlink(temp/MARKER)
        reject_symlink(temp/RECEIPT)
        (temp / MARKER).write_text(
            f"L4D2-4096 private copy\nbuild={manifest['build']}\nplatform={manifest['platform']}\n",
            encoding="ascii",
        )
        for item in manifest["files"]:
            path = temp / item["path"]
            reject_module_links(temp, item["path"])
            path.write_bytes(patch_bytes(path.read_bytes(), item))
            validate_architecture(path, manifest["platform"])

        receipt = {
            "schema": "l4d2-4096-install-receipt-v1",
            "manifest": str(args.manifest.resolve()),
            "build": manifest["build"],
            "platform": manifest["platform"],
            "source": str(game),
            "target": str(target),
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_files": source_info,
            "output_files": [{"path": i["path"], "sha256": i["output_sha256"],
                              "size": i["output_size"]} for i in manifest["files"]],
            "backup": None,
            "backup_files": backup_files,
            "created_new_target": not existing,
        }
        (temp / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if existing:
            backup = target.with_name(target.name + f".backup-{time.strftime('%Y%m%d-%H%M%S')}")
            if backup.exists():
                raise SystemExit(f"backup path already exists: {backup}")
            target.rename(backup)
            receipt["backup"] = str(backup)
            (temp / RECEIPT).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        temp.rename(target)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        if backup and backup.exists() and not target.exists():
            backup.rename(target)
        raise
    print(f"installed private copy: {target}")
    print(f"receipt: {target / RECEIPT}")
    return 0


def restore(args: argparse.Namespace) -> int:
    receipt_path = args.receipt.resolve()
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    if data.get("schema") != "l4d2-4096-install-receipt-v1":
        raise SystemExit("unsupported install receipt")
    target = Path(data["target"]).resolve()
    if receipt_path != target / RECEIPT:
        raise SystemExit("receipt must be inside its marked target")
    if not target.is_dir() or not (target / MARKER).is_file():
        raise SystemExit(f"marked private target not found: {target}")
    backup = Path(data["backup"]).resolve() if data.get("backup") else None
    if backup:
        if not backup.is_dir():
            raise SystemExit(f"backup is missing: {backup}")
        if not data.get("backup_files"):
            raise SystemExit("receipt has no backup hashes")
        for item in data["backup_files"]:
            if sha(backup / item["path"]) != item["sha256"]:
                raise SystemExit(f"backup hash mismatch: {item['path']}")
        quarantine = target.with_name(target.name + ".uninstalled")
        if quarantine.exists():
            raise SystemExit(f"quarantine path already exists: {quarantine}")
        target.rename(quarantine)
        try:
            backup.rename(target)
        except BaseException:
            quarantine.rename(target)
            raise
        shutil.rmtree(quarantine)
        print(f"restored previous private copy: {target}")
    else:
        if not data.get("created_new_target"):
            raise SystemExit("receipt has no backup and does not describe a new target")
        if not args.remove_created:
            raise SystemExit("this install created the target; pass --remove-created to delete it")
        shutil.rmtree(target)
        print(f"removed created private copy: {target}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("check", "install"):
        p = sub.add_parser(name, help="validate the original or install a private copy")
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--game", type=Path, required=True)
        if name == "install":
            p.add_argument("--target", type=Path)
            p.add_argument("--replace", action="store_true",
                           help="replace an existing marked private copy after backup")
            p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("restore", help="restore a receipt's backup or remove a new private copy")
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--remove-created", action="store_true")
    args = ap.parse_args()
    if args.command == "check":
        m = load_manifest(args.manifest.resolve())
        validate_source(args.game.resolve(), m)
        print("PASS: original file identities match the release manifest")
        return 0
    if args.command == "install":
        return install(args)
    return restore(args)


if __name__ == "__main__":
    raise SystemExit(main())
