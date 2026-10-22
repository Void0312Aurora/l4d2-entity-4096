# N23：容量约束的完整数据流（Linux 服务端 build 17033453）

> 目标：把 N22 的「找到容量写入点」升级为「确认容量约束的完整数据流」。
> 本报告**不修改任何二进制**；所有补丁候选只登记偏移与预期字节。

## 0 结论边界修正

N22 中「`sv+0x210` 是唯一的容量闸门」这一表述撤回。当前可证的表述是：

> `sv+0x210` 是**已验证的 edict 主容量控制字段**；尚不能排除其他独立容量约束
> （网络字段、快照体系、其他 `max_edicts` 派生结构）。

## 1 方法

- 静态：`objdump -drwC -Mintel` 全量反汇编 + `readelf` 符号表；
- 反编译：REA 6.7.0 内置 **Ghidra 12.1.4**（headless），按符号名解析；
- 动态：gdb（N22 已建立）。

**重要校准**：REA/Ghidra 报告的地址比 ELF 虚拟地址高 `0x10000`
（例：`ED_Alloc` 在 Ghidra 中为 `0x1D6A40`，ELF 中为 `0x1C6A40`）。
本报告一律使用 **ELF 地址**（= `.text` 文件偏移，因为 `.text` 的 `vaddr == off == 0x81850`）。

## 2 P0-1：`0x3A7F50` 的全部引用

全量反汇编中仅 2 处，**都是写**：

| 地址 | 指令 | 含义 |
|---|---|---|
| `0x1EE0D3` | `mov DWORD PTR ds:0x3A7F50,0x800` | `SpawnServer` 初始化 |
| `0x1F0617` | `mov DWORD PTR ds:0x3A7F50,0x0` | 关闭路径清零 |

`0x3A7F50 = sv - 0x10`。**在本模块内没有任何绝对读者**。

结论：在 `engine_srv.so` 内它不构成容量消费者；它更像一个供其他组件/统计读取的镜像值。
间接访问（经寄存器基址）无法用绝对地址扫描排除，列为未决项。

## 3 P0-2：`sv+0x20C` = `num_edicts` 的完整分配语义

Ghidra 反编译 `ED_Alloc(int)`（ELF `0x1C6A40`）恢复出的控制流：

```
if (index >= 0) {
    if (num_edicts <= index) { Warning("ED_Alloc( %d ) - invalid edict index specified."); return NULL; }
    edict = pEdicts + index*16;
    if ((edict->flags & 2) == 0) return NULL;       // 未在使用
    ED_ClearEdict(edict); return edict;
}
i = GetMaxClients() + 1;
edict = pEdicts + i*16;
while (i < num_edicts) {                            // 复用扫描
    if (edict->flags & 2) {
        freeTime = g_EdictFreeTime[i];
        if (freeTime >= 2.0f && now - freeTime < 1.0f) { i++; edict += 16; continue; }
        if (freeTime == 0.0f && sv_useexplicitdelete) CFrameSnapshotManager::AddExplicitDelete(i);
        ED_ClearEdict(edict); return edict;         // 复用
    }
    i++; edict += 16;
}
if (num_edicts < max_edicts) {                      // 增长
    num_edicts += 1;                                // 0x1C6BDE 写 sv+0x20C
    ED_ClearEdict(edict); return edict;
}
Sys_Error("ED_Alloc: no free edicts");              // 耗尽
```

要点：

1. `sv+0x20C` 是**已用 edict 数量**（从 `GetMaxClients()+1` 起算），`sv+0x210` 是**上限**；
2. 增长路径只在 `num_edicts < max_edicts` 时执行，因此**分配器天然可达任意 `max_edicts-1` 槽位**；
3. 复用依赖 `edict->flags & 2` 与 `g_EdictFreeTime[]`（即 `sv+0x218` 指向的 `max_edicts*4` 数组）；
4. 只有两者相等时才 `Sys_Error("ED_Alloc: no free edicts")`。

⇒ **把 `max_edicts` 提升到 4096 后，分配器不需要额外修改即可使用高索引槽位**（前提是数组按新上限分配，已由 N22 证实自动跟随）。

## 4 P0-3：`sv+0x210` 的消费者

绝对寻址读者（全量反汇编枚举，共 6 处）：

| 地址 | 所在函数 | 用途 |
|---|---|---|
| `0x1C687E` | `EDICT_NUM` | 越界上界（`index < max`） |
| `0x1C6907` | `NUM_FOR_EDICTINFO` | 反向映射上界 |
| `0x1C6B70` | `ED_Alloc` | 增长判定 |
| `0x1C6BB8` | `ED_Alloc` | 增长判定（第二路径） |
| `0x1EE111` | `SpawnServer` | `Hunk_AllocName(max*16)` |
| `0x1EE13B` | `SpawnServer` | `Hunk_AllocName(max*4)` |

