# Client-side signon trace for L4D2 (Proton/Windows engine.dll).
# Usage: gdb -q -batch -x client_signon_trace.gdb
# Requires: $GPID (client pid) and $BASE (engine.dll mapping start) substituted,
# then: attach $GPID; break *($BASE+0x77140) and *($BASE+0x93140).
# SetSignonState is __thiscall: this in ECX, new state at [esp+4], current at [this+0x68].
set pagination off
set confirm off
handle SIGUSR1 nostop noprint pass
handle SIGUSR2 nostop noprint pass
handle SIGCHLD nostop noprint pass
handle SIGPIPE nostop noprint pass
