# server.dll — CBaseEntityList 实体槽位布局实测

**目标**：确认实体槽位数组的真实规模、分区边界与句柄位布局，为「4096 网络 edicts」判断需要付出什么代价。
**方式**：Ghidra 12.1.4 只读反编译 + 全文件字节/重定位扫描。**未修改任何文件。**

| 项 | 值 |
|---|---|
| 目标 | `left4dead2/bin/server.dll` |
| SHA-256 | `a93ec916a8f26fbea85688c321d2ba8dd346d435fab09a0b926dd950c2e1ea12` |
| 大小 | 0x8B5130 |
| 格式 | PE32 i386，ImageBase 0x10000000 |
| 节 | `.text` 0x1000 / `.rdata` 0x5C1000 / `.data` 0x74A000(vsz 0x1555AC) / `.reloc` 0x8A0000 |

---

## 1. 对象布局（实测）

全局实例 **0x107E0760**，位于 `.data` 的 BSS 尾部（文件 raw 只到 0x7CE000，该地址在 0x7DF360 → 文件内为 0，加载时由构造函数初始化）。

```
+0x00000   vptr
+0x00004   CEntInfo m_EntPtrArray[4096]        0x10000 字节，步长 16
+0x10004   m_activeList.head
+0x10008   m_activeList.tail
+0x1000C   m_freeNonNetworkableList.head
+0x10010   m_freeNonNetworkableList.tail
           ---- 对象结束 = +0x10014 ----
```

`CEntInfo`（16 B）：`+0 pEntity`、`+4 serial(uint16)`、`+8 next`、`+0xC prev`。

证据（构造函数 `FUN_100b7890`，209 字节，0x100B7890–0x100B7960）：

```
0x100b7897  MOV [EDI], 0x105F3BA8          ; vptr（随后被静态初始化覆盖，见 §2）
0x100b78b5  LEA ESI, [EDI+4]               ; &m_EntPtrArray[0]
0x100b78b8  MOV EBX, 0x1000                ; 4096 个槽位
0x100b78c0  MOV [ESI+0xC], ESI             ; entry.prev = self
0x100b78c3  MOV [ESI+0x8], ESI             ; entry.next = self
0x100b78c6  CALL 0x101b49b0                ; rand
0x100b78cb  AND EAX, 0x7FFF                ; serial = rand & 0x7FFF
0x100b78d0  MOV [ESI+4], EAX
0x100b78d3  MOV [ESI], 0                   ; pEntity = NULL
0x100b78d9  ADD ESI, 0x10                  ; stride 16
```

---

## 2. 实例与静态初始化

- 唯一调用点：`0x105859A5`（静态初始化段内，Ghidra 未把它识别成函数）。
- 紧随其后 **直接改写 vptr**：

```
0x105859B1  C7 05 60 07 7E 10 78 3A 5F 10   MOV dword ptr [0x107E0760], 0x105F3A78
```

即构造函数先写入 0x105F3BA8，静态初始化再用 0x105F3A78 覆盖。**两个 vtable 的语义差异未确认**（可能是基类 ctor + 派生类 vptr），但对象地址唯一确定。

引用统计（全文件字节扫描，含 `.text`/`.data`）：

| 目标 | 次数 | 形态 |
|---|---|---|
| `0x107E0760`（对象基址） | **622** | 620 × `mov ecx,imm32`；1 × `mov dword ptr [0x107E0760],imm32`（0x105859B1）；1 × `.data` 指针表项（0x1075E9B8） |
| `0x107E0764`（数组基址） | **23** | 全部在 `.text`，形如 `shl reg,4` + `add reg,imm32`（5 字节立即数） |

---

## 3. 分区（实测）

构造函数后半段建立**非网络实体空闲链表**：

```
0x100b78df  LEA EAX, [EDI+0x801C]   ; = &m_EntPtrArray[0x801].next
0x100b78e5  MOV ESI, 0x7FF          ; 2047 次
            ; 逐个 AddToTail(&m_freeNonNetworkableList, entry)
```

由此得到实际分区：

| 索引范围 | 数量 | 用途 | 依据 |
|---|---|---|---|
| `0x000 – 0x7FF` | 2048 | 网络实体（按 edict 索引直接落位） | 0x100556A0 传入 edict 索引；`RemoveEntityAtSlot` 阈值 `0x7FF` |
| `0x800` | 1 | **既不初始化进空闲链表，也不参与网络分配** | 构造函数池起点 0x801；释放阈值 `>0x7FF` |
| `0x801 – 0xFFF` | 2047 | 非网络实体空闲池 | 构造函数 LEA/MOV 常量 |

合计 4096。**与 SDK 2013 的 `for (i = MAX_EDICTS + 1; i < NUM_ENT_ENTRIES; i++)` 一致**，其中 `MAX_EDICTS = 0x800`、`NUM_ENT_ENTRIES = 0x1000`。SDK 里 `MAX_EDICTS+1 = 0x801` 正好解释了索引 0x800 为何被跳过。

---

## 4. 实体列表 API（全部实测）

| 函数 | 地址 | 作用 |
|---|---|---|
| `AddToTail(list, entry)` | 0x100B7830 | 双向链表尾插；ECX = &list{head,tail} |
| `Ctor` | 0x100B7890 | 4096 槽初始化 + 建立非网络池 |
| `RemoveEntityAtSlot(index)` | 0x100B7970 | 见下 |
| `Clear/RemoveAll` | 0x100B7A30 | 遍历 m_activeList，逐个移除；索引 `>0x7FF` 的退回非网络池 |
| `AddEntityAtSlot(entity, out, index, serialOr-1)` | 0x100B7B70 | **无 index 边界检查** |
| `AddNonNetworkableEntity(entity, out)` | 0x100B7BD0 | 字符串确认：`"CBaseEntityList::AddNonNetworkableEntity: no free slots!\n"` |
| `RemoveEntity(handle)` | 0x100B7CA0 | `RemoveEntityAtSlot(handle & 0xFFF)` |

**`AddEntityAtSlot`（0x100B7B70）全文语义**：

```c
entry = &m_EntPtrArray[index];          // 无任何 index 上界判断
entry->pEntity = entity;
if (serial != -1) entry->serial = serial;
AddToTail(&m_activeList, entry);
*out = (entry->serial << 12) | index;   // 句柄打包
entity->SetRefEHandle(out);             // vtable[1]
this->OnAddEntity(entity, *out);        // vtable[0]
```

**`AddNonNetworkableEntity`（0x100B7BD0）**：

```c
head = m_freeNonNetworkableList.head;
if (!head) { Warning("...no free slots!\n"); *out = 0xFFFFFFFF; return; }
unlink(head);                            // 从空闲链表摘除
idx  = (head - this - 4) >> 4;           // 槽索引
entry = &m_EntPtrArray[idx];
entry->pEntity = entity;
AddToTail(&m_activeList, entry);
*out = (entry->serial << 12) | idx;
...
```

**`RemoveEntityAtSlot`（0x100B7970）**：

```c
entry = &m_EntPtrArray[index];
if (!entry->pEntity) return;
entity->SetRefEHandle(0xFFFFFFFF);
this->OnRemoveEntity(entity, (entry->serial << 12) | index);
entry->serial = (entry->serial + 1) & 0x7FFF;   // 序号自增，15 位
entry->pEntity = NULL;
unlink(entry);                                   // 从 active list 摘除
if (index > 0x7FF) AddToTail(&m_freeNonNetworkableList, entry);  // 回池
```

---

## 5. CBaseHandle 位布局（实测）

```
handle = ((serial & 0x7FFF) << 12) | (index & 0xFFF)
```

- 索引：**12 位**（`& 0xFFF`，0x100B7CA0 直接可见）
- 序号：**15 位**，`(s + 1) & 0x7FFF`
- 位 27–31 未使用

与 L4D2 的 `CBaseHandle` 约定一致：**扩容到 4096 个网络槽位必然要求索引位宽 12 → 13**，`serial << 12` 全部要变 `<< 13`，`& 0xFFF` 变 `& 0x1FFF`。

---

## 6. 关键冲突：高索引 edict 会直接落进非网络池

0x100556A0（唯一的 `AddEntityAtSlot` 调用点）中的实体落位逻辑：

```c
FUN_100b7b70(&handle, this,
             (this->m_pEdict - *(int *)(0x107F7690 + 0x58)) >> 4,   // = edict 索引
             -1);
```

- 索引来源是 **`(edict - pEdicts) >> 4`**，即引擎 edict 索引本身，**没有任何 `< 0x800` 判断，也没有重映射**。
- 分支条件只是 `in_ECX[0x4e]` 的 bit9/bit10 标志（网络/非网络），不校验索引范围。

**推论（这是本次最重要的结构性结论）**：

> 只把 engine 的 `max_edicts` 提到 4096，高索引 edict（2048–4095）会**直接写进 `m_EntPtrArray[0x800..0xFFF]`**——而这段正是非网络实体的空闲池。`AddEntityAtSlot` 不做检查，`AddNonNetworkableEntity` 随后会从同一批槽位摘链，结果是**空闲链表被破坏 / 双重占用**，表现为实体表静默损坏而非报错。

因此「4096 网络 edicts」在 server.dll 侧的硬性要求是：

```
N_network = 4096  ⇒  m_EntPtrArray 至少 8192 槽
                       且非网络池必须迁移到 [0x1001, 0x1FFF]
```

与你在需求里给的 `N_entries ≥ 8192` 完全一致，且现在有了二进制证据。

---

## 7. 扩容可行性：对象必须迁移，不能原地生长

对象结束于 `0x107E0760 + 0x10014 = 0x107F0774`。紧随其后的全局被实际引用：

| 地址 | 文件内出现次数 |
|---|---|
| 0x107F0774 | 1 |
| 0x107F0778 | 1 |
| 0x107F0780 | 1 |
| 0x107F0784 | 6 |
| 0x107F0798 | 11 |

→ **原地扩容会立刻覆盖活跃全局**，必须整体迁移对象（与 engine 的 `0x106b3a58` 情形同类，但规模大得多）。

迁移的技术形态（待你确认后实施）：

| 需要改动 | 数量 | 形态 |
|---|---|---|
| `mov ecx, 0x107E0760` | 620 | 5 字节立即数，等长替换 |
| `mov dword ptr [0x107E0760], imm` | 1 | 0x105859B1 |
| `.data` 指针表项 | 1 | 0x1075E9B8 |
| 数组基址 `0x107E0764`（`add reg,imm32`） | 23 | 5 字节立即数 |
| 构造函数常量 | 3 | `0x1000→0x2000`、`0x801C→0x1001C`、`0x7FF→0xFFF` |
| 释放阈值 `index > 0x7FF` | 2 | `CMP reg,0x7FF`（0x100B7970 / 0x100B7A30） |
| 句柄位宽 | 待统计 | `shl reg,0xC` 打包点 11 处；`& 0xFFF` 解包点全文件 298 处（含大量非句柄用途，需逐点甄别） |

目标对象尺寸：`0x20014`（131,092 B），仍可放在 `.data` 或新增 BSS 段。

---

## 8. 验收映射

| 你的验收条件 | 当前实测 | 结论 |
|---|---|---|
| `N_network = 4096` | 2048（`[0,0x7FF]`） | 需改容量 + 对象迁移 + 池位移 |
| `N_entries ≥ 8192` | 4096（`0x1000`） | 需 8192 槽 |
| `NetworkSlots ∩ NonNetworkSlots = ∅` | 当前为空（0x800 隔离带） | **扩容后若不同步移动池，交集非空** |
| `DecodeIndex(Encode(i,s)) = i` | 12 位索引下成立 | 13 位后需全量改写打包/解包点 |

**已证明**：布局、分区、构造函数、分配/回收路径、句柄位布局。
**未证明**：13 位索引后的全量一致性（需逐点甄别 298 处 `&0xFFF`）；`AddEntityAtSlot` 上层是否存在其它模块的 `index < 0x800` 守卫；client.dll 侧的同构对象。

---

## 9. 未知项（明确挂起）

1. vtable 双重写入（0x105F3BA8 → 0x105F3A78）的语义差异。
2. 槽位 `0x800` 是否被某条路径实际分配（构造函数跳过、释放阈值 `>0x7FF` 会把它放回池——两者不自洽）。
3. `0x107F7690 + 0x58` 指向的是哪个 `pEdicts` 副本（与 engine 的 `sv+0x21C` 关系待确认）。
4. `.data` 指针表 `0x1075E9B8` 的结构（疑似子系统注册表）。
5. `AddNetworkableEntity` 的上层索引守卫位置（0x100556A0 处未发现）。

---

## 10. 下一步建议

1. 先统计 13 位化所需的**打包/解包点全集**（`shl reg,0xC` + `& 0xFFF` + `& 0x7FFF` 的语义分类），这决定 gamedll 侧工程量。
2. 再做对象迁移的离线补丁清单（620 + 23 + 2 处立即数），验证方式沿用 engine 那一套（SHA-256 绑定 + 指令上下文校验 + 差异审计）。
3. 最后才谈网络协议（11 位 edict 索引）。

---

# 追加：CGlobalEntityList 完整布局与引用图谱（第 2 轮）

## 11. 派生类布局确认

静态初始化序列（`0x105859A0` 起）：

```
105859a0  mov ecx, 0x107E0760
105859a5  call 0x100B7890                    ; CBaseEntityList::ctor
105859aa  xor eax,eax
105859ac  push 0x105B0FE0                    ; 析构注册
105859b1  mov dword ptr [0x107E0760], 0x105F3A78   ; 派生类 vptr
105859bb  mov ds:0x107F0784, eax             ; obj+0x10024
105859c0  mov ds:0x107F0788, eax             ; obj+0x10028
105859c5  mov ds:0x107F078C, eax             ; obj+0x1002C
105859ca  mov ds:0x107F0790, eax             ; obj+0x10030
105859cf  mov ds:0x107F0794, eax             ; obj+0x10034
```

5 个连续 dword 被清零 = `CUtlVector`（0x14 字节）。因此派生成员块自 `+0x10014` 起：

| 偏移 | 字段 | 依据 |
|---|---|---|
| `+0x10014` | `m_iHighestEnt` | 派生块首字段；3 处位移引用 |
| `+0x10018` | `m_iNumEnts` | 5 处位移引用 |
| `+0x1001C` | `m_iNumEdicts` | 4 处位移引用 |
| `+0x10020` | `m_bClearingEntities`（+3 对齐填充） | 2 处位移引用 |
| `+0x10024 .. +0x10037` | `CUtlVector<IEntityListener*>`（pMemory / nAllocationCount / nGrowSize / m_Size / pElements） | 静态初始化清零 5 个 dword |
| `+0x10038` | **对象结束** | 0x107F0798 的 11 次引用属于相邻全局，未被构造函数触碰 |

**对象总大小 `0x10038`（65,592 B）；扩容到 8192 槽后为 `0x20038`（131,128 B）。**

## 12. 旧 → 新偏移映射

| 成员 | 旧 | 新 |
|---|---|---|
| vptr | 0x00000 | 0x00000 |
| `m_EntPtrArray[4096→8192]` | 0x00004 | 0x00004 |
| `m_activeList` | 0x10004 | **0x20004** |
| `m_freeNonNetworkableList` | 0x1000C | **0x2000C** |
| 派生成员块 | 0x10014 | **0x20014** |
| 对象结束 | 0x10038 | **0x20038** |

→ 你指出的关键点是成立的：**只改 `ecx` 里的对象地址不够**，所有 `[reg+0x100xx]` 位移指令必须同步 +0x10000。

## 13. 引用图谱（全量实测）

| 类别 | 数量 | 说明 |
|---|---|---|
| 对象基址 `0x107E0760` | **622** | 620 × `mov ecx,imm32`；1 × `mov [0x107E0760],imm32`（0x105859B1）；1 × `.data` 指针（0x1075E9B8） |
| 数组基址 `0x107E0764` | **23** | 全部 `add reg,imm32`，全部带 HIGHLOW 重定位，**全部指向 slot 0** |
| 槽地址区间内的绝对 dword | 35 | 其中**带重定位的 23 处 = 上述数组基址**；其余 12 处无重定位，是数值巧合（如 0x107E3914 并非地址操作数） |
| **硬编码单个槽地址** | **0** | 没有任何指令直接寻址 `slot N` |
| 成员位移候选 | **74** | 0x10004:20 / 0x10008:5 / 0x1000C:8 / 0x10010:17 / 0x10014:3 / 0x10018:5 / 0x1001C:4 / 0x10020:2 / 0x10024:6 / 0x10030:4 |
| 派生字段绝对引用 | 每字段 1 次 | 即静态初始化的那次写入；运行时均走 `this+displacement` |

**方法学更正**：不能用「附近 0x400 字节内有 `mov ecx,OBJ`」来判定成员访问归属——成员函数的 `this` 来自调用方，函数内部没有那条 load。74 处必须逐点用 Ghidra 解析所属函数后归类。已确认在 7 个列表 API 函数体内的位移命中，才是必然要改的集合。

## 14. 句柄操作实测（H 分类第一遍）

