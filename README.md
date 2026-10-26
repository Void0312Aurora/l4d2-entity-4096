# L4D2 实体上限扩容（2048 → 4096）

对《Left 4 Dead 2》build `23990068`（Source Engine 1，PE32 i386）实体管理体系的离线静态分析，
目标是在**不更换引擎、不修改 32 位构建**的前提下，把网络实体上限从 2048 提高到 4096。

扩容跨三层，缺一不可：

| 层 | 二进制 | 负责什么 | 状态 |
|---|---|---|---|
| 1 · 存储 | `engine.dll` | edict 数组容量、`sv.max_edicts` | 11 条补丁，副本已生成 |
| 2 · 实体管理 | `server.dll` / `client.dll` | 实体列表槽位、句柄位宽、分区 | 808 / 1091 条补丁 |
| 3 · 网络协议 | `engine.dll` | edict 索引线格式、快照、EHANDLE | **13/13 低索引通过；2048、2049、4095 已完成客户端创建、更新、删除** |

仓库只包含**分析产物**（补丁清单、生成器、报告），不包含任何 Valve 的二进制文件。

## 状态

| 模块 | 补丁 | 隔离副本 | 静态预检 |
|---|---|---|---|
| `engine.dll` | **11** | 已生成 | **43/43** |
| `server.dll` | **808** | 已生成 | PE 预检 **30/30** |
| `client.dll` | **1091** | 已生成（实验性） | 字节匹配通过 |

`client.dll` 的隔离副本 `out/client.4096.dll` 已构建（1,091 处补丁，SHA-256
`3e5c3f2ee98c2bfa3f3672c654f7ae8b3ae401cc437a08ae1abbe57a6d363943`）。它在隔离
Proton 测试中与扩容服务端达到 `active`，并在客户端槽位中实际创建了 index 2048、2049
的 `C_DynamicProp`；后续更新改变坐标，删除后槽位归零且序列号递增。相同生命周期也已在
最高合法索引 4095 通过。较早的高索引压力测试仍出现服务端 sky-camera 空指针，以及填满
低索引后的重连分配失败；密集压力与断线重连还未通过。

网络协议的 13/13 候选曾通过低索引双端测试；后续高索引运行暴露并修复了服务端
`TakeTickSnapshot`、`g_EdictFreeTime`、接收端位图和 baseline 数组等边界问题。当前
2048、2049、4095 均有客户端槽位、更新、删除的直接证据；密集压力、断线重连和早期
sky-camera 故障仍未解决。详见 [reports/n27d48/findings.md](reports/n27d48/findings.md)、[reports/n27d49/findings.md](reports/n27d49/findings.md)、
[reports/network-n1.md](reports/network-n1.md) 与 [reports/network-n2.md](reports/network-n2.md)。

N27-D56 后续分析发现，高索引网络实体会覆盖 `CBaseEntityList` 原本用于非网络实体的
`2049..4095` 槽位；旧 core 中的 sky-camera 句柄与槽位 serial 也吻合这一覆盖路径。D61
增加了一个**实验性 Linux 服务端候选构建器**，把网络槽和非网络槽分区，并扩宽对应句柄
访问。静态字节校验、隔离服务端地图启动以及服务端将实体分配到 index 2048 均已通过；
一个 index 2050 实体也完成了服务端侧坐标更新和删除请求。客户端仍停在网络初始化前，
这些服务端探针没有验证实体同步、实际槽位释放或 serial，因此 D61 不证明断线安全、根因
修复或重连成功。详见
[reports/n27d56/findings.md](reports/n27d56/findings.md) 与
[reports/n27d61/findings.md](reports/n27d61/findings.md)。

## 目录

