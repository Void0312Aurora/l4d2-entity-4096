#!/usr/bin/env bash
# 等待 Steam 更新完成 -> 校验 engine.dll -> 启动游戏 -> 报告 PID 与基址
set -u
. "$(dirname "$0")/env.sh"
MANI="/run/media/void0312/566EBEB06EBE87EF/SteamLibrary/steamapps/appmanifest_550.acf"
STEAM_SH="$HOME/.steam/debian-installation/steam.sh"

for i in $(seq 1 80); do
  flags=$(grep -m1 '"StateFlags"' "$MANI" | tr -dc '0-9')
  bd=$(grep -m1 '"BytesDownloaded"' "$MANI" | tr -dc '0-9')
  bt=$(grep -m1 '"BytesToDownload"' "$MANI" | tr -dc '0-9')
  echo "$(date +%T) StateFlags=$flags downloaded=${bd:-0}/${bt:-0}"
  if [ "$flags" = "4" ] || { [ -n "${bt:-}" ] && [ "${bd:-0}" = "$bt" ]; }; then break; fi
  sleep 30
done
echo "$(date +%T) update settled; engine.dll hash:"
sha256sum "$CLIENT/bin/engine.dll"
setsid "$STEAM_SH" -applaunch 550 -insecure -novid -console +map c1m1_hotel >/tmp/l4d2_launch2.log 2>&1 &
for i in $(seq 1 40); do
  sleep 5
  PID=$(ps -eo pid,args --no-headers | grep -i "Left 4 Dead 2/left4dead2.exe" | grep -v grep | awk '{print $1}' | head -1)
  [ -n "$PID" ] && break
done
echo "GAME_PID=${PID:-none}"
if [ -n "${PID:-}" ]; then
  echo "--- engine.dll mapping ---"
  grep -i "engine.dll" /proc/$PID/maps | head -3
fi