| 类别 | 全文件 | 实体列表 API 内 | 备注 |
|---|---|---|---|
| H1 打包 `shl reg,0xC` | 12 | **4** | 0x100B79A5 / 0x100B7A86 / 0x100B7BA3 / 0x100B7C65 |
| H2 索引掩码 `and reg,0xFFF` | **2840** | **1** | 列表内仅 0x100B7CA0（`RemoveEntity` → `& 0xFFF`） |
| H3 序号掩码 `and reg,0x7FFF` | 14 | **3** | 0x100B78CB（ctor rand）、0x100B79BE、0x100B7A9F |
| H3 序号解码 `shr reg,0xC` | 3004 | 待甄别 | 绝大多数是指针右移 |
| H6 `cmp reg,0x1000` | 3 | 0 | 与列表无关 |

**结论（重要）**：`CBaseEntityList` 自身的句柄打包/解包只有 **8 条指令**（4 打包 + 1 索引解包 + 3 序号掩码）。2840 处 `and 0xFFF` 绝大多数是页对齐/位域等无关用途——**掩码频率不是有效筛选手段**，13 位化的真实工作量在**句柄消费者**（每个内联解包点），必须从引用图谱反推，而非从掩码反推。

另注：`0x100B6380 / 0x100B6412 / 0x104CF68B` 等 8 处 `shl 0xC` 属于其它类（含 `cmp eax,0xFFFFFFFF` 的无效句柄分支），需单独归类为 H9。

## 15. 关于索引 0x800（接受你的解释）

SDK 的 `Init` 用 `MAX_EDICTS + 1`、`RemoveEntityAtSlot` 用 `>= MAX_EDICTS`，二者本就不对称；L4D2 实测为 init `0x801`、释放阈值 `> 0x7FF`，行为一致。`0x800` 是正常分配路径不会使用的边界空洞，释放函数对它不做精确例外。扩容目标保持同构：`[0x1000]` 为空洞、池起点 `0x1001`。

## 16. 本轮结论

1. 对象是 **CGlobalEntityList**，完整尺寸 `0x10038`，扩容后 `0x20038`；必须整体迁移，且成员偏移 +0x10000。
2. 数组引用干净：23 处基址、**0 处硬编码槽地址**；对象基址 622 处需要改。
3. 句柄核心只有 8 条指令；真正成本在消费者全集，需按 H1–H9 逐点分类。
4. 74 处成员位移候选待逐点判定；未生成任何补丁（按你的要求）。

---

# 追加：四项任务执行结果（第 3 轮）

## 17. 任务 3 — 620 处对象引用的语义分类

对每个 `mov ecx, 0x107E0760` 之后 12 字节做指令跟踪：

| 分类 | 数量 | 判据 |
|---|---|---|
| **仅传递 this**（`call rel32`） | **607** | 紧随 `E8` |
| 需人工复核 | **13** | 0x1006C074, 0x100EEAA0, 0x101BEC7E, 0x1023EDCE, 0x10257282, 0x10260CC6, 0x102833D9, 0x102872B7, 0x102F7249, 0x102F7902, … |
| 直接 `[ecx+disp]` 字段访问 | **0** | 无 |

**结论**：编译器从不用 `mov ecx,OBJ` 直接做字段访问；所有字段访问都发生在**成员函数内部**（`this` 由调用方传入）。因此对象迁移分两步：
- 620 处立即数替换（形态统一，5 字节等长）；
- 成员函数内部的 `this+displacement` 需要 +0x10000（74 处候选，见 §13）。

## 18. 任务 3 — 23 处数组基址 = 实体查找点

回看上下文，23 处全部是 `CBaseEntityList` 的 handle→entity 查找：

```
83 F8 FF              cmp  eax, -1              ; INVALID_HANDLE 判定
8B C8                 mov  ecx, eax
81 E1 FF 0F 00 00     and  ecx, 0xFFF           ; index = h & 0xFFF
C1 E1 04              shl  ecx, 4               ; stride 16
81 C1 64 07 7E 10     add  ecx, 0x107E0764      ; &m_EntPtrArray[index]
C1 E8 0C              shr  eax, 0xC             ; serial = h >> 12
```

| 形态 | 数量 |
|---|---|
| 标准（`cmp -1` + `and 0xFFF` + `shl 4` + `add array` + `shr 0xC`） | **20** |
| 变体（`movzx` 读 entity 指针 / `c1 e2 04`） | **2**（0x100B4CD2、0x100B5DBE） |
| 纯索引范围检查（`cmp reg,0x1000`，无掩码） | **1**（0x104CF67D） |
| 硬编码单个槽地址 | **0** |

## 19. 任务 2 — 句柄操作语义分类

用「掩码 + 紧随 `shl reg,4` + 连到数组基址」三重签名过滤 2840 处 `and reg,0xFFF`：

| 过滤级 | 剩余数量 |
|---|---|
| `and reg,0xFFF` 全量 | 2840 |
| 后 14 字节内有 `shl reg,4` | **27** |
| 其中 24 字节内出现数组基址 `0x107E0764` | **20** |

即 **实体句柄解码只有 20 处**，其余 2820 处是无关掩码（页对齐、位域等）。结合 §14，13 位化的完整改动面：

| 类别 | 数量 | 位置 |
|---|---|---|
| H1 打包 `serial << 12` | 4 | 0x100B79A5 / 0x100B7A86 / 0x100B7BA3 / 0x100B7C65 |
| H2 索引解包 `& 0xFFF` | 21 | 20 处查找点 + 0x100B7CA0 |
| H3 序号解包 `>> 12` | 20 | 上述查找点内的 `shr 0xC` |
| H3 序号掩码 `& 0x7FFF` | 3 | 0x100B78CB / 0x100B79BE / 0x100B7A9F |
| H6 范围检查 `cmp 0x1000` | 1 | 0x104CF67D |
| **合计** | **≈49** | 均在 server.dll，尚未发现跨模块 |

## 20. 任务 4 — server.dll 迁移补丁设计（未实施）

### 目标对象

```
新对象基址 = 新 BSS 段内（建议 .entlist，0x20038 字节）
m_EntPtrArray[8192]  +0x00004 (0x20000)
m_activeList          +0x20004
m_freeNonNetworkableList +0x2000C
m_iHighestEnt         +0x20014
m_iNumEnts            +0x20018
m_iNumEdicts          +0x2001C
m_bClearingEntities   +0x20020
m_entityListeners     +0x20024..+0x20037
对象结束              +0x20038
```

### 补丁阶段（每阶段独立可验证）

| 阶段 | 内容 | 数量 | 状态 |
|---|---|---|---|
| S0 | 新增 BSS 段 `.entlist`（0x20038）+ SizeOfImage/NumberOfSections | 1 段 | 设计完成 |
| S1 | 620 处 `mov ecx,OBJ` 立即数 | 620 | **gate：13 处待复核** |
| S2 | 23 处数组基址 → 新基址+4 | 23 | 就绪（23/23 有重定位） |
| S3 | 74 处成员位移 +0x10000 | 74 | **gate：需逐点解析所属函数** |
| S4 | ctor 常量：`0x1000→0x2000`、`0x801C→0x1001C`、`0x7FF→0xFFF` | 3 | 就绪（字节已确认） |
| S5 | 释放阈值 `>0x7FF → >0xFFF`（0x100B7970、0x100B7A30） | 2 | 就绪 |
| S6 | 句柄位宽 12→13（打包/解包/掩码） | ≈49 | 就绪（清单见 §19） |
| S7 | 派生成员绝对地址（静态初始化 5 处 + 对象基址写 1 处 + `.data` 指针 1 处） | 7 | 就绪 |
| S8 | 非网络池迁移（由 S4 常量自动完成，需验证 0x1001 起点） | — | 依赖 S4 |

### 明确阻塞项（按你的要求终止并上报）

1. **74 处成员位移候选**：无法用字节邻近启发式判定归属（成员函数的 `this` 来自调用方）。必须逐点解析所属函数或人工确认，才能决定是否 +0x10000。**未生成这部分补丁。**
2. **13 处 `mov ecx,OBJ` 非 call 后续**：需人工确认是否用于其它用途。**未生成。**
3. **7 处 `and 0xFFF` + `shl 4` 但未连到数组基址**（27−20）：可能是其它结构的索引，需甄别，避免误改。
4. **client.dll 同构对象未分析**：客户端侧是否存在同样布局，未验证。
5. `CGlobalEntityList` 的 `m_entityListeners` 在扩容后偏移变化，其使用者（AddListener/RemoveListener）未单独定位。

### 可以立即实施的子集

S2 / S4 / S5 / S6 / S7 共约 81 处，均具备：SHA-256 绑定、指令上下文校验、重定位覆盖确认。S0 可先落地为只增段、不启用（空段 0x20038，不改变行为）。S1/S3 待 gate 解除。

---

# 追加：任务 A/B/C 执行结果（第 4 轮）

脚本：[audit_object.py](audit_object.py)（只读）。产物：`member_offsets.csv`、`object_references.csv`、`unresolved_references.csv`。

## A. 成员位移候选逐点分类（69 处）

| 分类 | 数量 | 含义 |
|---|---|---|
| `confirm_entity_list` | **58** | 基址寄存器可追溯到成员函数的 `this`（`mov reg,ecx`），且所属函数被证明以 `gEntList` 为 `this` 调用（607 个 `mov ecx,OBJ; call` 站点），或落在核心方法/派生类虚表方法体内 |
| `offset_immediate` | **2** | 立即数形式的成员地址运算：`sub eax,0x10010`、`add ecx,0x10024`，需 +0x10000 |
| `false_positive` | **9** | 匹配字节跨两条指令（disp8 + imm32），并非 disp32 操作数 |

确认项按新偏移分布：`0x20004`:18、`0x20008`:3、`0x2000C`:8、`0x20010`:8、`0x20014`:3、`0x20018`:5、`0x2001C`:2、`0x20020`:2、`0x20024`:5、`0x20030`:4。

**结论**：全部 58 处均为 `mod=10` 的 disp32 形式，**等长原地替换可行**（`0x100xx → 0x200xx`）；2 处立即数同样等长。未发现需要代码桩的访问形态。

证据强度说明：其中 9 处位于派生类虚表方法（0x100B5820 / 0x100B5890），其 `this` 由虚调用传入、函数体内未显式 `mov reg,ecx`，归类依据是「函数属于 `CGlobalEntityList` 虚表 + 位移精确等于派生成员偏移」，证据等级为中；其余 49 处有显式寄存器追溯。

## B. 旧对象区间绝对引用审计

对 `[0x107E0760, 0x107F0798)` 做重定位表扫描（419,422 条 HIGHLOW）：

| 旧偏移 | 数量 | 说明 |
|---|---|---|
| `0x00000` | **622** | 对象基址（620 `mov ecx,imm` + 1 `mov [obj],imm` + 1 `.data` 指针） |
| `0x00004` | **23** | 数组基址（全部 23 个查找点） |
| `0x00008` | **2** | 0x104CF687 / 0x104CFB11，指向 `&array[0].serial`，需个案确认 |
| `0x10004` | **7** | `m_activeList.head` 的绝对引用（0x100B5F78…0x100ED6F2） |
| `0x10024` | **6** | `m_entityListeners.pMemory`（5 运行时 + 1 初始化） |
| `0x10014/18/1C/20/28/2C/30/34` | 各 1 | 静态初始化 `0x105859xx` 的绝对写 |
| 合计 | **668** | 667 代码 + 1 数据表 |

新地址规则（`NEW_BASE` 暂定 0x10982000，为 `.reloc` 之后首个空闲 RVA）：

```
off = old - 0x107E0760
new = NEW_BASE + off + (0 if off < 0x10004 else 0x10000)
```

## C. 迁移映射

- 对象内偏移 < 0x10004（数组区）→ 新对象基址下偏移不变；
- 偏移 ≥ 0x10004（链表 + 派生成员）→ 偏移 +0x10000；
- 668 条绝对引用全部可按下式重写；58 处成员位移 + 2 处立即数同样可等长改写。

## 遗留

1. `0x00008` 的 2 处绝对引用（`&array[0].serial`）语义未定。
2. 9 处虚表方法内的成员访问证据等级为中，建议人工复核。
3. 本轮未做任何写入，未生成 server.dll 补丁。

---

# 追加：审计闭环与句柄消费者边界（第 5 轮）

## 21. 74 → 69 差异闭包

坐标核对：CSV 记录的是**指令起始 VA**，而 dword 命中位置是 `起始+2`（或 `+3`，含 SIB），因此逐地址比较会产生 65 条假差异。按「每个 dword 命中对应一条候选」重新对齐后：

| 项 | 数量 |
|---|---|
| 全文件 dword 命中 | **74** |
| 位于 `.text`、构成合法 `[reg+disp32]`/立即数形式 | **69** |
| 位于 `.data` 的命中 | **5** |

5 条 `.data` 命中全部是 offset `0x10010` 的数值常量：`0x10757903`、`0x1077ECB3`、`0x107AD3C3`、`0x107AD8BB`、`0x107C37DB`。它们不在重定位表中指向对象（668 条集合内），属于**数据表里的整数常量和地址无关**，排除。

结论：69 = 74 − 5，无其它遗漏。

## 22. `+0x8` 两处绝对引用的闭环

`0x107E0768 = m_EntPtrArray[0].serial`（数组基址+4）。两处均为**带索引缩放的数组元素访问**，不是裸地址：

**（a）0x104CF687 — 序列号读取 + 句柄合成**

```
104cf676  mov  eax,edx
104cf678  shl  eax,0x4
104cf67b  mov  ecx,[eax+0x107E0764]     ; pEntity
104cf681  test ecx,ecx / je
104cf685  mov  eax,[eax+0x107E0768]     ; serial
104cf68b  shl  eax,0xC
104cf68e  or   eax,edx                   ; handle = serial<<12 | index
104cf690  cmp  eax,0xFFFFFFFF
104cf695  xor  eax,esi
104cf697  test eax,0x3FF000              ; ← 只比较 bit12..21
```

**（b）0x104CFB0F — 序列号写回**

```
104cfb09  mov  ecx,[esi+0x1C]
104cfb0c  shl  eax,0x4
104cfb0f  mov  [eax+0x107E0768],ecx     ; m_EntPtrArray[idx].serial = ...
```

两者都必须随数组基址迁移为 `NEW_BASE+8`，并且都受索引位宽影响（H1/H3）。

**新发现（H9）**：`test eax,0x3FF000` 只比较 bit12–21（10 位），与构造函数 `&0x7FFF`（15 位）不一致。13 位化后 bit12 的含义会改变，这个掩码必须单独定性——它是「只比较部分序列号」还是「另一种句柄表示」，目前未定。

## 23. 9 处虚表访问的闭环

| 函数 | 在 `.rdata` 中出现次数 | 位置 |
|---|---|---|
| `0x100B5820` | **1** | vtable `0x105F3A78` 槽 0 |
| `0x100B5890` | **1** | vtable `0x105F3A78` 槽 1 |
| （对照）`0x100B44E0` | 5 | 被多个虚表共享 |

两个函数各只被一个虚表引用，且被访问的偏移恰为派生成员 `+0x10018/+0x1001C/+0x10020/+0x10024/+0x10030`，因此 `this` 只能是 `CGlobalEntityList`。**9 处访问升级为高置信度。**

## 24. 句柄消费者：集合边界的新结论

对「`and 0xFFF` 且 ±64 字节内有 `shr 0xC`」做窗口匹配，命中 **2813** 处——与 2840 总数几乎相同，**证明窗口/常量法完全无效**，与你的判断一致。

改为「索引只在访问 `m_EntPtrArray` 处被解码」这一结构事实来定界：

| 数组访问形态 | 数量 | 位置 |
|---|---|---|
| 绝对基址 + 索引（查找点） | **23** | 0x10010695 … 0x104CF67D |
| 绝对基址 + 索引（序列号读/写） | **2** | 0x104CF687 / 0x104CFB0F |
| `this+4+idx*16` 相对形式 | **未定界** | `[base+index+4]` 扫描命中 166 处，但无基址来源证据，噪声过大，不能据此认定 |

因此当前可定界的解码点 = **25 处**；`this+4+idx*16` 形式必须靠所属函数与基址来源逐点确认，不能靠字节模式。

## 25. 独立实体索引数组：首次定位线索

`.rdata` 中存在 RTTI 类名字符串：

| 字符串 | 地址 | 含义 |
|---|---|---|
| `SimThink` | 0x10760B81 | 表明 `CSimThinkManager` 存在 |
| `GlobalEntityList` | — | 1 处 |
| `CBaseEntityList` | 2 处 |

`CSimThinkManager::m_entinfoIndex[NUM_ENT_ENTRIES]`（`unsigned short`，4096 项 = 0x2000 字节）若存在，必须随实体数扩容。下一步可从 RTTI 类型描述符（type descriptor → vftable → COL）反查其构造函数与数组基址。

## 26. 本轮结论

1. 74→69 已闭合：5 条 `.data` 常量命中被排除。
2. `+0x8` 已闭合：两处是带索引的数组元素访问（序列号读/写），非裸地址。
3. 9 处虚表访问升级为高置信度（函数在虚表中唯一）。
4. 句柄解码点可定界为 **25 处绝对数组访问**；相对形式与独立数组仍待定。
5. 新发现 `0x3FF000`（H9）与 `cmp 0x800/0x1000` 边界（H6），需在 13 位化时单独处理。

---

# 追加：H9 闭环与 CSimThinkManager 定位（第 6 轮）

## 27. H9 闭环：`0x3FF000` 的真实语义

`0x104CF640` 完整语义（反编译确认）：