```
engine/       第 1 层：engine.dll 存储扩容
  manifest.json   11 条补丁 + 新段定义
  verify_pe.py    43 项校验 + 副本构建
  report.md       分析记录
  run.log         最近一次运行输出
manifests/    第 2 层：补丁清单（核心产物）
  server.json   808 条
  client.json   1091 条（另含 3 个 pending 候选、802 处未分类掩码）
tools/        可复现的生成器与校验器
  config.py       二进制路径（L4D2_ENGINE_BIN / L4D2_GAMEDLL_BIN 分离）
  gen_server.py   生成 server 清单
  gen_client.py   生成 client 清单
  build_server.py 应用补丁 + PE 手术，产出隔离副本
  build_client.py 应用 1091 处补丁 + `.clentls` 段，产出隔离副本
  precheck_server.py 只读 PE 预检（30 项）
  check_artifacts.py 离线产物门禁（三个二进制的 SHA-256/尺寸校验，只读）
  scan_netproto.py 网络位缓冲原语与位宽站点初筛
  xrefs_by_imm.py / dump_fn.py 按立即数查引用 / 按地址反汇编整函数
  patch_engine_receive.py / patch_engine_baselines.py 客户端接收边界与 baseline 扩容
  linux/build_highindex.py 可重复构建 Linux 高索引服务端候选
data/         原始扫描结果（CSV）
  network_fields.csv    N1/N2 字段图（VA / 偏移 / 位宽 / 语义状态）
  network_boundary.csv  N1/N2 边界矩阵（0/1024/2046…4096/8191/8192）
  linux/                Linux 服务端实体表句柄扩宽候选点与成员偏移
reports/      分析报告（含 D56/D61 实体表与断线调查）、N1 网络报告、N2 更正与预检输出
out/          生成的 DLL（不纳入版本控制）
archive/      已废弃的脚本（不纳入版本控制）
```

## 使用

```bash
export L4D2_BIN="/path/to/left4dead2/bin"   # 必填

python3 engine/verify_pe.py      # → out/engine.4096.dll + engine/manifest.json
python3 tools/gen_server.py      # → manifests/server.json
python3 tools/gen_client.py      # → manifests/client.json
python3 tools/precheck_server.py # → reports/precheck/
python3 tools/build_server.py    # → out/server.4096.dll
```

所有脚本以游戏目录为**只读输入**，只写入本仓库的 `out/` 与 `reports/`。

## 核心结论

**引擎存储（第 1 层）**：`sv.max_edicts` 2048 → 4096；`pEdicts` 由 `cap<<4` 派生出 64 KB，
`reuseTimes` 迁入新 BSS 段 `.edict2`（VA `0x73F000`，16 KB），9 处数组引用重定位同步改基址。

**对象迁移（第 2 层）**

| 对象 | 原尺寸 | 新尺寸 | 方式 |
|---|---|---|---|
| `CGlobalEntityList` | 4096 槽 | 8192 槽 | 纯 BSS |
| `CSimThinkManager` | 0x2018 | 0x4018 | 需带初值节 |
| `CClientEntityList` | 0x180A8 | 0x300A8 | 纯 BSS + 多重继承调整 |

**内部句柄**：`serial << 13 | index`，索引 `& 0x1FFF`，序列号 `>> 13`（原 12 位）。

**槽位分区**：网络 `[0, 0xFFF]` · 空洞 `0x1000` · 非网络 `[0x1001, 0x1FFF]`。

**补丁类别**（client）：`C1-global` 4、`C1-interface` 1、`C2-vptr` 3、`C3-this` 18、`C4-vtload` 17、
`C5-col/bcd` 2、`C6-member` 131、`C7-bound` 2、`C7-ctor` 3、`C8-shl` 2、
`C9-mask` 453、`C10-shr` 453、`C11-rel` 2。

**网络层 N1（`engine.dll`）**

`SVC_PacketEntities` 的两条出入口通过 RTTI → CompleteObjectLocator → vftable
独立定位，不经字符串猜测：

| 符号 | VA | 依据 |
|---|---|---|
| `ReadFromBuffer` | `0x101D7460` | vftable `0x103584DC` 槽 5 |
| `WriteToBuffer` | `0x101D7340` | 同表槽 6 |

对象内两个**独立**的 11 位字段：`+0x54`（写 `push 0xb` @`0x101D7366`，读掩码 `0x7FF`
@`0x101D747E`）与 `+0x58`（写 `0x101D73D5`，读 `@0x101D7798` / `@0x101D77A8`）。

**字段语义（N2 更正）**：N1 曾据「原版 2048 实体不越界」推出「`+0x54` 必是最大索引、
12 位刚好够」，该推理已撤回——原版不越界只约束实际取值域，不能反推字段数学语义。
N2 从服务端组包函数 `FUN_10119F50` 恢复了线格式，整条报文**恰有两个 11 位字段**
（序 2 与序 8），二者因此定名：

