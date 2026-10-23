# N27-D13：首个客户端差异——FULL 之后的 LevelLoadingFinished 事件缺失

## 1 IDA 定位

`client.dll` 中字符串 `OnEngineLevelLoadingFinished` 的 xref 指向
`sub_101A0A70`（RVA `0x1A0A70`），这是客户端游戏事件处理入口；它在事件
到达后会调用 `sub_1019FAE0` 并读取 `Options/server` 等状态。

## 2 事件计数

在客户端 `client.dll+0x1A0A70` 设断点，统计 FULL 前后的命中：

| 镜像 | 命中总数 | 最后一次命中 | FULL 返回时间 |
|---|---|---|---|
| 原版 | 93 | t=25.739 | t=22.529 |
| frameonly | 92 | t=22.931 | t=22.932 |

原版在 FULL 之后还有 **一次** `OnEngineLevelLoadingFinished`（t=25.739），
frameonly 没有这一次；它的最后一次命中恰好落在 FULL 返回的同一时刻。

其他里程碑两边一致：

- `LevelInitPreEntity` 均 1 次（原版 t=21.301，frameonly t=21.744）；
- `SetSignonState(5→6)` 均成功，返回后状态 6；
- `ProcessPacketEntities` 均持续到 200 次以上。

## 3 结论

这是目前观察到的**第一个客户端事件差异**：

> frameonly 缺少 FULL 之后的那次 `OnEngineLevelLoadingFinished` 事件。

它和“加载界面停在 75%”在时间上吻合，但仍需确认该事件是加载完成的原因
还是结果。

## 4 下一步

1. 在原版第 93 次命中处抓调用栈，定位是谁触发了这次事件；
2. 在 frameonly 中检查该触发函数是否执行、返回什么；
3. 若触发函数未执行，沿其调用条件反向追踪（很可能是关卡初始化完成/玩家实体就绪）；
4. 若触发函数执行但事件未派发，检查事件分发条件。
