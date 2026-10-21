# L4D2 engine.dll — edict 4096 分配层补丁（BSS 方案）

**状态**：离线补丁清单 + 校验已固定，**未写入游戏目录**。
**产物**：`out/engine.4096.dll`（补丁副本）、`manifest.4096-bss.json`、`verify_pe.py`

| 项 | 值 |
|---|---|
| 源文件 | `<SteamLibrary>/steamapps/common/Left 4 Dead 2/bin/engine.dll` |
| 源 SHA-256 | `8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86` |
| 源大小 | 4,817,712 (0x498330) |
| buildid | 23990068（Windows depot, app 550） |
| 格式 | PE32 i386，ImageBase 0x10000000 |
| 输出 SHA-256 | `3ac18292d746d1d33445b82e83c237fa25b7a3daab5968c18ddf42144059012e` |
| 输出大小 | **4,817,712（与源相同）** |

---

## 1. 文件尾部布局修正

初见以为 `.reloc` raw 结束（0x492A00）即文件尾，实际不是。逐字节解析结果：

```
0x000000 .. 0x492A00   PE 头 + 5 个节的 raw 数据
0x492A00 .. 0x495698   旧 Authenticode 副本（0x2C98 字节，WIN_CERTIFICATE rev=0x200 type=2）
0x495698 .. 0x498330   现用证书表（0x2C98 字节，安全目录指向此处，并恰好止于 EOF）
```

- 两份 blob 长度相同（0x2C98），内容不同（989 字节差异）→ 该文件被**重新签名过一次**，旧签名未清理。
- 因此「在 0x492A00 追加 0x4000 原始数据」会覆盖旧签名副本，**原方案作废**。
- 采用 BSS 段后，文件长度与尾部 0x5930 字节**全部保持原样**（校验 `overlay 字节未改变` PASS）。

---

## 2. 新段定义（无文件内容）

| PE 字段 | 值 |
|---|---|
| Name | `.edict2` |
| VirtualAddress | `0x73F000`（= 旧 SizeOfImage，紧跟 `.reloc` 虚拟结束 0x73E98A 页对齐后） |
| VirtualSize | `0x4000` |
| SizeOfRawData | `0` |
| PointerToRawData | `0` |
| Characteristics | `0xC0000080`（CNT_UNINITIALIZED_DATA \| MEM_READ \| MEM_WRITE） |
| NumberOfSections | 5 → 6 |
| SizeOfImage | `0x73F000` → `0x743000` |
| SizeOfUninitializedData | `+0x4000` |
| CheckSum | 按 PE 规范重算（排除 checksum 字段与证书表） |
| 段头位置 | 文件 0x2F0（旧段表结束处，原为 40 字节零填充） |

加载器将其映射为 16 KiB 零初始化可读写内存；`SV_SpawnServer` 中的 `memset` 仍会每图清零（长度已改为 `0x4000`）。

---

## 3. 补丁清单（11 个 dword）

| id | 指令 VA | 文件偏移（dword） | 原值 | 新值 | 语义 |
|---|---|---|---|---|---|
| capacity_imm | 0x10123DA2 | 0x1231A3 | `0x00000800` | `0x00001000` | `sv.max_edicts`，唯一写入源 |
| reuse_clear_size | 0x101DFEF0 | 0x1DF2F1 | `0x00002000` | `0x00004000` | memset 长度 |
| reuse_arr_push | 0x101DFEF7 | 0x1DF2F8 | `0x106B3A58` | `0x1073F000` | memset 目标 |
| reuse_arr_S2 | 0x101DFF49 | 0x1DF34E | `0x106B3A58` | `0x1073F000` | 初始化清理循环 |
| reuse_arr_S3 | 0x101DFFC4 | 0x1DF3C7 | `0x106B3A58` | `0x1073F000` | 释放记录 sv.time |
| reuse_arr_S4 | 0x101DFFF2 | 0x1DF3F7 | `0x106B3A58` | `0x1073F000` | 指针差重置 |
| reuse_arr_S5 | 0x101E015B | 0x1DF560 | `0x106B3A58` | `0x1073F000` | ED_ClearEdict 内置零 |
| reuse_arr_S6 | 0x101E0201 | 0x1DF605 | `0x106B3A58` | `0x1073F000` | 复用节流 |
| reuse_arr_S7 | 0x101E021B | 0x1DF61E | `0x106B3A58` | `0x1073F000` | 时间差 |
| reuse_arr_S8 | 0x101E024F | 0x1DF654 | `0x106B3A58` | `0x1073F000` | 复用节流 |
| reuse_arr_S9 | 0x101E0295 | 0x1DF69A | `0x106B3A58` | `0x1073F000` | 复用节流 |

