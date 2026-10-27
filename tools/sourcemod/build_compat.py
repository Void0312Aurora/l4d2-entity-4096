#!/usr/bin/env python3
"""Build the pinned Linux x86 SourceMod compatibility package, outside Steam."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

PINS = {
    "source": "3808e21eb842d8598cc8351a341dcbe661d21b58",
    "metamod": "cb47755826fad1483291e5dc00222aa64303d12f",
    "sdk": "2a31cd007b2d7d2f964dc093eedcf7a812cf9dd6",
}


def git(path, *args):
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in PINS:
        ap.add_argument(f"--{name}", type=Path, required=True)
    ap.add_argument("--build", type=Path, required=True)
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    for name, pin in PINS.items():
        path = getattr(a, name).resolve()
        setattr(a, name, path)
        if git(path, "rev-parse", "HEAD") != pin:
            raise SystemExit(f"{name}: expected commit {pin}")
        changes = git(path, "diff", "HEAD", "--name-only").splitlines()
        if changes and not (name == "sdk" and changes == ["public/const.h"]):
            raise SystemExit(f"{name}: unexpected tracked changes: {changes}")
        subs = git(path, "submodule", "status", "--recursive")
        if any(line.startswith(("-", "+", "U")) for line in subs.splitlines()):
            raise SystemExit(f"{name}: submodules must match the pinned gitlinks")
    if a.sdk.name != "hl2sdk-l4d2":
        raise SystemExit("SDK directory must be named hl2sdk-l4d2 for upstream discovery")
    header = a.sdk/"public/const.h"
    original = git(a.sdk, "show", "HEAD:public/const.h")
    expected, n = re.subn(r"(#define\s+MAX_EDICT_BITS\s+)11\b", r"\g<1>12", original)
    if n != 1 or header.read_text().rstrip() not in {original.rstrip(), expected.rstrip()}:
        raise SystemExit("SDK header differs beyond the single MAX_EDICT_BITS change")
    print("PASS: SourceMod, Metamod, SDK and recursive submodule identities")
    if a.check_only:
        return 0
    header.write_text(expected + "\n")
    a.build = a.build.resolve()
    a.build.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(a.source/"configure.py"), "--sdks=l4d2", "--targets=x86",
                    "--enable-optimize", "--no-mysql", "--hl2sdk-root", str(a.sdk.parent),
                    "--mms-path", str(a.metamod)], cwd=a.build, check=True)
    subprocess.run([sys.executable, "-c", "from ambuild2.run import cli_run; cli_run()"],
                   cwd=a.build, check=True)
    package = a.build/"package/addons/sourcemod"
    here = Path(__file__).resolve().parent
    compiler = package/"scripting/spcomp"
    probe = package/"plugins/d65_probe.smx"
    subprocess.run([str(compiler), str(here/"d65_probe.sp"),
                    "-i"+str(package/"scripting/include"), "-o"+str(probe)], check=True)
    override = package/"gamedata/sdkhooks.games/custom/d65-entitylisteners.txt"
    override.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(here/"d65-entitylisteners.txt", override)
    artifacts = ["bin/sourcemod.2.l4d2.so", "extensions/sdktools.ext.2.l4d2.so",
                 "extensions/sdkhooks.ext.2.l4d2.so", "plugins/d65_probe.smx"]
    record = {"sources": PINS, "scope": "Linux x86 core, SDKTools, SDKHooks and probe",
              "artifacts": {p: hashlib.sha256((package/p).read_bytes()).hexdigest() for p in artifacts}}
    (a.build/"l4d2-4096-compat.json").write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
