# N1 网络序列化层静态审计报告

- 目标：`F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin\engine.dll`
- SHA-256：`8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86`（4,817,712 字节）
- 构建：L4D2 `23990068`，Source 1，PE32 i386，ImageBase `0x10000000`
- 阶段：N1（网络序列化与快照系统）静态审计；本报告只给坐标与字段语义，不给补丁
- 分析面：IG5 `reverse`（内置 Ghidra 12.1.4，14,038 函数）+ capstone 5.0.7 / pefile 逐字节复核
- 状态：全部结论为静态证据；无运行时验证

---

## 0 摘要

1. `SVC_PacketEntities` 的两条网络出入口已定位：`ReadFromBuffer = 0x101D7460`、`WriteToBuffer = 0x101D7340`。二者由 RTTI → CompleteObjectLocator → vftable 独立确认，不依赖字符串猜测。
2. 两个独立的 11 位字段成立：`m_nMaxEntries`（对象内 `+0x54`，写 `push 0xb` @`0x101D7366`，读掩码 `0x7FF` @`0x101D747E`）与 `+0x58` 的第二个 11 位字段（写 `push 0xb` @`0x101D73D5`，读 `0x101D7798`）。
3. 字段语义首次给出可判定的结论：`m_nMaxEntries` 不是「条目计数」，而是「最大实体索引（含）」。理由是本次静态证据里的强约束——写入侧带着 `bCheckRange = 1`，而 11 位只能到 2047；若它是计数，原版 2048 实体在同一条路径上就会越界。这属于逻辑排除，仍需一次运行时探针确认（见 §9 P1）。
4. 由此得出与「11 改 12」不同的结论：在「最大索引」语义下 4096 槽位需要的最大值是 4095，**12 位刚好充分**；而在「计数」语义下 4096 需要 13 位，12 位会在 4096 处溢出。两种语义对补丁位宽的要求不同，必须先定语义再定位宽。
5. 边界矩阵（`2046/2047/2048/2049/4094/4095/4096`）已落表：`data/network_boundary.csv`；字段图：`data/network_fields.csv`。

---

## 1 方法与坐标基准

- VA ↔ RVA 关系：`RVA = VA - 0x10000000`（`.text` 起始 `0x10001000`）。
- 函数边界：先前由 `E8` 调用目标 + MSVC 序言（`55 8B EC` / `55 89 E5`）恢复 13,745 个起点；本轮对候选点一律再以 IG5 的 Ghidra 函数边界校正，凡「起点落在指令中间」的候选直接作废（见 §8）。
- 符号归属：`RTTI TypeDescriptor → CompleteObjectLocator → vftable-ptr → vftable` 链。本条链给出类身份与虚槽位置，是本轮唯一「不靠字符串」的归属证据。
- 常量位宽：`bf_write::WriteUBitLong` = `0x10061340`，thiscall `(value, numBits, bCheckRange)`；`bf_read` 的位宽以内联形式出现，用掩码常量反推位宽（`0x7FF` ⇒ 11 位，`0x3F` ⇒ 6 位，`0xFFFFFFFF` ⇒ 32 位）。

### 1.1 SVC_PacketEntities 的 RTTI 链（可复现）

| 环节 | 地址 | 值/说明 |
|---|---|---|
| TypeDescriptor 名 | `0x104253AC` | `.?AVSVC_PacketEntities@@` |
| TypeDescriptor | `0x104253A4` | 头 `0x10406B3C`, `0x00000000` |
| CompleteObjectLocator | `0x10412620` | `sig=0, off=0, cd=0, pTD=0x104253A4, pCHD=0x10412634` |
| vftable 指针槽 | `0x103584D8` | 指向 `0x10412620` |
| vftable | `0x103584DC` | 10 槽 |

vftable 槽位（`0x103584DC`）：

