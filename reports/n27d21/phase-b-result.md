# N27-D21 Phase B 结果：客户端发送了 Signon 6，服务端没有处理

## 0 结论

在相同采集方式下：

- frameonly 客户端：发送 `NET_SignonState(2/3/4/5/6)`，6 的 `SendNetMsg` 返回 1，
  本地状态最终为 6；
- frameonly 服务端：只处理 signon 2/3/4/5，**没有 6**；
- pristine 客户端：发送序列相同，6 返回 1；
- pristine 服务端：处理 2/3/4/5/**6**。

因此首个缺失阶段已经不在客户端发送侧，而在：

> **服务端接收/解析/派发 NET_SignonState(6) 的阶段，或该消息在网络上的交付阶段。**

## 1 客户端证据

| 事件 | frameonly | pristine |
|---|---|---|
| `send_signonstate_return(2)` | 1 | 1 |
| `(3)` | 0 | 0 |
| `(4)` | 1 | 1 |
| `(5)` | 1 | 1 |
| `(6)` | **1** | **1** |
| `SetSignonState(6)` 返回 | 1 | 1 |
| 返回后本地状态 | **6** | **6** |

注意：State 3 的发送返回 0，但服务端仍处理了 3，说明该返回值不是“消息是否送达”的
可靠判据；不能把返回 0 当成丢失原因。

## 2 服务端证据

| 事件 | frameonly | pristine |
|---|---|---|
| `ProcessSignonStateMsg(2/3/4/5)` | 有 | 有 |
| `ProcessSignonStateMsg(6)` | **无** | **有** |
| 首次连接 `SendNetMsg` 数 | 7 | 58 |

frameonly 服务端首次连接的完整序列仍是：

`signon 2 → 3 → 4 → SpawnPlayer → 5 → ActivatePlayer`，无 6。

## 3 解释

客户端确实构造并提交了 6 号消息，且本地状态已到 6；所以此前“客户端没有发送 6”
的可能性被排除。

剩余可能：

1. 6 号消息在客户端 netchan 发送缓冲中没有真正上线（返回 1 只代表接受）；
2. 已在网络上丢失（可靠性/分片/序列号问题）；
3. 已到达服务端，但服务端 netchan 解析失败或未派发；
4. 已解析，但被状态过滤，未进入 `ProcessSignonStateMsg`。

当前证据无法区分 1–4；需要服务端收包/解析入口的观测或抓包。

## 4 下一步

在服务端 `CNetChan::_ProcessMessages` 与 `NET_SignonState::ReadFromBuffer`
路径记录：

- 收到的消息类型 ID；
- 对应连接对象；
- 解析返回值；
- 是否进入 `ProcessSignonStateMsg`。

若 6 号类型根本没有出现在服务端解析入口，则优先查传输/可靠性；若出现但解析失败，
查位流；若解析成功但未派发，查状态过滤。

## 5 有效性

- 本轮 frameonly/pristine 各一次；客户端探针命中 2–5 全部阶段，安装正控有效；
- 功能正控（原版进入地图）仍未建立，因此不能把该协议差异直接归因于 75% 卡载入；
- `SendNetMsg` 返回 1 不能证明数据包已到达服务端。
