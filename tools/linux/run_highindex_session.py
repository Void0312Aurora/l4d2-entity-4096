#!/usr/bin/env python3
"""Run a VScript high-index session over a PTY and keep srcds alive.

Waits for BEGIN/TARGET/ALIVE/DONE, asserts the target is alive and its index
is >= 2048, prints the server PID and run id, and does not kill the server.
Exit codes: 0 ok, 2 no DONE, 3 no TARGET, 4 target < 2048, 5 server exited,
6 missing BEGIN, 7 target did not resolve alive at its index.
"""
import argparse, hashlib, json, os, pty, re, select, shutil, signal, socket, subprocess, sys, time, uuid
from pathlib import Path

ROOT = Path("/home/void0312/l4d2_test/cleanrun")
BIN = ROOT / "bin"
LD = f"{BIN}:{ROOT}:{ROOT/'left4dead2'/'bin'}"

ap = argparse.ArgumentParser()
ap.add_argument("--port", default="27021")
ap.add_argument("--ip", default=None, help="explicit local address for the isolated server")
ap.add_argument("--no-watchdog", action="store_true", help="disable frame watchdog during debugger tracing")
ap.add_argument("--script", default="d50_session")
ap.add_argument("--no-script", action="store_true", help="keep a normal low-index map for a control run")
ap.add_argument("--timeout", type=float, default=180)
ap.add_argument("--keep", action="store_true",
                help="keep the server and publish a persistent Unix control socket")
ap.add_argument("--session-dir", type=Path, default=None,
                help="directory for the keep-alive metadata, PTY log, and socket")
ap.add_argument("--control-socket", type=Path, default=None,
                help="override the Unix control socket path used with --keep")
a = ap.parse_args()
lab_cfg = ROOT / "left4dead2" / "cfg" / "n27_lab.cfg"
if lab_cfg.is_symlink():
    raise SystemExit("refusing symlinked lab config")
lab_cfg.write_text('hostname "L4D2-4096-lab"\nsv_lan 1\nnet_public_adr ""\n'
                   'sv_password ""\nsv_cheats 1\nsv_consistency 0\n'
                   'sv_allow_lobby_connect_only 0\nsv_hibernate_when_empty 0\n'
                   'sb_all_bot_game 1\ndirector_stop 1\n')
script_sources = Path(__file__).resolve().parent / "vscript"
script_targets = ROOT / "left4dead2" / "scripts" / "vscripts"
script_targets.mkdir(parents=True, exist_ok=True)
for script_source in script_sources.glob("*.nut"):
    shutil.copy2(script_source, script_targets / script_source.name)
run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
master, slave = pty.openpty()
env = dict(os.environ, LD_LIBRARY_PATH=LD)
proc = subprocess.Popen(
    ["./srcds_linux", "-game", "left4dead2", "-insecure", "-console",
     *(["-nowatchdog"] if a.no_watchdog else []),
     "-port", a.port, *(["-ip", a.ip] if a.ip else []),
     "+servercfgfile", "n27_lab.cfg", "+map", "c1m1_hotel"],
    cwd=str(ROOT), stdin=slave, stdout=slave, stderr=slave,
    env=env, start_new_session=True, close_fds=True)
os.close(slave)
buf = bytearray()
sent = False
status_requested = False
state = {"begin": False, "target": None, "alive": None, "done": False, "ready": False}
deadline = time.time() + a.timeout
rc = 2


