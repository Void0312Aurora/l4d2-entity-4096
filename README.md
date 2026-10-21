# L4D2 实体上限扩容（2048 → 4096）

对《Left 4 Dead 2》build `23990068`（Source Engine 1，PE32 i386）实体管理体系的离线静态分析，
目标是在**不更换引擎、不修改 32 位构建**的前提下，把网络实体上限从 2048 提高到 4096。

扩容跨三层，缺一不可：

| 层 | 二进制 | 负责什么 | 状态 |
|---|---|---|---|
| 1 · 存储 | `engine.dll` | edict 数组容量、`sv.max_edicts` | 11 条补丁，副本已生成 |
| 2 · 实体管理 | `server.dll` / `client.dll` | 实体列表槽位、句柄位宽、分区 | 808 / 1089 条补丁 |
| 3 · 网络协议 | `engine.dll` | edict 索引线格式、快照、EHANDLE | **未开始** |

仓库只包含**分析产物**（补丁清单、生成器、报告），不包含任何 Valve 的二进制文件。

## 状态

| 模块 | 补丁 | 隔离副本 | 静态预检 |
|---|---|---|---|
| `engine.dll` | **11** | 已生成 | **43/43** |
| `server.dll` | **808** | 已生成 | PE 预检 **30/30** |
| `client.dll` | **1089** | 未生成 | 字节匹配通过 |

网络协议层（`svc_PacketEntities`、网络 EHANDLE、快照差分）**尚未开始**。
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
  config.py       二进制路径（支持 L4D2_BIN 覆盖）
  gen_server.py   生成 server 清单
  gen_client.py   生成 client 清单
  build_server.py 应用补丁 + PE 手术，产出隔离副本
  precheck_server.py 只读 PE 预检（30 项）
  scan_refs.py / audit_object.py 早期扫描工具
data/         原始扫描结果（CSV）
reports/      分析报告（第 1–35 轮完整记录）与预检输出
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

## 已知限制

- **版本绑定**：所有地址对应 build `23990068`，游戏更新后全部失效。
- **超出 2048 后不再兼容原版客户端**：网络 edict 索引是 11 位，扩容端只能与扩容端联机。
- **签名失效**：补丁后 Authenticode 无效，仅供离线研究/自建服务器使用。
- **未验证**：无运行时加载、构造、实体生命周期或联机测试。
- **未覆盖**：802 处 `and 0xFFF` 未分类；`RemoveEntity` 静态零调用者，真实删除入口未确认。

## 分析记录

逐轮结论见 [reports/report.md](reports/report.md)（第 1–35 轮）。
