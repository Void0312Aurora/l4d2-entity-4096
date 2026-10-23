#!/usr/bin/env python3
"""Run one L4D2 client experiment against a chosen server engine image.

Requires the prepared clean server tree (/tmp/cleanrun) and the local Steam client.
The runner validates hashes, starts the server, launches the Proton client,
attaches the declarative GDB probe collector, and records metadata + JSONL.
"""
import argparse, hashlib, json, os, re, shutil, signal, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLEAN = Path("/tmp/cleanrun")
PROBE = ROOT / "tools/n27d19/gdb_probe.py"
CONFIG = ROOT / "tools/n27d19/probe_config.json"

IMAGES = {
    "pristine": ("/home/void0312/l4d2_server/bin/engine_srv.so", "5fa15f2820ab67b955ff227a20dbb3fda54d463f3799f33d71b6fd6f38e309b7"),
    "frameonly": ("/tmp/n27/frameonly.so", "89152442f624339b"),
}

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def run(cmd, **kw):
    return subprocess.run(cmd, text=True, **kw)

def pid_of(name):
    out = run(["pgrep", "-x", name], capture_output=True)
    return int(out.stdout.split()[0]) if out.stdout.strip() else None

def kill_name(name):
    pid = pid_of(name)
    if pid:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        time.sleep(1.0)

def module_base(pid, suffix):
    # suffix must be an exact path ending, e.g. '/bin/engine.dll'
    maps = Path(f"/proc/{pid}/maps").read_text(errors="ignore")
    pat = re.compile(r"^([0-9a-f]+)-[0-9a-f]+ .* (\S*%s)$" % re.escape(suffix), re.M)
    m = pat.search(maps)
    return int(m.group(1), 16) if m else None

def wait_for(path, needle, timeout, pid=None):
    end = time.time() + timeout
    while time.time() < end:
        if path.exists() and needle in path.read_text(errors="ignore"):
            return True
        if pid and pid_of("srcds_linux") is None:
            return False
        time.sleep(0.5)
    return False

