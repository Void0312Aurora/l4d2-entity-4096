# N27-D22 第三轮：Signon 6 已成功写入客户端发送缓冲

## 0 结论

修正客户端 `NET_SignonState::WriteToBuffer` 地址后（真正路径是 vtable slot 6，
`engine.dll+0x1D8110`，不是之前的 `+0x50320`），得到：

| 镜像 | 客户端 WriteToBuffer 返回值 | 服务端解码 |
|---|---|---|
| frameonly | 2→1, 3→1, 4→1, 5→1, **6→1** | 2,3,4,5 |
| pristine | 2→1, 3→1, 4→1, 5→1, **6→1** | 2,3,4,5,**6** |

因此 client-side serialization 不再是候选差异点：

> frameonly 客户端已把 `NET_SignonState(6)` 成功写入发送缓冲；该消息没有进入
> 服务端 `ReadFromBuffer`。

首个缺失阶段现在位于：

> **客户端发送缓冲之后：datagram 实际发送、网络传输、服务端收包/消息分发。**

## 1 修正内容

- 客户端 `WriteToBuffer` 真实地址来自 `NET_SignonState` vtable slot 6：
  `engine.dll+0x1D8110`；
- `SendNetMsg`（`engine+0x1B19B0`）选择 netchan 内嵌 `bf_write` 后调用该虚函数；
- 旧探针 `+0x50320` 只命中部分状态，且 pristine 也缺 6，已确认是错误地址；
- 服务端 `ReadFin.state` 统一改为 `+0x4C`，与 `fields["0x4c"]` 一致。

## 2 当前证据链

| 环节 | frameonly | pristine |
|---|---|---|
| 客户端本地状态到 6 | 有 | 有 |
| 客户端提交 SendNetMsg(6) | 有 | 有 |
| 客户端 WriteToBuffer(6) | **成功（1）** | **成功（1）** |
| 服务端 ReadFromBuffer(6) | 无 | 有 |
| 服务端 ProcessSignonStateMsg(6) | 无 | 有 |

## 3 剩余可能

消息已写入客户端缓冲，但在以下任一环节丢失：

1. netchan 没有把该缓冲内容组成 datagram 发出；
2. 已发出但 UDP 丢包/未重传；
3. 服务端收到包，但包内消息类型流中没有 6；
4. 服务端解析到 6 之前被过滤（当前 `ReadFromBuffer` 未命中，说明还未到解析）。

## 4 下一步

1. 客户端 hook `SendDatagram` / 发包路径，记录 Signon 6 写入后的出站序列号与返回值；
2. 服务端 hook 收到包的 message type 流，确认 6 是否出现在包内；
3. 用 pcap 按连接、方向、序列号统计提交 6 前后的上行包与重传；
4. 对比 Signon 5 成功交付到 Signon 6 提交后的几个发送周期。

## 5 限制

- WriteToBuffer 返回 1 只证明写入缓冲成功，不证明 datagram 已发送或到达；
- 每镜像仍为一次运行，需要重复；
- 原版功能正控（进入地图）仍未建立。
