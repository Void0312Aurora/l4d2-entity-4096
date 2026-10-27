#!/usr/bin/env python3
"""Expose D65 observer/one-shot boundary RPCs for an owned isolated server.

Use the Python environment containing Frida. The Unix socket is mode 0600.
Lists request capture; {"op":"arm","index":4095} arms the optional factory hook.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import time

import frida

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('pid', type=int)
ap.add_argument('session', type=Path)
ap.add_argument('--boundary', action='store_true')
a = ap.parse_args()
meta = json.loads((a.session/'session.json').read_text())
cmd = Path(f'/proc/{a.pid}/cmdline').read_bytes().split(b'\0')
if meta['pid'] != a.pid or any(p in cmd for p in [b'27073', b'27074']):
    raise SystemExit('owned private server identity mismatch')
attached = frida.attach(a.pid)
log = (a.session/'frida.jsonl').open('a', buffering=1)
scripts = []
def message(m, data):
    log.write(json.dumps(dict(time=time.time(), **m))+'\n')
for name in ['d65_observe.js'] + (['d65_boundary.js'] if a.boundary else []):
    path = Path(__file__).with_name(name)
    script = attached.create_script(path.read_text())
    script.on('message', message)
    script.load()
    scripts.append(script)
    message(dict(type='script_identity', name=name,
                 sha256=hashlib.sha256(path.read_bytes()).hexdigest()), None)
sock = socket.socket(socket.AF_UNIX)
path = a.session/'frida.sock'
path.unlink(missing_ok=True)
sock.bind(str(path)); os.chmod(path, 0o600); sock.listen(4)
attached.on('detached', lambda *args: sock.close())
try:
    while True:
        c, _ = sock.accept()
        with c:
            c.settimeout(5)
            try:
                q = json.loads(c.recv(65536))
                if isinstance(q, list):
                    result = scripts[0].exports_sync.capture(q)
                elif a.boundary and q.get('op') == 'arm':
                    result = scripts[1].exports_sync.arm(q['index'])
                else:
                    raise ValueError('unknown request')
                c.sendall(json.dumps(result).encode())
            except Exception as e:
                c.sendall(json.dumps(dict(error=str(e))).encode())
finally:
    path.unlink(missing_ok=True)
    log.close()