def launch_server(run_dir, image, port, mapname, log):
    shutil.copyfile(image, CLEAN / "bin/engine_srv.so")
    os.chmod(CLEAN / "bin/engine_srv.so", 0o755)
    fifo = run_dir / "commands.fifo"
    if fifo.exists(): fifo.unlink()
    os.mkfifo(fifo)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ":".join([str(CLEAN/"bin"), str(CLEAN), str(CLEAN/"left4dead2/bin")])
    cmd = ["sh", "-c", f"tail -f {fifo} | exec ./srcds_linux -game left4dead2 -insecure -console -port {port} +map {mapname}"]
    p = subprocess.Popen(cmd, cwd=CLEAN, env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    return p, fifo

def fifo_write(fifo, text):
    fd = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
    os.write(fd, (text + "\n").encode()); os.close(fd)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", choices=sorted(IMAGES), required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, default=27016)
    ap.add_argument("--map", default="c1m1_hotel")
    ap.add_argument("--duration", type=float, default=40)
    ap.add_argument("--connect-ip", default="10.77.88.2")
    ap.add_argument("--no-client", action="store_true", help="server-only smoke test")
    args = ap.parse_args()

    run_dir = Path(args.out); run_dir.mkdir(parents=True, exist_ok=True)
    image, want = IMAGES[args.image]
    if not Path(image).exists():
        sys.exit(f"image missing: {image}")
    got = sha256(image)
    if not got.startswith(want):
        sys.exit(f"image hash mismatch: {got} != {want}")

    meta = {"image": args.image, "image_path": image, "sha256": got,
            "port": args.port, "map": args.map, "started": time.time(),
            "ok": False, "invalid_reason": None}
    server_log = run_dir / "server.log"
    client_log = run_dir / "client.console.log"
    jsonl = run_dir / "events.jsonl"

    kill_name("srcds_linux"); kill_name("left4dead2.exe")
    p, fifo = launch_server(run_dir, image, args.port, args.map, server_log)
    meta["server_pid"] = pid_of("srcds_linux")
    if not wait_for(server_log, "Host_NewGame", 60):
        meta["invalid_reason"] = "server did not reach Host_NewGame"
        (run_dir/"metadata.json").write_text(json.dumps(meta, indent=2)); sys.exit(2)

    for cmd in ('sv_lan 1', 'sv_password ""', 'sv_consistency 0'):
        fifo_write(fifo, cmd)
    time.sleep(2)

    if not args.no_client:
        env = os.environ.copy()
        env.setdefault("DISPLAY", ":0")
        cp_log0 = Path("/home/void0312/.steam/debian-installation/steamapps/common/Left 4 Dead 2/left4dead2/console.log")
        console_offset = cp_log0.stat().st_size if cp_log0.exists() else 0
        with open("/tmp/n27d19-steam.log", "w") as sf:
            subprocess.Popen(["/home/void0312/.steam/debian-installation/ubuntu12_32/steam",
                              "-applaunch", "550", "-novid", "-console", "-condebug",
                              "+connect", f"{args.connect_ip}:{args.port}"],
                             env=env, stdout=sf, stderr=subprocess.STDOUT, start_new_session=True)
        gpid = None
        end = time.time() + 60
        while time.time() < end:
            gpid = pid_of("left4dead2.exe")
            if gpid: break
            time.sleep(0.3)
        if not gpid:
            meta["invalid_reason"] = "client process did not start"
            (run_dir/"metadata.json").write_text(json.dumps(meta, indent=2)); sys.exit(3)
        meta["client_pid"] = gpid
        ebase = cbase = None
        end = time.time() + 20
        while time.time() < end:
            ebase = module_base(gpid, "/bin/engine.dll")
            cbase = module_base(gpid, "/bin/client.dll")
            if ebase and cbase: break
            time.sleep(0.2)
        if not (ebase and cbase):
            meta["invalid_reason"] = "module bases not found"
            (run_dir/"metadata.json").write_text(json.dumps(meta, indent=2)); sys.exit(4)
        meta["engine_base"] = hex(ebase); meta["client_base"] = hex(cbase)

        senv = os.environ.copy()
        senv.update({"N27_PROBE_CONFIG": str(CONFIG), "N27_PROBE_OUT": str(jsonl),
                     "N27_MODULE_BASE_ENGINE": hex(ebase), "N27_MODULE_BASE_CLIENT": hex(cbase),
                     "N27_RUN_ID": run_dir.name, "N27_PROBE_RUN_ID": run_dir.name})
        gdb_cmd = ["sudo", "-n", "env",
                   f"N27_PROBE_CONFIG={CONFIG}", f"N27_PROBE_OUT={jsonl}",
                   f"N27_MODULE_BASE_ENGINE={hex(ebase)}", f"N27_MODULE_BASE_CLIENT={hex(cbase)}",
                   f"N27_RUN_ID={run_dir.name}", f"N27_PROBE_RUN_ID={run_dir.name}",
                   "timeout", str(int(args.duration) + 15), "gdb", "-q", "-batch",
                   "-ex", "set pagination off", "-ex", "set confirm off",
                   "-ex", "handle SIGUSR1 nostop noprint pass",
                   "-ex", "handle SIGUSR2 nostop noprint pass",
                   "-ex", "handle SIGCHLD nostop noprint pass",
                   "-ex", "handle SIGPIPE nostop noprint pass",
                   "-ex", f"attach {gpid}",
                   "-ex", f"python exec(open('{PROBE}').read())",
                   "-ex", "continue"]
        with open(run_dir/"gdb.log", "w") as gf:
            proc = subprocess.run(gdb_cmd, stdout=gf, stderr=subprocess.STDOUT, env=senv, timeout=args.duration+25)
        meta["gdb_returncode"] = proc.returncode
        cp_log = Path("/home/void0312/.steam/debian-installation/steamapps/common/Left 4 Dead 2/left4dead2/console.log")
        if cp_log.exists():
            data = cp_log.read_bytes()[console_offset:]
            client_log.write_bytes(data)
        meta["connect_ok"] = client_log.exists() and "Connected to" in client_log.read_text(errors="ignore")
        events = [json.loads(l) for l in jsonl.read_text(errors="ignore").splitlines() if l.startswith("{")] if jsonl.exists() else []
        meta["event_lines"] = len(events)
        meta["install_failed"] = any(e.get("event") == "install_failed" for e in events)
        meta["install_ok"] = any(e.get("event") == "install_summary" and e.get("ok") for e in events)
        meta["full_state_seen"] = any(e.get("event") == "full_state" for e in events)
        meta["ok"] = bool(meta["connect_ok"] and meta["install_ok"] and not meta["install_failed"]
                          and meta["full_state_seen"] and meta["event_lines"] > 0)
        if not meta["ok"]:
            meta["invalid_reason"] = "connect/install/probe validity failed"

    kill_name("left4dead2.exe"); kill_name("srcds_linux")
    meta["ended"] = time.time()
    (run_dir/"metadata.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: meta.get(k) for k in ("image","ok","connect_ok","event_lines","engine_base","client_base","invalid_reason")}, indent=2))

if __name__ == "__main__":
    main()
