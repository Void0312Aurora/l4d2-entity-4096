# N27-D21 Phase A：实验环境与镜像等价性

## 1 目标

在追踪客户端 Signon 6 确认之前，先回答两个前置问题：

1. 当前环境能否让原版客户端**正常完成加载**（正向控制）；
2. D20 使用的 frameonly 重建镜像是否只包含预期的 F1/F2/F3 改动。

## 2 正向控制结果：仍不成立

使用两种启动顺序、均不附加任何调试器：

| 顺序 | 服务端 | 客户端结果 |
|---|---|---|
| client-first | pristine | `console.log` 最后为 `Receiving uncompressed update from server` |
| server-first | pristine | 同上 |

服务端均已 `Host_NewGame`，并发送 `sv_lan 1`、`sv_password ""`、`sv_consistency 0`。
两种顺序下原版客户端都没有越过错载入点。

因此当前环境**不能作为“正常完成加载”的正向控制**，也不能据此继续断言
Signon 6 缺失是 frameonly 特有原因。

可能原因（尚未区分）：

- Steam/客户端运行时状态在多次重启后发生变化；
- 服务端启动参数或客户端连接重试状态与 D19 不一致；
- 截图/窗口观测失败，实际画面状态未被记录。

`import -window root` 在当前 Xwayland 下返回
`UnableToReadXWindowImage 'root': Resource temporarily unavailable`，
需要改为按游戏窗口 ID 截图或使用 x11grab；本轮未能取得画面证据。

## 3 镜像等价性

D20 的 frameonly 由当前构建器重建，SHA-256 前缀 `29175010`；D19 的
`89152442` 镜像已随 `/tmp` 清理丢失，无法做逐字节对照。

对 `pristine → frameonly(29175010)` 做逐字节差分：

- 变更字节：**59**；
- 变更范围：`0xEA996`–`0x1DE525`；
- 所有变更偏移都落在 CSV 计划行内：
  - F1：4 字节；
  - F3：7 字节；
  - 帧成员位移行：48 字节；
- **没有计划外的变更字节**。

结论：重建镜像只应用了预期的帧大小/位图/字段位移补丁，没有额外代码改动。
但它与 D19 旧镜像的二进制等价性仍无法证明，因为旧文件不存在。

## 4 对 D21 Phase B 的影响

在正向控制恢复之前，追踪“客户端 Signon 6 确认在哪一步消失”会面临解释风险：
缺失可能来自环境异常，而不是 frameonly 补丁。

建议先恢复正向控制，再执行双端闭环：

1. 用游戏窗口 ID 截图，确认原版是否真正进入地图；
2. 对比 D19 当时的客户端/服务端启动参数与当前差异；
3. 确认后，再按计划 hook 客户端 `SetSignonState(6)`、`SendNetMsg` 入队、
   服务端接收/解析/`ProcessSignonStateMsg(6)`。

## 5 本轮结论

- D20 的服务端激活与消息计数结论保留；
- D20 报告已修正“7 条消息全部在 signon 6 之前”的表述；
- 镜像重建未发现计划外改动；
- **D21 Phase B 暂不开始**，因为原版正向控制仍卡在 75%，此时无法把后续差异归因于 frameonly。

## 6 按 `CBaseClient*` 归组后的修正

D20 摘要把原版 `ActivatePlayer=4` 与 frameonly 的 1 直接比较是不正确的。按客户端
对象地址归组后：

| 连接对象（pristine） | 事件序列 |
|---|---|
| `259450832`（首次连接） | signon 2 → 3 → 4 → SpawnPlayer → 5 → ActivatePlayer → **signon 6** |
| `260890336` | 仅 SetSignonState/ActivatePlayer（重连残留） |
| `261424880` | 同上 |
| `261672368` | 同上 |

frameonly 只有 `256460656` 一个对象：

`signon 2 → 3 → 4 → SpawnPlayer → 5 → ActivatePlayer`，**没有 signon 6**。

因此正确表述应为：**两者首次连接都完成 SpawnPlayer/ActivatePlayer；原版首次连接
随后处理 signon 6，frameonly 没有。** 其余 `ActivatePlayer` 来自重连对象，不应计入
同一连接的协议序列。

## 7 `SendNetMsg` 也按连接对象归组

| 连接对象 | 消息数 | 主要类型 |
|---|---:|---|
| frameonly `256460656` | 7 | UserMessage 3、SetView 2、Tick 1、SignonState 1 |
| pristine `259450832`（首次） | 58 | UserMessage 35、Prefetch 7、Sounds 5 |
| pristine `260890336` | 34 | 重连对象 |
| pristine `261424880` | 33 | 重连对象 |
| pristine `261672368` | 32 | 重连对象 |

因此原版 157 条不能直接与 frameonly 7 条比较；首次连接的正确对比是 **58 vs 7**。
