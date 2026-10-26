#!/usr/bin/env python3
"""Reproduce the integrated Linux high-index engine and transmit game module."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('out/linux'))
    ap.add_argument('--server', type=Path,
                    default=Path('/home/void0312/l4d2_server/left4dead2/bin/server_srv.so'))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    here = Path(__file__).resolve().parent

    def run(name, *args):
        subprocess.run([sys.executable, str(here/name), *map(str, args)], check=True)

    run('build_n27_4096.py', a.out/'capacity.so')
    run('patch_n27_13bit.py', a.out/'capacity.so', a.out/'wire.so')
    run('patch_snapshot_stack.py', a.out/'wire.so', a.out/'snapshot.so')
    run('patch_transmit_limits.py', 'engine', a.out/'snapshot.so', a.out/'transmit.so')
    run('patch_snapshot_cache.py', a.out/'transmit.so', a.out/'engine_srv.so')
    run('patch_transmit_limits.py', 'server', a.server, a.out/'server_transmit.so')
    run('patch_entitylist_linux.py', a.out/'server_transmit.so', a.out/'server_srv.so')
    identities = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(a.out.glob('*.so'))}
    (a.out/'sha256.json').write_text(json.dumps(identities, indent=2)+'\n')
    print(json.dumps(identities, indent=2))


if __name__ == '__main__':
    main()