| 槽 | VA | 角色（据形态判定） |
|---|---|---|
| 0 | `0x100541A0` | 标量删除析构 |
| 1 | `0x100025E0` | 小 stub（置位/清零） |
| 2 | `0x100025C0` | 小 stub（读取标志） |
| 3 | `0x10053FE0` | `GetName` 一类（返回 `svc_PacketEntities` 字串指针） |
| 4 | `0x10002620` | 小 stub（`GetType`/`GetGroup` 量级） |
| 5 | **`0x101D7460`** | **`ReadFromBuffer`**（1,447 字节，读 `bf_read`） |
| 6 | **`0x101D7340`** | **`WriteToBuffer`**（291 条指令，写 `bf_write`） |
| 7 | `0x100025D0` | 小 stub |
| 8 | `0x10053FB0` | 短函数（`ToString` 量级） |
| 9 | `0x10053FF0` | 短函数 |

> 槽 3 与 `svc_PacketEntities` 字串（`0x10358518`）的引用点 `0x10053FC1` 同一区域，交叉印证类身份。

---

## 2 已确认符号坐标

| 符号 | VA | RVA | 证据 |
|---|---|---|---|
| `SVC_PacketEntities::ReadFromBuffer` | `0x101D7460` | `0x001D7460` | vftable `0x103584DC[5]` |
| `SVC_PacketEntities::WriteToBuffer` | `0x101D7340` | `0x001D7340` | vftable `0x103584DC[6]` |
| `bf_write::WriteUBitLong` | `0x10061340` | `0x00061340` | 177 处直接调用，形参 `(value,bits,bCheckRange)` |
| `CL_CopyNewEntity` | `0x10076A40` | `0x0076A40` | 断言串 `0x103635C8` 引用点 `0x10076EB5` |
| `CL_ParsePacketEntities`（状态机） | `0x10091F50` | `0x00091F50` | 缓冲溢出串 `0x1036A344` 引用点 `0x1009247A` |
| `CL_ParsePacketEntities` 头部读取（内联 `bf_read`） | `0x10091910` | `0x00091910` | 掩码表 `0x103ECE50` + `0x3F` |
| `SV_WriteEnterPVS` | `0x10119490` | `0x00119490` | 断言串 `0x1037864C` 引用点 `0x10119521`；写网络序列号 10 位 |
| `CL_ParseDelta` | 在 `0x10091910`/`0x10091F50` 邻域 | — | 串 `0x10363658` 引用点 `0x10076CC3`、`0x10076F80` |
| `CL_ReadPreserveEnt` | — | — | 串 `0x1036A3A8` 引用点 `0x10092016`、`0x10185494` |

`bf_read` 掩码常量（内联位读取反推位宽的依据）：

| 地址 | 值 | 用途 |
|---|---|---|
| `0x103ECE7C` | `0x000007FF` | 11 位掩码 |
| `0x103ECE68` | `0x0000003F` | 6 位掩码 |
| `0x103ECED0` | `0xFFFFFFFF` | 32 位掩码 |
| `0x103ECE50` | 掩码表基址（`[bits]`） | `ReadUBitLong` 变宽路径 |

---

## 3 `SVC_PacketEntities` 字段图（对象布局）

对象基址记作 `obj`；全部偏移来自 `0x101D7460` / `0x101D7340` 的指令级证据。

| 偏移 | 字段 | 位宽 | 写入证据 | 读取证据 | 合法值 |
|---|---|---|---|---|---|
| `+0x54` | `m_nMaxEntries` | **11** | `mov eax,[edi+0x54]` @`0x101D7362`；`push 1`(bCheckRange) `push 0xb` @`0x101D7366`；`call 0x10061340` @`0x101D736B` | `and esi,[0x103ECE7C]`(=0x7FF) @`0x101D747E`；`shr edx,0xb` @`0x101D748E`；`mov [edi+0x54],ecx` @`0x101D754D` | `0..0x7FF`（0..2047） |
| `+0x58` | 第二个 11 位字段（语义候选 `m_nDeltaFrom` / `m_nUpdatedEntries`） | **11** | `mov edx,[edi+0x58]` @`0x101D73D1`；`push 1` `push 0xb` @`0x101D73D5` | 掩码 `0x7FF` + `shr edx,0xb` @`0x101D77A8` | `0..0x7FF`（0..2047） |
| `+0x5C` | `m_bIsDelta` | 1 | — | 读 1 位后 `mov [edi+0x5C],cl` @`0x101D75A2` | `0..1` |
| `+0x5D` | 第二个 1 位标志（`m_bUpdateBaseline` 量级） | 1 | — | `mov [edi+0x5D]` | `0..1` |
| `+0x64` | 基线/无效哨兵 | 32 | — | `mov dword [edi+0x64],0xFFFFFFFF` @`0x101D76A8` | `0xFFFFFFFF` 为无效值 |
| `+0x6C` | `m_DataIn`（内嵌 `bf_read`，36 字节 = 9 dword） | 288 | — | 9 次 dword 拷贝 → `obj+0x6C..` | — |

