#!/usr/bin/env python3
"""Run a VScript high-index session over a PTY and keep srcds alive.

Waits for BEGIN/TARGET/DONE, asserts target index >= 2048, prints the
server PID and run id, and does not kill the server. Exit codes:
 0 ok, 2 no DONE, 3 no TARGET, 4 target < 2048, 5 server exited.
"""
import argparse, os, pty, re, select, subprocess, sys, time, uuid
from pathlib import Path

ROOT = Path("/home/void0312/l4d2_test/cleanrun")
BIN = ROOT / "bin"
LD = f"{BIN}:{ROOT}:{ROOT/'left4dead2'/'bin'}"

p = argparse.ArgumentParser()
p.add_argument("--port", default="27021")
p.add_argument("--script", default="d50_session")
p.add_argument("--timeout", type=float, default=180)
p.add_argument("--keep", action="store_true")
a = p.parse_args()
run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
master, slave = pty.openpty()
env = dict(os.environ, LD_LIBRARY_PATH=LD)
proc = subprocess.Popen(
    ["./srcds_linux", "-game", "left4dead2", "-insecure", "-console",
     "-port", a.port, "+map", "c1m1_hotel"],
    cwd=str(ROOT), stdin=slave, stdout=slave, stderr=slave,
    env=env, start_new_session=True, close_fds=True)
os.close(slave)
buf = bytearray()
sent = False
state = {"begin": False, "target": None, "done": False}
deadline = time.time() + a.timeout
rc = 2
try:
    while time.time() < deadline:
        r, _, _ = select.select([master], [], [], 0.5)
        if r:
            try: chunk = os.read(master, 65536)
            except OSError: break
            if not chunk: break
            buf += chunk
            text = buf.decode("utf-8", "replace")
            if not sent and "Initializing Director's script" in text:
                time.sleep(0.5)
                os.write(master, b"sv_cheats 1\n")
                time.sleep(0.2)
                os.write(master, f"script_execute {a.script}\n".encode())
                sent = True
            if "D50_BEGIN" in text: state["begin"] = True
            m = re.search(r"D50_TARGET idx=(\d+)", text)
            if m: state["target"] = int(m.group(1))
            if "D50_DONE" in text: state["done"] = True
            if state["done"]: break
        if proc.poll() is not None: break
    if state["done"]:
        if state["target"] is None: rc = 3
        elif state["target"] < 2048: rc = 4
        else: rc = 0
    elif proc.poll() is not None: rc = 5
    elif state["target"] is not None: rc = 2
finally:
    print(f"RUN_ID={run_id} PID={proc.pid} PORT={a.port} SCRIPT={a.script}")
    print(f"BEGIN={state['begin']} TARGET={state['target']} DONE={state['done']} RC={rc}")
    if not a.keep:
        try: os.killpg(proc.pid, 15)
        except ProcessLookupError: pass
    os.close(master)
sys.exit(rc)
