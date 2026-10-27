#!/usr/bin/env python3
"""Exercise in-place install, failure handling, and restore on a module fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from install import load_manifest, validate_source


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--game", type=Path, required=True)
    ap.add_argument("--write", type=Path, required=True)
    a = ap.parse_args()
    manifest = load_manifest(a.manifest)
    validate_source(a.game, manifest)
    installer = Path(__file__).with_name("install.py")
    steps = []

    with tempfile.TemporaryDirectory(prefix="d66-install-exercise-") as td:
        game = Path(td) / "game"
        for item in manifest["files"]:
            path = game / item["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(a.game / item["path"], path)
        initial = {item["path"]: digest(game / item["path"])
                   for item in manifest["files"]}

        def call(name, args, ok=True):
            proc = subprocess.run([sys.executable, str(installer), *map(str, args)],
                                  capture_output=True, text=True)
            if (proc.returncode == 0) != ok:
                raise RuntimeError(f"{name}: {proc.stdout}\n{proc.stderr}")
            steps.append({"name": name, "result": "PASS", "exit_code": proc.returncode})

        common = ["--manifest", a.manifest.resolve(), "--game", game]
        call("source identities and architecture", ["check", *common])
        call("dry-run", ["install", *common, "--dry-run"])
        if any((game / item["path"]).with_name(
                (game / item["path"]).name + ".l4d2-4096.bak").exists()
               for item in manifest["files"]):
            raise RuntimeError("dry-run created a backup")

        call("in-place install", ["install", *common])
        for item in manifest["files"]:
            path = game / item["path"]
            if digest(path) != item["output_sha256"]:
                raise RuntimeError(f"patched hash mismatch: {item['path']}")
            backup = path.with_name(path.name + ".l4d2-4096.bak")
            if digest(backup) != item["source_sha256"]:
                raise RuntimeError(f"backup hash mismatch: {item['path']}")
        receipt = game / "l4d2-4096-install.json"
        call("patched identities", ["check", *common])
        call("restore in place", ["restore", "--receipt", receipt])
        if initial != {item["path"]: digest(game / item["path"])
                       for item in manifest["files"]}:
            raise RuntimeError("restore did not recover original modules")

        bad = json.loads(json.dumps(manifest))
        bad["files"][0]["output_sha256"] = "0" * 64
        badpath = Path(td) / "bad.json"
        badpath.write_text(json.dumps(bad), encoding="utf-8")
        call("failed candidate leaves source unchanged", ["install", "--manifest", badpath,
                                                           "--game", game], False)
        if initial != {item["path"]: digest(game / item["path"])
                       for item in manifest["files"]}:
            raise RuntimeError("failed install changed source modules")

        first = game / manifest["files"][0]["path"]
        original = first.read_bytes()
        first.write_bytes(original + b"X")
        call("unsupported source rejected", ["check", *common], False)
        first.write_bytes(original)
        parent = first.parent
        real = parent.with_name(parent.name + "-real")
        parent.rename(real)
        parent.symlink_to(real, target_is_directory=True)
        call("symlinked module parent rejected", ["check", *common], False)
        parent.unlink()
        real.rename(parent)

        final = {item["path"]: digest(game / item["path"])
                 for item in manifest["files"]}
        if initial != final:
            raise RuntimeError("source fixture changed")

    record = {"result": "PASS", "platform": manifest["platform"],
              "fixture": "module-only original fixture; no full game copy",
              "steps": steps, "original_modules_unchanged": True,
              "installer_sha256": hashlib.sha256(installer.read_bytes()).hexdigest()}
    a.write.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
