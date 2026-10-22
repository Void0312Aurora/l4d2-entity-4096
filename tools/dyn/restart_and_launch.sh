#!/usr/bin/env bash
set -u
. "$(dirname "$0")/env.sh"
STEAM_SH="$HOME/.steam/debian-installation/steam.sh"
STEAM_BIN="$HOME/.steam/debian-installation/ubuntu12_32/steam"
echo "$(date +%T) shutting down steam"
"$STEAM_BIN" -shutdown >/dev/null 2>&1
sleep 8
echo "$(date +%T) restarting steam"
setsid "$STEAM_SH" -silent >/tmp/steam_restart.log 2>&1 &
sleep 40
echo "$(date +%T) launching app 550 (Proton mapping now active)"
setsid "$STEAM_SH" -applaunch 550 -insecure -novid -console +map c1m1_hotel >/tmp/proton_launch.log 2>&1 &
PID=""
for i in $(seq 1 48); do
  sleep 5
  for p in $(ls /proc | grep -E '^[0-9]+$'); do
    if grep -q "engine.dll" /proc/$p/maps 2>/dev/null; then PID=$p; break; fi
  done
  [ -n "$PID" ] && break
done
echo "$(date +%T) PROTON_GAME_PID=${PID:-none}"
if [ -n "$PID" ]; then
  echo "--- engine.dll mapping ---"; grep -i "engine.dll" /proc/$PID/maps | head -2
  echo "--- cmdline ---"; tr '\0' ' ' < /proc/$PID/cmdline | head -c 160; echo
fi
