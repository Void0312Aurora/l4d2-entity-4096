#!/usr/bin/env python3
"""Run one L4D2 client experiment against a chosen server engine image.

Requires the prepared clean server tree (/tmp/cleanrun) and the local Steam client.
The runner validates hashes, starts the server, launches the Proton client,
attaches the declarative GDB probe collector, and records metadata + JSONL.
"""
import argparse, hashlib, json, os, re, shutil, signal, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLEAN = Path(os.environ.get("N27_CLEAN", "/home/void0312/l4d2_test/cleanrun"))
PROBE = ROOT / "tools/n27d19/gdb_probe.py"
CONFIG = ROOT / "tools/n27d19/probe_config.json"

IMAGES = {
    "pristine": ("/home/void0312/l4d2_server/bin/engine_srv.so", "5fa15f2820ab67b955ff227a20dbb3fda54d463f3799f33d71b6fd6f38e309b7"),
    "frameonly": ("/home/void0312/l4d2_test/n27/frameonly.so", "2917501000a2cb12e6b9"),
    "sizeonly": ("/home/void0312/l4d2_test/n27/sizeonly.so", "6f722e05c92219a31396"),
    "frame_offsets": ("/home/void0312/l4d2_test/n27/frame_offsets.so", "b232407b81cb57396dc9"),
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
    pids = [int(x) for x in out.stdout.split()]
    for p in pids:
        try:
            stat = Path(f"/proc/{p}/stat").read_text().split()
            if len(stat) > 2 and stat[2] != "Z":
                return p
        except Exception:
            pass
    return pids[0] if pids else None

def kill_name(name):
    pid = pid_of(name)
    if pid:
        try: os.kill(pid, signal.SIGKILL)
        except ProcessLookupError: pass
        time.sleep(1.0)

def client_pid():
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            cmd = (d/"cmdline").read_bytes()
        except Exception:
            continue
        if b"left4dead2.exe" not in cmd:
            continue
        if any(x in cmd for x in (b"bwrap", b"proton", b"steam-launch-wrapper", b"reaper", b"srt-bwrap", b"pv-adverb")):
            continue
        try:
            if (d/"comm").read_text().strip() in ("steam.exe", "left4dead2.exe"):
                return int(d.name)
        except Exception:
            pass
    return None

def server_pid_on_port(port):
    needle = f"-port".encode()
    pneedle = str(port).encode()
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            cmd = (d/"cmdline").read_bytes()
            if b"srcds_linux" not in cmd:
                continue
            parts = cmd.split(b"\0")
            if b"-port" in parts and pneedle in parts:
                return int(d.name)
        except Exception:
            continue
    return None

def child_pid(parent, comm, timeout=12):
    end = time.time() + timeout
    while time.time() < end:
        try:
            kids = Path(f"/proc/{parent}/task/{parent}/children").read_text().split()
        except Exception:
            kids = []
        for k in kids:
            try:
                if Path(f"/proc/{k}/comm").read_text().strip() == comm:
                    return int(k)
            except Exception:
                pass
        time.sleep(0.2)
    return None

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
    dst = CLEAN / "bin/engine_srv.so"
    # Never follow a symlink into the production install: a previous cleanrun
    # built with `cp -as` left this path as a symlink, and copyfile() then
    # overwrote /home/void0312/l4d2_server/bin/engine_srv.so.
    if dst.is_symlink():
        dst.unlink()
    tmp = dst.with_name(dst.name + ".n27tmp")
    shutil.copyfile(image, tmp)
    os.chmod(tmp, 0o755)
    os.replace(tmp, dst)
    if CLEAN.resolve() == Path("/home/void0312/l4d2_server").resolve():
        sys.exit("refusing to run in the production install directory")
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
    ap.add_argument("--port", type=int, default=27020)
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

    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_sock:
        if probe_sock.connect_ex(("127.0.0.1", args.port)) == 0:
            sys.exit(f"port {args.port} already in use; refusing to disturb a running server")
    p, fifo = launch_server(run_dir, image, args.port, args.map, server_log)
    meta["server_pid"] = server_pid_on_port(args.port) or child_pid(p.pid, "srcds_linux")
    if not wait_for(server_log, "Host_NewGame", 60):
        meta["invalid_reason"] = "server did not reach Host_NewGame"
        (run_dir/"metadata.json").write_text(json.dumps(meta, indent=2)); sys.exit(2)

    for cmd in ('sv_lan 1', 'sv_password ""', 'sv_consistency 0'):
        fifo_write(fifo, cmd)
    time.sleep(2)

    srv_gdb = None
    server_jsonl = run_dir / "server_events.jsonl"
    if not args.no_client and Path(__file__).resolve().parents[2].joinpath("tools/n27d20/server_probe.py").exists():
        sbase = None
        try:
            maps = Path(f"/proc/{meta['server_pid']}/maps").read_text(errors="ignore")
            m = re.search(r"^([0-9a-f]+)-[0-9a-f]+ .*engine_srv\.so$", maps, re.M)
            sbase = int(m.group(1), 16) if m else None
        except Exception:
            sbase = None
        if sbase:
            live = server_pid_on_port(args.port)
            if live:
                meta["server_pid"] = live
                try:
                    lm = Path(f"/proc/{live}/maps").read_text(errors="ignore")
                    mm = re.search(r"^([0-9a-f]+)-[0-9a-f]+ .*engine_srv\.so$", lm, re.M)
                    if mm:
                        sbase = int(mm.group(1), 16)
                except Exception:
                    pass
            meta["server_base"] = hex(sbase)
            inner = (
                f"sudo -n env N27_SERVER_OUT='{server_jsonl}' "
                f"N27_SERVER_BASE='{hex(sbase)}' "
                f"N27_SERVER_VTABLES='{ROOT/'tools/n27d20/server_vtables.json'}' "
                f"N27_RUN_ID='{run_dir.name}' "
                f"timeout {int(args.duration)+25} gdb -q -batch "
                f"-ex 'set pagination off' -ex 'set confirm off' "
                f"-ex 'attach {meta['server_pid']}' "
                f"-ex \"python exec(open('{ROOT/'tools/n27d20/server_probe.py'}').read())\" "
                f"-ex continue"
            )
            sgdb = ["bash", "-lc", inner]
            time.sleep(3)
            with open(run_dir/"server_attach_debug.txt","w") as dbg:
                dbg.write(subprocess.run(["ps","-o","pid,ppid,stat,comm","-p",str(meta['server_pid'])],capture_output=True,text=True).stdout)
                dbg.write("exists=%s\n" % Path(f"/proc/{meta['server_pid']}").exists())
                dbg.write("pgrep=%s\n" % subprocess.run(["pgrep","-ax","srcds_linux"],capture_output=True,text=True).stdout)
            srv_gdb = subprocess.Popen(sgdb, stdin=subprocess.DEVNULL,
                                       stdout=open(run_dir/"server_gdb.log","w"),
                                       stderr=subprocess.STDOUT, env=os.environ.copy())
            time.sleep(1)

    if not args.no_client:
        env = os.environ.copy()
        env.setdefault("DISPLAY", ":0")
        if not env.get("XAUTHORITY"):
            import glob
            auth = sorted(glob.glob("/run/user/1000/.mutter-Xwaylandauth.*"))
            if auth:
                env["XAUTHORITY"] = auth[-1]
        cp_log0 = Path("/home/void0312/.steam/debian-installation/steamapps/common/Left 4 Dead 2/left4dead2/console.log")
        console_offset = cp_log0.stat().st_size if cp_log0.exists() else 0
        with open("/tmp/n27d19-steam.log", "w") as sf:
            subprocess.Popen(["/home/void0312/.steam/debian-installation/steam.sh",
                              "-applaunch", "550", "-novid", "-console", "-condebug",
                              "+connect", f"{args.connect_ip}:{args.port}"],
                             env=env, stdout=sf, stderr=subprocess.STDOUT, start_new_session=True)
        gpid = None
        end = time.time() + 150
        while time.time() < end:
            gpid = client_pid()
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
        meta["server_event_lines"] = sum(1 for l in server_jsonl.read_text(errors="ignore").splitlines() if l.startswith("{")) if server_jsonl.exists() else 0
        meta["install_failed"] = any(e.get("event") == "install_failed" for e in events)
        meta["install_ok"] = any(e.get("event") == "install_summary" and e.get("ok") for e in events)
        meta["full_state_seen"] = any(e.get("event") == "full_state" for e in events)
        meta["ok"] = bool(meta["connect_ok"] and meta["install_ok"] and not meta["install_failed"]
                          and meta["full_state_seen"] and meta["event_lines"] > 0)
        if not meta["ok"]:
            meta["invalid_reason"] = "connect/install/probe validity failed"

    if srv_gdb is not None:
        try:
            srv_gdb.wait(timeout=8)
        except Exception:
            try: srv_gdb.kill()
            except Exception: pass
    if 'gpid' in locals() and gpid:
        try: os.kill(gpid, signal.SIGKILL)
        except ProcessLookupError: pass
    try:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
    except ProcessLookupError:
        pass
    meta["ended"] = time.time()
    (run_dir/"metadata.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: meta.get(k) for k in ("image","ok","connect_ok","event_lines","engine_base","client_base","invalid_reason")}, indent=2))

if __name__ == "__main__":
    main()
