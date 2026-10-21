# L4D2 实体上限扩容（2048 → 4096）

对《Left 4 Dead 2》build `23990068`（Source Engine 1，PE32 i386）实体管理体系的离线静态分析，
目标是在**不更换引擎、不修改 32 位构建**的前提下，把网络实体上限从 2048 提高到 4096。

扩容跨三层，缺一不可：

| 层 | 二进制 | 负责什么 | 状态 |
|---|---|---|---|
| 1 · 存储 | `engine.dll` | edict 数组容量、`sv.max_edicts` | 11 条补丁，副本已生成 |
| 2 · 实体管理 | `server.dll` / `client.dll` | 实体列表槽位、句柄位宽、分区 | 808 / 1089 条补丁 |
| 3 · 网络协议 | `engine.dll` | edict 索引线格式、快照、EHANDLE | **N1 审计完成，补丁未开始** |

仓库只包含**分析产物**（补丁清单、生成器、报告），不包含任何 Valve 的二进制文件。

## 状态

| 模块 | 补丁 | 隔离副本 | 静态预检 |
|---|---|---|---|
| `engine.dll` | **11** | 已生成 | **43/43** |
| `server.dll` | **808** | 已生成 | PE 预检 **30/30** |
| `client.dll` | **1089** | 已生成（实验性） | 字节匹配通过 |

`client.dll` 的隔离副本 `out/client.4096.dll` 已构建（1,089 处补丁，SHA-256
`2f0e723a2991edee628e20638c506ce9508cb96fc8dd226d37603cc0035e0752`）。
它是**实验性静态产物**：未做运行时验证，也不声称位移/掩码语义正确。

网络协议层已进入 **N1** 阶段：`SVC_PacketEntities` 出入口、两个 11 位字段、
实体索引与网络序列号位宽均已用静态证据定位（见
[reports/network-n1.md](reports/network-n1.md)）；补丁尚未生成。
运行时加载与实体生命周期**尚未验证**。

## 目录

```
engine/       第 1 层：engine.dll 存储扩容
  manifest.json   11 条补丁 + 新段定义
  verify_pe.py    43 项校验 + 副本构建
  report.md       分析记录
  run.log         最近一次运行输出
manifests/    第 2 层：补丁清单（核心产物）
  server.json   808 条
  client.json   1089 条（含 3 条 pending、802 处未分类掩码）
tools/        可复现的生成器与校验器
  config.py       二进制路径（L4D2_ENGINE_BIN / L4D2_GAMEDLL_BIN 分离）
  gen_server.py   生成 server 清单
  gen_client.py   生成 client 清单
  build_server.py 应用补丁 + PE 手术，产出隔离副本
  build_client.py 应用 1089 处补丁 + `.clentls` 段，产出隔离副本
  precheck_server.py 只读 PE 预检（30 项）
  scan_netproto.py 网络位缓冲原语与位宽站点初筛
  xrefs_by_imm.py / dump_fn.py 按立即数查引用 / 按地址反汇编整函数
data/         原始扫描结果（CSV）
  network_fields.csv    N1 字段图（VA / 偏移 / 位宽 / 合法值）
  network_boundary.csv  N1 边界矩阵（2046…4096）
reports/      分析报告（第 1–35 轮完整记录）、N1 网络报告与预检输出
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

**补丁类别**（client）：`C1-global` 4、`C2-vptr` 3、`C3-this` 18、`C4-vtload` 17、
`C5-col/bcd` 2、`C6-member` 129、`C7-bound` 2、`C7-ctor` 3、`C8-shl` 2、
`C9-mask` 453、`C10-shr` 453、`C11-rel` 2。

**网络层 N1（`engine.dll`）**

`SVC_PacketEntities` 的两条出入口通过 RTTI → CompleteObjectLocator → vftable
独立定位，不经字符串猜测：

| 符号 | VA | 依据 |
|---|---|---|
| `ReadFromBuffer` | `0x101D7460` | vftable `0x103584DC` 槽 5 |
| `WriteToBuffer` | `0x101D7340` | 同表槽 6 |

对象内两个**独立**的 11 位字段：`m_nMaxEntries`（`+0x54`，写 `push 0xb`
@`0x101D7366`，读掩码 `0x7FF` @`0x101D747E`）与 `+0x58` 的第二个 11 位字段
（写 `0x101D73D5`，读 `0x101D7798`）。

字段语义：`m_nMaxEntries` 承载「最大实体索引（含）」而**不是**条目计数——
写入侧带 `bCheckRange=1`，11 位上限 2047，若为计数则原版 2048 实体在同一条
路径上就已越界。该判定同时决定了补丁位宽：索引语义下 4096 槽位需要
`0xFFF`，12 位刚好够；计数语义下 4096 需 13 位，12 位会在 4096 处溢出。

网络 EHANDLE：索引 11 位 + 序列号 **10 位**（`WriteUBitLong(serial,10,1)`
@`0x10119576`）= 21 位，目标态 `12+10=22` 位。`CBitVec<MAX_EDICTS>` 是
对象内固定内联数组（`+0xC` / `+0x10C` 常量基址，`>>5` 取字、`&0x1F` 取位），
2048 位 = 256 字节 → 4096 位 = 512 字节，扩容需同步移动其后字段。

## 已知限制

- **版本绑定**：所有地址对应 build `23990068`，游戏更新后全部失效。
- **超出 2048 后不再兼容原版客户端**：网络 edict 索引是 11 位，扩容端只能与扩容端联机。
- **签名失效**：补丁后 Authenticode 无效，仅供离线研究/自建服务器使用。
- **未验证**：无运行时加载、构造、实体生命周期或联机测试。
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
网络层 N1 阶段结论见 [reports/network-n1.md](reports/network-n1.md)。
