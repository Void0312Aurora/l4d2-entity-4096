#!/usr/bin/env bash
# 动态分析环境（Proton + L4D2 客户端 build 23990068）
export DISPLAY="${DISPLAY:-:0}"
XA="$(ls -t /run/user/1000/.mutter-Xwaylandauth.* 2>/dev/null | head -1)"
export XAUTHORITY="${XAUTHORITY:-$XA}"
export CLIENT="/run/media/void0312/566EBEB06EBE87EF/SteamLibrary/steamapps/common/Left 4 Dead 2"
export PROTON="$HOME/.steam/steam/steamapps/common/Proton - Experimental/proton"
export STEAM_COMPAT_DATA_PATH="$HOME/.steam/steam/steamapps/compatdata/550"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$HOME/.steam/steam"