```c
undefined4 FUN_104cf640(int *pEntity)
{
  if (!pEntity) return 0;
  uint *pHandle = (uint *)(**(code **)(*pEntity + 8))();   // 取实体持有的句柄指针
  uint idx = *pHandle & 0xFFF;
  if (idx < 0x800 && idx < 0x1000) {                       // 双重上界，实际 < 0x800
    if (m_EntPtrArray[idx].pEntity != NULL) {
      uint h2 = (m_EntPtrArray[idx].serial << 12) | idx;    // 反构句柄
      if (h2 != 0xFFFFFFFF && ((h2 ^ *pHandle) & 0x3FF000) == 0)
        return entity->vtable[0x14/4]();                    // 命中则回调
    }
  }
  return 0;
}
```

结论：
- `0x3FF000 = (2^10-1) << 12`，**只比较 15 位序列号的低 10 位**（bit12–21），不是完整序列号比较，也不是网络 EHANDLE 编码。
- 该函数是「句柄 → 实体」的弱校验解析器：索引必须 `< 0x800`，序列号低 10 位必须一致。
- 13 位索引下，该处需同时改：`& 0xFFF→0x1FFF`、`<<12→<<13`、`0x3FF000→0x7FE000`、`<0x800→<新网络上限`。
- **这是唯一一处把索引上界写死为 0x800 的句柄解码点**，属于必须改的 H6。

## 28. CSimThinkManager 已定位

| 项 | 值 | 证据 |
|---|---|---|
| RTTI 名称 | `.?AVCSimThinkManager@@` @ 0x10760B7C | TD @ 0x10760B74 |
| 全局对象 | **0x1075E9E0** | `mov ecx,0x1075E9E0; call Clear` @0x100B688C、@0x10585A0A |
| vptr | 0x105F3A94 | 0x1075E9E0 处的 dword 即该地址 |
| `m_entinfoIndex` | **obj+0x4**，4096 × uint16 = **0x2000 B** | `Clear()` 用 `0x800` 次 dword 填 `0xFFFFFFFF` |
| `m_simThinkList` | **obj+0x2004**（CUtlVector，0x14 B） | Clear 中 pMemory/nAlloc/nGrow/m_Size/pElements 依次访问 |
| 对象尺寸 | **0x2018** | 0x1075E9E0 + 0x2018 = 0x107609F8（下一个全局的起点，已被 .data 表引用） |

`CSimThinkManager::Clear` @ **0x100B62E0**：

```c
m_simThinkList.m_Size = 0;                    // +0x2010
if (m_simThinkList.m_nGrowSize > -1) {
    if (m_simThinkList.m_pMemory) { free(...); m_pMemory = 0; }
    m_simThinkList.m_nAllocationCount = 0;    // +0x2008
}
m_simThinkList.m_pElements = m_pMemory;       // +0x2014
for (i = 0x800; i; --i) *p++ = 0xFFFFFFFF;    // +0x4 起 0x2000 B → 4096 个 uint16 = 0xFFFF
```

**扩容影响**：

| 成员 | 旧偏移 | 新偏移 |
|---|---|---|
| vptr | 0x0 | 0x0 |
| `m_entinfoIndex[4096]` | 0x4 | 0x4（大小 0x2000→**0x4000**） |
| `m_simThinkList` | **0x2004** | **0x4004** |
| 对象尺寸 | 0x2018 | **0x4018** |

`unsigned short` 足以容纳 0–8191，元素宽度不变；但**后续向量成员必须整体后移 0x2000**，这与 `CGlobalEntityList` 的 `+0x10000` 是同类问题。

## 29. 新发现：另外两个 0x2000 字节全局

`rep stosd` 前 `mov ecx,0x800`（=0x2000 字节）的目标：

| 站点 | 目标 | 语义 |
|---|---|---|
| 0x101AEE12 | 0x1081E200 | `xor eax,eax` 清零 0x2000 B |
| 0x1058CBDD | 0x1081E200 | 静态初始化清零 0x2000 B |

0x1081E200 位于 `.data` 尾部 BSS，容量 0x2000 字节，与 `m_entinfoIndex` 同尺寸，**是下一个待审计的实体索引数组候选**（可能是 4096 个 dword 或 4096 个 word 的另一张表）。

## 30. 结论与边界

**已确认**：
- H9 语义闭环（弱序列号比较 + `idx<0x800` 硬上界）。
- `CSimThinkManager` 全局对象、数组偏移、尺寸、`Clear()` 语义。
- 第二个 4096 项数组候选（0x1081E200）。

**未确认**（避免过度声明）：
- `m_entinfoIndex` 的**全部**访问形式（`index*2` 寻址点）尚未枚举，仅确认初始化路径。
- 0x1081E200 的用途与元素宽度未定。
- `this` 相对数组访问、跨模块访问仍未定界。

---

# 追加：CSimThinkManager 访问审计 + 0x1081E200 定性（第 7 轮）

## 31. 对象绝对引用（重定位表）

`[0x1075E9E0, 0x107609F8)` 区间内共 **9 条**绝对引用：

| 偏移 | 数量 | 含义 |
|---|---|---|
| `+0x00000` | 7 | 对象基址（vptr 写入、`mov ecx,obj` 调用） |
| `+0x02004` | 1 | `m_simThinkList.m_pMemory` |
| `+0x02010` | 1 | `m_simThinkList.m_Size` |

对比 `CGlobalEntityList` 的 668 条：该对象绝大多数访问走 `this+disp`，绝对引用极少。

## 32. `m_entinfoIndex` 访问形态（实测 4 处）

| 站点 | 指令 | 语义 |
|---|---|---|
| 0x100B5CA7 | `movzx eax, WORD PTR [ecx+edi*2+4]` | 读 `m_entinfoIndex[index]`（`ecx`=this，`edi`=索引） |
| 0x100B5D00 | `mov [ecx+edx*2+4], eax` | 写 `m_entinfoIndex[index]` |
| 0x100B6BD6 | `mov WORD PTR [edi+esi*2+4], ax` | 写回索引（OnEntityCreated 路径） |
| 0x100B6C0A | `movzx eax, WORD PTR [edi+esi*2+4]` | 读索引 |

`0x100B5CA0` 函数体（RemoveEntinfoIndex/EntityChanged 类）：

```
mov  edi,[ebp+8]                 ; index
movzx eax,WORD [ecx+edi*2+4]     ; m_entinfoIndex[index]
cmp  eax,0xFFFF                  ; 空闲标记
mov  esi,[ecx+0x2010]            ; m_simThinkList.m_Size
mov  edx,[ecx+0x2004]            ; pMemory
```

`0x100B6BC0` 函数体（OnEntityCreated 类）：

```
lea  ecx,[edi+0x2004]            ; &m_simThinkList
call 0x100B6990                  ; CUtlVector::AddToTail
mov  WORD [edi+esi*2+4],ax       ; m_entinfoIndex[index] = listHandle
mov  ecx,[edi+0x2004]            ; pMemory
movzx eax,ax
mov  WORD [ecx+eax*8],si         ; entry[handle].entEntry = index（步长 8）
```

**关键数据**：`simthinkentry_t` 元素步长 = **8 字节**（`[reg+eax*8]`），与 `m_entinfoIndex` 的 16 位索引配合；`entEntry` 为 `unsigned short`，8192 索引仍可容纳，无需扩宽。

## 33. `m_simThinkList` 位移分布

`0x2004`/`0x2008`/`0x200C`/`0x2010`/`0x2014` 的 dword 命中分别为 28/26/52/54/47，但其中大部分属于其它结构的同名偏移（无基址来源证明）。**已确认属于本对象的**为 §32 中两处函数内的 `[ecx+0x2004]`、`[ecx+0x2010]`（以及 Clear 中的 5 个成员）。逐点归属仍需按第 5 轮的「所属函数 + 调用点」方法确认。

## 34. 扩容修改清单（CSimThinkManager）

| 项 | 旧 | 新 |
|---|---|---|
| `Clear()` 填充计数 | `mov ecx,0x800`（0x100B6334 附近） | **`mov ecx,0x1000`**（0x4000 字节） |
| 空闲标记 | `0xFFFFFFFF` 逐 dword | 不变（仍生成 0xFFFF 半字） |
| 数组尺寸 | 0x2000 | **0x4000** |
| `m_simThinkList` 位移 | 0x2004/0x2008/0x200C/0x2010/0x2014 | **+0x2000** |
| 对象尺寸 | 0x2018 | **0x4018** |
| 索引上界检查 | 若存在 `cmp …,0x1000` | 需核对 |

**初始化正确性条件（接受你的强调）**：新 BSS 的零初始化**不能**替代 `Clear()`；新增 4096 项必须显式写 `0xFFFF`，否则 `0` 会被当成合法的 `m_simThinkList` 索引。

## 35. 0x1081E200 定性

访问点：9 条绝对引用（全部 offset 0），集中在 `0x101AEE00–0x101AF330` 与静态初始化 `0x1058CBDD`。

```
101aee08  mov  ecx,0x800
101aee0d  mov  edi,0x1081E200
101aee12  rep stosd                 ; 清零 0x2000 字节
101aee14  mov  eax,0x10804200
101aee19  mov  ecx,0x400
101aee20  ... 0x68 步长构建 1024 项链表 ; eax += 0x68
101af1e9  lea  ecx,[ecx*4+0x1081E200]   ; ← 4 字节步长
```

结论：
- 容量严格为 **0x2000 字节**；
- 访问采用 **4 字节步长**（`lea ecx,[ecx*4+0x1081E200]`）→ **2048 个 dword**，不是 4096 个 word；
- 2048 恰等于旧 `MAX_EDICTS`，**存在按 edict 索引寻址的可能，但尚未取得索引来源证据**；
- 相邻结构 `0x10804200`：0x400 项 × 0x68 字节的双向链表（与 0x1081E200 同期构建），可能与之配对，用途未定。

因此：**不能判定它必须扩容**，需继续追踪索引来源。

## 36. 状态

| 项 | 状态 |
|---|---|
| `m_entinfoIndex` 读写形态 | ✅ 4 处已识别（读/写各 2） |
| `simthinkentry_t` 步长 | ✅ 8 字节 |
| `Clear()` 修改点 | ✅ 已定位（`mov ecx,0x800`） |
| `m_simThinkList` 位移 | ◐ 仅已确认函数内的 2 处 |
| 监听器注册/注销路径 | ⛔ 未定位 |
| 0x1081E200 | ◐ 容量/步长已定，索引来源未定 |

---

# 追加：0x1081E200 定性 + 监听器路径闭环（第 8 轮）

## 37. H9 汇编复核：四个判断点都是真实的

原始汇编（0x104CF640，已对齐）：

```
104cf65c  and  edx,0xFFF          ; idx = h & 0xFFF
104cf662  cmp  edx,0x800          ; idx < MAX_EDICTS(网络上限)
104cf668  jge  fail
104cf66a  test edx,edx
104cf66c  js   fail               ; 有符号检查（int 转换）
104cf66e  cmp  edx,0x1000         ; idx < NUM_ENT_ENTRIES(总上限)
104cf674  jge  fail
```

**结论**：反编译器没有合并数据流。`0x800` 与 `0x1000` 是**两个独立比较**，作用在同一掩码后的变量上；虽然第二个在数学上冗余，但二进制中确实存在。因此 H9 的修改点是 4 个（掩码、两个上界、序列号掩码），不是 2 个。

## 38. 0x1081E200 定性：2048 桶哈希表，不是实体索引数组

Ghidra 反编译 `FUN_101af170`（唯一使用者）：

```c
piVar5 = (&DAT_1081e200)[*(int *)(unaff_EDI + 0x48)];      // 桶头
for (; piVar5; piVar5 = *piVar5) { ... }                    // 遍历链表

iVar2 = piVar5[0x14];                                       // entry+0x50 = 键
*piVar5 = (&DAT_1081e200)[iVar2];                           // 插入桶
(&DAT_1081e200)[iVar2] = piVar5;
```

结构关系：

| 项 | 值 |
|---|---|
| `0x1081E200` | **2048 个桶头指针**（0x800 dword，4 字节步长） |
| `0x10804200` | 1024 项 × **0x68 字节** 的节点池（双向链表） |
| 节点键 | `entry+0x50`（`piVar5[0x14]`），另有一处取 `EDI+0x48` |
| 关系 | `0x1081E200 − 0x10804200 = 0x1A000 = 1024 × 0x68`（相邻布局，同一分配器） |

**结论**：桶索引来自**节点自身的键字段**，不是 edict 索引，也不是 `CBaseHandle` 解码。因此：

- 2048 只是哈希表容量，与 `MAX_EDICTS=2048` 的数值巧合不构成依赖；
- 实体扩容到 4096 **不要求**该表扩容；若键含实体索引，只是桶冲突率上升，**正确性不受影响**；
- 它与 `CSimThinkManager` 是两回事，**不应并入实体容量迁移清单**。

这条结论与「容量恰好等于 2048 就值得警惕」的直觉相反，但有反编译证据支撑。

## 39. 监听器注册/注销路径已定位

**注册**（0x100B751D）：

```
100b751d  push 0x1075E9E0          ; &g_SimThinkManager
100b7522  mov  ecx,0x107E0760      ; this = &gEntList
100b752c  call 0x100B6DA0          ; AddListenerEntity
```

**注销**（0x100B6876）：

```
100b6876  mov  [ebp-4],0x1075E9E0  ; 局部变量 = &g_SimThinkManager
100b6868  lea  ecx,[ebp-4]
100b686b  push ecx
100b686c  mov  ecx,0x107F0784      ; &gEntList.m_entityListeners (= obj+0x10024)
100b687d  call 0x100B5B60          ; RemoveListenerEntity / Find
100b6882  mov  ecx,0x1075E9E0
100b6887  call 0x100B62E0          ; Clear()
```

**跨对象不变量已具象化**：注册与注销**各自独立地**使用两个对象的绝对地址——
`0x107E0760`（或 `0x107F0784` 派生地址）与 `0x1075E9E0`。迁移时必须同步改写：

| 站点 | 旧值 | 新值 |
|---|---|---|
| 0x100B7522/0x100B6882 的 `mov ecx` | 0x107E0760 / 0x1075E9E0 | 各自新基址 |
| 0x100B686C 的 `mov ecx,0x107F0784` | gEntList+0x10024 | 新基址+**0x20024** |
| 0x100B751D / 0x100B6876 的立即数 | 0x1075E9E0 | CSimThinkManager 新基址 |

后者正是 `object_references.csv` 中 `+0x10024` 那 6 条之一，可作为一致性校验点。

## 40. 补丁 manifest 的两类条目（按你的要求分开）

**A 类：可直接构造**

| 项 | 数量 | 说明 |
|---|---|---|
| `CGlobalEntityList` 对象基址引用 | 622 | 620 `mov ecx` + 1 绝对写 + 1 `.data` |
| 数组基址引用 | 23 | 全部 slot 0 |
| 成员位移 | 58 | `0x100xx→0x200xx` |
| 立即数位移 | 2 | `+0x10000` |
| `CSimThinkManager::Clear()` 计数 | 1 | `0x800→0x1000` |
| `CSimThinkManager` 向量位移 | 5 成员 | `+0x2000` |
| 句柄 H1/H2/H3/H6/H9 | ~49 | 含 4 个判断点 |
| 静态初始化绝对写 | 9 | gEntList 派生成员 |

**B 类：待语义确认，不得提前标记完成**

| 项 | 原因 |
|---|---|
| `this+4+idx*16` 相对数组访问 | 基址来源未证明 |
| 跨模块句柄消费者 | client.dll 未分析 |
| 监听器回调路径（OnEntityCreated/Deleted） | 仅注册/注销确认 |
| `m_entinfoIndex` 其余访问 | 仅 4 处已识别 |
| 高索引运行时行为 | 未执行 |

## 41. 状态

| 项 | 状态 |
|---|---|
| H9 四判断点 | ✅ 汇编复核完成 |
| `0x1081E200` | ✅ 定性为哈希桶表，**不并入**容量迁移 |
| 监听器注册/注销 | ✅ 已定位（两处绝对地址） |
| 统一 manifest A/B 分类 | ✅ 已成表 |

---

# 追加：P0 验证结果（第 9 轮）

## 42. `CSimThinkManager` 初始化状态：**文件内静态 vptr，不能迁到纯 BSS**

| 检查 | 结果 |
|---|---|
| 0x1075E9E0 所在节 | `.data`（文件偏移 0x75D5E0，在 raw 范围内） |
| 文件首 dword | **0x105F3A94**（vtable 指针） |
| 该 dword 有 HIGHLOW 重定位 | **是** |
| 运行时写 vptr（`C7 05 e0 e9 75 10 94 3a 5f 10`） | **0 处** |
| 文件内 0x2004..0x2018（向量成员） | 全 0 |
| 文件内 m_entinfoIndex（0x2000 B） | 全 0（运行期由 `Clear()` 填 0xFFFF） |

静态初始化 0x10585A00：

```
10585a00  mov  ecx,0x1075E9E0
10585a05  call 0x100B62E0        ; Clear()
10585a0a  push 0x105B1020        ; atexit 注册
10585a0f  call 0x1055E8C6
```

**结论（情况 B）**：`CSimThinkManager` 的 vptr 来自 **PE 文件数据 + 重定位**，不是运行时构造函数写入。因此「新 BSS 段 + 零初始化」的迁移方式对它**无效**——迁入零区后 vptr = 0，首次虚调用即崩。

迁移方式必须改为以下之一：

