#!/usr/bin/env python3
import argparse, json, os, re, signal, subprocess, sys, time
from pathlib import Path

ROOT = Path("/home/void0312/Workshop/l4d2-entity-4096")
CLEAN = Path("/home/void0312/l4d2_test/cleanrun")
PROBE = ROOT/"tools/n27d21_client_signon.py"
SERVER_PROBE = ROOT/"tools/n27d20/server_probe.py"
VT = ROOT/"tools/n27d20/server_vtables.json"
PORT = 27020
STEAM = "/home/void0312/.steam/debian-installation/steam.sh"
GAME = Path("/home/void0312/.steam/debian-installation/steamapps/common/Left 4 Dead 2/left4dead2/console.log")

def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

def client_pids():
    out=[]
    for d in Path("/proc").iterdir():
        if not d.name.isdigit(): continue
        try:
            cmd=(d/"cmdline").read_bytes(); comm=(d/"comm").read_text().strip()
        except Exception: continue
        if b"left4dead2.exe" not in cmd: continue
        if any(x in cmd for x in (b"bwrap",b"proton",b"reaper",b"pv-adverb",b"srt-bwrap")): continue
        if comm not in ("steam.exe","left4dead2.exe"): continue
        try: started=float((d/"stat").read_text().split()[21])/100.0
        except Exception: started=0
        out.append((int(d.name), started))
    return [p for p,_ in sorted(out, key=lambda x:-x[1])]

def module_base(pid, suffix):
    try:
        for line in Path(f"/proc/{pid}/maps").read_text(errors="ignore").splitlines():
            parts=line.split()
            if len(parts)>=6 and parts[-1].endswith(suffix):
                return int(parts[0].split("-")[0],16)
    except Exception: pass
    return None

def port_pid(port):
    for d in Path("/proc").iterdir():
        if not d.name.isdigit(): continue
        try: cmd=(d/"cmdline").read_bytes()
        except Exception: continue
        parts=cmd.split(b"\0")
        if b"srcds_linux" in cmd and b"-port" in parts and str(port).encode() in parts:
            return int(d.name)
    return None