字段顺序（读侧）：`m_nMaxEntries(11)` → `m_bIsDelta(1)` → 若 delta 则 `+0x58(11)` → `m_bUpdateBaseline(1)` → 内嵌 `bf_read` 快照。写侧顺序与之对应（`0x101D7362` → `0x101D73D1`）。这与 SDK 中 `SVC_PacketEntities` 的头部形状一致：两个 `MAX_EDICT_BITS` 宽字段 + 两个 1 位标志。**这两个 11 位字段是独立的**，不是同一常量的两种写法。

---

## 4 字段语义判定：最大索引 vs 条目计数

这是本轮最关键、也最容易被「找到 11 改成 12」掩盖的一步。

**证据链**

1. 写入侧 `bCheckRange = 1`（`push ebx`，`ebx = 1`，紧邻 `push 0xb`）。
2. 11 位可表达的最大值是 2047。
3. 原版 `MAX_EDICTS = 2048`，且该构建在 2048 实体配置下可正常运行。
4. 若字段语义是「条目计数」，那么满编时它的值必然等于（或达到）2048，第 1、2 条会在原版就触发越界。原版不越界 ⇒ 该值在原版从未达到 2048。

**结论（高度可信，经逻辑排除）**：`m_nMaxEntries` 承载的是「最大实体索引（含）」，取值为最后一个被描述的实体槽位下标，原版满编时为 `0x7FF = 2047`。它不是「条目数」。

辅助证据：`CL_CopyNewEntity`（`0x10076A40`）对实体索引的合法域谓词为 `(idx < 0) || (0x7FF < idx)` 即 `idx ∈ [0, 2047]`，与「索引」语义同域；若是计数，其同域上界应为 `1..2048`。

**对补丁位宽的直接影响**

| 语义假设 | 2048 槽位 | 4096 槽位的编码 | 11→12 位是否够 |
|---|---|---|---|
| A：最大索引（本报告结论） | `0x7FF`，11 位 | `0xFFF = 4095`，**12 位** | 够，且刚好 |
| B：条目计数 | 2048，11 位**放不下**（与运行时事实矛盾） | 4096，需 **13 位** | 不够，差 1 位 |

因此「把 11 改成 12」在 A 下是自洽的；在 B 下会在 `n = 4096` 处溢出。这也说明为什么不能只凭「存在一个 11」就下手改：位宽数字相同，语义不同，正确位宽就不同。

---

## 5 边界矩阵

完整表：`data/network_boundary.csv`。摘录（`A` = 最大索引语义，`B` = 计数语义）：

| n | A：11 位 | A：12 位 | B：11 位 | B：12 位 | B：13 位 | 结论 |
|---|---|---|---|---|---|---|
| 2046 | 可 | 可 | 可 | 可 | 可 | 两侧均安全 |
| 2047 | 可（A 上界） | 可 | 可 | 可 | 可 | 11 位极限 |
| 2048 | **越界** | 可 | **越界** | 可 | 可 | `n=2048` 是 A 的越界点、B 的临界点 |
| 2049 | 越界 | 可 | 越界 | 可 | 可 | 12 位覆盖 |
| 4094 | 越界 | 可 | 越界 | 可 | 可 | 12 位覆盖 |
| 4095 | 越界 | 可（A 上界） | 越界 | 可 | 可 | 12 位极限 |
| 4096 | 越界 | **越界** | 越界 | **越界** | 可 | 分水岭：A 不需要、B 必须 13 位 |