| 方案 | 做法 | 代价 |
|---|---|---|
| **S-a** | 新对象放在**文件有初值**的节：首 dword 写新 vtable 地址并生成 HIGHLOW | 需要新增 raw 数据 + 重定位项 |
| **S-b** | 保留 BSS，但在静态初始化里插入 `mov dword [NEW], 0x105F3A94` 桩 | 需要代码桩（当前唯一必须的桩） |
| S-c | 原地不迁移，改为「扩容数组 + 指针间接」 | 需改所有 `this+disp`，不可行 |

对比 `CGlobalEntityList`：它的 vptr 由静态初始化 `0x105859B1 C7 05 … 0x105F3A78` 在运行时写入，所以可以放纯 BSS。**两个对象的初始化方式确实不同**，你的判断成立。

## 43. 哈希键来源：部分闭合

- `FUN_101ae850` = 22 dword（0x58 B）结构拷贝，把入参的 `+0x50` 复制到节点 `+0x50`，**不是键的生产者**。
- 插入时 `bucket = buckets[entry+0x50]`；查找时 `bucket = buckets[*(EDI+0x48)]`。
- 键的**最初来源**仍在调用者（`FUN_101af170` 的入参）中，尚未追到赋值点。

当前可下的结论：桶索引来自节点键字段，**没有证据表明 `bucket == edictIndex`**；也没有证据表明它是 `CBaseHandle` 解码。因此：

- **不列入** 4096 扩容清单（结论不变）；
- 但按你的要求，**不宣布完全无关**，保留为「键来源未追」的独立条目。

## 44. Manifest 新增前置项（必须）

| 编号 | 类型 | 内容 |
|---|---|---|
| M-1 | **A 类（新增）** | `CSimThinkManager` 新对象必须有初值：vtable `0x105F3A94` + HIGHLOW，否则需 S-b 桩 |
| M-2 | A 类 | `Clear()` 填充计数 `0x800→0x1000` |
| M-3 | A 类 | `m_simThinkList` 5 个成员位移 `+0x2000` |
| M-4 | A 类 | 注册/注销 4 个绝对立即数（0x107E0760 / 0x1075E9E0 / 0x107F0784） |
| M-5 | B 类 | 哈希键来源未追 |
| M-6 | B 类 | `this+4+idx*16` 相对访问 |
| M-7 | B 类 | 监听器回调路径 |
| M-8 | B 类 | `m_entinfoIndex` 其余访问 |

## 45. H9 补丁计数口径（避免重复）

| 位置 | 原值 | 新值 | 归类 |
|---|---|---|---|
| 0x104CF65E | `and edx,0xFFF` | `0x1FFF` | H2 |
| 0x104CF662 | `cmp edx,0x800` | `0x1000` | H6 |
| 0x104CF66E | `cmp edx,0x1000` | `0x2000` | H6 |
| 0x104CF68B | `shl eax,0xC` | `0xD` | **H1（已计入 4 处打包点？需核对——此处不在列表 API 内，应单列）** |
| 0x104CF697 | `test eax,0x3FF000` | `0x7FE000` | H9 |

该函数共 **5 处**与句柄布局相关；其中 `shl` 属于 H1 语义但**不在**先前 4 处列表 API 打包点内，manifest 中应作为独立的 H1 条目，不与列表 API 的 4 处混算。

---

# 追加：P0-1 / P0-2 结果（第 10 轮）

## 46. P0-2：对象文件初值全量核查（结论：只需 4 字节 raw）

扫描 `0x1075E9E0` 起 **0x2018 字节**的全部 dword：

| 结果 | 值 |
|---|---|
| 非零 dword | **1 个**：`+0x00000 = 0x105F3A94` |
| 区间内重定位项 | **1 条**（即 vptr 所在位置） |
| `+0x2004..+0x2017`（CUtlVector） | **全 0** |
| `+0x0004..+0x2003`（m_entinfoIndex） | **全 0**（运行期由 Clear 填 0xFFFF） |

因此 S-a 所需的初始化数据只有 **4 字节有效内容**：

```
新段 .simthink
  VirtualSize   = 0x4018
  SizeOfRawData = FileAlignment (0x200)
  raw 内容      : 94 3A 5F 10 00 ... 00   (仅首 dword 有效)
  +0x0200..+0x04018 : 加载器零填充
  重定位        : 1 条 HIGHLOW @ 新段+0
```

**不存在需要迁移的其它初值**，`CUtlVector` 在文件中本就是零，运行期由 `Clear()` 建立。这一点比预期简单——你担心的「向量初值」实测为零。

## 47. P0-1：哈希键范围压缩已定位

`FUN_101af170` 只有 **一个直接调用点**：

```
101af48d  call 0x101AF170
  前置: 25 ff 07 00 00   and eax,0x7FF          ← 范围压缩
         8d 7d a4         lea edi,[ebp-0x64]
         89 45 ec         mov [ebp-0x14],eax
         e8 e3 fc ff ff   call
```

- 调用前对键值执行 **`and eax,0x7FF`**，即强制落在 **0..2047**；
- 唯一调用点意味着所有直接调用路径都经过该掩码；
- 与 `FUN_101af170` 内 `buckets[key]`、`buckets[*(EDI+0x48)]` 的用法一致。

**结论**：桶索引被显式压缩到 2048 以内，**不会越界**。若键原本是 0..8191 的实体索引，掩码会带来更多碰撞，但**不破坏正确性，也不要求扩容**。

保留的不确定性：`and eax,0x7FF` 掩码后存入 `[ebp-0x14]`，而函数内读取的是 `EDI+0x48`（`ebp-0x1C`）；两者是否同一字段尚需一条 store 链确认。若不同，则掩码作用于另一字段，键的界限需另行证明。**这一点不宣布闭合**。

## 48. M-4 更正：5 个操作数位置

| VA | 原引用 | 类型 |
|---|---|---|
| 0x100B751D | 0x1075E9E0 | push imm（注册） |
| 0x100B7522 | 0x107E0760 | mov ecx,imm（注册） |
| 0x100B6876 | 0x1075E9E0 | mov [ebp-4],imm（注销） |
| 0x100B686C | 0x107F0784 | mov ecx,imm（&m_entityListeners） |
| 0x100B6882 | 0x1075E9E0 | mov ecx,imm（Clear 调用） |

合计 **5 处**，其中 0x107E0760/0x107F0784/0x1075E9E0 均已包含在两个对象的绝对引用集合内，manifest 中不得重复计数。

## 49. 表述收紧

「唯一需要代码桩或文件初值的地方」应限定为：

> **在已识别的两个迁移对象中**，`CSimThinkManager` 是唯一确认不能采用纯零初始化 BSS 的对象。

未分析的独立对象、client.dll 结构均可能再有同类问题，不作普遍断言。

## 50. 状态

| 项 | 状态 |
|---|---|
| P0-2 文件初值 | ✅ 完成（仅 1 个 dword + 1 条重定位） |
| P0-1 桶索引范围 | ◐ 掩码已定位，字段同一性待确认 |
| M-4 计数 | ✅ 更正为 5 |
| S-a 可行性 | ✅ 确认（4 字节 raw + 1 条 HIGHLOW） |

---

# server.dll 统一迁移 manifest（第 11 轮）

产物：[manifest.server.json](manifest.server.json)（生成器 [gen_manifest.py](gen_manifest.py)，只读）。

## 51. 目标布局

| 新段 | RVA | VA | VirtualSize | SizeOfRawData | 类型 |
|---|---|---|---|---|---|
| `.entlist` | 0x982000 | 0x10982000 | 0x20038 | 0 | **BSS**（vptr 由 `0x105859B1` 运行期写入） |
| `.simthink` | 0x9A3000 | 0x10A03000 | 0x4018 | **0x200** | 有初值（首 dword `0x105F3A94` + 1 条 HIGHLOW） |

`SizeOfImage_new = 0x9A5000`。

| 对象 | 旧 | 新 | 尺寸 |
|---|---|---|---|
| `CGlobalEntityList` | 0x107E0760 | 0x10982000 | 0x10038 → 0x20038 |
| `CSimThinkManager` | 0x1075E9E0 | 0x10A03000 | 0x2018 → 0x4018 |

## 52. 补丁清单（791 条，A 类）

| 类别 | 数量 | 内容 |
|---|---|---|
| `A1-glref` | **668** | gEntList 全部绝对引用（含数组基址、字段、`.data` 指针） |
| `A10-stref` | **9** | CSimThinkManager 绝对引用（含 +0x2004/+0x2010 的 +0x2000 位移） |
| `A3-gldisp` | **58** | gEntList 成员位移 `0x100xx→0x200xx` |
| `A4-glimm` | **2** | 成员偏移立即数（`sub eax,0x10010`、`add ecx,0x10024`） |
| `A7-ctor` | **3** | 构造常量：`0x1000→0x2000`、`0x801C→0x1001C`、`0x7FF→0xFFF` |
| `A8-thresh` | **2** | `cmp ebx,0x800 → 0x1000`（分离网络/非网络） |
| `A9-mask` | **21** | `and reg,0xFFF → 0x1FFF`（20 查找点 + RemoveEntity） |
| `A9-shl` | **4** | 列表 API 打包 `shl reg,0xC → 0xD` |
| `A9-h9` | **5** | H9 函数五处（掩码、两上界、移位、序列号掩码） |
| `A10-vec` | **18** | `m_simThinkList` 成员位移 `+0x2000` |
| `A10-clear` | **1** | `Clear()` 填充 dword 数 `0x800→0x1000` |

## 53. 离线校验结果

对原始文件逐字节应用 791 条补丁：

| 项 | 结果 |
|---|---|
| 条目数 | 791 |
| 区间重叠 | **0** |
| 原始字节不匹配 | **0** |
| 实际改动字节 | **2,147** |
| 去重丢弃 | 1（H9 的 `shl` 与列表 API 打包语义重复，按唯一位置合并） |

SHA-256 绑定：`a93ec916a8f26fbea85688c321d2ba8dd346d435fab09a0b926dd950c2e1ea12`（必须与该文件完全一致才应用）。

## 54. B 类（未生成补丁，独立保留）

| 编号 | 内容 |
|---|---|
| B-hashkey | `0x1081E200` 桶键：`and eax,0x7FF` 已定位，但与 `EDI+0x48` 字段同一性未证明 |
| B-rel16 | `this+4+idx*16` 相对数组访问：基址来源未证明 |
| B-callback | 监听器虚回调路径未完整追踪（仅注册/注销） |
| B-entinfo | `m_entinfoIndex` 除 4 处外的其余访问 |
| B-client | client.dll 与跨模块句柄消费者 |
| B-runtime | 未做 >2048 实体运行验证 |

## 55. 需要人工复核的两处

1. **`A10-vec = 18`**：扫描范围取 `0x100B5C00–0x100B6E00`，其中可能混入同值立即数的其它结构。清单已标注，建议逐条核对所属函数后再应用。
2. **`A8-thresh = 2`**：三个候选函数只命中 2 处 `cmp ebx,0x800`，第三处可能被编译器换成别的形式（或与 `A10-clear` 的 `mov ecx,0x800` 合并），需确认是否遗漏。

## 56. 未包含在 manifest 中的内容

- PE 节表/SizeOfImage/重定位目录的**结构修改**（JSON 中仅有段描述，未生成节头补丁）。
- 网络协议（11 位 edict 索引）、client.dll、快照。
- 任何运行时验证。

---

# manifest v2：PE 布局修正与分类复核（第 12 轮）

生成器 v2：[gen_manifest_v2.py](gen_manifest_v2.py) → [manifest.server.json](manifest.server.json)。

## 57. PE 布局修正（采纳）

原 manifest 有两处错误：

| 项 | v1（错） | v2（修正） |
|---|---|---|
| 第二节段名 | `.simthink`（9 字符，超限） | **`.simthnk`**（8 字符） |
| 第二节 VA | 0x10A03000（与 RVA 0x9A3000 不自洽） | **0x109A3000** |
| `SizeOfImage` | 0x9A5000 | **0x9A8000** |

校验：`0x9A3000 + 0x4018 = 0x9A7018`，按 `SectionAlignment=0x1000` 对齐 → **0x9A8000** ✓。

| 节 | RVA | VA | VirtualSize | SizeOfRawData | 初始化 |
|---|---|---|---|---|---|
| `.entlist` | 0x982000 | 0x10982000 | 0x20038 | 0 | 运行期构造写入 vptr |
| `.simthnk` | 0x9A3000 | 0x109A3000 | 0x4018 | 0x200 | 静态 vptr + 1 条 HIGHLOW |

新增重定位块（已写入 manifest）：

```
Page RVA     0x009A3000
SizeOfBlock  0x0000000C
Entry 0      0x3000   HIGHLOW, offset 0
Entry 1      0x0000   ABSOLUTE 填充
```

## 58. 去重口径（已可解释）

v2 改用主键 `(rva, file_offset, size)`，并记录被丢弃项：

| 丢弃 | 保留 | 位置 | 原因 |
|---|---|---|---|
| `A8-thresh` | `A8-thresh` | RVA 0xB7AE9 | 同一 `cmp ebx,0x800` 被 `0x100B7970` 与 `0x100B7A30` 两个扫描窗口同时命中 |

这是扫描窗口重叠导致的**同址重复**，不是语义冲突。最终唯一条目数：**786 A 类 + 5 B 类 = 791**。

## 59. A10-vec 由 18 降为 13

以「函数被 `mov ecx,0x1075E9E0; call` 调用」为基址证明条件，13 条通过，5 条降级为 `B-vec`：

| RVA | 偏移 | 说明 |
|---|---|---|
| 0xB5CB6 / 0xB5CC7 / 0xB5CDE / 0xB5CEF / 0xB5CF7 | +0x2010 / +0x2004 | 位于 `0x100B5CA0` 函数内 |

这 5 条与已证明的 `movzx eax,[ecx+edi*2+4]`（`m_entinfoIndex` 访问）在**同一函数**内，几乎可以确定属于 `CSimThinkManager`；但缺少「该函数以 simthink 为 this」的调用证据，故不入 A 类。

## 60. A9-mask 21 条的证据

全部 21 条均满足：掩码后 24 字节内出现 `0x107E0764`（数组基址）——即「掩码 → shl 4 → 数组寻址」序列。第 21 条为 `RemoveEntity(handle & 0xFFF)`，随后直接调用 `RemoveEntityAtSlot`。这与之前 2840 条全量掩码中的 2820 条无关命中形成区分。

## 61. v2 校验

| 项 | 结果 |
|---|---|
| A 类补丁 | **786** |
| B 类（不应用） | **5** |
| 原始字节不匹配 | **0** |
| 改动字节 | **2,142** |
| SHA-256 | `a93ec916…1ea12` |

## 62. 仍未闭合

- B-hashkey：`and eax,0x7FF` 与 `EDI+0x48` 相差 8 字节（`ebp-0x14` vs `ebp-0x1C`），不是同一字段，桶索引界限未证。
- B-vec ×5：见 §59。
- B-callback / B-entinfo / B-client / B-runtime 不变。
- PE 结构修改（节表、SizeOfImage、重定位目录、校验和、证书表）尚未生成，仅有描述。

---

# PE 预检器 + B-hashkey 闭环（第 13 轮）

## 63. 只读 PE 预检器

[precheck_server.py](precheck_server.py) → [precheck/precheck.json](precheck/precheck.json)。**30 项检查全部通过**，不改写任何文件（内存模拟）。

| 组 | 检查 | 结果 |
|---|---|---|
| 绑定 | SHA-256 与 manifest 一致 | PASS |
| 头 | PE 签名、PE32 magic、SectionAlignment=0x1000、FileAlignment=0x200 | PASS |
| 节 | 4 个原节的 raw 均在文件内 | PASS |
| 布局 | 原镜像末地址 0x981800 → 对齐 0x982000 == SizeOfImage | PASS |
| 新节 | RVA 推导与 manifest 一致（0x982000 / 0x9A3000）、名字 ≤8 字节、无虚拟重叠 | PASS |
| 镜像 | `SizeOfImage_new = 0x9A8000` | PASS |
| 节头 | 需要 0x2D8 ≤ `SizeOfHeaders` 0x400，且 ≤ 首节 raw 0x400 | PASS |
| 重定位 | 目录 RVA 0x8A0000、1948 个块、完整消费 0xD10F4 | PASS |
| 新重定位块 | 12 字节可追加，尾部余量 0x1603C | PASS |
| 补丁 | 786 条全部 old 字节匹配、0 重叠 | PASS |
| 再解析 | NumberOfSections、SizeOfImage、reloc size、新块可见、`.simthnk` 头与 vptr 字节 | PASS |
| 签名 | 证书表 0x8B2498 + 0x2C98 恰至 EOF；**补丁后 Authenticode 失效** | 已报告 |

## 64. B-hashkey 闭环：桶索引确实被限制在 2048 内

调用点 0x101AF48D 的真实上下文：

```
101af47d  and  eax,0x7FF            ; key & 2047
101af482  lea  edi,[ebp-0x5C]       ; ← Ghidra 报的是 ebp-0x64，实际是 0x5C
101af485  mov  [ebp-0x14],eax       ; 存入局部结构
101af488  call 0x101AF170
```

被调用函数读取 `*(int*)(EDI+0x48)`：

```
(ebp - 0x5C) + 0x48 = ebp - 0x14
```

