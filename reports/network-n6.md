# N6：`capacity_imm` 的「sole writer」标注未获证实——它改的不是 `[0x10645770]`

> 本轮核对 `engine/manifest.json` 的存储层补丁 `capacity_imm`（`0x10123DA2`）。
> 结论：该立即数的数据流**不通向** `sv.max_edicts` 的全局槽位 `0x10645770` 的绝对写；
> 而 edict 数组的分配大小恰恰由 `[0x10645770]` 决定。这是一个**需要先解决的问题**，
> 否则第 1 层补丁可能只改了另一个字段，数组仍是 2048 项。

## 0 结论

| 命题 | 结果 |
|---|---|
| `0x10645770` 在 `.text` 中有绝对地址写 | **没有**（8 处引用逐一解码，全为读） |
| `0x10123DA2` 的 `0x800` 是否直接写入 `0x10645770` | **否**；写入的是 `sv+0x218` 与 `0x10429308` |
| edict 数组大小是否取自 `0x10645770` | **是**：`DAT_10645774 = alloc([0x10645770] << 4)` |
| `capacity_imm` 能否单独完成 2048→4096 | **不能证明**；需先找到 `0x10645770` 的赋值者 |
| manifest 的 `note="sv.max_edicts, sole writer"` | **降级为未验证标注**（已在 JSON 中加 `verified:false`） |

## 1 `0x10645770` 的 8 处引用全是读

| 地址 | 指令 | 类型 | 所在函数 |
|---|---|---|---|
| `0x10123de1` | `MOV ECX,[0x10645770]` | 读 | `FUN_10123B20`（`SV_SpawnServer`） |
| `0x10123e01` | `MOV EDX,[0x10645770]` | 读 | 同上 |
| `0x101e000b` | `CMP ESI,[0x10645770]` | 读 | `FUN_101E0000`（`EDICT_NUM`） |
| `0x101e0074` | `CMP ESI,[0x10645770]` | 读 | `FUN_101E0060` |
| `0x101e00a0` | `CMP ESI,[0x10645770]` | 读 | `FUN_101E0090` |
| `0x101e00ed` | `CMP ESI,[0x10645770]` | 读 | `FUN_101E00D0` |
| `0x101e011e` | `CMP ESI,[0x10645770]` | 读 | `FUN_101E00D0` |
| `0x101e023a` | `MOV EAX,[0x10645770]` | 读 | `FUN_101E0170`（`ED_Alloc`） |

没有一处是 `MOV [0x10645770], …`，也没有 `C7 05`/`89 ??`/`A3`/`81 05` 等绝对写编码命中。
因此写入只能来自**计算基址**（把 `&g_EdictManager` 装进寄存器后按 `+0x110` 之类的位移写），
这解释了为什么 xref 列表里只有读。

## 2 `SV_SpawnServer` 里那个 `0x800` 到底去了哪

`FUN_10123B20`（`SV_SpawnServer`，字符串 `"SV_SpawnServer(%s)"` 与 `"SV_SpawnServer -- Finished"` 同址段）
的关键片段：

```c
in_ECX[0x86] = 0x800;            // sv + 0x218 = 0x800      <<< 0x10123DA2 的 EAX 在此落地
_DAT_10429308 = 0x800;           // 另一个全局 = 0x800      <<< 同一常量的第二处落地
_DAT_104292cc = (**(code **)(*in_ECX + 0x14))();
...
DAT_10645774 = FUN_10215d90(DAT_10645770 << 4, "edicts", 1);          // 分配 = max_edicts * 16
FUN_101dfef0();
DAT_10645778 = FUN_10215d90(DAT_10645770 * 4, "edictchangeinfo", 1);  // 分配 = max_edicts * 4
```

三件事同时成立：

1. `mov eax,0x800`（`0x10123DA2`，字节 `b8 00 08 00 00`）编译自 `in_ECX[0x86] = 0x800` 与
   `_DAT_10429308 = 0x800` 这类**字段/全局**赋值，与 `[0x10645770]` 无关；
2. 紧接其后，edict 数组的两笔分配**读取** `[0x10645770]` 作为容量；
3. 函数体内**没有**任何写 `[0x10645770]` 的指令。

因此：**只改 `0x10123DA2` 的立即数，不会改变这两笔分配的大小**，除非另有代码在此之前把
`sv+0x218` 或 `0x10429308` 复制进 `[0x10645770]`。

## 3 风险等级与需要回答的问题

| 问题 | 影响 |
|---|---|
| `[0x10645770]` 的赋值者是谁 | 决定第 1 层补丁是否真的把 edict 数组扩到 4096 |
| `sv+0x218` / `0x10429308` 是否别名到 `[0x10645770]` | 若是别名，`capacity_imm` 可通过间接路径生效；若不是，则补丁失效 |
| `FUN_101DFEF0` 是否重设该全局 | 它在数组分配之后调用，若它从 `sv+0x218` 拷贝，则 `capacity_imm` 间接生效 |

`FUN_101DFEF0` 现在是最高优先级的候选：它紧跟在 `edicts` 分配之后、`edictchangeinfo` 分配之前，
且把 `0x2000` 长度的 `reuseTimes` 数组也初始化（见 manifest 的 `reuse_clear_size` 等 9 个补丁），
很可能同时承担 edict 管理器的容量落地。

## 4 已采取的记录动作

`engine/manifest.json` 的 `capacity_imm` 条目**未改动任何补丁字段**，只追加两键：

```json
"verified": false,
"verification_note": "0x10123DA2 is MOV EAX,0x800 feeding sv+0x218 and 0x10429308, not [0x10645770]; edict allocations read [0x10645770] << 4 / *4. Sole-writer claim unproven; see reports/network-n6.md"
```

这样既保留了原补丁定义（可回滚），又将注释降级为可追踪的待验证状态。

## 5 下一步

1. 反编译 `FUN_101DFEF0`，确认是否写 `[0x10645770]`（或其别名）；
2. 在 `SV_SpawnServer` 的调用链里向前找 `[0x10645770]` 的初始化（引擎启动期或 `Host_Init`）；
3. 若确认 `sv+0x218` 与 `[0x10645770]` 存在拷贝关系，则 `capacity_imm` 仍可用，但需要
   在 manifest 中写明「间接生效」并给出中间拷贝点；
4. 若不存在拷贝关系，则第 1 层补丁必须新增一个真正的 `[0x10645770]` 写点（或把 9 处分配尺寸
   的乘法基数改为常量 4096），否则 4096 扩容在存储层就失效。

## 6 复现

```bash
# REA 会话内
#   inspect_native_instruction(0x10123da2)  -> MOV EAX,0x800（5 字节立即数）
#   inspect_native_instruction(0x10123de1)  -> MOV ECX,[0x10645770]（读）
#   inspect_native_instruction(0x10123e01)  -> MOV EDX,[0x10645770]（读）
#   procedure_pseudo_code(0x10123B20)       -> SV_SpawnServer：0x800 落 sv+0x218 / 0x10429308
#   xrefs(0x10645770)                       -> 8 处，全部为读
```