另有 **43 处** `[reg+0x210]` 形式的相对访问，需逐条判定是否指向 `sv+0x210`
（许多是同偏移的无关结构），已列入未决项，尚不能据此断言存在额外硬边界。

## 5 P1：`SVC_PacketEntities::WriteToBuffer` 字段图（ELF `0x9A300`）

Ghidra 反编译恢复的写序列（`this` 为 `SVC_PacketEntities`）：

| 顺序 | 字段偏移 | 位宽 | 值来源 |
|---|---|---|---|
| 1 | — | 6 | 虚调用 `*(this)+0x24`（消息类型 ID） |
| 2 | `this+0x4C` | **11** | `m_nMaxEntries` |
| 3a | `this+0x5C` | 32 | 仅 delta：`WriteLong`（`m_nDeltaFrom`） |
| 3b | `this+0x58` | 1 | 仅 delta：baseline 位 |
| 3c | `this+0x50` | **11** | `m_nUpdatedEntries` |
| 4 | `this+0x60` | **20** | `m_nLength`（数据位数） |
| 5 | `this+0x55` | 1 | `m_bUpdateBaseline` |
| 6 | `this+0x88` | `m_nLength` 位 | 数据缓冲 |

对照 Windows N1–N19：

- `m_nMaxEntries` 的 11 位假设在 Linux 上**成立且被直接证实**；
- `m_nUpdatedEntries` 在 Linux 上是 **11 位**（不是 12/13），与 Windows 结论存在差异，须以 Linux 为准重新评估；
- 两者上限均为 2047 ⇒ 若要承载 4096 实体，**11→13 的位宽变更不可避免**，且会改变线格式；
- `this+0x4C` 的**生产者**尚未定位（谁写入 `m_nMaxEntries`），这是下一步的关键。

## 6 Phase B 候选补丁清单（未实施）

`.text` 的 `vaddr == file offset`，故下表偏移即文件偏移。

| # | 文件偏移 | 预期原字节 | 候选修改 | 状态 |
|---|---|---|---|---|
| P1 | `0x1EE0D3` | `c7 05 50 7f 3a 00 00 08 00 00` | 立即数 `0x800 → 0x1000`（`00 10 00 00`） | 依赖 `0x3A7F50` 语义确认 |
| P2 | `0x1EE0DD` | `c7 83 10 02 00 00 00 08 00 00` | 立即数 `0x800 → 0x1000` | **主候选**（`sv+0x210`） |
| — | `0x1EE0FC` | `83 c0 01 89 83 0c` | 不改（`num_edicts = maxclients+1`） | 无需改 |
| — | 分配点 `0x1EE12C`/`0x1EE156` | — | 不改（尺寸由 `sv+0x210` 推导） | 已验证 |
| P3 | `0x9A3xx` 区（`WriteToBuffer`） | 11 位写序列 | 11→13 位宽改造 | **未决**，需先定位生产者与接收端 |
| P4 | `0xA5170` 区（`ReadFromBuffer`） | 11 位读序列 | 与 P3 对称 | **未决** |

## 7 Phase B 验收分级（采纳）

| 层级 | 目标 |
|---|---|
| B1 初始化 | `max_edicts=4096`；主数组 `0x10000` B；第二数组 `0x4000` B |
| B2 实体管理 | 高索引实体可分配/访问/释放/复用，无越界 |
| B3 快照处理 | 高索引进入服务器快照，不破坏内存 |
| B4 网络联机 | 客户端正确接收/更新/删除高索引实体 |

B1、B2 可在专用服务器独立验证；B3、B4 依赖协议改造。

## 8 证据与可复现性

- 提取脚本：`tools/linux/extract_evidence.sh`（不修改二进制）；
- 产物：`evidence/linux/`
  - `engine_srv.sha256`（`5fa15f28…`）、`engine_srv.notes.txt`（build-id `91c46dee…`）
  - `spawnserver.asm`、`ed_alloc_edictnum.asm`、`packet-writer.asm`、`packet-reader.asm`
  - `capacity_refs.txt`（容量全局全部引用）、`rels_0x210.count`（43）
  - `asm.sha256`（反汇编快照校验）

## 9 未决项

1. `0x3A7F50` 的间接读者/外部读者；
2. 43 处 `[reg+0x210]` 相对访问的逐一判定；
3. `SVC_PacketEntities::m_nMaxEntries`（`this+0x4C`）的生产者；
4. `ReadFromBuffer` 对 11 位字段的对称读取与越界行为；
5. 快照体系（`CFrameSnapshotManager`、`CFrame` 位图）在 Linux 上的容量依赖。