**正是被掩码写入的那个字段**。此前「相差 8 字节」的判断源于反编译器给出的 `lea edi,[ebp-0x64]`，机器码实为 `8d 7d a4` = `ebp-0x5C`。

结论：
- 桶索引 = `(key) & 0x7FF`，恒 `< 2048`；
- 2048 桶表**不会越界**，**不需要扩容**；
- 与 edict 索引的关系：即使 key 携带 13 位实体编号，掩码会压缩，正确性不受影响（仅碰撞上升）。

`0x1081E200` 正式从「待定」移出扩容清单。

## 65. B 类剩余

| 编号 | 状态 |
|---|---|
| B-hashkey | ✅ 关闭 |
| B-vec ×5 | 位于 0x100B5CA0，与已证 `[ecx+edi*2+4]` 同函数，缺 this 证明 |
| B-callback | 未追踪 |
| B-entinfo | 4 处之外的访问未枚举 |
| B-client | 未分析 |
| B-runtime | 未执行 |

## 66. 当前可交付状态

- `engine.dll`：4096 edicts 存储层补丁副本，43 项校验通过（既有）。
- `server.dll`：786 条 A 类字节级补丁 + 5 条 B 类，PE 预检 30/30 通过，SHA-256 绑定。
- 尚未生成实际 `server.dll` 输出文件（预检器为只读），未写入游戏目录，未运行。

---

# B-vec ×5 闭环（第 14 轮）

## 67. `0x100B5CA0` 的 `this` 一致性证明

完整反编译（`CSimThinkManager::RemoveEntinfoIndex`）：

```c
void FUN_100b5ca0(int index)              // __thiscall, this = ECX
{
  u16 h = *(u16 *)(this + 4 + index*2);   // m_entinfoIndex[index]
  if (h == 0xFFFF) return;
  int n = *(int *)(this + 0x2010);        // m_simThinkList.m_Size
  if (n > 0) {
    if (h != n-1) {
      int p = *(int *)(this + 0x2004);    // m_pMemory
      *(u32*)(p + h*8)     = *(u32*)(p - 8 + n*8);   // 元素搬移（stride 8）
      *(u32*)(p + 4 + h*8) = *(u32*)(p - 4 + n*8);
    }
    *(int *)(this + 0x2010) = n - 1;
  }
  *(u16 *)(this + 4 + index*2) = 0xFFFF;
  if ((int)h < *(int *)(this + 0x2010))
    *(u16 *)(this + 4 + 2*(*(u16*)(*(int*)(this+0x2004) + h*8))) = h;
}
```

关键数据流事实：

| 事实 | 证据 |
|---|---|
| `ECX` 在函数内**从未重新赋值** | 全程只改 eax / edx / esi / ebx / edi |
| 五处访问均以 `[ecx+disp]` 寻址 | 0xB5CB6/CC7/CDE/CEF/CF7 的 modrm 基址均为 `ecx` |
| 0x100B5CA7 的数组访问与它们同源 | 同一 `ecx`，中间无 `call`、无 `mov ecx,...` |
| 偏移恰为 `m_Size`(0x2010) 与 `m_pMemory`(0x2004) | 与 `Clear()` 中的成员访问一致 |

因此这五处的基址**不是「同函数出现正确数组访问」的推断**，而是寄存器级证明：`ECX` 单一来源，即函数入口的 `this`。

## 68. 升级为 A 类

| RVA | 指令 | 旧 → 新 |
|---|---|---|
| 0xB5CB6 | `mov esi,[ecx+0x2010]` | 0x2010 → 0x4010 |
| 0xB5CC7 | `mov edx,[ecx+0x2004]` | 0x2004 → 0x4004 |
| 0xB5CDE | `dec dword [ecx+0x2010]` | 0x2010 → 0x4010 |
| 0xB5CEF | `cmp eax,[ecx+0x2010]` | 0x2010 → 0x4010 |
| 0xB5CF7 | `mov edx,[ecx+0x2004]` | 0x2004 → 0x4004 |

全部为 disp32、等长替换。

## 69. manifest v3

| 项 | v2 | v3 |
|---|---|---|
| A 类 | 786 | **791** |
| B 类补丁 | 5 | **0** |
| `A10-vec` | 13 | **18** |
| 改动字节 | 2142 | **2147** |
| 原始字节不匹配 | 0 | 0 |
| PE 预检 | 30/30 | **30/30** |

新增位移后所有字段仍落在新对象 `0x4018` 范围内（最大 0x4014 < 0x4018）。

## 70. 剩余分析项（不再是补丁分类问题）

| 编号 | 内容 | 状态 |
|---|---|---|
| B-callback | `CGlobalEntityList` 监听器向量回调时使用迁移后指针 | 待追踪 |
| B-entinfo | `m_entinfoIndex` 4 处之外是否还有访问；`this+4+idx*16` 相对实体访问 | 待枚举 |
| B-client | client.dll 与跨模块句柄 | 未开始 |
| B-runtime | >2048 实体运行验证 | 未执行 |

`0x1081E200` 已退出扩容清单；仅剩一项低风险确认：哈希链表的键比较应使用完整原始键，避免不同实体索引落入同桶时被误认为同一条目。

---

# B-callback 闭环与最终静态审计（第 15 轮）

## 71. 监听器回调路径

`CGlobalEntityList::OnAddEntity`（0x100B5820）：

```c
m_iNumEnts++;                                  // this+0x10018
if (m_iHighestEnt < (handle & 0xFFF))          // this+0x10014
    m_iHighestEnt = handle & 0xFFF;
entity = (**(code**)(*pEntity + 0x14))();
if (*(entity + 0x28)) m_iNumEdicts++;          // this+0x1001C
for (i = m_entityListeners.m_Size; --i >= 0; )
    (**(code**)**(void***)(m_entityListeners.pMemory + i*4))(entity);
```

关键点：

| 事实 | 影响 |
|---|---|
| 遍历 `this+0x10024`（pMemory）与 `this+0x10030`（m_Size） | 已在 `A1-glref` 的 668 条内（+0x20024/+0x20030） |
| 存储的是**监听器对象指针**（`0x1075E9E0`） | 由注册点 `0x100B751D` 的 `push 0x1075E9E0` 写入 → 已随 `A10-stref` 迁移 |
| 回调经 `listener->vtable[0]` | 虚表地址 `0x105F3A94` 不变，回调对象地址更新即可 |
| `handle & 0xFFF` 用于 `m_iHighestEnt` | **新发现**：与数组寻址无关，之前的掩码扫描未覆盖 → 补入 |

因此注册、回调、注销三条路径都指向同一迁移后的对象，**不存在 Register(new)/Unregister(old) 的悬空风险**（只要 A10-stref 与 A1-glref 同步应用）。

## 72. 最终静态审计

| 项 | 结果 |
|---|---|
| A 类补丁 | **792** |
| B 类补丁 | **0** |
| 分布 | `.text` 791、`.data` 1 |
| 修改区间 | 0xE20B … 0x75D5BC（文件 0x8B5130） |
| 落在重定位项上的补丁 | 677 |
| **未覆盖的旧地址引用** | **0** |
| 原始字节不匹配 | 0 |
| 改动字节 | 2,148 |
| PE 预检 | **30/30** |
| SHA-256 绑定 | `a93ec916…1ea12` |

补丁分类：`A1-glref` 668、`A3-gldisp` 58、`A9-mask` 22、`A10-vec` 18、`A10-stref` 9、`A9-h9` 5、`A9-shl` 4、`A7-ctor` 3、`A4-glimm` 2、`A8-thresh` 2、`A10-clear` 1。

## 73. `m_entinfoIndex` 不需要补丁

数组固定在 `obj+4`，扩容只改尺寸（0x2000→0x4000）与 `Clear()` 填充次数；所有 `[ecx+4+idx*2]`、`[ecx+edi*2+4]` 访问的位移**不变**。需要改的只有数组之后的五个向量成员（18 处，`A10-vec`）。

## 74. 静态审计的边界

已证明：地址映射、操作数宽度、PE 布局、重定位、补丁一致性。
未证明：运行时行为、client.dll 消费者、网络协议、>2048 实体的实际调度。

---

# 服务端测试副本 + client.dll 起点（第 16 轮）

## 75. 隔离测试副本已生成

[build_server.py](build_server.py) → `out/server.4096.dll`

| 项 | 值 |
|---|---|
| 大小 | 0x8B5400（原 0x8B5130，+0x2D0） |
| SHA-256 | `6fa5fd362fb646be8e7eed758dd21a17e5917afd834f588f42efa3ab7d2fcfc9` |
| SizeOfImage | 0x9A8000 |
| 节数 | 6 |
| 补丁 | 792 条 |
| PE 校验和 | 0x8B6020（重算） |

结构处理：
- 新节头写入原节表空闲区（0x2D8 ≤ SizeOfHeaders 0x400）；
- `.reloc` 原有 0x1080C 字节余量，12 字节新块**原地追加**，未移动任何原始数据；
- `.simthnk` 的 0x200 字节 raw 追加在文件末尾（0x8B5400 处，按 FileAlignment 对齐）；
- 证书表仍在 0x8B2498，**未移动**；补丁后 Authenticode 失效（已知）。

验证：重新解析写入文件，节数/SizeOfImage/reloc size/新块可见/vptr 字节全部通过。

**注意**：raw 数据位于证书表之后（非典型布局），仅用于离线加载测试；正式分发应改为证书表前置或重建签名。

## 76. client.dll 起点

| 项 | 值 |
|---|---|
| 大小 | 0x7EBC00 |
| SHA-256 | `c0a8e1e88f7312db11bcfd4b0ec574d224a34b2d9a615d6088b28335eeb4af1f` |
| SizeOfImage | 0x963000 |
| 节 | `.text`(0x1000) `.rdata`(0x529000) `.data`(0x6BC000) `.rsrc`(0x894000) `.reloc`(0x895000) |

RTTI 定位：

| 项 | 值 |
|---|---|
| 类型描述符 `.?AVCClientEntityList@@` | TD = **0x106C50D0** |
| COL 候选 | 0x1068E1F4（offset 0x0）、0x1068E294（offset **0x10014**） |
| 虚表 1 | 0x10564B8C → `vt[0]=0x100BB8C0`、`vt[1]=0x100BB9E0` |
| 虚表 2 | 0x10564B60 → `vt[0]=0x100B8D20`、`vt[1]=0x100B8E60` |

`0x10014` 这个 offset 值需要核实：它既可能是多重继承的 vtable 偏移，也可能是别的结构；在确认前不能假定 client 侧与 server 侧同构（SDK 2013 的 `NUM_ENT_ENTRIES=8192` 与 L4D2 实测 4096 不同，正是这个原因）。

## 77. 方法学约束（采纳）

后续不能再用 `NUM_ENT_ENTRIES = MAX_EDICTS << 2` 推导 L4D2 的数据结构。每个模块必须实测：
- 对象尺寸与数组容量；
- 内部句柄索引位宽；
- 网络 EHANDLE 的网络索引/序列号位宽；
- 无效句柄哨兵值。

## 78. 下一阶段任务

| 优先级 | 对象 | 要回答 |
|---|---|---|
| P0 | `CClientEntityList` | 槽位数、布局、句柄位宽 |
| P0 | 客户端实体创建/回收 | 网络索引 → 客户端实体的映射 |
| P0 | `svc_PacketEntities` | 2048 上限在编解码中的体现 |
| P0 | 网络 EHANDLE | 11 位索引 + 10 位序列号的编码/解码与哨兵 |
| P1 | 快照/PackedEntity | 固定位图与差分是否依赖 2048 |

---

# client.dll 首批结构实测（第 17 轮）

## 79. `CClientEntityList` 的两个虚表

| 虚表 | 地址 | 函数 | 语义 |
|---|---|---|---|
| A | 0x10564B8C | `vt[0]=0x100BB8C0` | `AddEntity(handle, entity)` 类 |
| A | | `vt[1]=0x100BB9E0` | 待定 |
| B | 0x10564B60 | `vt[0]=0x100B8D20` | `GetEntity(index)`：数组在 `this+0x28`，步长 8 |
| B | | `vt[1]=0x100B8E60` | 待定 |

## 80. `0x100BB8C0` 实测

```asm
and   edi,0xFFF              ; ← 内部索引 12 位（与 server 相同掩码）
mov   esi,ecx
cmp   edi,0x7FF              ; ← 网络实体上界 2048
ja    skip
inc   dword [esi+0x1002C]    ; 计数
cmp   edi,[esi+0x10038]
mov   [esi+0x10038],edi      ; m_iHighestEnt
mov   [esi+edi*8+0x1003C],eax      ; 数组元素 = 实体指针（步长 8）
mov   word [esi+edi*8+0x10042],1   ; 同条目内的标志/序列
lea   ecx,[esi+0x1803C]      ; 另一结构起点
```

推出对象布局（client 侧，与 server 不同构）：

| 偏移 | 含义 |
|---|---|
| +0x1002C | 计数器（Add 次数） |
| +0x10038 | `m_iHighestEnt` |
| **+0x1003C** | 实体数组，**步长 8**，2048 项 → 0x4000 字节，止于 0x1403C |
| +0x1803C | 第二个数组/结构（0x1403C + 0x4000） |

对比 server：数组在 +4、步长 16；client 在 +0x1003C、步长 8。**两者不是同一布局**，不能复用 server 的补丁生成器。

## 81. `0x100B8D20` 实测

```asm
cmp  eax,0x7FF
ja   ret0
mov  eax,[ecx+eax*8+0x28]    ; 数组在 this+0x28，步长 8
ret
```

这是另一个类（数组基址 +0x28），很可能是 `CClientEntityList` 的基类实现（对应 server 的 `CBaseEntityList`，但布局完全不同）。

## 82. 位宽结论（初步）

| 项 | client.dll 实测 | server.dll 实测 |
|---|---|---|
| 内部索引掩码 | `0xFFF`（12 位） | `0xFFF`（12 位） |
| 网络实体上界 | `0x7FF`（2048） | `0x800`（2048） |
| 实体条目步长 | 8 | 16 |
| 数组偏移 | +0x1003C | +4 |
| `m_iHighestEnt` | +0x10038 | +0x10014 |

**两端位宽假设一致**（12 位内部索引、2048 网络实体），但对象布局不同。这为「client 与 server 可独立迁移、参数不同」提供了实测依据，也再次否定按 SDK 宏推导。

## 83. 下一步（P0）

1. 定位 `CClientEntityList` 全局实例（vptr 可能像 `CSimThinkManager` 一样静态写在 `.data`）。
2. 确认 `+0x1003C` 数组的真实容量（是否有 0x1000 次初始化循环）。
3. 确认 `+0x1803C` 是什么（第二个数组？快照位图？）。
4. 找 `svc_PacketEntities` 的解析函数，看 11 位 edict 索引如何解出 `handle`。

---

# client.dll 对象布局确认（第 18 轮）

## 84. `+0x10014` 是次级基类 vptr —— 你的推断成立

构造点 `0x100BB3F0`：

```asm
100bb3f0  push esi / push edi
100bb3f2  mov  edi,ecx
100bb3f4  mov  dword [edi], 0x10564B8C          ; 主 vptr  @ +0x0
100bb3fa  mov  dword [edi+0x10014], 0x10564B60  ; 次 vptr  @ +0x10014
100bb404  call 0x100B9280
```

同一构造函数写入两个 vptr，间隔正好 0x10014。因此：

```
this_B = this_A + 0x10014
this_B + 0x28 = this_A + 0x1003C     ← 同一数组
```

**虚表 A 与虚表 B 访问的是同一块实体数组**，不是两个独立类。`0x10014 + 0x28 = 0x1003C` 不是巧合。

（另一构造点 0x100BB500 是派生类，先把 0x10564B34 写到 +0x10014，再覆盖 +0 为同一 vtA。）

## 85. 客户端基类数组：与 server 同构

`0x100B9280`（构造后调用，遍历清除）：

```asm
mov  eax,[esi+0x10004]        ; 链/指针
sub  eax,esi
sub  eax,0x4
sar  eax,0x4                  ; index = (p - this - 4) >> 4   ← 16 字节步长
...
mov  edi,[esi+edx*8+0x8]
shl  edi,0xC                  ; handle = serial << 12 | index
or   edi,eax
cmp  edi,0xFFFFFFFF
```

| 项 | client | server |
|---|---|---|
| 基类数组偏移 | `+0x4` | `+0x4` |
| 步长 | **16** | **16** |
| 容量 | **4096**（0x10000 字节，止于 +0x10004） | 4096 |
| 句柄编码 | `serial<<12 \| index` | 同 |

## 86. 客户端实体缓存：4096 项，你的计算成立

| 项 | 值 |
|---|---|
| 缓存起点 | `+0x1003C` |
| 下一成员 | `+0x1803C` |
| 差值 | **0x8000** |
| 步长 | 8 |
| 容量 | **4096 项** |

所以 `cmp edi,0x7FF` 只是**网络实体与非网络实体的逻辑分界**，不是数组物理末端。这一条纠正了我上一轮「2048 项」的表述。

## 87. 完整对象布局（推定，待逐项验证）

| 偏移 | 成员 | 尺寸 |
|---|---|---|
| +0x00000 | 主 vptr（`IClientEntityList` 主接口） | 4 |
| +0x00004 | `CBaseEntityList::m_EntPtrArray[4096]`（16B） | 0x10000 |
| +0x10004 | 链表头/计数等 | 0x10 |
| +0x10014 | 次级 vptr（vtable 0x10564B60） | 4 |
| +0x10018.. | 次级基类成员 | ~0x24 |
| +0x1003C | `m_EntityCacheInfo[4096]`（8B） | 0x8000 |
| +0x1803C | 后续成员（待定性） | ? |

