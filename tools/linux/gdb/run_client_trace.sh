#!/bin/sh
# usage: run_client_trace.sh <client_pid> <engine_base> <outfile> [seconds]
PID=$1; BASE=$2; OUT=$3; DUR=${4:-40}
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: > "$OUT"
sudo -n env CLIENT_BASE="$BASE" timeout "$DUR" gdb -q -batch \
  -ex "set pagination off" -ex "set confirm off" \
  -ex "handle SIGUSR1 nostop noprint pass" -ex "handle SIGUSR2 nostop noprint pass" \
  -ex "handle SIGCHLD nostop noprint pass" -ex "handle SIGPIPE nostop noprint pass" \
  -ex "attach $PID" \
  -ex "python exec(open('$DIR/client_trace.py').read())" \
  -ex "continue" > "$OUT" 2>&1
