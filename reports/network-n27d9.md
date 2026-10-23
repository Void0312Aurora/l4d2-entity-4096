# N27-D9：客户端侧 gdb 跟踪，故障点移到 FULL 之后

## 1 客户端 instrumentation 路径

Frida 无法附加 Proton 进程（`ProcessNotRespondingError`），改用 gdb 直接附加
`left4dead2.exe`，按 `engine.dll` 映射基址 + RVA 下断点：

| 函数 | RVA | 说明 |
|---|---|---|
| `CBaseClientState::ProcessPacketEntities` | `0x77140` | 打印 "Receiving uncompressed update" 的函数 |
| `CClientState::SetSignonState` | `0x93140` | `__thiscall`：this 在 ECX，状态字段 `this+0x68`，新状态 `[esp+4]` |

## 2 原版客户端

```
SETSIGNON cur=0 new=1
SETSIGNON cur=1 new=2
SETSIGNON cur=2 new=3
SETSIGNON cur=3 new=4
SETSIGNON cur=4 new=5
PPE n=1
SETSIGNON cur=5 new=6
```

## 3 frameonly 客户端

同一次启动、尽早附加：

```
SETSIGNON cur=0 new=1
SETSIGNON cur=1 new=2
SETSIGNON cur=2 new=3
SETSIGNON cur=3 new=4
SETSIGNON cur=4 new=5
PPE n=1
SETSIGNON cur=5 new=6
PPE n=2 ... n=671
```

**frameonly 的客户端同样完成 5→6，并持续处理 PacketEntities**；但画面仍停在
“正在加入…载入中 75%”。

## 4 结论

D8 的“客户端没有回送 signon 6”不再成立：客户端确实进入 FULL，并持续消费
实体更新。故障发生在 **FULL 之后的关卡/世界加载阶段**，不是连接、认证或 signon。

下一步应跟踪 FULL 之后的客户端路径：

1. 客户端 `LevelInit`/地图加载完成回调；
2. 首个玩家实体/出生点相关实体是否到达；
3. 服务端 spawn 相关实体数据（`svc_PacketEntities` 中 player/entity 条目）
   与客户端的消费结果。

## 5 附带修正

`WriteDeltaEntities` 的 Frida 参数已按 Source 约定重命名：
`args[2] = target`，`args[3] = baseline`。
