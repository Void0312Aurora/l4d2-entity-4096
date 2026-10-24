# N27-D26：BaselineAck 已收到并处理，但之后没有 Signon 6

## 0 结论

39 位前缀被验证为 `CLC_BaselineAck`（type 11, tick, nr=0）。服务端探针确认：

| 镜像 | 首个 BaselineAck | 处理 | BaselineAck 总数 | Signon 解码 |
|---|---|---|---|---:|---|
| frameonly | tick 660, nr 0 | `ProcessBaselineAck` 命中 | **1** | 2,3,4,5 |
| pristine | tick 671, nr 0 | 命中 | **31**（后续持续） | 2,3,4,5,6 |

因此：

- frameonly 服务端**确实收到并处理了 BaselineAck**；
- 之后既没有后续 BaselineAck，也没有 Signon 6；
- pristine 在 Signon 6 之后仍持续收到大量 BaselineAck。

此前“服务器连 BaselineAck 都没收到”的假设被排除。

## 1 字段正控

`CLC_BaselineAck::ReadFromBuffer`（`engine_srv.so+0x9C230`）返回对象：

- `+0x4C` = baseline tick；
- `+0x50` = baseline nr。

随后 `CBaseClient::ProcessBaselineAck`（`+0xE9030`）读到相同 tick/nr，
构成独立正控。

## 2 关键现象

frameonly 的时间顺序是：

```
BaselineAck(tick=660) ReadFromBuffer 成功
→ ProcessBaselineAck 命中
→ 无后续 BaselineAck
→ 无 SignonState 6
```

pristine 是：

```
BaselineAck(tick=671) 成功
→ SignonState 6 成功
→ 后续大量 BaselineAck 持续
```

这说明 frameonly 不是“BaselineAck 完全没到”，而是**首条 ACK 之后消息流没有继续到 Signon 6**。

## 3 不能直接下的结论

- tick 660 vs 671 的差异很可能只是运行时机不同，不能据此认定 ACK 非法；
- 尚未证明 BaselineAck 与 Signon 6 在**同一个 datagram / 同一个消息流**中；
- 尚未证明 `ProcessBaselineAck` 的返回/状态处理导致流提前结束；
- 仍可能是 ACK 正常、后续消息在组包/传输/服务端重组时丢失。

## 4 下一步

1. 在 `CNetChan::_ProcessMessages` 记录每个消息类型与读取位置，确认 ACK 后是否尝试读取 type 7；
2. 证明 ACK 与 Signon 6 是否在同一出站 datagram；
3. 对比 `ProcessBaselineAck` 返回后服务端 baseline/ACK 状态；
4. 检查 frameonly 为何首条 ACK 后不再产生后续 BaselineAck。

## 5 限制

- 每镜像一次；
- 功能正控仍未建立；
- 当前只是把差异推进到“首条 BaselineAck 之后的消息流”。