判读规则：在 `bCheckRange = 1` 下，越界写入不会静默成立，而是走到「溢出置位 + 低位截断」的路径，接收侧随后按截断值解释，表现为实体索引错位或快照不一致。该路径的具体行为列入 §9 P1 探针，不在静态结论中冒充已证实。

---

## 6 实体增量编码与网络 EHANDLE

| 项 | 结论 | 证据 |
|---|---|---|
| 内部句柄布局 | `handle = serial << 12 | index`，`index = handle & 0xFFF` | `shr ecx,0xc` @`0x10076AE2` |
| 内部索引位宽 | 12 位（`NUM_ENT_ENTRY_BITS = MAX_EDICT_BITS + 1 = 12`） | 同上；与槽位分区 `[0x801,0xFFF]` 非网络实体池吻合 |
| 网络可寻址索引 | 11 位，`[0, 0x7FF]` | `CL_CopyNewEntity` 谓词 + 断言串 `0x103635C8` |
| 网络序列号 | **10 位**，显式 `WriteUBitLong(serial, 10, 1)` | `push 0xa` @`0x10119576`（`SV_WriteEnterPVS`） |
| 网络 EHANDLE 总位宽 | `11 + 10 = 21` 位；目标态 `12 + 10 = 22` 位 | 上两行合成 |
| 无效值 | 原版 `0x1FFFFF`（21 位全 1）；目标态 `0x3FFFFF` | 由总位宽推得，**待运行时确认实际哨兵写入点** |
| 槽位步长 | `CEntInfo` 16 字节 | `shl ebx,4` @`0x10076AAD` |
| 记录位图写入 | `word = base + (idx>>5)*4`，`bit = 1 << (idx & 0x1F)` | `and ecx,0x1f` @`0x10076DEA`（客户端，基址 `+0xC`）；`and ecx,0x1f` @`0x10119614`（服务端满更新位图，基址 `+0x10C`） |

关于 `CBitVec<MAX_EDICTS>`：位图以「`>>5` 取 dword 下标、`& 0x1F` 取位」的形态内联展开，容量由 `MAX_EDICTS/32*4` 决定，即 2048 位 = 256 字节 → 4096 位 = 512 字节。这是**结构体内固定内联数组**，不是运行时分配：位图基址是对象内常量偏移（`+0xC` / `+0x10C`），没有任何「指针 + 长度」形态的二次解引用。因此扩容必须同步移动该对象内的后续字段与外部对 `+0x10C` 的硬编码偏移使用者。

---

## 7 快照与发送路径（已定位部分）

| 项 | 结论 | 证据 |
|---|---|---|
| `CL_ParsePacketEntities` | 260 字节状态机，按 update flags 分派（0/2/3/4） | `0x10091F50` 反编译 |
| 头部位读取 | 6 位首字段 + `0x30` 掩码分流，内联 `bf_read` | `0x10091910`，掩码 `0x3F` @`0x103ECE68` |
| 缓冲溢出检测 | 每轮解析后检查 `bf_read` 溢出标志并报 `CL_ParsePacketEntities: buffer read overflow` | 串 `0x1036A344` 引用点 `0x1009247A` |
| `SV_WriteEnterPVS` 单实体写入 | 位标志 2 位 + `classID`（位宽取自 `pClass+0xFC`）+ 序列号 10 位 + 基线 delta | `0x10119490` |
| `SV_AllocateEdicts` / `ED_Alloc` | 已定位串引用，尚未反编译 | `0x10123DD5` / `0x101E02E5` 等 |

---

## 8 排除的假阳性（避免误补丁）

| 候选 | 排除理由 |
|---|---|
| `0x1029F880` | 逐位写入 11/11/10/10/8/9/9/8 位，但每字段走**不同对象**的虚槽 `0xF8`，且带「2 位退化分支」；是位缓冲基准/自检代码，不是协议报文。其 11 位连续只为压测，不能作为 `MAX_EDICT_BITS` 证据 |
| `0x1008D0B1` | 起点落在指令中间（`adc [ebx-0x57281735],cl`），真实函数为浮点/几何代码 |
| `0x10073A80`、`0x10123880` | 同类「起点错位」，序言不成立 |
| `0x101D40D5`、`0x101D3DDE` 等 11 位写点 | 是实体 delta 头的索引写入（`SV_WriteDeltaHeader` 族），不是 `SVC_PacketEntities` 头部字段；位宽相同但对象不同，不可与 §3 混用 |
| `0x10333E13` | 两处 11 位参数指向**不同**被调函数，非位缓冲 |

