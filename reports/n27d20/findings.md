# N27-D20：服务端激活完成，但缺少客户端 Signon 6 确认

## 0 摘要

本轮把观测推进到服务端：`CBaseClient::ProcessSignonStateMsg`、`SetSignonState`、
`SpawnPlayer`、`ActivatePlayer`、`SendSignonData` 与 `SendNetMsg`。

两种镜像都完成了 **SpawnPlayer + ActivatePlayer**（服务端激活），所以
“frameonly 服务端没有激活玩家”这个假设被证伪。

真正的首个差异在激活之后：

> 原版服务端收到并处理了客户端的 **SignonState 6**；
> frameonly 服务端把本地状态设为 6，但 **从未处理客户端的 6 号确认**，
> 随后只发出 7 条初始消息，原版发出 157 条（含 98 条 SVC_UserMessage）。

## 1 实验方式

使用反向启动顺序：先启动客户端并让它重试 `+connect`，再启动服务端并立刻附加
服务端 GDB 探针。原因：Steam 会把先启动的 `srcds_linux`（命令行含
`left4dead2`）误认为 App 550 已运行，从而拒绝再启动客户端。

- 端口：27020，独立于生产服务器；
- 服务端镜像：pristine `5fa15f28…`、frameonly `29175010…`（重建版）；
- 客户端：Steam 已登录，`engine.dll=0x79E00000`、`client.dll=0x74630000`；
- 采集：服务端 GDB Python 探针，JSONL 原始记录见 `data/n27d20/`。

## 2 激活序列

| 事件 | frameonly | pristine |
|---|---|---|
| `SendSignonData` | 1 | 1 |
| `ProcessSignonStateMsg` 2/3/4/5 | 有 | 有 |
| `SpawnPlayer` | 1 | 1 |
| `ActivatePlayer` | 1 | 4 |
| `SetSignonState(6)` 请求 | 有 | 有 |
| `ProcessSignonStateMsg(6)` | **0** | **1** |

frameonly 的 `signonmsg` 序列是 `[2,3,4,5]`；pristine 是 `[2,3,4,5,6]`。

结论：**服务端激活本身不是故障点**；frameonly 在“等待/处理客户端最终确认”处
断开。

## 3 激活后的消息生成

`CBaseClient::SendNetMsg` 观察到的消息类（按 vtable 归一）：

| 消息类 | frameonly | pristine |
|---|---|---|
| `SVC_UserMessage` | 3 | 98 |
| `SVC_SetView` | 2 | 13 |
| `SVC_Prefetch` | 0 | 28 |
| `SVC_Sounds` | 0 | 5 |
| `SVC_CrosshairAngle` | 0 | 4 |
| `NET_SetConVar` | 0 | 4 |
| `NET_StringCmd` | 0 | 3 |
| `NET_Tick` | 1 | 1 |
| `NET_SignonState` | 1 | 1 |
| 合计 | **7** | **157** |

frameonly 的 7 条消息全部发生在 signon 6 之前；没有进入正常游戏消息阶段。

## 4 首个缺失阶段

按“生成 → 入队 → 发送 → 接收 → 解析 → 派发”划分：

| 阶段 | frameonly 观测 | 判定 |
|---|---|---|
| 服务端激活 | SpawnPlayer + ActivatePlayer，状态到 5 | 通过 |
| 服务端生成消息 | 仅 7 条初期消息 | 在 signon 6 之后缺失 |
| 客户端 Signon 6 确认到达服务端 | `ProcessSignonStateMsg(6)` = 0 | **首个缺失** |

因此当前最优先的问题不是“某个 SVC 消息类没有生成”，而是：

> frameonly 的客户端为什么没有把 SignonState 6 确认送到服务端，或服务端为什么
> 没有处理它？

## 5 被证实/证伪

| 假设 | 结论 |
|---|---|
| frameonly 服务端未完成玩家激活 | **证伪**：SpawnPlayer + ActivatePlayer 均发生 |
| frameonly 服务端完全不生成 SVC 消息 | **证伪**：生成 UserMessage/SetView/Tick/SignonState，但仅限 signon 6 前 |
| frameonly 缺少 Signon 6 确认处理 | **证实（本窗口）** |
| 缺失消息是卡 75% 的根因 | 仍未证明；当前只确定它发生在激活之后、正常消息阶段之前 |

## 6 下一步

1. 客户端侧 hook `SendNetMsg`/`CNetChan::SendNetMsg`，确认客户端是否构造并发送
   `NET_SignonState(6)`；
2. 服务端 netchan 接收路径 hook，确认该消息是否到达但被丢弃/解析失败；
3. 只在确定“客户端没发”或“服务端没处理”之后，再回到帧字段/网络流。

## 7 工程注意

- 服务端 GDB 通过 `bash -lc` 包装后附加成功；直接 `subprocess.Popen(["sudo",...])`
  在部分情况下报 `attach PID: No such file or directory`，原因未完全定位；
- Steam 会把先启动的 `srcds_linux` 误判为 App 550，必须先启动客户端；
- 生产服务器未被触碰；实验固定 27020 端口、只杀本次 PID。
