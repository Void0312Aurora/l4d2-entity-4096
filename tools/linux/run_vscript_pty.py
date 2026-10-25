#!/usr/bin/env python3
"""Run a VScript command against an isolated srcds through a PTY.

The FIFO/tail-based harness was unreliable because srcds only treats a TTY
stdin as its console. This launcher owns a PTY, waits for the map script VM,
sends the cheats + script_execute commands, and captures the D37/D46 markers.
"""
import os, pty, select, signal, subprocess, sys, time
from pathlib import Path

ROOT = Path("/home/void0312/l4d2_test/cleanrun")
BIN = ROOT / "bin"
LD = f"{BIN}:{ROOT}:{ROOT/'left4dead2'/'bin'}"
PORT = sys.argv[1] if len(sys.argv) > 1 else "27021"
SCRIPT = sys.argv[2] if len(sys.argv) > 2 else "d37_batch"
TIMEOUT = float(sys.argv[3]) if len(sys.argv) > 3 else 90.0

master, slave = pty.openpty()
env = dict(os.environ, LD_LIBRARY_PATH=LD)
p = subprocess.Popen(
    ["./srcds_linux", "-game", "left4dead2", "-insecure", "-console",
     "-port", PORT, "+map", "c1m1_hotel"],
    cwd=str(ROOT), stdin=slave, stdout=slave, stderr=slave,
    env=env, start_new_session=True, close_fds=True,
)
os.close(slave)
out = bytearray()
sent = False
deadline = time.time() + TIMEOUT
try:
    while time.time() < deadline:
        r, _, _ = select.select([master], [], [], 1.0)
        if r:
            try:
                chunk = os.read(master, 65536)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
            text = out.decode("utf-8", "replace")
            if not sent and ("Initializing Director's script" in text or "Commentary: Loading" in text):
                os.write(master, b"sv_cheats 1\n")
                time.sleep(0.3)
                os.write(master, f"script_execute {SCRIPT}\n".encode())
                sent = True
            if f"D37_" in text or f"D46_" in text or f"D47_" in text:
                if "D37_BATCH" in text or "D46_" in text or "D47_" in text:
                    break
        if p.poll() is not None:
            break
finally:
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    os.close(master)

text = out.decode("utf-8", "replace")
for line in text.splitlines():
    if any(k in line for k in ("D37_", "D46_", "D47_", "AN ERROR", "FUNCTION [main")):
        print(line)
if not any(k in text for k in ("D37_", "D46_", "D47_")):
    print("NO_MARKER")
    sys.exit(2)
