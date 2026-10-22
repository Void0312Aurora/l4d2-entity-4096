#!/usr/bin/env bash
# 重新生成 Linux 服务端分析证据（不修改任何二进制）
# 用法: tools/linux/extract_evidence.sh [输出目录]
set -euo pipefail
SO="${SO:-$HOME/l4d2_server/bin/engine_srv.so}"
OUT="${1:-evidence/linux}"
mkdir -p "$OUT"
echo "[1/5] 身份"
sha256sum "$SO" | tee "$OUT/engine_srv.sha256"
readelf -n "$SO" > "$OUT/engine_srv.notes.txt"
readelf -SW "$SO" > "$OUT/engine_srv.sections.txt"

echo "[2/5] 符号表"
readelf -sW "$SO" > "$OUT/engine_srv.syms.txt"

echo "[3/5] 反汇编快照"
objdump -drwC -Mintel --start-address=0x1EDE70 --stop-address=0x1EEAA0 "$SO" > "$OUT/spawnserver.asm"
objdump -drwC -Mintel --start-address=0x1C6820 --stop-address=0x1C6D00 "$SO" > "$OUT/ed_alloc_edictnum.asm"
objdump -drwC -Mintel --start-address=0x9A300  --stop-address=0x9A6C7  "$SO" > "$OUT/packet-writer.asm"
objdump -drwC -Mintel --start-address=0xA5170  --stop-address=0xA5A67  "$SO" > "$OUT/packet-reader.asm"

echo "[4/5] 容量全局引用清单"
objdump -drwC -Mintel "$SO" > /tmp/_eng.dis
grep -nE "3a7f50|3a816c|3a8170|3a8174|3a8178" /tmp/_eng.dis > "$OUT/capacity_refs.txt"
grep -cE "\+0x210\]" /tmp/_eng.dis > "$OUT/rels_0x210.count" || true

echo "[5/5] 清单"
sha256sum "$OUT"/*.asm > "$OUT/asm.sha256"
echo "done -> $OUT"