## 88. 对扩容方案的影响

| 项 | 现状 | 4096 网络实体所需 |
|---|---|---|
| 内部索引位宽 | 12 位（0..4095） | **不变**（4095 足够） |
| 网络上界检查 | `cmp 0x7FF` | `cmp 0xFFF`（或 0x1000） |
| 基类数组 | 4096×16 | 若需保留非网络实体池 → 8192×16，位移 +0x10000 |
| 缓存数组 | 4096×8 | 同上则 → 8192×8，再 +0x8000 |

即：**若客户端允许 4096 个网络实体全部占满 4096 槽位**，则只改上界，数组与对象布局都不用动；**若要与服务端一样保留非网络池**，则两个数组都要扩容，后续成员总位移 0x18000。

这是需要先决策的设计分支，而不是可以先写补丁的技术细节。

## 89. 下一步

1. 定性 `+0x1803C`（是否 `m_BaseEntities` 链表）。
2. 找到 `CClientEntityList` 全局实例地址与构造调用点。
3. 统计 client 侧 `cmp 0x7FF` 的全部站点（决定改动面）。
4. 决策：客户端是否保留非网络实体池（决定是否扩容两个数组）。

---

# client.dll：`+0x1803C` 定性（第 19 轮）

## 90. `+0x1803C` = `CUtlLinkedList`（`m_BaseEntities`）

初始化序列（0x100BB530）：

```asm
mov [esi+0x1803C], eax        ; m_pMemory / m_Head
mov [esi+0x18040], eax        ; m_Tail
mov [esi+0x18044], eax
mov ecx, 0xFFFF
mov word [esi+0x18052], cx    ; m_FirstFree = 0xFFFF
mov [esi+0x1804C], ecx
mov ecx, [esi+0x1803C]
mov [esi+0x18054], ecx        ; m_pElements
mov [esi+0x18048], 0xFFFFFFFF ; m_LastAlloc = 0xFFFFFFFF
```

与 `CUtlLinkedList` 的字段特征完全一致（NULL 头尾、0xFFFF 空闲索引、0xFFFFFFFF 末分配、pElements 回指）。访问方式也匹配：

| 站点 | 指令 | 语义 |
|---|---|---|
| 0x100BB463 | `lea ecx,[edi+0x1803C]` | 取链表对象地址（传 this） |
| 0x100BB491 | `mov [edi+0x1803C],0` | 清空 |
| 0x100BB92B | `lea ecx,[esi+0x1803C]; push 0; call` | `AddToTail` |
| 0x100BBA89 | `lea ecx,[esi+0x1803C]; call` | 遍历/查找 |
| 0x100B997B | `mov eax,[edx+0x1803C]; mov edi,[eax+ecx*8]` | 元素访问（8 字节/项） |

结论：`+0x1803C` 是**链表成员**，不是第二个数组。对象尺寸 **≥ 0x18058**（最后写入 0x18054）。

## 91. 完整对象布局（C2 基线）

| 偏移 | 成员 | 旧尺寸 | 新偏移 |
|---|---|---|---|
| +0x00000 | 主 vptr | 4 | +0x0 |
| +0x00004 | `m_EntPtrArray[4096]` ×16 | 0x10000 | +0x4（8192 项，0x20000） |
| +0x10004 | 基类链表/计数 | 0x10 | **+0x20004** |
| +0x10014 | 次级 vptr | 4 | **+0x20014** |
| +0x10018..0x1003B | 次级基类成员 | 0x24 | **+0x20018..** |
| +0x1003C | `m_EntityCacheInfo[4096]` ×8 | 0x8000 | **+0x2003C**（8192 项，0x10000） |
| +0x1803C | `m_BaseEntities`（CUtlLinkedList） | ≥0x1C | **+0x3003C** |
| +0x18058+ | 后续成员 | ? | **+0x30058+** |

位移：`Δ₁ = 0x10000`（基类数组）、`Δ₂ = 0x8000`（缓存）、`Δ_total = 0x18000`。

## 92. 次级 this 与 RTTI（C2 特有）

| 项 | 旧 | 新 |
|---|---|---|
| 主 vptr 写入 | `[edi], 0x10564B8C` | 不变 |
| 次 vptr 写入 | `[edi+0x10014], 0x10564B60` | `[edi+0x20014]` |
| COL #2 `offset` | `0x10014` | **`0x20014`** |
| 经次级 this 访问缓存 | `[ecx+0x28]`（`this_B`） | **仍为 +0x28** |

因为 `this_B' = this_A' + 0x20014`，故 `this_B' + 0x28 = this_A' + 0x2003C`。**次级 this 的成员偏移不迁，只有完整对象 this 的成员偏移迁。** 这是客户端不能做全文件简单替换的原因。

还需审计 Base Class Descriptor 的 PMD 位移是否含 0x10014。

## 93. 全局实例

构造函数 0x100BB3F0 的唯一直接调用者是 **0x100BB650**（另一个构造函数：`push esi; mov esi,ecx; call 0x100BB3F0` 后接放置删除判断），说明它是被派生类构造链调用的，**不是静态初始化点**。全局实例需从 0x100BB650 的调用者继续上溯，或从 `new` 运算符的调用点定位。

当前**未定位**全局对象地址。

## 94. 下一步

1. 从 0x100BB650 上溯到静态初始化（`mov ecx, imm; call` 或 `operator new`）。
2. 确认对象是否含文件静态初值（两个 vptr 是否像 `CSimThinkManager` 一样写在 `.data`）。
3. 统计 `+0x1803C` 之后到对象末尾的成员（0x18058..0x18080 区间的写入点）。
4. 再进入 `0x7FF` 的语义分类。

---

# client.dll：构造函数/析构函数更正与全局实例（第 20 轮）

## 95. `0x100BB650` 确认是 scalar deleting destructor

```asm
100bb650  push ebp / mov ebp,esp / push esi
100bb654  mov  esi,ecx
100bb656  call 0x100BB3F0          ; ~CClientEntityList()
100bb65b  test byte [ebp+0x8],1    ; flags & 1
100bb65f  je   skip
100bb661  push esi
100bb662  call 0x100011F0          ; operator delete
100bb66a  mov  eax,esi             ; return this
100bb66d  ret  4
```

标准 MSVC 模式。因此：

| 地址 | 原标注 | 更正 |
|---|---|---|
| 0x100BB650 | 构造函数调用者 | **scalar deleting destructor** |
| 0x100BB3F0 | 构造函数 | **析构函数** `~CClientEntityList()` |
| 0x100BB500 | — | **真正的构造函数** |

## 96. 构造函数 0x100BB500

```asm
push esi / mov esi,ecx
call 0x100EA580                    ; 基类 CBaseEntityList 构造
mov  [esi+0x10014], 0x10564B34     ; 构造期基类 vptr
mov  [esi],          0x10564B8C    ; 主 vptr
mov  [esi+0x10014], 0x10564B60     ; 次级 vptr（最终）
xor  eax,eax
mov  [esi+0x10018],eax ... [esi+0x10024],eax
; 随后初始化 m_BaseEntities（0x1803C..0x18054）等
```

次级 vptr 被写两次（先基类表，后本类表），这是多重继承构造的正常形态。

## 97. 全局实例：0x1073A560（BSS）

| 项 | 值 |
|---|---|
| 实例地址 | **0x1073A560** |
| 所在区域 | `.data` 的 **BSS 尾部**（RVA 0x73A560 > raw 覆盖末端 0x71FA00）→ **无文件初值** |
| 静态初始化 | `0x104FD9E0` 附近：`mov ecx,0x1073A560; call 0x100BB500` |
| 全局指针 | `[0x106C50A8] = 0x1073A560`、`[0x106C50AC] = 0x1073A560` |
| 对象尺寸 | 下一个全局 0x10752608 起 → **0x180A8** |

**关键结论**：客户端实体列表是 BSS 对象，vptr 由构造函数在运行期写入，**不存在 `CSimThinkManager` 那样的静态 vptr 问题**，迁移可直接用纯 BSS 段。

两个 `.data` 指针 `0x106C50A8/AC` 对应 `g_pEntityList` 与 `cl_entitylist`（同一地址的双导出），迁移时必须同步改写。

## 98. C2 迁移映射（client）

| 成员 | 旧 | 新 |
|---|---|---|
| 主 vptr | +0 | +0 |
| `m_EntPtrArray[4096]×16` | +4 | +4（8192 → 0x20000） |
| 基类链表/计数 | +0x10004 | +0x20004 |
| 次级 vptr | +0x10014 | +0x20014 |
| `m_EntityCacheInfo[4096]×8` | +0x1003C | +0x2003C（8192 → 0x10000） |
| `m_BaseEntities` | +0x1803C | +0x3003C |
| 对象尺寸 | **0x180A8** | **0x300A8** |

`Δ_total = 0x18000`。

## 99. 客户端待办

| 优先级 | 任务 |
|---|---|
| P0 | 次级接口 `this` 调整点（`+0x10014` 加/减、调整桩、接口工厂） |
| P0 | COL #2 `offset` 0x10014 → 0x20014，及 Base Class Descriptor 的 PMD |
| P0 | `0x18058..0x180A8` 的成员（PVS 通知链表/映射） |
| P1 | 全局指针 0x106C50A8/AC 与接口暴露路径 |
| P2 | `0x7FF` 语义分类 |

---

# client.dll：次级 this 调整与剩余成员（第 21 轮）

## 100. `+0x10014` 的两类用途（已枚举 20+ 处）

### (a) 取次级 vptr / 调整 this 后调虚函数

```asm
100B8ECD  mov  eax,[ecx+0x10014]     ; 取 vtB
100B8ED3  mov  edx,[eax+8]           ; slot
100B8ED6  add  ecx,0x10014           ; ← this_B = this_A + 0x10014
          call edx
```

同一模式出现在 **0x100B50B8、0x100B8ED6、0x100B8F16、0x100B8F56、0x100B92C0（lea）、0x1017257E、0x10172BEE、0x1017AE02**。

**全部必须改为 `0x20014`**——这正是此前判断「第二种最容易遗漏」的那一类。

### (b) 写入次级 vptr

| 站点 | 位置 | 归属 |
|---|---|---|
| 0x100BB3FC | 析构 | 写 vtB `0x10564B60` |
| 0x100BB50A | 构造 | 写基类 vtB `0x10564B34` |
| 0x100BB51A | 构造 | 写最终 vtB `0x10564B60` |

## 101. COL #2 确认

```
0x1068E294: signature=0x0  offset=0x10014  cdOffset=0x0
            pTypeDescriptor=0x106C50D0 (CClientEntityList)
            pClassDescriptor=0x1068E208
```

`offset` 字段 = 0x10014，**必须改为 0x20014**，否则 RTTI 计算完整对象地址会偏移。
`pClassDescriptor`（0x1068E208）中的 Base Class Descriptor 是否含 PMD 位移，需逐项核对。

## 102. `0x18058..0x180A4` 的成员确实存在

对区间内每个 4 字节位移统计 `.text` 命中：

| 偏移 | 命中 | 偏移 | 命中 |
|---|---|---|---|
| +0x18058 | 4 | +0x18080 | 8 |
| +0x1805C | 2 | +0x18084 | 13 |
| +0x18060 | 1 | +0x18088 | 6 |
| +0x18064 | 4 | +0x1808C | 4 |
| +0x18068 | 8 | +0x18090 | 102（含其他结构同值） |
| +0x1806C | 4 | +0x18094..A4 | 各 1–2 |
| +0x18070 | 13 | | |

说明对象在 `m_BaseEntities` 之后仍有连续成员（与 SDK 的 `m_PVSNotifyInfos` / `m_PVSNotifierMap` 位置相符），**对象尺寸 0x180A8 可信**。

## 103. 客户端迁移修改清单（新增类别）

| 类别 | 数量 | 说明 |
|---|---|---|
| `C1-global` | 4 | 对象地址引用（静态初始化 + 2 个 `.data` 指针） |
| `C2-vptr` | 3 | 主/次级 vptr 写入（含构造期基类 vptr） |
| `C3-this` | **≥8** | `add/lea ...,0x10014` 次级 this 调整 |
| `C4-vtload` | **≥8** | `mov reg,[reg+0x10014]` 取次级 vptr |
| `C5-col` | 1 | COL #2 offset 0x10014 → 0x20014 |
| `C6-member` | ? | 完整对象 this 的成员位移（0x10004..0x180A4 区间） |
| `C7-array` | ? | 两个数组容量相关常量 |

`C3` 与 `C4` 是客户端独有、服务端没有的类别。

## 104. 下一步

1. 全量枚举 `+0x10014`/`-0x10014` 的调整点（当前只看了前 20 处）。
2. 解析 `pClassDescriptor = 0x1068E208` 的 Base Class Descriptor，核对 PMD 位移。
3. 枚举完整对象 this 的成员访问（`0x10004..0x180A4`），建立旧→新映射表。
4. 之后才统计 `0x7FF` 语义。

---

# client.dll：次级 this 全量分类 + RTTI/PMD（第 22 轮）

## 105. `0x10014` 全量分类（45 处命中）

| 类别 | 数量 | 说明 |
|---|---|---|
| **ADD-this** | **17** | `add reg,0x10014` → 转次级 this |
| **LEA-this** | **1** | `lea ecx,[esi+0x10014]` @ 0x100B92C0 |
| **LOAD-vt** | **10** | `mov reg,[reg+0x10014]` 取次级 vptr |
| **WRITE-vptr** | **3** | 构造/析构写 vptr |
| other | 14 | 与其他结构同值，无关 |

### ADD-this 17 处

```
0x100B50B8 0x100B8ED6 0x100B8F16 0x100B8F56 0x1017257E 0x10172BEE
0x1017AE02 0x1017BCE2 0x101905F9 0x10190655 0x10190CA0 0x10192912
0x101D8D31 0x101D8EA1 0x1020EB71 0x1020F32E 0x10212CB4
```

### WRITE-vptr 3 处

| 站点 | 归属 |
|---|---|
| 0x100BB3FC | 析构函数 |
| 0x100BB50A | 构造函数（基类 vptr 0x10564B34） |
| 0x100BB51A | 构造函数（最终 vptr 0x10564B60） |

## 106. RTTI 层级与 PMD

CHD @ `0x1068E208`：`attributes=1`、`numBaseClasses=3`、`pBaseClassArray=0x1068E218`

| # | BCD | 类型 | mdisp | pdisp | vdisp |
|---|---|---|---|---|---|
| 0 | 0x1068E228 | `CClientEntityList` | 0 | -1 | 0 |
| 1 | 0x1068E244 | `CBaseEntityList` | 0 | -1 | 0 |
| 2 | **0x1068E278** | **`IClientEntityList`** | **0x10014** | -1 | 0 |

**BCL #2 的 `mdisp = 0x10014` 必须改为 `0x20014`**，与 COL #2 的 `offset` 一致。前两个基类 mdisp=0，不随布局变化。

## 107. 三段式成员映射（验证你给出的公式）

$$F(o)=\begin{cases}o & 0\le o<0x10004\\ o+0x10000 & 0x10004\le o<0x1803C\\ o+0x18000 & 0x1803C\le o<0x180A8\end{cases}$$

次级 this 的位移增量：

$$\Delta d=F(o)-F(0x10014)-(o-0x10014)$$

| 次级 this 访问目标 | Δd |
|---|---|
| 次级 vptr 本身 | 0 |
| `m_EntityCacheInfo`（0x1003C..0x1403C） | **0** |
| `m_BaseEntities` 及之后（0x1803C+） | **+0x8000** |

例：`this_B+0x28`（缓存起点）不变；`this_B+0x8028`（`m_BaseEntities`）需 +0x8000。**次级 this 的访问并非全部保持不变**，这一点你的推导成立。

## 108. 客户端补丁类别（更新）

| 类别 | 数量 |
|---|---|
| `C1-global`（对象地址引用） | 4 |
| `C2-vptr`（写入） | 3 |
| `C3-this`（ADD/LEA 调整） | **18** |
| `C4-vtload`（取次级 vptr） | **10** |
| `C5-rt`（COL offset + BCD mdisp） | **2** |
| `C6-member` | 待枚举 |
| `C7-array` | 待枚举 |

## 109. 仍待完成

1. 完整对象 this 的成员访问枚举（0x10004..0x180A4），建立 C6 表。
2. 次级 this 访问 `m_BaseEntities` 的 +0x8000 站点（与 C6 交叉）。
3. `0x7FF`/`0xFFF` 语义分类（C7）。
4. 对象尺寸 0x180A8 的最终确认（最后一字段）。

---

# client.dll：C6 成员表（第 23 轮）

## 110. 方法集界定

以「访问 `m_BaseEntities`（0x1803C）」为对象方法判据，得到 5 个方法：

```
0x100B9960  0x100BB3F0 (析构)  0x100BB500 (构造)  0x100BB7F0  0x100BB9E0
```

在这 5 个方法体内枚举 `[reg+disp]` 形式、disp ∈ [0x10004,0x180A8)：

**35 个偏移、156 个站点**

