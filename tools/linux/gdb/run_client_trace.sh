#!/bin/sh
# usage: run_client_trace.sh <client_pid> <engine_base> <outfile> [seconds]
PID=$1; BASE=$2; OUT=$3; DUR=${4:-40}
: > "$OUT"; chmod 666 "$OUT"
sudo -n env CLIENT_BASE="$BASE" timeout "$DUR" gdb -q -batch \
  -ex "set pagination off" -ex "set confirm off" \
  -ex "handle SIGUSR1 nostop noprint pass" -ex "handle SIGUSR2 nostop noprint pass" \
  -ex "handle SIGCHLD nostop noprint pass" -ex "handle SIGPIPE nostop noprint pass" \
  -ex "attach $PID" \
  -ex "python exec(open('/home/void0312/Workshop/l4d2-entity-4096/tools/linux/gdb/client_trace.py').read())" \
  -ex "continue" > "$OUT.gdb" 2>&1
