# N27-D12：客户端关卡初始化里程碑在两种镜像下相同

## 1 修正 client.dll 基址解析

此前用 `grep client.dll` 会先匹配到 `lsteamclient.dll`，导致
`LevelInitPreEntity` 断点落在错误模块。现改为匹配 `bin/client.dll`。

客户端实际基址：`client.dll=0x74630000`，`engine.dll=0x79e00000`。
`LevelInitPreEntity` 的 RVA 为 `0x179DB0`（IDA 校验）。

## 2 事件时间线

原版：

```
t=16.273 ENTER signon before=2 req=3
t=21.466 ENTER signon before=3 req=4
t=21.503 ENTER signon before=4 req=5
t=21.571 ENTER levelinit n=1
t=22.408 ENTER ppe n=1
t=22.428 ENTER signon before=5 req=6
t=22.805 RETURN signon after=6
t=22.858 ENTER ppe n=2
...
t=33.633 ENTER ppe n=200
```

frameonly：

```
t=14.989 ENTER signon before=2 req=3
t=20.108 ENTER signon before=3 req=4
t=20.143 ENTER signon before=4 req=5
t=20.218 ENTER levelinit n=1
t=21.018 ENTER ppe n=1
t=21.036 ENTER signon before=5 req=6
t=21.384 RETURN signon after=6
t=21.461 ENTER ppe n=2
...
t=36.317 ENTER ppe n=300
```

**两者在 LevelInitPreEntity、FULL、PPE 前 200 次调用上完全同构**，只有时间差
（启动速度不同）。因此第一处差异发生在这些事件之后：玩家实体就绪、
`LevelInitPostEntity` 或加载界面关闭。

## 3 当前边界

- 服务端：帧分配、快照编码、发送均执行；
- 客户端：连接、signon、FULL 持续、LevelInitPreEntity、PPE 处理均正常；
- 差异只在 **FULL 后的世界加载完成条件/加载界面解除**；
- 尚不能区分“玩家实体未创建”与“加载完成通知未发出”。

## 4 下一步

1. 在 `client.dll` 中按 `LevelInitPreEntity` 的调用者向上追溯，定位
   `LevelInitPostEntity` 对应路径（可能不以字符串形式存在）；
2. 跟踪本地玩家实体创建/绑定（`CBasePlayer`/本地玩家索引）；
3. 跟踪 `m_loadingProgress` 与加载界面关闭通知；
4. 只保留第一个出现差异的事件，不再增加无判据的断点。