| 字段 | 生产来源 | 位宽 |
|---|---|---|
| `m_nMaxEntries`（`+0x54`） | `[[to_frame+0x118]+0x0C]`，即帧快照对象的容量/条目数 @`0x1011A096` | 11 |
| `m_nUpdatedEntries`（`+0x58`） | 本次实际发射的实体条目计数器 @`LAB_1011A248` | 11 |
| `m_nDeltaFrom` | `[from_frame+0x08]`，经 `FUN_10290330` = 32 位写入 | **32** |
| `payloadBitLength`（原 `m_nHeaderCount`） | 实体体比特长度 `edi->m_iCurBit - [ebp-0x180]`（同一 `bf_write`） | 20 |

**32 位回填区（N2.3 新证据）**：发送端在实体体之前先冻结主缓冲区视图
（`0x1011A11F`–`0x1011A13B`，把 `bf_write` 头拷到 `ebp-0x17c`），再 `push 0x20` 占位；
实体体写完后，`UpdatedEntries`(11)、`payloadBitLength`(20)、标志位(1) **全部经这份冻结视图
回填**，`11+20+1 = 32` 与占位宽度精确相等。所以线格式是
`type/maxEntries/isDelta/[deltaFrom]/flag/[Updated 11][Length 20][flag 1]/body`。
把 `Updated` 改 13 位后回填区需 34 位：先占位、后回填的机制不变，但**不能把 `0x1011A144`
的 `push 0x20` 改成 `push 0x22`**——`WriteUBitLong` 的 `numBits` 只能是 `0..32`，掩码按
`(curbit&31)*33 + numBits` 寻址，34 会取到下一行的 1 位掩码并静默写错。合法做法是让保留区
"推进 34 位"而不是"一次写 34 位"：保留区那 32 个零位本来就会被回填全量覆盖
（13+20+1 = 34），所以最小改动是在 `0x1011A156` 把死存储 `mov [ebp-0x168],eax`（6 B）
换成 `add dword ptr [edi+0xC],2`（4 B + 2×NOP），详见 `reports/network-n2.md` §13。
回填标志的位号取自冻结游标 `[ebp-0x170]`，会随之自动落到 bit 33，无需改硬编码。

这条约束已写成可执行检查：`python3 tools/net_patch_plan.py --check` 会核验 13 个改动点的
expected 字节、位置不变量（`F'=F+2`、`B'=B+4`、冻结游标终点 = `B'`），并在任何位宽 > 32
时直接抛错。

`data/network_fields.csv` 的字段图是历史产物，**列数不统一**（表头 12 列、众数 11 列，
部分行的 `encoding_rule` 里 `WriteUBitLong(v, 11, 1)` 的逗号未加引号）。它只作文档使用，
没有任何脚本按列位读取；跑 `python3 tools/check_fields_csv.py` 可以看到每一行的实际列数，
`--strict` 用于把「行宽不齐」变成失败门禁。**不要**用脚本批量重排该文件——引用与否是
证据的一部分，按启发式重新切分会静默改变字段归属。

**`bCheckRange` 已失效**：`FUN_10061340` 实际签名是 `(this, value, numBits)`，第三个实参被忽略，
范围检查只针对缓冲区剩余位数（`m_nDataBits`），超出 `numBits` 的值按掩码表 `DAT_106df750`
**静默截断**——2048 写 11 位会静默变 0，不断言、不崩溃。因此「原版能跑」不能作为
`m_nMaxEntries < 2048` 的证明；`13/13` 补丁也没有内建自检，验收必须逐 bit 解析报文头。

`m_nDeltaFrom` 是 32 位、`payloadBitLength` 是 20 位，二者位宽不变，但起点随回填区一起移动。
快照工厂 `FUN_1011D320` 把 `maxEntities` 直接写入 `obj+0x0C`（无 `-1`），而其两个调用点
都以 `push 0x800` 传 2048；若发送路径取到的就是 2048，11 位写入会静默截断成 0。但
`bCheckRange` 失效使这条论据**不能反证「原版必坏」**——它只说明原版在 4096 槽位下无法正确
编码 2048，不能排除消费者对 0 另有处理。因此语义仍分成「计数语义 ⇒ 4096 需 13 位」与
「`n-1` 调整编码 ⇒ 4095 需 12 位」两支，工作假设取 `13/13`（全量更新时
`m_nUpdatedEntries` 同样可达 4096），裁定探针与四格式代价表见
[reports/network-n2.md](reports/network-n2.md) §7.2–§8。