---

## 9 尚未定位 / 待运行时验证

| 编号 | 问题 | 精确探针 |
|---|---|---|
| P1 | `m_nMaxEntries` 在满编时的实际取值（0x7FF 还是 0x800） | 在 `0x101D7362`（读 `[edi+0x54]` 处）下断，采集一次 `sv_maxentities=2048` 的完整快照；期望 `0x7FF`。该点同时验证 §4 的 A/B 判定 |
| P2 | `+0x58` 字段的确切语义（`m_nDeltaFrom` vs `m_nUpdatedEntries`） | 在同一断点处按报文顺序记录 `0x101D73D1` 与第二处 11 位写的先后，与接收侧 `0x101D7798` 对齐 |
| P3 | 21 位网络 EHANDLE 的无效哨兵写入点 | 搜索 `0x1FFFFF` 立即数出现在 `.text` 的位置，并核对其是否为 `CBaseHandle::Invalidate` 的内联 |
| P4 | `SVC_SetView` / `SVC_EntityMessage` 的字段位宽 | 同 §1.1 的 RTTI→vftable 链，对两个类各取一次 `ReadFromBuffer`，读取内联 `bf_read` 的掩码常量 |
| P5 | `CFrameSnapshotManager` 的 2048 位固定数组与索引缓存 | 反编译串 `0x10379038` 引用点的 `BuildSnapshotList`，确认容量常量出现处 |
| P6 | `bCheckRange=1` 越界后的确切行为（置溢出位 + 截断 / 断言） | 反编译 `0x10061340` 的越界分支，记录写入的标志位与是否触发断言 |

---

## 10 客户端实体管理层：删除路径的现有结论

已确认：客户端和服务端独立释放函数的内部容量补丁均已覆盖。

高度可信：目前未发现具有相同序列号更新特征的内联释放副本。

待运行时验证：真正执行的删除入口、调用栈，以及实体槽位释放行为。

补充说明：`0x1003C` / `0x10014` / `0x10004` 三处常量比较构成的是**排除性证据**——它们排除了「同族容量比较未被覆盖」的情形，不等于证明了「不存在内联删除副本」。因此上述第二行维持「高度可信」，不上升为「已确认」。本阶段不再对客户端删除函数做同类同质扫描。

---

## 11 产物与复现

| 文件 | 内容 |
|---|---|
| `data/network_fields.csv` | 字段图（VA / RVA / 偏移 / 位宽 / 合法值 / 证据点 / 排除项） |
| `data/network_boundary.csv` | 边界矩阵 `0/1024/2046/2047/2048/2049/4094/4095/4096/8191/8192` |
| `data/width_sites.txt` | 位宽实参抽样（162 点） |
| `data/netproto_primitives.csv`、`data/netproto_width_sites.csv` | 位缓冲原语与位宽站点初筛（含需人工剔除的噪声） |
| `out/client.4096.dll` | **实验性静态副本**，1,089 处补丁，SHA-256 `2f0e723a2991edee628e20638c506ce9508cb96fc8dd226d37603cc0035e0752`；未做运行时验证，不声称位移/掩码正确 |

复现命令（PowerShell）：

```powershell
$env:L4D2_ENGINE_BIN='F:\SteamLibrary\steamapps\common\Left 4 Dead 2\bin'
$env:L4D2_GAMEDLL_BIN='F:\SteamLibrary\steamapps\common\Left 4 Dead 2\left4dead2\bin'
cd 'D:\workshop\Research\l4d2-entity-4096\tools'
python dump_fn.py 0x101d747e      # 读侧 11 位掩码点
python dump_fn.py 0x101d7366      # 写侧 push 0xb
```

> 版本绑定：本报告全部坐标仅对 `engine.dll` SHA-256 `8a6d4680…` 有效；任何版本更新都会使 VA 与位宽站点失效。
