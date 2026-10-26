# N27-D48：修复 `g_EdictFreeTime` 越界；高索引服务器连接达到 active

## 1 根因

原版服务端的 `_ZL15g_EdictFreeTime` 位于 `0x39E4C0`，大小 `0x2000`，即 2048 个
`float`。数组紧邻 `sv_useexplicitdelete`（`0x3A04C0`）。`ED_Free` 释放索引 2048
的实体时写入 `g_EdictFreeTime[0x800]`，地址恰好越过数组并覆盖相邻 ConVar。硬件
watchpoint 捕获到 `ED_Free`、`esi=0x800` 时该全局被写成 `0x3F844445`；随后客户端连接
触发 `Host_CountVariablesWithFlags -> Host_BuildConVarUpdateMessage -> SendServerInfo`
并在间接调用处崩溃。

## 2 构建修复

`tools/linux/build_n27_full.py` 现在把 8 处数组引用（文件/ELF 地址
`0x1C6839, 0x1C6863, 0x1C6989, 0x1C6A28, 0x1C6AD6, 0x1C6B3B, 0x1C6B85,
0x1C6C8D`）从 `0x39E4C0` 改到 `0x3FA000`，并把数组和 ELF 符号大小扩到 `0x4000`
（4096 个 `float`）。RW `PT_LOAD` 的 `p_memsz` 扩到 `0xD24D0`，终点 `0x3FE000`；
`.bss` 同步扩展，仍与 `0x400000` 的 RX stub 段保持间隔。

必须使用完整集成入口 `tools/linux/build_n27_4096.py`：它在 full builder 之后再应用
两处 `0x800 -> 0x1000` 容量补丁。最终候选 `/tmp/n27/engine_srv_n27_4096_free.so` 的
SHA-256 为 `22d8e8a8366c81b561c9459005a1e314c811e708a2483075e5879c31dc051154`。
`verify_n27_patched.py` 通过；`readelf` 显示符号地址/大小为 `0x3FA000/16384`，RW
加载段终点为 `0x3FE000`。

有一次验证误用了 `build_n27_full.py` 的中间产物，漏掉最后两处容量补丁；它到达
`idx=2047` 后报 `ED_Alloc: no free edicts`。改用完整集成入口后，高索引分配成功。
该错误产物没有保留在游戏目录。

## 3 运行结果

使用 `client.4096.dll`（SHA-256 `be3e52cdbce7203238c97ed36036374672588297cd2f9808bf741e0db9762b69`）
和集成服务端候选做 direct-Proton 联机：

```text
D50_TARGET idx=2048
D50_DONE idx=2048
Client "Void0312" connected
players : 1 humans, 0 bots
#  2 1 "Void0312" ... active ...
Receiving uncompressed update from server
```

服务端保持运行，没有重现 `Host_CountVariablesWithFlags` 崩溃。此运行测试使用的
服务端 SHA-256 为 `d25abdba0a04ccd85681fc0f4f5e0ffd99f33ae9c11e72e68ede9e11d037521d`；
最终构建随后只更新了未加载的 `.symtab` 中该局部数组符号的 `st_value/st_size`。
两版的三个 `PT_LOAD` 段及文件内容逐字节相同。

PTY keep-alive 中继也修复了后台子进程继承捕获管道、令 `subprocess.run()` 无法返回的问题。
一次误用中间产物的测试和一次因该管道问题挂起的测试均已停止；之后的完整测试成功结束。
测试结束后，游戏安装目录恢复为原始 `client.dll` SHA-256
`c0a8e1e88f7312db11bcfd4b0ec574d224a34b2d9a615d6088b28335eeb4af1f`，隔离服务器恢复为原始
`engine_srv.so` SHA-256 `d0975da61fe8ae85e7dac0b489cd1e0deb48c4a5867e8cea498b760166ecfd5e`；无测试进程残留。

## 4 结论边界与下一步

这证明候选客户端能与持有服务器端 `idx=2048` 实体的候选服务器完成连接并达到
`active`，也证明此前的 ConVar 越界崩溃已被本次构建修复。客户端日志只确认收到服务器
更新包，没有直接读取客户端实体列表中对应槽位，因此**还不能声称客户端已正确创建或
解析索引 2048 的实体**。网络 13-bit 格式、更新/删除/重用，以及 `idx=4095` 边界仍须
分别验收。

测试 PTY 和客户端日志保存在当次 `/tmp/n27-client-highindex-1792940833/` 目录；本报告保留
经筛选的判定行，避免将无关主机信息带入仓库。