容量派生项**无需补丁**：`pEdicts = hunk(cap<<4)`、`pEdictChangeInfo = hunk(cap*4)`、6 处边界比较同源读取。

---

## 4. 强制校验（全部通过：43/43）

| 类别 | 检查 |
|---|---|
| 绑定 | 完整 SHA-256、文件长度、PE32/i386/ImageBase、NumberOfSections、SizeOfImage、SizeOfHeaders |
| 尾部 | 证书表止于 EOF、`WIN_CERTIFICATE` 字段合法、旧签名副本存在且内容不同 |
| 指令上下文 | 11 处均校验**完整指令字节**（非仅 4 字节数值），并核对 dword 原值 |
| 重定位 | 9 处数组引用 RVA 全部为 `IMAGE_REL_BASED_HIGHLOW`；全文件 `0x106B3A58` 常量计数 = 9 |
| 布局 | 现有节虚拟区间不重叠；新段 `0x73F000..0x743000` 不与任何节相交；第 6 段头止于 0x318 ≤ SizeOfHeaders(0x400)；段头区原为空白 |
| 输出重解析 | 文件长度不变、6 段、SizeOfImage=0x743000、新段字段正确、overlay 字节不变、`.reloc` 目录一致（143,365 条） |
| 差异审计 | 全文件差异 **47 字节**，全部落在 11 个 dword / 5 个头部字段 / 40 字节段头内，**0 字节越界** |

独立工具复核：`file` → `PE32 ... 6 sections`；`objdump -p` → `SizeOfImage 00743000`、`SizeOfHeaders 00000400`、`ImageBase 10000000`。

---

## 5. 验收目标（离线可判定部分）

| 目标 | 结果 |
|---|---|
| `max_edicts = 4096` | ✅ |
| `sizeof(pEdicts) = 65536` | ✅（`cap<<4` 派生，未改表达式） |
| `sizeof(pEdictChangeInfo) = 16384` | ✅（`cap*4` 派生） |
| `sizeof(reuseTimes) = 16384` | ✅（新段 VirtualSize） |
| 9 处复用时间引用一致重定位 | ✅ |

`EDICT_NUM(i) = pEdicts + 16i` 对 `i ∈ [0,4096)` 成立，与 edict 指针差相关的 S3/S4/S5 也全部指向新基址。

---

## 6. 复现

```bash
cd engine
python3 verify_pe.py          # 43 checks，输出 out/engine.4096.dll 与 manifest
```

脚本对游戏目录只读；源文件 SHA-256 在运行前后一致。

---

## 7. 本报告**不能**声称的（验证边界）

1. **hunk 无固定上限未证明。** 只证明 `FUN_10215D90` 触及提交边界时会调用 `FUN_1028C470`；后者是否受预留/提交/分配器状态约束未确认。本次增量 0xA000 字节存在自动增长路径，不等于引擎整体无上限。
2. **`EDICT_NUM(4095)` 可寻址 ≠ 4096 个 edict 能安全运行。** 只证明内存布局正确；`ED_Alloc` 造出的高索引实体随后会进入未修改的其它引擎结构（快照、包、栈帧），需动态验证。
3. **未做运行时验证。** 没有任何一次执行；所有结论均为静态/离线。
4. **未覆盖**：网络 11 位线格式、`CL_CopyNewEntity` 等固定栈帧、`server.dll` 的 `CBaseEntityList` 4096 槽分区。

---

## 8. 下一步

按你的判断，优先级应是 `server.dll` 的 `CBaseEntityList`：先确定原版 4096 槽位如何分区（联网 2048 / 非联网池），以及高索引 edict 是否会与非联网实体冲突。这比先动网络协议更接近结构性瓶颈。
