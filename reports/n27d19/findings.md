# N27-D19：自动化差分体系与首个可重复差异

## 0 摘要

本轮把逐点断点改成了声明式探针、自动实验运行器和轨迹差分。两种镜像各完成一次
有效端到端实验（30 s 窗口）：

> **FULL 之后，`pristine` 客户端的 `INetMessage::Process` 派发包含
> `SVC_GameEvent`（engine.dll+0x4EE80）与 `SVC_UserMessage`（engine.dll+0x56E60）；
> `frameonly` 只派发 `NET_Tick`（+0x4E510）与 `SVC_PacketEntities`（+0x53FE0）。**

该差异可重复、由自动差分直接从原始 JSONL 得出，而不是手工抄录。

同时修正了 D15–D18 的关键误判：`0x56E60` 不是“加载完成处理函数”，而是
`SVC_UserMessage` 的 slot-3 转发器；它本身不接触 `CClientFrame`。

## 1 角色与产出

| Agent | 工作 | 状态 |
|---|---|---|
| Lead | 运行器、差分器、实验执行、报告 | 完成 |
| static-analyst | IDA 复原 0x1BC301 虚调用、RTTI/vtable/类映射 | 完成，报告与 JSON 已提交 |
| probe-engineer | 声明式探针、JSONL 采集器、离线测试 | 完成，225 项测试通过 |
| reviewer | 独立证据审查 | 完成；`reports/n27d19/review.md` |

## 2 工具

| 文件 | 作用 |
|---|---|
| `tools/n27d19/probe_config.json` | 6 个声明式探针、FULL 检测、采样上限、期望字节 |
| `tools/n27d19/gdb_probe.py` | gdb 采集器；module+RVA 归一、分阶段计数、直方图、安装正控 |
| `tools/n27d19/run_experiment.py` | 单实验入口：校验 SHA、起服、起客户端、解析模块、附加 gdb、判定有效 |
| `tools/n27d19/diff_traces.py` | 轨迹差分：只统计 post-FULL hit，输出 Markdown/JSON |
| `tools/n27d19/test_probe_schema.py` | 离线 schema/计数/直方图/安装测试 |

## 3 实验

| run | 镜像 | SHA-256 前缀 | 结果 | 事件数 |
|---|---|---|---|---|
| pristine-2 | 原版 `engine_srv.so` | `5fa15f2820ab67b9` | ok | 1003 |
| frameonly-2 | `frameonly.so` | `89152442f624339b` | ok | 844 |
| pristine-3 | 原版（重复） | `5fa15f2820ab67b9` | ok | 731 |
| frameonly-3 | `frameonly.so`（重复） | `89152442f624339b` | ok | 714 |

两轮均为 30 s 采集窗口，客户端 `engine.dll=0x79E00000`、`client.dll=0x74630000`，
引擎/客户端模块基址运行时记录在 `metadata.json`。原始事件与 gdb 日志见
`data/n27d19/runs/<run>/events.jsonl.gz`、`gdb.log.gz`。

## 4 自动差分事实（post-FULL）

### 4.1 派发目标

| target | pristine | frameonly |
|---|---|---|
| `engine.dll+0x4E510` NET_Tick | 628 | 715 |
| `engine.dll+0x53FE0` SVC_PacketEntities | 628 | 715 |
| `engine.dll+0x53EF0` 未分类 SVC | 136 | **0** |
| `engine.dll+0x4EE80` SVC_GameEvent | 57 | **0** |
| `engine.dll+0x56E60` SVC_UserMessage | 50 | **0** |
| `engine.dll+0x53E40` 未分类 SVC | 28 | 0 |
| `engine.dll+0x26E0` 未分类 | 9 | 0 |
| `engine.dll+0x4E440` 未分类 | 6 | 0 |

frameonly 的 post-FULL 目标集合只有 `{NET_Tick, SVC_PacketEntities}`，其余 SVC
消息派发为零。两次独立重复运行（pristine-2/3、frameonly-2/3）得到同一结论。

### 4.2 对象证据

`SVC_UserMessage` 目标的 sampled receiver：

```
target=engine.dll+0x56E60  edx=engine.dll+0x358EEC  esi=37800528  hits=26
```

`edx` 与静态分析得到的 `SVC_UserMessage` vtable（RVA `0x358EEC`）一致，
证明该目标确实是 `SVC_UserMessage` 的 slot-3 覆写，而不是帧或加载函数。

### 4.3 时间线（pristine）

```
FULL               17:03:16.134
SVC_GameEvent      +0.095 s
NET_Tick           +0.107 s
SVC_PacketEntities +0.111 s
SVC_UserMessage    +3.217 s
加载完成事件        +3.329 s
```

frameonly 在 FULL 后只有 Tick/PacketEntities，没有 GameEvent/UserMessage，
也没有加载完成事件。

