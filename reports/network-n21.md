# N21：转向 Linux 服务端（engine_srv.so）——符号地图与 2048 常量定位

> 决策背景：本机部署形态是 **Linux 专用服务器 + Linux 原生客户端**，因此服务端 `engine_srv.so`
> 才是 4096 补丁的主交付物；Windows `engine.dll` 的分析（N1–N20）作为语义依据保留。

## 0 目标二进制

| 项 | 值 |
|---|---|
| 文件 | `~/l4d2_server/bin/engine_srv.so` |
| 大小 | 4,051,241 B |
| 格式 | ELF 32-bit LSB shared object, Intel i386（PIC） |
| 服务端 build | **17033453**（客户端 build 为 23990068） |
| 符号 | `.symtab` 完整：**8,756 个有地址的 FUNC**（另含 UND 导入），C++ mangled |

这是与 Windows 路线的根本差异：Windows `engine.dll` 无符号，只能靠字节特征猜；
Linux 服务端可直接按符号名定位。

## 1 已定位的关键符号

| 符号（c++filt） | 地址 | 大小 | 说明 |
|---|---|---|---|
| `CGameServer::SpawnServer(char*, char*)` | `0x001EDE70` | 3054 | 对应 Windows 的 `SV_SpawnServer` |
| `ED_Alloc(int)` | `0x001C6A40` | 469 | edict 分配 |
| `EDICT_NUM(int)` | `0x001C6870` | 55 | edict 索引 → 指针 |
| `NUM_FOR_EDICTINFO(edict_t const*)` | `0x001C6900` | — | 反向映射 |
| `SVC_PacketEntities::WriteToBuffer(bf_write&)` | `0x0009A300` | 967 | **snapshot 打包（位宽所在）** |
| `SVC_PacketEntities::ReadFromBuffer(bf_read&)` | `0x000A5170` | 2295 | 客户端解析（对称） |
| `CBaseClientState::ProcessPacketEntities(SVC_PacketEntities*)` | `0x000EFC20` | 648 | 客户端处理入口 |
| `CClientState::ProcessPacketEntities(SVC_PacketEntities*)` | `0x00105EC0` | — | 同上（另一实现） |

## 2 全局变量（.bss，PIC 下为绝对地址）

| 地址 | 角色 | 证据 |
|---|---|---|
| `0x003A816C` | `num_edicts` | `ED_Alloc` 首检：`cmp 0x3a816c,%ebx; jge` |
| `0x003A8170` | 上界（`max_edicts`） | `EDICT_NUM`：`cmp 0x3a8170,%ebx; jl ok`，越界 `Sys_Error` |
| `0x003A8174` | `pEdicts`（指针） | `EDICT_NUM`：`shl $4,%eax; add 0x3a8174,%eax` |
| `0x003A7F50` | 容量相关全局 | `SpawnServer` 写入 `$0x800` |

`edict_t` 步长 = **16 字节**（`shl $4`）。

## 3 2048 常量在 SpawnServer 中的两处

```
1ee0d3:  c7 05 50 7f 3a 00 00  movl $0x800, 0x3a7f50
1ee0dd:  c7 83 10 02 00 00 00  movl $0x800, 0x210(%ebx)      ; CGameServer 字段 +0x210
```

与 Windows 的对应关系：

| Linux | Windows（N6–N10 结论） |
|---|---|
| `[0x3A7F50] = 0x800` | `[0x10645770] = 0x800`（`max_edicts`） |
| `[CGameServer + 0x210] = 0x800` | `[sv + 0x218] = 0x800` |
| `EDICT_NUM` 上界 `0x3A8170` | `EDICT_NUM` 用同一上界 |

字段偏移不同（0x210 vs 0x218），但语义一致：**容量常量在 SpawnServer 初始化，并由 EDICT_NUM/ED_Alloc 共同使用**。

## 4 下一步（Linux 服务端）

1. 反汇编 `SpawnServer` 全段（0x1EDE70–0x1EEAA0），确认 `0x3A7F50`、`+0x210` 与 `num_edicts/pEdicts`
   的初始化顺序，落成「2048→4096」最小改动集；
2. 反汇编 `SVC_PacketEntities::WriteToBuffer`（0x9A300），定位 `m_nMaxEntries` 的 11 位写入
   （`WriteUBitLong(x, 11)` / 掩码 `0x7FF`），确定是否需要 13 位；
3. 检查快照相关数组/位图（`CFrameSnapshotManager`，符号已见）是否按 `max_edicts` 分配；
4. 客户端侧（`engine.so` 的 `ReadFromBuffer`）同步修改位宽，两端成对验证。

## 5 验证环境

- 服务器：`~/l4d2_server`，`srcds_linux`（ELF 32-bit），可本地起服；
- 客户端：本机原生 `hl2_linux + engine.so`（需切回原生并补下 Linux depot 才能用）；
- 压测思路：生成 >2048 个实体（插件或 `ent_create` 循环），观察 `status`/`max_edicts` 与客户端是否截断。
