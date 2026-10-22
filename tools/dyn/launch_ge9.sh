#!/usr/bin/env bash
set -u
. "$(dirname "$0")/env.sh"
STEAM_SH="$HOME/.steam/debian-installation/steam.sh"
echo "$(date +%T) start steam"
setsid "$STEAM_SH" -silent >/tmp/steam8.log 2>&1 &
sleep 45
echo "$(date +%T) applaunch"
setsid "$STEAM_SH" -applaunch 550 -insecure -novid -console +map c1m1_hotel >/tmp/launch13.log 2>&1 &
PID=""
for i in $(seq 1 30); do
  sleep 5
  for p in $(ls /proc | grep -E '^[0-9]+$'); do
    grep -q "engine.dll" /proc/$p/maps 2>/dev/null && { PID=$p; break; }
  done
  [ -n "$PID" ] && break
done
echo "$(date +%T) PID=${PID:-none}"
[ -n "$PID" ] && grep -i "engine.dll" /proc/$PID/maps | head -1
echo "--- console ---"; tail -4 "$HOME/.steam/steam/logs/console-linux.txt" | strings