| 偏移 | 新偏移 | 站点 | | 偏移 | 新偏移 | 站点 |
|---|---|---|---|---|---|---|
| +0x10014 | +0x20014 | 5 | | +0x18058 | +0x30058 | 4 |
| +0x10018 | +0x20018 | 11 | | +0x1805C | +0x3005C | 3 |
| +0x1001C | +0x2001C | 2 | | +0x18060 | +0x30060 | 2 |
| +0x10020 | +0x20020 | 2 | | +0x18064 | +0x30064 | 2 |
| +0x10024 | +0x20024 | 9 | | +0x18068 | +0x30068 | 2 |
| +0x10028 | +0x20028 | 2 | | +0x1806C | +0x3006C | 3 |
| +0x10030 | +0x20030 | 2 | | +0x18070 | +0x30070 | 14 |
| +0x10038 | +0x20038 | 12 | | +0x18074..0x1808C | +0x30074… | 各 2–3 |
| +0x1803C | +0x3003C | 25 | | +0x18090 | +0x30090 | 7 |
| +0x18040 | +0x30040 | 3 | | +0x18094..0x180A4 | +0x30094… | 各 2 |
| +0x18044 | +0x30044 | 3 | | | | |
| +0x18048 | +0x30048 | 2 | | | | |
| +0x1804C | +0x3004C | 10 | | | | |
| +0x18050/54 | +0x30050/54 | 各 2 | | | | |

## 111. 对象尺寸确认

对象内最后一个被访问的成员偏移是 **+0x180A4**（2 处），之后无访问；与「下一全局 0x10752608」给出的边界一致：

```
0x180A8 = 0x10752608 - 0x1073A560
```

**对象尺寸 0x180A8 得到双向确认**（成员上界 + 全局边界）。

## 112. 未覆盖的方法

`0x100BB8C0`（AddEntity）访问 0x1002C / 0x10038 / 0x1003C，但并不访问 0x1803C，因此未被上述判据收入。这说明：

- C6 的 35/156 是**已验证子集**；
- 完整集合还需把「访问 0x10014、0x1002C、0x10038、0x1003C 的函数」并入方法集，再去重。

另外，缓存数组内部访问走的是次级 this（`this_B+0x28`），位移不变，不应进入 C6。

## 113. 客户端补丁类别（更新）

| 类别 | 数量 | 状态 |
|---|---|---|
| `C1-global` | 4 | 已验证 |
| `C2-vptr` | 3 | 已验证 |
| `C3-this` | 18 | 已验证 |
| `C4-vtload` | 10 | 已验证 |
| `C5-rt` | 2 | 已验证 |
| **`C6-member`** | **156（子集）** | 待扩全 |
| `C7-array` | 待定 | 未开始 |

## 114. 下一步

1. 扩充方法集（并入访问 0x10014/0x1002C/0x10038 的函数），重算 C6。
2. C7：`0x7FF`/`0xFFF` 按语义分类。
3. 生成 client.dll manifest（先 A/B 分类，不写文件）。

---

# client.dll：C6-A/B/C 审计（第 24 轮）

## 115. 统计范围澄清（回应「45 处」）

全文件 dword `0x10014` 分布：

| 节 | 数量 |
|---|---|
| `.text` | **39**（不同 dword 位置） |
| `.rdata` | **2**（RTTI：COL offset @ 0x1068E298、BCD mdisp @ 0x1068E280） |

此前的 45 = 扫描时的**逐字节匹配数**，其中 6 处是重叠匹配（同一 dword 在不同起始偏移被重复命中）。真实指令数：

| 类别 | 数量 |
|---|---|
| ADD-this | 17 |
| LEA-this | 1 |
| LOAD-vt | 10 |
| WRITE-vptr | 3 |
| 合计 | **31** |

RTTI 的 2 处**不在** 39 之内（位于 `.rdata`），必须单独计入 manifest。

## 116. 负向 this 调整：不存在

| 检查 | 结果 |
|---|---|
| `sub ecx/esi/eax,0x10014` | **0 处** |
| `lea reg,[reg-0x10014]` | 0 处 |
| dword `0xFFFEFFEC` | 3 处，但都不是 this 调整 |

3 处 `0xFFFEFFEC` 实际是栈帧位移：

```
100C219D  c7 85 ec ff fe ff ff ff ff ff   ; mov dword [ebp-0x114], -1
100C2237  39 b5 ec ff fe ff               ; cmp  [ebp-0x114], esi
100C2264  39 b5 ec ff fe ff               ; cmp  [ebp-0x114], esi
```

`0xFFFEFFEC = -0x114`，是局部变量偏移，与对象无关。

**结论：反向调整不存在，只有正向 18 处（17 ADD + 1 LEA）。**

## 117. C6-C：对象区间的绝对引用

对 `[0x1073A560, 0x10752608)` 做重定位引用审计，共 **5 处**：

| 引用位置 | 节 | 目标 |
|---|---|---|
| **0x100B8CF1** | `.text` | **对象 + 0x10014**（次级接口指针） |
| 0x104FD9E1 | `.text` | 对象 + 0 |
| 0x1051ED91 | `.text` | 对象 + 0 |
| 0x106C50A8 | `.data` | 对象 + 0（`g_pEntityList`） |
| 0x106C50AC | `.data` | 对象 + 0（`cl_entitylist`） |

**0x100B8CF1 是唯一保存次级接口指针的位置**，迁移后必须指向 `NEW+0x20014`，而不是 `NEW`。这正是接口边界一致性检查的关键点：如果只替换对象基址而漏掉这一处，引擎拿到的 `IClientEntityList*` 会指向错误子对象。

## 118. C6-A 与 C6-B 的现状

| 集合 | 数量 | 状态 |
|---|---|---|
| C6-A 主对象成员（5 个方法内） | 35 偏移 / 156 站点 | 已验证子集 |
| C6-B 次级 this 成员 | 由 10 处 LOAD-vt + 18 处 ADD-this 进入 | 位移规则确定（缓存区 0，链表区 +0x8000） |
| C6-C 绝对引用 | **5** | 完成 |

## 119. 客户端清单现状

| 类别 | 数量 |
|---|---|
| `C1-global` | 4（1 + 2 指针 + 静态初始化） |
| `C2-vptr` | 3 |
| `C3-this` | 18 |
| `C4-vtload` | 10 |
| `C5-rt` | 2 |
| `C6-member` | 156（子集） |
| C6-C | 5（含 1 处次级接口指针） |

## 120. 下一步

1. 扩充 C6-A 方法集（并入访问 0x10014/0x1002C/0x10038/0x1003C 的函数）。
2. C6-B：从 10 处 LOAD-vt 的调用点反查次级 this 的成员访问，确认 +0x8000 站点。
3. C7：`0x7FF`/`0xFFF` 语义分类。
4. 生成 client.dll manifest。

---

# 修正：0xFFFEFFEC = -0x10014（第 25 轮）

## 121. 算术更正

| 值 | 正确含义 |
|---|---|
| `0xFFFEFFEC` | **-0x10014** |
| `0xFFFFFEEC` | -0x114（我此前误写） |

因此三处指令实际是：

```
100C219D  mov dword [ebp-0x10014], -1
100C2237  cmp [ebp-0x10014], esi
100C2264  cmp [ebp-0x10014], esi
```

## 122. 栈帧核实：-0x10014 落在合法局部区

所属函数 `0x100C1FE0` 序言：

```asm
100C1FE0  push ebp
100C1FE1  mov  ebp,esp
100C1FE3  mov  eax,0x1A064
100C1FE8  call 0x1047FE00        ; __alloca_probe —— 申请 0x1A064 字节栈帧
100C1FED  mov  eax,ds:0x1071AC70
100C1FF2  xor  eax,ebp           ; /GS cookie
...
100C1FFC  lea  eax,[ebp-0x18024] ; 大局部结构起点
```

栈帧 **0x1A064 > 0x10014**，所以 `[ebp-0x10014]` 是**合法的局部变量位移**，不是 this 调整。

**修正后的结论**：存在与 `-0x10014` 数值相同的操作数，但基址为 `EBP` 且落在 0x1A064 字节栈帧内，属于局部结构访问，**不属于对象指针调整**。负向 this 调整仍然未发现。

## 123. 负向调整的排除理由（修正版）

| 检查 | 结果 | 依据 |
|---|---|---|
| `sub ecx/esi/eax,0x10014` | 0 处 | 指令编码扫描 |
| `lea reg,[reg-0x10014]` | 0 处 | 指令编码扫描 |
| `0xFFFEFFEC` | 3 处 | 均为 `[ebp-0x10014]`，帧 0x1A064，合法局部 |

## 124. 采纳的审计规则

1. **方法集扩展靠调用关系**，不以「访问 0x1803C」为必要条件；0x100BB8C0 已证明反例。
2. **去重主键**：`(RVA, operand_offset, operand_size)`；语义类别作为多标签，不重复计数。
3. **C1-interface 单列**：`0x100B8CF1` → `NEW+0x20014`，不并入 `C1-global=4`。
4. 已确认方法内也须逐条基址证明（同函数可能同时用 ECX/EAX/EDX 指向不同对象）。
5. C6 标记全集的停止条件：所有对象入口、虚表方法、调用关系均已分析，且每条未分类访问都有明确原因。

## 125. 初始化审计待办（下一轮）

| 项 | 内容 |
|---|---|
| 缓存语义 | 新增缓存项初值 0 是否满足 `m_EntityCacheInfo` 语义 |
| 无效标记 | `m_BaseEntitiesIndex` 的无效值设置点 |
| 最高索引 | `RecomputeHighestEntityUsed` 的反向遍历是否仍按旧上界 |
| 非网络池 | 客户端分配起点是否需从 `0x801` 移到 `0x1001` |

---

# client.dll manifest（第 26 轮）

## 126. 方法图谱

种子 17 个（构造 0x100BB500、析构 0x100BB3F0、0x100B9960、0x100BB7F0、0x100BB9E0 + 两个虚表槽位），
按直接调用关系扩展后 **40 个方法**。

## 127. C6-A/B 结果

在 40 个方法体内按 `[reg+disp32]`（mod=10）枚举，记录基址寄存器：

| 类别 | 数量 |
|---|---|
| C6-member | **129**（去重后） |
| C4-vtload | **17**（含此前误分为 other 的 `mov edx,[ecx+0x10014]` 7 处） |
| C3-this | **18** |
| C2-vptr | **3** |
| C1-global | **4** |
| C1-interface | **1** |
| C5-col / C5-bcd | **2** |
| C7-bound | **5** |
| **合计** | **179** |

去重 8 处（C6 与更高优先级标签重合），按 `(file_offset,size)` 主键合并，保留高优先级标签。

## 128. C7 结果

`cmp reg,0x7FF` 共 **5 处**：0x100BB8D6、0x100BB9F3、0x10177DCB、0x10179C46、0x1044725B → 统一改 `0xFFF`。

`and reg,0xFFF` 共 **802 处**，语义未定，全部列入 B 类（需数据流分类），未生成补丁。

## 129. PE 布局

| 项 | 值 |
|---|---|
| 原镜像末虚拟地址 | 0x962600 |
| 新节 `.client_el` RVA | **0x963000** |
| VA | **0x10963000** |
| VirtualSize | 0x300A8 |
| SizeOfRawData | 0（BSS） |
| **SizeOfImage_new** | **0x994000** |
| 节头空间 | 需要 0x300 ≤ SizeOfHeaders 0x400，且 ≤ 首节 raw 0x400 |

注：上一版写 0x993000 是错的（0x963000+0x300A8=0x9930A8 → 对齐 0x994000），已修正。

## 130. 校验

| 项 | 结果 |
|---|---|
| SHA-256 绑定 | 通过 |
| 补丁应用 | 179 条，0 不匹配，0 重叠 |
| 改动字节 | 262 |

## 131. 初始化待办（下一轮）

- 缓存项初值语义、`m_BaseEntitiesIndex` 无效标记
- `RecomputeHighestEntityUsed` 反向遍历上界
- 非网络池起点是否从 0x801 移到 0x1001
- 802 处 `and 0xFFF` 的数据流分类

---

# 客户端基类构造逆向 + manifest v2（第 27 轮）

## 132. 节名修正

`.client_el`（10 字节）→ **`.clentls`**（8 字节）；生成器已加入 `len(name) <= 8` 断言。

## 133. `CBaseEntityList` 构造（0x100EA580）完整逆向

```asm
mov [edi], 0x10568CFC          ; 基类 vptr
mov [edi+0x10004..0x10010], 0  ; 链表头
lea esi,[edi+4]                ; 实体数组
mov ebx,0x1000                 ; ← 4096 槽
loop1:
  mov [esi+0xC],esi / [esi+8],esi
  call 0x1018BE40              ; rand
  and eax,0x7FFF               ; 15 位序列号
  mov [esi+4],eax              ; slot.serial
  mov [esi],0                  ; slot.entity = NULL
  add esi,0x10                 ; 步长 16
  dec ebx / jne loop1

lea eax,[edi+0x801C]           ; ← 非网络池起点 slot 0x801
mov esi,0x7FF                  ; ← 2047 个槽
loop2: 建立非网络空闲链
  add eax,0x10 / dec esi / jne loop2
```

与服务端 `CBaseEntityList` 构造**结构完全一致**：4096 槽、随机 15 位序列号、网络区 0..0x7FF、空洞 0x800、非网络 0x801..0xFFF。

三处容量常量已加入 manifest：

| 位置 | 旧 | 新 |
|---|---|---|
| 0x100EA5A8 | 0x1000 | **0x2000** |
| 0x100EA5CF | 0x801C | **0x1001C** |
| 0x100EA5D5 | 0x7FF | **0xFFF** |

## 134. 句柄打包

新增 `C8-shl` 2 处：`shl reg,0xC → 0xD`
- 0x100B92A7（`shl edi,0xC`，实体句柄构造）
- 0x10190CCF

## 135. C1-interface 目标值修正

`0x100B8CF1` 保存的是次级接口指针，目标应为 `NEW+0x20014`：

```
0x1074A574 -> 0x10983014
```

（上一版误算为 `NEW+0x10014`。）

## 136. manifest v2

| 类别 | 数量 |
|---|---|
| C6-member | 129 |
| C3-this | 18 |
| C4-vtload | 17 |
| C7-bound | 5 |
| C1-global | 4 |
| C2-vptr | 3 |
| C7-ctor | 3 |
| C8-shl | 2 |
| C5-col / C5-bcd | 2 |
| C1-interface | 1 |
| **合计** | **184** |

校验：0 不匹配、0 重叠、改动 268 字节。

## 137. B 类与未决

| 项 | 数量 | 说明 |
|---|---|---|
| `and 0xFFF` 掩码 | **802** | 需数据流分类，未生成补丁 |
| C7 未确认比较 | 3 | 0x10177DCB、0x10179C46、0x1044725B 语义未证 |
| 无效句柄 | — | 需验证 `GetEntryIndex(0xFFFFFFFF)` 与 slot 0x1FFF 是否冲突 |

## 138. 下一轮

1. 802 处掩码的前向/后向数据流分类（从句柄生产者与数组消费者出发）。
2. 三处 C7 比较的函数语义确认。
3. 无效句柄兼容性（0xFFFFFFFF → 最后槽位）实测控制流。
4. 客户端初始化/清理路径检查（free-list 返回、序列号）。

---

# 客户端句柄消费者审计 + manifest v3（第 28 轮）

## 139. 掩码分类：452 处确认为 CEntInfo 索引解码

对 802 处 `and REG,0xFFF` 按后续指令分类：

| 后续形态 | 数量 | 判定 |
|---|---|---|
| `add REG,REG` + `lea [base+REG*8+disp]` | **452** | **索引解码 → &CEntInfo[idx]（16 字节步长）** |
| `cmp` 边界 | 2 | 网络边界比较 |
| 其它/未知 | 348 | 待数据流 |

典型序列（0x10011E41）：

```asm
and  ecx,0xFFF
add  ecx,ecx            ; idx*2
lea  ecx,[edx+ecx*8+4]  ; &CEntInfo[idx]（4 + idx*16）
shr  eax,0xC            ; serial
cmp  [ecx+4],eax        ; 序列号比较
```

这类掩码**全部需要 0xFFF → 0x1FFF**，已作为 `C9-mask` 加入 manifest。

## 140. C7 分类修正（采纳）

| 站点 | 状态 |
|---|---|
| 0x100BB8D6 | **A 类**（AddEntity 网络上界，已见 `[esi+0x10038]` m_iHighestEnt 更新） |
| 0x100BB9F3 | **A 类** |
| 0x10177DCB、0x10179C46、0x1044725B | **降级为 pending**，语义未证 |

## 141. manifest v3

| 类别 | 数量 |
|---|---|
| C9-mask | **452** |
| C6-member | 129 |
| C3-this | 18 |
| C4-vtload | 17 |
| C1-global | 4 |
| C2-vptr | 3 |
| C7-ctor | 3 |
| C8-shl | 2 |
| C7-bound | **2** |
| C5-col / C5-bcd | 2 |
| C1-interface | 1 |
| **合计** | **633** |

pending：3 处 `cmp 0x7FF`。

校验：0 不匹配、0 重叠，改动 **717** 字节。

## 142. 剩余

| 项 | 数量 | 说明 |
|---|---|---|
| 未知掩码 | 348 | 需逐条数据流 |
| pending 比较 | 3 | 语义未证 |
| 实体释放路径 | — | 未审计（free-list 返回、分区判断） |
| 无效句柄 | — | `0xFFFFFFFF & 0x1FFF = 0x1FFF` 与末槽冲突 |

