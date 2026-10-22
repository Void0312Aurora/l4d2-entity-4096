# N26 基线：真实客户端联机与首份快照遥测

> Linux 专用服务器（原版 `engine_srv.so`）+ Proton Windows 客户端，本地同机。
> 本轮只做观测，未修改任何二进制。

## 1 连接路径：不能使用 127.0.0.1

服务端 `NET_SendPacket` 在入口调用 `netadr_s::IsLocalhost()`：

- 命中时跳到 `NET_SendLoopPacket`（`0x1B85A0`），这是**引擎进程内回环队列**，
  不会经过真实 UDP；
- 因此独立客户端连接 `127.0.0.1:27016` 永远收不到 challenge，
  抓包也只能看到请求、看不到任何回包。

改用本机非 loopback 地址即可：

```
connect 10.77.88.2:27016        # 或 192.168.123.103
```

实测合成 connect 包立即收到 29 字节 `S2C_CHALLENGE`。

服务器 `cfg/server.cfg` 自带 `sv_password "12344321"`，联机时需输入。

## 2 客户端状态

```
players : 1 humans, 0 bots (4 max) (not hibernating)
#  2 1 "Void0312" STEAM_1:1:437610251 ... active 20000 10.77.88.2:27005
# 3 "Rochelle" BOT active
# 4 "Ellis" BOT active
# 5 "Coach" BOT active
```

## 3 首份快照遥测（gdb，`CBaseServer::WriteDeltaEntities`）

| 快照 | `sv.num_edicts` | snapshot `+0x0C` | `m_nUpdatedEntries` | `m_nLength`（bit） |
|---|---|---|---|---|
| 1 | 1528 | 1528 | 9 | — |
| 2 | 1528 | 1528 | 9 | — |
| 3 | 1528 | 1528 | 8 | 512 |
| 4 | 1528 | 1528 | 8 | 512 |
| 5 | 1528 | 1528 | 6 | 512 |
| 6 | 1528 | 1528 | 6 | 512 |
| 7 | 1528 | 1528 | 7 | 512 |

要点：

- `m_nMaxEntries` 的生产值 = 快照时的 `sv.num_edicts` = **1528**，
  不是最大容量 2048 —— 与 N24 结论一致；
- `m_nUpdatedEntries` 为 6~9，随 tick 波动；
- `m_nLength` 实测 **512 bit（64 字节）**，远低于 20 位上限 1,048,575 bit。

## 4 结论与下一步

- 真实联机链路已打通，基线可用；
- 本轮不改变 `m_nLength` 的 `unresolved` 状态：512 bit 只是当前场景，
  4096 实体全量快照仍需专门测量；
- 下一步回到 N26-A/B：在原版与隔离补丁版上验证 `max_edicts=4096`
  与 `ED_Alloc` 高索引分配，暂不让 >2048 实体进入快照/网络路径。
