#!/usr/bin/env bash
# 附加 gdb 并打印 engine.dll 基址与 SV_SpawnServer 的 ECX
set -e
. "$(dirname "$0")/env.sh"
PID=$(pgrep -f left4dead2.exe | head -1)
[ -n "$PID" ] || { echo "game not running"; exit 1; }
echo "pid=$PID"
gdb -q -p "$PID" \
  -ex "set pagination off" \
  -ex "info sharedlibrary" \
  -ex "info proc mappings" \
  -ex "detach" -ex "quit" 2>&1 | grep -iE "engine|0x10|pid|reading" | head -30
