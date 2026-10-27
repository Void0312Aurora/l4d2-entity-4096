#!/usr/bin/env python3
"""Exercise install/failure/restore using a temporary module-only fixture."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from install import load_manifest, validate_source


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--game",type=Path,required=True)
    ap.add_argument("--write",type=Path,required=True)
    a=ap.parse_args()
    manifest=load_manifest(a.manifest)
    validate_source(a.game,manifest)
    installer=Path(__file__).with_name("install.py")
    steps=[]
    with tempfile.TemporaryDirectory(prefix="d66-install-exercise-") as td:
        base=Path(td); game=base/"source";target=base/"private"
        for f in manifest["files"]:
            p=game/f["path"];p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(a.game/f["path"],p)
        initial={f["path"]:hashlib.sha256((game/f["path"]).read_bytes()).hexdigest() for f in manifest["files"]}
        def call(name,args,ok=True):
            proc=subprocess.run([sys.executable,str(installer),*map(str,args)],capture_output=True,text=True)
            if (proc.returncode==0) != ok:
                raise RuntimeError(f"{name}: {proc.stdout}\n{proc.stderr}")
            steps.append({"name":name,"result":"PASS","exit_code":proc.returncode})
        common=["--manifest",a.manifest.resolve(),"--game",game]
        call("source identities and architecture",["check",*common])
        call("dry-run",["install",*common,"--target",target,"--dry-run"])
        if target.exists(): raise RuntimeError("dry-run created a target")
        call("new private copy",["install",*common,"--target",target])
        (target/"sentinel.txt").write_text("preserve existing private content")
        call("replace with backup",["install",*common,"--target",target,"--replace"])
        receipt=target/"l4d2-4096-install.json"
        backup=Path(json.loads(receipt.read_text())["backup"])
        if not (backup/"sentinel.txt").is_file(): raise RuntimeError("backup lost private content")
        call("restore verified backup",["restore","--receipt",receipt])
        if not (target/"sentinel.txt").is_file(): raise RuntimeError("restore lost private content")
        bad=json.loads(json.dumps(manifest));bad["files"][0]["output_sha256"]="0"*64
        badpath=base/"bad.json";badpath.write_text(json.dumps(bad))
        call("failed patch keeps old target",["install","--manifest",badpath,"--game",game,
                                              "--target",target,"--replace"],False)
        if not (target/"sentinel.txt").is_file() or list(base.glob(".private.*")):
            raise RuntimeError("failed install left incomplete output")
        call("remove newly created copy",["restore","--receipt",receipt,"--remove-created"])
        if target.exists(): raise RuntimeError("created target was not removed")
        first=game/manifest["files"][0]["path"];original=first.read_bytes()
        first.write_bytes(original+b"X")
        call("unsupported source rejected",["check",*common],False)
        first.write_bytes(original)
        # Parent-directory links are significant: following them could write
        # through the private copy back into the source module tree.
        parent=first.parent;real=parent.with_name(parent.name+"-real")
        parent.rename(real);parent.symlink_to(real,target_is_directory=True)
        call("symlinked module parent rejected",["check",*common],False)
        parent.unlink();real.rename(parent)
        final={f["path"]:hashlib.sha256((game/f["path"]).read_bytes()).hexdigest() for f in manifest["files"]}
        if initial != final: raise RuntimeError("source fixture changed")
    record={"result":"PASS","platform":manifest["platform"],
            "fixture":"module-only original fixture; not a full game installation",
            "steps":steps,"original_modules_unchanged":True,
            "installer_sha256":hashlib.sha256(installer.read_bytes()).hexdigest()}
    a.write.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