def server_alive(pid):
    """Return whether the server still has a process entry."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def relay_control(master_fd, server_pid, socket_path, log_path, initial):
    """Keep the PTY master alive and relay console commands over AF_UNIX."""
    try:
        os.setsid()
    except OSError:
        pass
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    socket_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        socket_path.unlink()
    except FileNotFoundError:
        pass
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(socket_path))
    os.chmod(socket_path, 0o600)
    listener.listen(4)
    listener.setblocking(False)
    clients = []
    with log_path.open("ab") as log:
        if initial:
            log.write(initial)
            log.flush()
        try:
            while server_alive(server_pid):
                watch = [master_fd, listener, *clients]
                try:
                    ready, _, _ = select.select(watch, [], [], 0.5)
                except (OSError, ValueError):
                    break
                if listener in ready:
                    try:
                        conn, _ = listener.accept()
                        conn.setblocking(False)
                        clients.append(conn)
                    except OSError:
                        pass
                if master_fd in ready:
                    try:
                        chunk = os.read(master_fd, 65536)
                    except OSError:
                        break
                    if not chunk:
                        break
                    log.write(chunk)
                    log.flush()
                    for conn in clients[:]:
                        try:
                            conn.sendall(chunk)
                        except OSError:
                            clients.remove(conn)
                            conn.close()
                for conn in clients[:]:
                    if conn not in ready:
                        continue
                    try:
                        command = conn.recv(65536)
                    except BlockingIOError:
                        continue
                    except OSError:
                        command = b""
                    if not command:
                        clients.remove(conn)
                        conn.close()
                        continue
                    if command.strip().lower() in (b"stop", b"quit", b"exit"):
                        try:
                            os.killpg(server_pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                    else:
                        try:
                            os.write(master_fd, command)
                        except OSError:
                            clients.remove(conn)
                            conn.close()
        finally:
            for conn in clients:
                conn.close()
            listener.close()
            try:
                socket_path.unlink()
            except FileNotFoundError:
                pass
    try:
        os.close(master_fd)
    except OSError:
        pass


try:
    while time.time() < deadline:
        r, _, _ = select.select([master], [], [], 0.5)
        if r:
            try: chunk = os.read(master, 65536)
            except OSError: break
            if not chunk: break
            buf += chunk
            text = buf.decode("utf-8", "replace")
            if not status_requested and "Initializing Director's script" in text:
                # The first Director message can occur during map precache.
                # Only the processed console reply proves the frame loop is ready.
                os.write(master, b"status\n")
                status_requested = True
            if not sent and status_requested and re.search(r"hostname\s*:", text):
                state["ready"] = True
                if a.no_script:
                    rc = 0
                    break
                time.sleep(0.5)
                os.write(master, b"sv_cheats 1\n")
                time.sleep(0.2)
                os.write(master, f"script_execute {a.script}\n".encode())
                sent = True
            if "D50_BEGIN" in text: state["begin"] = True
            m = re.search(r"D50_TARGET idx=(\d+)", text)
            if m: state["target"] = int(m.group(1))
            m = re.search(r"D50_ALIVE idx=(\d+) valid=1", text)
            if m: state["alive"] = int(m.group(1))
            m = re.search(r"D50_DONE idx=(\d+)", text)
            if m and int(m.group(1)) == state["target"]: state["done"] = True
            if state["done"]: break
        if proc.poll() is not None: break
    if state["done"]:
        if not state["begin"]: rc = 6
        elif state["target"] is None: rc = 3
        elif state["alive"] != state["target"]: rc = 7
        elif state["target"] < 2048: rc = 4
        else: rc = 0
    elif proc.poll() is not None: rc = 5
    elif state["target"] is not None: rc = 2
finally:
    print(f"RUN_ID={run_id} PID={proc.pid} PORT={a.port} SCRIPT={a.script}")
    print(
        f"BEGIN={state['begin']} TARGET={state['target']} ALIVE={state['alive']} "
        f"DONE={state['done']} RC={rc}"
    )
    if rc != 0:
        print("FAIL_LOG_TAIL=" + buf.decode("utf-8", "replace")[-4000:])
    if a.keep and rc == 0:
        session_dir = a.session_dir or Path("/tmp/l4d2-highindex") / run_id
        session_dir.mkdir(parents=True, exist_ok=True)
        control_socket = a.control_socket or session_dir / "console.sock"
        log_path = session_dir / "pty.log"
        metadata = {
            "run_id": run_id,
            "pid": proc.pid,
            "port": int(a.port),
            "script": a.script,
            "target": state["target"],
            "mode": "low-index-control" if a.no_script else "high-index",
            "state": state,
            "argv": proc.args,
            "engine_sha256": hashlib.sha256((BIN / "engine_srv.so").read_bytes()).hexdigest(),
            "control_socket": str(control_socket),
            "log": str(log_path),
        }
        (session_dir / "session.json").write_text(json.dumps(metadata, indent=2) + "\n")
        relay_pid = os.fork()
        if relay_pid == 0:
            # Do not keep a caller's captured stdout/stderr pipe open after
            # the launcher exits; the relay has no user-facing output.
            null_fd = os.open(os.devnull, os.O_WRONLY)
            os.dup2(null_fd, 1)
            os.dup2(null_fd, 2)
            if null_fd > 2:
                os.close(null_fd)
            try:
                relay_control(master, proc.pid, control_socket, log_path, bytes(buf))
            finally:
                os._exit(0)
        print(f"RELAY_PID={relay_pid} CONTROL={control_socket} SESSION={session_dir}")
        # The relay child is now the sole owner of the master FD.
        master = -1
    else:
        try: os.killpg(proc.pid, 15)
        except ProcessLookupError: pass
    if master >= 0:
        os.close(master)
sys.exit(rc)