**位宽不是充分条件**：即使改成 13 位，仍有三处 2048 硬边界——`FUN_1004E310`
的 `cmp idx,0x800` 与 `iVar2 < 0x40` 扫描、`CClientFrame+0x10C` 的 256 字节**内联**位图、
`SV_WriteEnterPVS` 的可空堆位向量。且 `0x1011A080` 把帧内联位图地址写进另一对象的
`+0x10C` 指针字段——同一偏移在不同类型上语义不同，扩容必须按类型逐个处理。

网络 EHANDLE：索引 11 位 + 序列号 **10 位**（`WriteUBitLong(serial,10,1)`
@`0x10119576`）= 21 位，目标态 `12+10=22` 位。

位图布局（N2 更正）：`0x10C` 与 `0x0C` 相差 `0x100` 不是「两个相邻内联向量」，而是
`struct+0x0C` 处的**内联** `CBitVec<2048>`（256 字节，客户端 `CL_CopyNewEntity` 直接 `p = *(this+0xC)`，
无空指针检查）把后续字段整体推后 `0x100`。`struct+0x10C` 是**可空堆指针**指向裸向量
（服务端 `SV_WriteEnterPVS` 有 `if (q != 0)`）。故偏移映射为 `F(o)=o+0x100 (o≥0x10C)`，
sizeof `+0x100`；向量本体 256→512 字节的改动落在**分配点常量**上，与结构体字段偏移是两件事。

## 已知限制

- **版本绑定**：所有地址对应 build `23990068`，游戏更新后全部失效。
- **超出 2048 后不再兼容原版客户端**：网络 edict 索引是 11 位，扩容端只能与扩容端联机。
- **签名失效**：补丁后 Authenticode 无效，仅供离线研究/自建服务器使用。
- **运行时边界**：已验证候选可与扩容服务端连接到 `active`；客户端 `idx=2048`、`2049`、`4095` 均完成槽位创建、坐标更新与删除释放。高索引密集压力、断线重连和更长时间稳定性仍未验证。
- **未覆盖**：802 处 `and 0xFFF` 未分类。

## 客户端删除路径的三级结论

**已确认**：客户端和服务端独立释放函数的内部容量补丁均已覆盖。

**高度可信**：目前未发现具有相同序列号更新特征的内联释放副本。

**待运行时验证**：真正执行的删除入口、调用栈，以及实体槽位释放行为。

说明：`0x1003C` / `0x10014` / `0x10004` 三处常量比较构成的是**排除性证据**
（排除了同族容量比较未被覆盖的情形），不等于证明「不存在内联删除副本」，
因此第二行维持「高度可信」。本阶段不再对客户端删除函数做同类同质扫描。

## 分析记录

逐轮结论见 [reports/report.md](reports/report.md)（第 1–35 轮）。
网络层 N1 阶段结论见 [reports/network-n1.md](reports/network-n1.md)；
N2 更正（`+0x54` 语义撤回、位图布局更正、边界重推）见 [reports/network-n2.md](reports/network-n2.md)。

## 离线工作约定

本仓库只存分析产物，**不含任何 Valve 二进制**：所有字节级扫描都以外部盘上的安装目录为只读输入。
该盘未挂载时静态分析无法继续，此时只做文档与数据整理，不凭记忆补证据、不写未观测的地址。

恢复分析前先跑门禁，确认坐标仍指向同一构建：

```bash
python3 tools/check_artifacts.py    # 校验 engine/server/client 的 SHA-256 与尺寸
```

任一项不符即说明版本变了，`data/` 与 `reports/` 里的 VA、位宽站点全部失效。

## N3 记录（2026-10-22）

第 3 层网络协议的位宽争议在本轮收窄了一条关键前提：`m_nMaxEntries` 的构造参数不是常量，而是
`sv.num_edicts`（`ED_Alloc` 唯一自增的运行时全局 `0x1064576C`），因此容量随实体分配增长。
同时确认 `frame+0x118` 只在帧构造器里赋值一次，发送端只做按 tick 的查找；接收端的更新迭代由
**2048 位掩码**驱动（`FindNextSetBit` 的 `0x800`/`0x40` 常量），构成第 4 条 2048 硬边界。
详见 [reports/network-n3.md](reports/network-n3.md)，坐标见 `data/network_n3.csv`。
