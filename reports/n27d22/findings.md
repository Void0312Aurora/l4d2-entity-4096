# N27-D22：序列化 / 收包 / 解析四层观测（第一轮）

## 0 摘要

本轮在 D21 基础上增加了：

- 客户端 `NET_SignonState` 序列化探针；
- 服务端 `NET_SignonState::ReadFromBuffer` 探针；
- 服务端 `CNetChan::_ProcessMessages` 健康计数；
- 实验端口 UDP 抓包（tcpdump）。

结果：

- 两镜像客户端都向 `SendNetMsg` 提交 `SignonState(6)`，返回 1；
- frameonly 服务端 `ReadFromBuffer` 入口 **4 次**，pristine **5 次**；
- frameonly 服务端 `ProcessSignonStateMsg(6)` 仍为 0，pristine 有；
- 服务端 `_ProcessMessages` 计数到 900，说明收包/消息处理线程在客户端提交 6 之后仍活跃；
- tcpdump 记录 1802 个 UDP 包。

## 1 客户端序列化探针的限制

客户端 `WriteToBuffer` 探针（按 vtable slot 推断的 `engine+0x50320`）观察到：

| state | frameonly | pristine |
|---|---|---|
| 0 / 3 / 4 / 5 | 有 | 有 |
| 2 / 6 | **没有** | **没有** |

pristine 同样没有 6，说明该探针**没有覆盖到 SignonState(6) 的实际序列化路径**，
或者地址不是真正的 `WriteToBuffer`。因此不能把“没有 write 6”当成 frameonly
的差异；这属于探针缺陷。

`SendNetMsg` 对 6 的返回仍为 1（两镜像一致）。

## 2 服务端解析入口

`NET_SignonState::ReadFromBuffer`（`engine_srv.so+0xA8080`）入口调用次数：

| 镜像 | ReadFromBuffer 调用 |
|---|---:|
| frameonly | 4 |
| pristine | 5 |

与 signon 2/3/4/5（4 次）和 2/3/4/5/6（5 次）一致。

但当前 Finish 探针读取 `NET_SignonState+0x54` 得到 0，说明 `this` 指针或读取时机
尚未校准；**计数可比，state 字段暂不可用**。

## 3 健康证明与抓包

- frameonly：`_ProcessMessages` 计数 900 次，发生在客户端提交 6 之后；
- tcpdump：UDP 27020 共 1802 个包，双向均有流量（原始 pcap 未入库，大小约 392 KB）；
- 因此“服务端进程/GDB 在 6 之后完全停止工作”这一混杂因素可以排除。

## 4 第一轮结论

当前最可信的层级判断：

| 层级 | 状态 |
|---|---|
| 客户端构造 Signon 6 | 已确认 |
| 客户端调用 SendNetMsg | 已确认 |
| SendNetMsg 返回 1 | 已确认 |
| 客户端写位流 | 探针未覆盖 6（两镜像） |
| 服务端收到 Signon 6 | 未确认 |
| 服务端 ReadFromBuffer | frameonly 4 次、pristine 5 次，差 1 次 |
| 服务端 ProcessSignonStateMsg(6) | frameonly 缺失 |

因此首个**计数层面**的差异出现在服务端解析入口：frameonly 比 pristine 少一次
`ReadFromBuffer`，与缺少 6 一致；但仍需修正 state 字段读取，才能确认少的就是 6。

## 5 下一步

1. 校准服务端 `ReadFromBuffer` 的 `this` 指针与 `+0x54` 读取；
2. 客户端改用 `SendNetMsg` 内部的实际序列化调用，而不是当前错误的 `+0x50320`；
3. 在服务端 `_ProcessMessages` 记录消息类型 ID，确认 6 是否出现在类型流中；
4. 对 pcap 统计客户端提交 6 前后的上行包数量与序列号。
