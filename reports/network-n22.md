# N22：Linux 服务端容量初始化的动态证据（第一阶段闭环）

> 目标：回答 N21 遗留的关键疑问——`0x3A7F50` 与 `0x3A8170` 到底是不是同一个东西，
> 以及 `SpawnServer` 在什么时刻初始化 `max_edicts`。本报告用 gdb 在真实地图加载中取证。

## 0 二进制身份（首次固定）

| 项 | 值 |
|---|---|
| 文件 | `~/l4d2_server/bin/engine_srv.so` |
| SHA-256 | `5fa15f2820ab67b955ff227a20dbb3fda54d463f3799f33d71b6fd6f38e309b7` |
| Build ID | `91c46deefb839f46c317eee10964c07222f83186` |
| 服务端 build | 17033453 |
| 大小 | 4,051,241 B |

反汇编快照已固化：`/tmp/spawnserver.asm`（690 行，0x1EDE70–0x1EEAA0）、
`/tmp/packet-writer.asm`（319 行，0x9A300–0x9A6C7）。

## 1 关键发现：`0x3A8170` 就是 `sv+0x210`

符号表里有 `sv`：

```
003a7f60  0x2d37c  OBJECT  LOCAL  DEFAULT  25  sv
```

于是：

| 绝对 VA | 相对 `sv` | 含义（N21 命名） |
|---|---|---|
| `0x003A816C` | `sv+0x20C` | 被 `ED_Alloc` 首检引用 |
| `0x003A8170` | **`sv+0x210`** | 容量上界（`EDICT_NUM` 越界检查 + 分配大小） |
| `0x003A8174` | `sv+0x214` | `pEdicts` |
| `0x003A8178` | `sv+0x218` | 第二数组（`max*4` 字节） |

`SpawnServer` 里的 `mov DWORD PTR [ebx+0x210],0x800`（`ebx = this = &sv`）与
`EDICT_NUM` 读的 `0x3A8170` **是同一块内存**——N21 里看似两个地址的矛盾由此消解：
一条是寄存器相对寻址，一条是绝对寻址。

`0x3A7F50` 位于 `sv-0x10`，是同一代码块里写入的**镜像全局**（`0x800`，退出时清零），
其读者尚待确认。

## 2 动态取证（gdb，真实地图 c1m1_hotel）

方法：`disable-randomization` 固定布局；`&sv` 取自符号；断点分别设在
`CGameServer::SpawnServer` 入口、两条 `0x800` 存储之后（`+0x1EE0E7`）、
以及 `Hunk_AllocName` 调用点（`+0x1EE12C`）。

结果：

```
BASE=0xf70bc000  sv=0xf7463f60

BEFORE : sv+0x210 = 0     cap(0x3A7F50) = 0
AFTER  : sv+0x210 = 2048  cap(0x3A7F50) = 2048
HUNK   : Hunk_AllocName(size=0x8000)      # 0x8000 = 2048 × 16
```

结论链（全部有运行时证据）：

1. 进入 `SpawnServer` 时容量为 **0**，未初始化；
2. 两条 `mov ...,0x800` 执行后，`sv+0x210` 与 `0x3A7F50` 同时变为 **2048**；
3. 紧随其后的 `Hunk_AllocName` 以 `[sv+0x210] × 16 = 0x8000` 分配 edict 数组，
   返回值写入 `sv+0x214`（`pEdicts`）；
4. 同一字段 `sv+0x210` 被 `EDICT_NUM` 用作越界上界、被 `ED_Alloc` 用作分配边界。

⇒ **`sv+0x210` 是唯一的容量闸门**，`0x800` 的两处写入是它的初始化点。

## 3 对补丁的含义（尚未生成补丁）

最小改动候选收敛为：

| 位置 | 现状 | 候选 |
|---|---|---|
| `0x1EE0DD` | `mov DWORD PTR [ebx+0x210],0x800` | 立即数 `0x800 → 0x1000` |
| `0x1EE0D3` | `mov DWORD PTR ds:0x3A7F50,0x800` | 同步改 `0x1000`（待确认读者） |
| edict 数组分配 | `max×16`，自动跟随 `sv+0x210` | 无需改动 |
| 第二数组 | `max×4`，同样自动跟随 | 无需改动 |

仍需先确认的项：

- `0x3A7F50` 的读者（是否参与其它容量判断）；
- `sv+0x20C`（`SpawnServer` 写入 `GetMaxClients()+1` 的字段）与 `ED_Alloc` 首检的关系；
- `EDICT_NUM` 之外的边界检查（如 `NUM_FOR_EDICTINFO`）；
- 网络侧 `SVC_PacketEntities::WriteToBuffer` 的 11 位字段（N1–N19 的结论需在 Linux 重新确认）。

## 4 环境备注

- 专用服务器启动时同样会报 Steam API IPC 失败（`GetConnectedUniverse failure code 12`），
  但地图加载与 `SpawnServer` 正常执行，因此**服务端动态分析不受 Steam 阻塞影响**；
- 客户端（原生或 Proton）仍受该问题影响，联机验证需要先解决或绕开。