## 5 被证实/证伪的假设

| 假设 | 结论 | 依据 |
|---|---|---|
| `0x56E60` 是加载完成路径函数 | **证伪** | RTTI/vtable：它是 `SVC_UserMessage` slot 3；D15–D18 的框架不再成立 |
| frameonly “从未调用” `0x56E60` | **证伪** | 全程直方图 frameonly 有 3 次（FULL 前；reviewer 核对）；准确说法是 **post-FULL 为 0** |
| frameonly 在条件分支提前退出 | **证伪** | D18 已撤销；本轮 post-FULL 探针正常命中 |
| frameonly 缺少 post-FULL SVC_GameEvent/UserMessage 派发 | **证实（本窗口内稳定）** | 自动差分表 |
| 缺少这两个消息就是卡 75% 的根因 | **未证实** | 可能是客户端未 active 导致的服务器抑制，或客户端消息表/接收问题 |

## 6 因果性评估

当前只能确定“控制流差异”，不能确定“原发数据错误”：

- `SVC_GameEvent` 在 FULL 后约 95 ms 就缺失，早于加载完成事件约 3.2 s；
- 但若 frameonly 客户端没有被服务器视为 active，服务器本就不会向它发送这些
  消息，于是缺失是“未加载”的结果而非原因；
- `SVC_PacketEntities` 仍在派发并进入 `CL_ProcessPacketEntities`，说明实体
  更新通路本身在工作，问题更可能位于 **消息选择/发送条件** 或客户端状态，
  而不是 `CClientFrame` 的虚调用点。

因此下一步必须区分：

1. 服务器是否向 frameonly 客户端发送了 GameEvent/UserMessage；
2. 若发送了，客户端 `FindNetMessage`/`ReadFromBuffer` 是否拒绝；
3. 若没发送，服务器的客户端状态（active/signon）与 pristine 有何不同。

## 7 已修正的历史结论

- D15/D16 的“`sub_10056E60` 是加载完成路径”不成立：它是 UserMessage 转发器；
- D17 的“提前离开 `sub_101BBCF0`”已在 D18 撤销；
- D18 的“frameonly 从未命中 `0x56E60`”应改为“post-FULL 未命中”；
- D18 将 `EDX`/`ESI` 直接称为 vtable/对象，本轮由 RTTI 与 vtable 交叉引用证实
  后才保留这一称呼。

## 8 复现

```bash
cd /home/void0312/Workshop/l4d2-entity-4096
python3 tools/n27d19/test_probe_schema.py
python3 tools/n27d19/run_experiment.py --image pristine  --out /tmp/n27d19-runs/pristine-2  --duration 30
python3 tools/n27d19/run_experiment.py --image frameonly --out /tmp/n27d19-runs/frameonly-2 --duration 30
python3 tools/n27d19/diff_traces.py \
  --runs /tmp/n27d19-runs/pristine-2 /tmp/n27d19-runs/frameonly-2 \
  --out reports/n27d19/auto-diff.md --json data/n27d19/auto-diff.json
```

## 9 下一步最有价值的实验

在 **服务端** 的 netchan 发送路径记录每条消息的类型 ID 与目标客户端，
对 pristine/frameonly 做同样的 30 s 对照：

- 若 frameonly 服务端根本没有发送 GameEvent/UserMessage → 查服务器客户端状态机
  （active/signon、`CBaseClient` 状态字段）；
- 若发送了而客户端未派发 → 查客户端 `CNetChan::ProcessMessages` 的消息表查找
  与 `ReadFromBuffer` 返回值；
- 两种情况都不需要再扩大 `CClientFrame` 的断点范围。

## 10 独立审查结论（reviewer）

| 检查项 | 结论 |
|---|---|
| 分阶段采样，无累计计数门 | PASS |
| 地址校验/回退/字节校验 | PASS（3 个探针仅 2 字节前缀，见 review） |
| frameonly post-FULL 只有 Tick/PacketEntities | PASS（原始 JSONL 复核，采样未截断） |
| `0x56E60` 是 SVC_UserMessage 而非加载函数 | PASS（RTTI/vtable 独立复核） |
| 缺失消息与卡加载的因果性 | INCONCLUSIVE |

reviewer 修正：

- `frameonly` 的 FULL 前 `0x56E60` 命中实际为 **3** 次（非 12）；
- `counts.histograms` 是全程直方图，不能与 post-FULL 差分计数直接比较；
- 旧 `client.console.log` 跨 run 累积，`connect_ok` 已改为按本次偏移读取；
- `clientEventBranch` 的 `expected_post_full_hits=0` 语义错误，已改为不设期望；
- runner 已补上 `full_state_seen`、gdb 返回码、安装失败判定。

因果性仍需服务端发送/客户端接收证据，当前证据不能区分“缺失导致卡加载”与
“客户端未 active 导致服务器不发送”。
