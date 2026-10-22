#!/usr/bin/env bash
# 通过 Steam 启动 L4D2（离线、控制台、单人地图）
set -e
. "$(dirname "$0")/env.sh"
steam -applaunch 550 -insecure -console -novid +map c1m1_hotel >/tmp/l4d2_launch.log 2>&1
echo "launch requested (log: /tmp/l4d2_launch.log)"