def wait_ready(path, proc, timeout):
    end=time.time()+timeout
    while time.time()<end:
        if path.exists():
            txt=path.read_text(errors="ignore")
            if '"event": "ready"' in txt or '"event":"ready"' in txt: return True
            if "install_failed" in txt: return False
        if proc.poll() is not None: return False
        time.sleep(0.2)
    return False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--duration", type=int, default=60)
    args=ap.parse_args()
    out=Path(args.out); out.mkdir(parents=True, exist_ok=True)
    image=Path(args.image)
    env=os.environ.copy(); env.setdefault("DISPLAY",":0")
    if not env.get("XAUTHORITY"):
        import glob
        a=sorted(glob.glob("/run/user/1000/.mutter-Xwaylandauth.*"))
        if a: env["XAUTHORITY"]=a[-1]
    # refuse if port busy
    import socket
    s=socket.socket(); busy=s.connect_ex(("127.0.0.1",PORT))==0; s.close()
    if busy: sys.exit("port busy")
    # packet capture (best effort)
    pcap=out/"d22.pcap"; tcpdump=None
    try:
        if subprocess.run(["sudo","-n","tcpdump","--version"],capture_output=True).returncode==0:
            tcpdump=subprocess.Popen(["sudo","-n","tcpdump","-i","any","-nn","-tt","-U","-w",str(pcap),"udp","port",str(PORT)],
                                     stdout=open(out/"tcpdump.log","w"), stderr=subprocess.STDOUT, start_new_session=True)
            time.sleep(0.5)
    except Exception:
        tcpdump=None
    # client first
    cp0=GAME.stat().st_size if GAME.exists() else 0
    subprocess.Popen([STEAM,"-applaunch","550","-novid","-console","-condebug","+connect",f"10.77.88.2:{PORT}"],
                     env=env, stdout=open(out/"steam.log","w"), stderr=subprocess.STDOUT, start_new_session=True)
    chosen=None; cgdb=None
    deadline=time.time()+150
    while time.time()<deadline and not chosen:
        for pid in client_pids():
            eb=module_base(pid,"/bin/engine.dll"); cb=module_base(pid,"/bin/client.dll")
            if not (eb and cb): continue
            js=out/"client_events.jsonl"
            if js.exists(): js.unlink()
            e2=env.copy()
            e2.update(N27_MODULE_BASE_ENGINE=hex(eb), N27_MODULE_BASE_CLIENT=hex(cb),
                      N27_SIGNON_OUT=str(js), N27_RUN_ID=out.name)
            cmd=["sudo","-n","env",f"N27_MODULE_BASE_ENGINE={hex(eb)}",f"N27_MODULE_BASE_CLIENT={hex(cb)}",
                 f"N27_SIGNON_OUT={js}",f"N27_RUN_ID={out.name}","timeout",str(args.duration+40),
                 "gdb","-q","-batch","-ex","set pagination off",
                 "-ex","handle SIGUSR1 nostop noprint pass","-ex","handle SIGUSR2 nostop noprint pass",
                 "-ex","handle SIGCHLD nostop noprint pass",f"-ex","attach %d"%pid,
                 "-ex",f"python exec(open('{PROBE}').read())","-ex","continue"]
            p=subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=open(out/"client_gdb.log","w"),
                               stderr=subprocess.STDOUT, env=e2)
            if wait_ready(js,p,12):
                chosen=(pid,eb,cb,p); break
            try: p.kill()
            except Exception: pass
        time.sleep(0.4)
    if not chosen: sys.exit("client probe not ready")
    pid,eb,cb,cgdb=chosen
    (out/"metadata.json").write_text(json.dumps({"client_pid":pid,"engine_base":hex(eb),"client_base":hex(cb)},indent=1))
    # server after client probe ready
    # P0: never follow a symlink into the production install; install atomically.
    prod = Path("/home/void0312/l4d2_server").resolve()
    dst = CLEAN/"bin/engine_srv.so"
    clean_resolved = CLEAN.resolve()
    if clean_resolved == prod or prod in clean_resolved.parents:
        sys.exit("refusing to install image into production server tree")
    if dst.is_symlink():
        sys.exit(f"refusing symlinked target: {dst}")
    dst_resolved = dst.resolve()
    if dst_resolved == prod or prod in dst_resolved.parents:
        sys.exit("refusing target resolving into production server tree")
    tmp = dst.with_name(".engine_srv.so.tmp")
    tmp.write_bytes(image.read_bytes())
    os.replace(tmp, dst)
    if dst.is_symlink() or not dst.is_file():
        sys.exit("image install did not produce a regular file")
    import hashlib
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    if sha != hashlib.sha256(image.read_bytes()).hexdigest():
        sys.exit("installed image hash mismatch")
    (out/"image.json").write_text(json.dumps({
        "source": str(image), "source_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "installed": str(dst), "installed_resolved": str(dst_resolved),
        "installed_sha256": sha, "clean": str(clean_resolved)}, indent=1))
    fifo=out/"commands.fifo"
    if fifo.exists(): fifo.unlink()
    os.mkfifo(fifo)
    srv_log=open(out/"server.log","w")
    p=subprocess.Popen(["sh","-c",f"tail -f {fifo} | env LD_LIBRARY_PATH={CLEAN}/bin:{CLEAN}:{CLEAN}/left4dead2/bin ./srcds_linux -game left4dead2 -insecure -console -port {PORT} +map c1m1_hotel"],
                       cwd=CLEAN, stdout=srv_log, stderr=subprocess.STDOUT, start_new_session=True)
    spid=None
    for _ in range(100):
        spid=port_pid(PORT)
        if spid: break
        time.sleep(0.1)
    if not spid: sys.exit("server pid not found")
    sb=module_base(spid,"/engine_srv.so")
    sjson=out/"server_events.jsonl"
    inner=(f"sudo -n env N27_SERVER_OUT={sjson} N27_SERVER_BASE={hex(sb)} "
           f"N27_SERVER_VTABLES={VT} N27_RUN_ID={out.name} timeout {args.duration+40} "
           f"gdb -q -batch -ex 'set pagination off' -ex 'attach {spid}' "
           f"-ex \"python exec(open('{SERVER_PROBE}').read())\" -ex continue")
    sgdb=subprocess.Popen(["bash","-lc",inner], stdin=subprocess.DEVNULL,
                          stdout=open(out/"server_gdb.log","w"), stderr=subprocess.STDOUT, env=env)
    end=time.time()+60
    while time.time()<end:
        try: txt=srv_log and Path(out/"server.log").read_text(errors="ignore")
        except Exception: txt=""
        if "Host_NewGame" in txt: break
        time.sleep(0.2)
    for line in ('sv_lan 1','sv_password ""','sv_consistency 0'):
        with open(fifo,"w") as f: f.write(line+"\n")
    time.sleep(args.duration)
    try: os.kill(pid,signal.SIGKILL)
    except Exception: pass
    try: os.killpg(os.getpgid(p.pid),signal.SIGKILL)
    except Exception: pass
    try: sgdb.wait(timeout=5)
    except Exception: sgdb.kill()
    try: cgdb.wait(timeout=5)
    except Exception: cgdb.kill()
    if tcpdump is not None:
        try: os.killpg(os.getpgid(tcpdump.pid), signal.SIGINT)
        except Exception:
            try: tcpdump.terminate()
            except Exception: pass
        try: tcpdump.wait(timeout=5)
        except Exception: tcpdump.kill()
    if GAME.exists():
        (out/"client.console.log").write_bytes(GAME.read_bytes()[cp0:])
    print(json.dumps({"client_pid":pid,"server_pid":spid,"client_events":sum(1 for _ in open(out/"client_events.jsonl")) if (out/"client_events.jsonl").exists() else 0,
                      "server_events":sum(1 for _ in open(sjson)) if sjson.exists() else 0}, indent=1))

if __name__=="__main__": main()
