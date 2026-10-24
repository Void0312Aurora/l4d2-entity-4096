#!/bin/bash
set -u
img="$1"; out="$2"; dur="${3:-30}"
mkdir -p "$out"
export DISPLAY=:0
export XAUTHORITY=$(ls -t /run/user/1000/.mutter-Xwaylandauth.* 2>/dev/null | head -1)
CLEAN=/home/void0312/l4d2_test/cleanrun
cp "$img" "$CLEAN/bin/engine_srv.so"; chmod +x "$CLEAN/bin/engine_srv.so"
: > "$out/client.log"
/home/void0312/.steam/debian-installation/steam.sh -applaunch 550 -novid -console -condebug +connect 10.77.88.2:27020 > "$out/steam.log" 2>&1 &
GPID=""
for i in $(seq 1 200); do
  GPID=$(python3 - <<'PY'
import os
for d in os.listdir('/proc'):
    if not d.isdigit(): continue
    try:
        cmd=open(f'/proc/{d}/cmdline','rb').read(); comm=open(f'/proc/{d}/comm').read().strip()
    except Exception: continue
    if b'left4dead2.exe' in cmd and comm in ('steam.exe','left4dead2.exe'):
        print(d); break
PY
)
  [ -n "$GPID" ] && break
  sleep 0.5
done
[ -z "$GPID" ] && { echo "no client"; exit 3; }
echo "client $GPID"
sleep 3
cd "$CLEAN"
rm -f /tmp/cf-cmds; : > /tmp/cf-cmds
setsid nohup sh -c "tail -f /tmp/cf-cmds | env LD_LIBRARY_PATH=$CLEAN/bin:$CLEAN:$CLEAN/left4dead2/bin ./srcds_linux -game left4dead2 -insecure -console -port 27020 +map c1m1_hotel" > "$out/server.log" 2>&1 < /dev/null &
for i in $(seq 1 120); do grep -qa Host_NewGame "$out/server.log" && break; sleep 0.5; done
SPID=$(python3 - <<'PY'
import os
for d in os.listdir('/proc'):
    if not d.isdigit(): continue
    try: cmd=open(f'/proc/{d}/cmdline','rb').read()
    except Exception: continue
    if b'srcds_linux' in cmd and b'-port\x0027020' in cmd:
        print(d); break
PY
)
[ -z "$SPID" ] && { echo "no server"; exit 4; }
SBASE=$(python3 -c "import re;print(hex(int(re.search(r'^([0-9a-f]+)-[0-9a-f]+ .*engine_srv\\.so$', open('/proc/$SPID/maps').read(), re.M).group(1),16)))")
echo "server $SPID base $SBASE"
sudo -n env N27_SERVER_OUT="$out/server_events.jsonl" N27_SERVER_BASE="$SBASE" N27_SERVER_VTABLES=/home/void0312/Workshop/l4d2-entity-4096/tools/n27d20/server_vtables.json N27_RUN_ID="$(basename "$out")" timeout $((dur+20)) gdb -q -batch -ex "set pagination off" -ex "attach $SPID" -ex "python exec(open('/home/void0312/Workshop/l4d2-entity-4096/tools/n27d20/server_probe.py').read())" -ex "continue" > "$out/server_gdb.log" 2>&1 &
GDBPID=$!
sleep "$dur"
tail -20 "/home/void0312/.steam/debian-installation/steamapps/common/Left 4 Dead 2/left4dead2/console.log" > "$out/client.console.log" 2>/dev/null || true
kill "$GPID" 2>/dev/null || true
kill "$SPID" 2>/dev/null || true
sleep 1
kill "$GDBPID" 2>/dev/null || true
python3 - "$SPID" "$GPID" > "$out/metadata.json" <<'PY'
import json,sys
print(json.dumps({"server_pid":sys.argv[1],"client_pid":sys.argv[2],"port":27020},indent=1))
PY
echo done