## 143. 下一轮

1. 实体释放/回收路径（对照构造分区，检查 0x800/0x1000 阈值）。
2. 348 处未知掩码的数据流。
3. 3 处 pending 比较。
4. 无效句柄兼容性。

---

# 序列号右移消费者（第 29 轮）—— 两端均遗漏，已补齐

## 144. 问题

句柄解码是**成对**的：

```
and ecx,0xFFF          ; index
add ecx,ecx
lea ecx,[edx+ecx*8+4]  ; &CEntInfo[idx]
shr eax,0xC            ; serial = handle >> 12   ← 此处此前未纳入
cmp [ecx+4],eax        ; 序列号比较
```

只改掩码而保留 `shr 12`，会导致：索引与地址都对，但序列号比较恒失败，有效句柄被拒绝。

## 145. 配对审计方法

以已确认的索引解码点（C9/A9-mask）为锚，查找 ±32 字节内的 `shr reg,0xC`：

| 模块 | 掩码点 | `shr 0xC` 总数 | 配对 |
|---|---|---|---|
| client.dll | 452 | 756 | **453** |
| server.dll | 22 | 3053 | **16** |

客户端接近 1:1（每个解码点各带一次序列号提取），与「同一解引用序列」的结构吻合。

## 146. 两端 manifest 更新

### client.dll

| 类别 | 数量 |
|---|---|
| C9-mask | 452 |
| **C10-shr** | **453** |
| C6-member | 129 |
| C4-vtload | 17 |
| C3-this | 18 |
| 其余 | 17 |
| **合计** | **1086** |

校验：0 不匹配、0 重叠，改动 1170 字节。

### server.dll

| 类别 | 数量 |
|---|---|
| A1-glref | 668 |
| A3-gldisp | 58 |
| A9-mask | 22 |
| A10-vec | 18 |
| **S10-shr** | **16** |
| A10-stref | 9 |
| 其余 | 17 |
| **合计** | **808**（原 792，+16） |

校验：0 不匹配、0 重叠，改动 2164 字节；PE 预检 **30/30** 仍通过。

## 147. 结论

此前「服务端 792 条补丁已完备」的判断不成立——序列号右移是一整类遗漏。现在两端都补上了 `S10/C10`。

## 148. 剩余

| 项 | 数量 |
|---|---|
| 未知掩码（client） | 348 |
| pending 比较 | 3 |
| `cmp 0x1000` 站点 | 3 |
| 实体释放/回收路径 | 未审计 |
| 无效句柄末槽 | 未验证 |

---

# 释放路径审计 + 服务端副本重建（第 30 轮）

## 149. 一处地址口径错误（已修正）

此前用 `cmp ...,0x800` 的**指令地址**去比对 manifest 的 **rva**，导致误报「未覆盖」。
manifest 记录的是**操作数**地址（指令起始 +2），所以 `0x100B79A5` 的补丁 rva 是 `0xB79A7`。

## 150. 服务端释放路径：已完成覆盖

`CGlobalEntityList::RemoveEntityAtSlot`（0x100B7970）：

| 位置 | 指令 | manifest |
|---|---|---|
| 0x100B79A5 | `shl ecx,0xC`（构造失效句柄） | **A9-shl @0xB79A7** |
| 0x100B7A06 | `cmp ebx,0x800`（分区判断） | **A8-thresh @0xB7A08** |
| 0x100B79BE | `and eax,0x7FFF`（序列号 +1 回绕） | 不需要改（序列号仍 15 位） |

分区逻辑：`index >= 0x800` 才进入非网络空闲链（`[edi+0x1000C]`）。改成 `0x1000` 后，`0x800–0xFFF` 不再被误归入非网络池。

## 151. `cmp ...,0x800` 全量清单（地址已修正）

| 模块 | 数量 |
|---|---|
| server.dll | 21 |
| client.dll | 10 |

其中已确认属于实体分区/句柄边界的仅少数（如 server 0x100B7A06、H9 的 0x104CF662），其余多为无关常量，需逐点判定，不能批量替换。

## 152. 服务端测试副本重建

| 项 | 值 |
|---|---|
| 补丁 | **808** |
| 大小 | 0x8B5400 |
| SHA-256 | `af09f77cd6930971494389051741c26717f9c6eacfe0af8a88a1e26979b7560a` |
| SizeOfImage | 0x9A8000 |
| 节数 | 6 |
| PE 预检 | **30/30** |

上一版 792 条副本已被取代。

## 153. 未完成

| 项 | 状态 |
|---|---|
| 客户端释放路径 | 未定位（`0x100BB7F0` 经查非回收函数） |
| `S10/C10` 寄存器级验证 | 仍为 ±32 字节配对候选 |
| 无效句柄 `0xFFFFFFFF` | 未验证 |
| 客户端 348 处掩码 | 未分类 |
| 3 处 pending 比较 | 未决 |

---

# 客户端释放函数搜索：三次尝试与结论（第 31 轮）

## 154. 已确认（服务端）

`RemoveEntityAtSlot` 的两个补丁**早已在 manifest 中**：

| 指令 | manifest 条目 |
|---|---|
| 0x100B79A5 `shl ecx,0xC` | A9-shl @ rva 0xB79A7 |
| 0x100B7A06 `cmp ebx,0x800` | A8-thresh @ rva 0xB7A08 |

上一条的「未覆盖」是地址口径错误（用指令地址比对操作数 rva）。服务端副本已按 808 条重建：

```
sha256 af09f77cd6930971494389051741c26717f9c6eacfe0af8a88a1e26979b7560a
SizeOfImage 0x9A8000  sections 6  PE 预检 30/30
```

## 155. 客户端释放函数：未定位

三次搜索均未命中目标函数：

| 方法 | 结果 |
|---|---|
| `inc reg; and reg,0x7FFF` 窗口扫描 | 0 命中（扫描逻辑缺陷，紧邻字节判断失效） |
| 序列号自增完整签名 `mov r,[slot+4]; inc r; and 0x7FFF; mov [slot+4],r` | **2 处，均在构造函数**（0x100EA6AA、0x100EA78B 的池初始化循环） |
| `cmp reg,0x800` 清单 | 客户端 10 处，含构造区 2 处，其余未定性 |

结论：客户端的释放路径**没有复用构造函数的序列号自增序列**，可能通过辅助函数或不同寄存器组合实现，尚未找到入口。

## 156. 无效句柄：编码空间分析（理论）

| 项 | 值 |
|---|---|
| 有效句柄最大值 | `(0x7FFF << 13) | 0x1FFF = 0x0FFFFFFF` |
| 无效句柄 | `0xFFFFFFFF` |
| `0xFFFFFFFF` 拆出的 index | `0x1FFF` |
| `0xFFFFFFFF` 拆出的 serial | `0x7FFFF`（**超出 15 位**） |

因此**只要执行完整序列号比较**，无效句柄不会匹配任何有效槽位——`0x1FFF` 与末槽同索引本身不构成别名。风险仅存在于「只取索引、不比序列号」的路径。

按 `81 f8/…, 0xFFFFFFFF` 与 `3D` 编码扫描，两端均未见 `cmp reg,0xFFFFFFFF`；说明无效句柄检查可能使用 `cmp ...,-1` 的短编码或其他形式，尚未系统枚举。

## 157. 状态

| 模块 | 补丁 | 副本 | 预检 |
|---|---|---|---|
| engine.dll | 4096 方案 | 已生成 | 43 项 |
| server.dll | **808** | **已重建** | **30/30** |
| client.dll | 1086 | 未生成 | 字节校验通过 |

运行时加载与生命周期测试：均未进行。

---

# 客户端 RemoveEntityAtSlot 定位（第 32 轮）

## 158. 函数地址：0x100EA660

结构与服务端 0x100B7970 逐指令对应：

| 客户端 | 服务端 | 操作 |
|---|---|---|
| 0x100EA66D `add eax,eax` → `[edi+eax*8+4]` | 0x100B797D | &CEntInfo[index] |
| 0x100EA67F `mov [ebp+8],0xFFFFFFFF` | 0x100B798F | 失效句柄 |
| 0x100EA68F `call edx`（vt[1]） | 0x100B799F | SetRefEHandle |
| 0x100EA695 `shl ecx,0xC` | 0x100B79A5 | 构造句柄 |
| 0x100EA6A8 `call edx` | 0x100B79B8 | OnRemoveEntity |
| 0x100EA6AD `inc` / `and 0x7FFF` | 0x100B79BD | 序列号回绕（不变） |
| 0x100EA6B9 `mov [esi],0` | 0x100B79C9 | 清实体指针 |
| 0x100EA6BF.. | 0x100B79CF.. | 活动链解除 |
| 0x100EA6F6 `cmp ebx,0x800` | 0x100B7A06 | 非网络池阈值 |

## 159. 补丁（新增 C11-rel 2 条）

| 地址 | 旧 → 新 |
|---|---|
| 0x100EA697 | `shl ecx,0xC` → `0xD` |
| 0x100EA6F8 | `cmp ebx,0x800` → `0x1000` |

## 160. manifest v5

| 类别 | 数量 |
|---|---|
| C9-mask | 452 |
| C10-shr | 453 |
| C6-member | 129 |
| C4-vtload | 17 |
| C3-this | 18 |
| **C11-rel** | **2** |
| 其余 | 17 |
| **合计** | **1088** |

0 不匹配、0 重叠，改动 1172 字节。

## 161. 无效句柄：风险确认（比理论分析更严重）

`RemoveEntityAtSlot(index)` **内部不做序列号校验**——它只按索引取槽位。

因此若 `RemoveEntity(handle)` 直接用 `handle & 0x1FFF`：

```
0xFFFFFFFF & 0x1FFF = 0x1FFF  →  释放非网络池最后一个真实槽位
```

这是**错误删除**，不是查询失败。必须在 `RemoveEntity` 入口确认：调用者是否保证句柄有效、是否有 `0xFFFFFFFF` 前置判断。

## 162. 状态

| 模块 | 补丁 | 副本 |
|---|---|---|
| engine.dll | 4096 | 已生成 |
| server.dll | 808 | 已重建（af09f77c） |
| client.dll | **1088** | 未生成 |

---

# RemoveEntity 入口与无效句柄约束（第 33 轮）

## 163. RemoveEntityAtSlot 的唯一调用者

| 模块 | 调用点 | 函数 |
|---|---|---|
| client | 0x100EA99C | `RemoveEntity(handle)` @ **0x100EA980** |
| server | 0x100B7CAC | `RemoveEntity(handle)` @ **0x100B7C90** |

两端函数体完全一致：

```asm
push ebp / mov ebp,esp
mov  eax,[ebp+8]      ; handle
and  eax,0xFFF        ; ← 只取索引，无任何有效性检查
push eax
call RemoveEntityAtSlot
pop ebp / ret 4
```

**没有任何 `0xFFFFFFFF` 判断、没有序列号比较、没有 IsValid()。** 无效句柄会直接按 `0xFFF`（新方案 `0x1FFF`）释放槽位。

## 164. 客户端遗漏的一处掩码（已补）

| | 地址 | 状态 |
|---|---|---|
| server | 0x100B7CA7 | 已在 A9-mask |
| client | **0x100EA997** | **此前遗漏**，已补入 C9-mask |

遗漏原因：该掩码后接 `push eax; call`，不满足 C9 的「`add reg,reg` + `lea [..*8]`」特征。

## 165. 这解释了 452 vs 453 的数量差

补入后：

| | 数量 |
|---|---|
| C9-mask | **453** |
| C10-shr | **453** |

两者现在 1:1 对应，此前的差一正是这条掩码缺失造成的。

## 166. 无效句柄风险的正确表述

原版：`0xFFFFFFFF & 0xFFF = 0xFFF`，而原版非网络池为 `[0x801,0xFFF]`——**最后一个槽位本来就在池内**。

扩容后：`0xFFFFFFFF & 0x1FFF = 0x1FFF`，新池为 `[0x1001,0x1FFF]`——**结构完全同构**。

因此：
- 这不是扩容引入的新风险；
- 原版是否存在保护，取决于 `RemoveEntity` 的调用者是否保证句柄有效；
- 二进制中 `RemoveEntity` 内部**没有**保护，与 SDK 的 `RemoveEntity(handle)` 直接 `GetEntryIndex()` 的实现一致。

## 167. manifest v6

| 类别 | 数量 |
|---|---|
| C9-mask | **453** |
| C10-shr | 453 |
| C6-member | 129 |
| C4-vtload | 17 |
| C3-this | 18 |
| C11-rel | 2 |
| 其余 | 17 |
| **合计** | **1089** |

0 不匹配、0 重叠，改动 1173 字节。

## 168. 下一步

1. `RemoveEntity` 的调用者清单，确认是否有人传入无效句柄。
2. 原版 `0xFFF` 槽位是否真的会被分配（链表分配顺序）。
3. `S10/C10` 寄存器级验证。

---

# RemoveEntity 调用者审计（第 34 轮）

## 169. 统计口径修正（采纳）

`C9-mask=453` 与 `C10-shr=453` **不构成一一配对证明**：

- `RemoveEntity` 的掩码（0x100EA997）只提取 index，**没有配对的 `shr`**；
- 因此必然另有右移点不与该掩码配对，或存在一掩码多右移。

正确表述：**453 个掩码与 453 个右移候选已识别，配对关系未验证。**

## 170. RemoveEntity 的调用者：零

| 模块 | 函数 | 直接调用者 | 指针引用 |
|---|---|---|---|
| client | 0x100EA980 | **0** | **0** |
| server | 0x100B7C90 | **0** | **0** |

而 `RemoveEntityAtSlot` 的唯一调用者正是这两个函数。因此：

- 这两个 `RemoveEntity` 在静态层面**无引用**（可能是未内联的残留副本、或仅被不可见路径调用）；
- 无效句柄经「`RemoveEntity` → `RemoveEntityAtSlot`」这条链**当前不可达**；
- 真正的实体删除必然走其他路径（内联副本、间接调用或引擎回调）。

## 171. 对无效句柄判断的修正

| 结论 | 状态 |
|---|---|
| `RemoveEntity(0xFFFFFFFF) → slot 0x1FFF` 行为存在 | **代码事实**（但函数未被引用） |
| 该路径实际可达 | **未证明**（无调用者） |
| 需要立即加有效性检查 | **不需要**——先找真正的删除入口 |

## 172. 下一步

1. 找客户端真正的实体删除入口：`OnRemoveEntity`（0x100BB9E0）的调用者，以及 `RemoveEntityAtSlot` 的间接调用（`ff d0`/`ff 52`）。
2. 末端槽位 `0x1FFF` 的分配顺序（非网络链表头部还是尾部）。
3. `S10/C10` 逐条配对验证。

---

# 内联删除路径排查（第 35 轮）

## 173. 序列号写回点的全量清单

以 `and reg,0x7FFF`（含 `25` 短编码与 `81 /4` 长编码）为准：

| 模块 | 总数 | 位于实体列表函数内 | 其他 |
|---|---|---|---|
| client | 23 | **3**（0x100EA5BB 构造、0x100EA6AE / 0x100EA78F 释放与池初始化） | 20 |
| server | 16 | **3**（0x100B78CB、0x100B79BE、0x100B7A9F） | 13 |

## 174. 其余站点全部与实体列表无关

对候选函数逐一检查是否引用实体列表特征偏移（`0x1003C` 缓存、`0x10014` 次级接口、`0x10004` 链表）：

| 函数 | 0x1003C | 0x10014 | 0x10004 |
|---|---|---|---|
| 0x100E0020 | 0 | 0 | 0 |
| 0x101738F0 | 0 | 0 | 0 |
| 0x103477C0 | 0 | 0 | 0 |
| 0x103782C0 | 0 | 0 | 0 |
| 0x10378B70 | 0 | 0 | 0 |
| 0x104A1290 | 0 | 0 | 0 |
| 0x1048D140 | 0 | 0 | 0 |

**结论：没有发现内联的 `RemoveEntityAtSlot` 副本。** 客户端 1089 条补丁未覆盖内联删除代码——因为该类代码不存在。

## 175. 仍未解决的问题

「`RemoveEntity` 零调用者」意味着：

- 要么它是未内联的死代码，真正的删除入口在别处（如引擎通过接口调用）；
- 要么调用关系是间接的（`ff d0` / `ff 52`），当前 E8 扫描未覆盖。

静态上无法再进一步区分。

## 176. 运行时验证方案（本环境无法执行）

| 模块 | 函数 | RVA |
|---|---|---|
| client | RemoveEntity | 0xEA980 |
| client | RemoveEntityAtSlot | 0xEA660 |
| client | OnRemoveEntity | 0xBB9E0 |
| server | RemoveEntity | 0xB7C90 |
| server | RemoveEntityAtSlot | 0xB7970 |

步骤：
1. 加载原版 client.dll，基址 + 上表 RVA 设断点；
2. 触发一次客户端实体销毁；
3. 记录命中顺序与调用栈；
4. 若均未命中，对已知槽位 `CEntInfo[index].m_pEntity`（`base+slot*16+4`）设写断点，追踪清零指令。

## 177. 当前三模块状态

| 模块 | 补丁 | 副本 | 预检 |
|---|---|---|---|
| engine.dll | 4096 | 已生成 | 43 项 |
| server.dll | 808 | 已重建 | 30/30 |
| client.dll | 1089 | 未生成 | 字节通过 |

运行时：全部未验证。
