#!/usr/bin/env python3
"""Make a Windows private-copy kit from exact source and D62 candidate images.

Ships byte differences, never whole Valve DLLs. Every hunk and final image is
verified here; the Windows installer repeats source/byte/output assertions.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import zipfile

REPO = Path(__file__).resolve().parent.parent
TARGETS = {
    'bin/engine.dll': ('out/engine.4096.13bit.baselines.dll', '48329969eaaedee94d011957d81cf53b5a06d8c8098a5e548a7e741309994bd9'),
    'left4dead2/bin/client.dll': ('out/client.4096.dll', '3e5c3f2ee98c2bfa3f3672c654f7ae8b3ae401cc437a08ae1abbe57a6d363943'),
    'left4dead2.exe': (None, 'c1007187e05ed681173b1c44c043980edf72dfcb2183ad90ec8e6d874d1b14e3'),
}
SOURCES = {
    'bin/engine.dll': '8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86',
    'left4dead2/bin/client.dll': 'c0a8e1e88f7312db11bcfd4b0ec574d224a34b2d9a615d6088b28335eeb4af1f',
    'left4dead2.exe': TARGETS['left4dead2.exe'][1],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_image(relative, source, target):
    padded = source + bytes(max(0, len(target) - len(source)))
    hunks = []
    i = 0
    while i < len(target):
        if padded[i] == target[i]:
            i += 1
            continue
        start = i
        while i < len(target) and padded[i] != target[i]:
            i += 1
        hunks.append(dict(offset=start, old=base64.b64encode(padded[start:i]).decode(),
                          new=base64.b64encode(target[start:i]).decode()))
    # Exercise precisely the operation performed by PowerShell.
    check = bytearray(padded[:len(target)])
    for hunk in hunks:
        offset = hunk['offset']
        old, new = (base64.b64decode(hunk[k]) for k in ['old', 'new'])
        assert check[offset:offset+len(old)] == old
        check[offset:offset+len(new)] = new
    assert bytes(check) == target
    return dict(path=relative.replace('/', '\\'), source_sha256=sha(source),
                output_sha256=sha(target), output_size=len(target), hunks=hunks)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game', type=Path, required=True, help='read-only original Steam game root')
    ap.add_argument('--out', type=Path, default=REPO/'out/L4D2-4096-D63-Windows.zip')
    a = ap.parse_args()
    images = []
    for relative, (candidate, expected) in TARGETS.items():
        source = (a.game/relative).read_bytes()
        if sha(source) != SOURCES[relative]:
            raise SystemExit(f'original SHA mismatch: {relative}')
        target = (REPO/candidate).read_bytes() if candidate else source
        if sha(target) != expected:
            raise SystemExit(f'candidate SHA mismatch: {relative}')
        images.append(make_image(relative, source, target))
    manifest = dict(schema='l4d2-private-copy-delta-v1', images=images)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('patches.json', json.dumps(manifest, indent=2)+'\n')
        for name in ['Join-D63.cmd', 'Join-D63.ps1', 'Capture-D63.cmd', 'Capture-D63.ps1', '加入说明.txt']:
            text = (REPO/'tools/windows'/name).read_text()
            archive.writestr(name, (b'\xef\xbb\xbf' if name.endswith(('.ps1', '.txt')) else b'') + text.replace('\n', '\r\n').encode())
    print(json.dumps(dict(path=str(a.out), sha256=sha(a.out.read_bytes()), size=a.out.stat().st_size,
                          images=[{k:v for k,v in x.items() if k != 'hunks'} for x in images]), indent=2))


if __name__ == '__main__':
    main()
