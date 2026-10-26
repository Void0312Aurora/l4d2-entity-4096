#!/usr/bin/env python3
"""Bounded, isolated Proton run with module identities and first-signal capture.

The game tree must already contain private engine/client DLL files. Assets may
be symlinked. Never installs into the Steam library or kills an existing game.
The console is available on --netcon-port when supported by the engine.
"""
import argparse
import glob
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time


def game_pids():
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if (proc / 'comm').read_text().strip() == 'left4dead2.exe':
                found.append(int(proc.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return found


def verify_local_target(target):
    """Fail before launching Wine if the isolated local server does not match."""
    host, port = target.rsplit(':', 1)
    address = socket.gethostbyname(host)
    listeners = subprocess.check_output(['ss', '-H', '-l', '-u', '-n', '-p'], text=True)
    matches = []
    for line in listeners.splitlines():
        fields = line.split()
        if len(fields) < 5 or 'srcds_linux' not in line:
            continue
        bound_host, bound_port = fields[3].rsplit(':', 1)
        if bound_port == port and bound_host in (address, '0.0.0.0', '*'):
            matches.append(line)
    if not matches:
        raise ValueError(f'no local srcds listener matches {address}:{port}')
    return dict(target=target, resolved_address=address, listeners=matches)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--game', type=Path, default=Path('/home/void0312/l4d2_test/client4096'))
    ap.add_argument('--proton', type=Path, default=Path('/home/void0312/.steam/steam/steamapps/common/Proton - Experimental/proton'))
    ap.add_argument('--prefix', type=Path, default=Path('/home/void0312/.steam/steam/steamapps/compatdata/550'))
    ap.add_argument('--client', type=Path, required=True)
    ap.add_argument('--engine', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--connect')
    ap.add_argument('--duration', type=float, default=90)
    ap.add_argument('--netcon-port', type=int, default=27101)
    ap.add_argument('--debug', action='store_true')
    a = ap.parse_args()
    a.game = a.game.resolve()
    steam = Path('/home/void0312/.steam/steam').resolve()
    if steam == a.game or steam in a.game.parents:
        ap.error('use a private game directory outside Steam')
    old = game_pids()
    if old:
        ap.error(f'existing game processes: {old}')
    try:
        target_check = verify_local_target(a.connect) if a.connect else None
    except (OSError, ValueError) as error:
        ap.error(str(error))
    a.out.mkdir(parents=True, exist_ok=False)
    for source, dest in [(a.client, a.game/'left4dead2/bin/client.dll'),
                         (a.engine, a.game/'bin/engine.dll')]:
        if dest.is_symlink():
            ap.error(f'private regular DLL required: {dest}')
        shutil.copy2(source, dest)
    console = a.game/'left4dead2/console.log'
    if console.is_symlink():
        ap.error('console.log must be private')
    console.write_text('')
    env = os.environ.copy()
    env.update(DISPLAY=env.get('DISPLAY', ':0'),
               STEAM_COMPAT_DATA_PATH=str(a.prefix),
               STEAM_COMPAT_CLIENT_INSTALL_PATH=str(steam),
               SteamAppId='550', SteamGameId='550',
               PROTON_LOG='1', PROTON_LOG_DIR=str(a.out.resolve()),
               WINEDEBUG='+timestamp,+pid,+tid,+seh,+loaddll')
    auth = glob.glob('/run/user/1000/.mutter-Xwaylandauth.*')
    if auth:
        env.setdefault('XAUTHORITY', auth[0])
    cmd = [str(a.proton), 'run', str(a.game/'left4dead2.exe'),
           '-steam', '-insecure', '-novid', '-windowed', '-w', '960', '-h', '540',
           '-console', '-condebug', '-netconport', str(a.netcon_port)]
    if a.connect:
        cfg = a.game/'left4dead2/cfg/n27_connect.cfg'
        if cfg.is_symlink():
            ap.error('connect config must be private')
        cfg.write_text(f'wait 120; connect {a.connect}\n')
        cmd += ['+exec', 'n27_connect.cfg']
    meta = dict(argv=cmd, prefix=str(a.prefix), proton_version=(a.proton.parent/'version').read_text().strip(),
                started=time.time(), modules={}, events=[], target_check=target_check,
                graphics_environment={key: env.get(key) for key in
                                      ['DISPLAY', 'XAUTHORITY', 'XDG_SESSION_TYPE', 'WAYLAND_DISPLAY']})
    if a.connect:
        meta['connect_config'] = cfg.read_text()
    for rel in ['left4dead2.exe', 'bin/engine.dll', 'left4dead2/bin/client.dll']:
        meta['modules'][rel] = hashlib.sha256((a.game/rel).read_bytes()).hexdigest()
    debugger = None
    owned = set()
    maps_seen = set()
    previous_pids = set()
    with (a.out/'launcher.log').open('w') as log:
        proc = subprocess.Popen(cmd, cwd=a.game, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        meta['launcher_pid'] = proc.pid
        print(f'LAUNCHER={proc.pid} OUT={a.out}', flush=True)
        try:
            end = time.monotonic() + a.duration
            while time.monotonic() < end:
                current = set(game_pids())
                for pid in previous_pids-current:
                    meta['events'].append(dict(event='game_exited', pid=pid, time=time.time()))
                previous_pids = current
                for pid in current-owned:
                    owned.add(pid)
                    meta['events'].append(dict(event='game_created', pid=pid, time=time.time()))
                    print(f'GAME_PID={pid}', flush=True)
                for pid in owned:
                    try:
                        mappings = Path(f'/proc/{pid}/maps').read_text()
                    except (FileNotFoundError, ProcessLookupError):
                        continue
                    for rel in ['bin/engine.dll', 'left4dead2/bin/client.dll']:
                        if rel in mappings and (pid, rel) not in maps_seen:
                            maps_seen.add((pid, rel))
                            meta['events'].append(dict(event='module_loaded', pid=pid, module=rel, time=time.time()))
                            (a.out/f'maps-{pid}.txt').write_text(mappings)
                    if a.debug and debugger is None and (pid, 'left4dead2/bin/client.dll') in maps_seen:
                        fault = a.out/'fault.log'
                        gcmd = ['sudo', '-n', 'gdb', '-q', '-batch',
                                '-ex', 'set pagination off', '-ex', 'set print thread-events off']
                        for sig in ['SIGUSR1', 'SIGUSR2', 'SIGCHLD', 'SIGSYS', 'SIGPIPE', 'SIGTERM']:
                            gcmd += ['-ex', f'handle {sig} nostop noprint pass']
                        gcmd += ['-ex', f'attach {pid}', '-ex', 'continue', '-ex', 'info registers',
                                 '-ex', 'bt 30', '-ex', 'x/16i $pc-24', '-ex', 'info proc mappings',
                                 '-ex', f'generate-core-file {a.out.resolve()}/client.core', '-ex', 'detach']
                        debugger = subprocess.Popen(gcmd, stdout=fault.open('w'), stderr=subprocess.STDOUT)
                        meta['debugger_pid'] = debugger.pid
                    if debugger and debugger.poll() is not None:
                        break
                if proc.poll() is not None:
                    meta['launcher_returncode'] = proc.returncode
                    break
                if debugger and debugger.poll() is not None:
                    meta['debugger_returncode'] = debugger.returncode
                    meta['captured_signal'] = 'received signal' in (a.out/'fault.log').read_text(errors='replace')
                    break
                time.sleep(0.1)
        finally:
            meta['ended_observation'] = time.time()
            meta['alive_at_cleanup'] = game_pids()
            if debugger and debugger.poll() is None:
                debugger.terminate()
                try:
                    debugger.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    debugger.kill()
            for pid in owned:
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                for pid in owned:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                proc.terminate()
                proc.wait(timeout=5)
            meta['launcher_final_returncode'] = proc.returncode
            meta['ended'] = time.time()
            shutil.copy2(console, a.out/'console.log')
            (a.out/'run.json').write_text(json.dumps(meta, indent=2)+'\n')
    print(json.dumps(meta), flush=True)


if __name__ == '__main__':
    main()
