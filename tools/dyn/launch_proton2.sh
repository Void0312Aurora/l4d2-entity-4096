#!/usr/bin/env bash
set -u
. "$(dirname "$0")/env.sh"
STEAM_SH="$HOME/.steam/debian-installation/steam.sh"
echo "$(date +%T) start steam"
setsid "$STEAM_SH" -silent >/tmp/steam3.log 2>&1 &
sleep 45
echo "$(date +%T) applaunch 550"
setsid "$STEAM_SH" -applaunch 550 >/tmp/launch4.log 2>&1 &
PID=""
for i in $(seq 1 48); do
  sleep 5
  for p in $(ls /proc | grep -E '^[0-9]+$'); do
    grep -q "engine.dll" /proc/$p/maps 2>/dev/null && { PID=$p; break; }
  done
  [ -n "$PID" ] && break
done
echo "$(date +%T) PROTON_GAME_PID=${PID:-none}"
if [ -n "$PID" ]; then
  echo "--- engine.dll mapping ---"; grep -i "engine.dll" /proc/$PID/maps | head -2
  echo "--- cmdline ---"; tr '\0' ' ' < /proc/$PID/cmdline | head -c 160; echo
fi
