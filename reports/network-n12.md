# N12：补丁生成器按 review 收紧——地址白名单、显式异常、写盘回读

> 上一版工具的 `--check` 通过模式搜索定位，且「回读」只验证内存缓冲。本轮改为数据驱动：
> 10 个站点写死在 `tools/n4s_sites.json`，逐站点校验前缀字节与旧位移；所有门禁用 `SystemExit`；
> 写盘后重新打开文件验证。计数不变：**10 disp32 + 1 立即数 = 11 个操作数**。

## 0 已修正的三点

| review 指出的问题 | 本轮处理 |
|---|---|
| 未做指令级 EBP 枚举，只是字节模式搜索 | 改为**显式地址白名单**（10 个 VA），每站点校验「前缀 4 字节 + 旧 disp 4 字节」 |
| 「写盘后回读」实际只验证了内存 | 写盘后 `out.read_bytes()` 重新解析 PE、重定位、逐站点复验，再比对 sha/长度 |
| `assert` 在 `-O` 下失效 | 全部门禁改为 `SystemExit("REFUSED: …")`，不依赖断言 |

新增 `tools/n4s_sites.json`（审计产物），记录：审计 SHA-256、函数名、帧大小新旧值、
`chkstk` 地址与新旧字节、以及 10 个站点的 `va / prefix / disp_old / disp_new / context`。

## 1 站点白名单（10 个 disp32）

| VA（disp 字段） | 前缀字节 | 旧 → 新 | 语义 |
|---|---|---|---|
| `0x1011D927` | `5250898d` | `f0efffff → f0dfffff` | `local_1010` 保存 `ECX` |
| `0x1011D942` | `7e088985` | `f4efffff → f4dfffff` | `local_100c` 写 |
| `0x1011D950` | `c3f08985` | `f8efffff → f8dfffff` | `local_1008` 写 |
| `0x1011D97B` | `7e2b3b85` | `f4efffff → f4dfffff` | `local_100c` 比较 |
| `0x1011D9B7` | `d0668b95` | `f8efffff → f8dfffff` | `local_1008` 读 |
| `0x1011D9C4` | `6689944d` | `fcefffff → fcdfffff` | 数组写（`[EBP+ECX*2+disp32]`） |
| `0x1011D9CD` | `46148b85` | `f8efffff → f8dfffff` | 索引自增后写 |
| `0x1011D9D4` | `ff408985` | `f8efffff → f8dfffff` | 索引写 |
| `0x1011DA01` | `c9518d95` | `fcefffff → fcdfffff` | `LEA EDX,[EBP+disp32]`（memcpy 源） |
| `0x1011DA5A` | `c4108bbd` | `f0efffff → f0dfffff` | 取回保存的 `ECX` |

加 `0x1011D903` 的 `b810100000 → b810200000`，合计 11 个机器码操作数。

## 2 运行结果

```
$ python3 tools/patch_n4s_engine.py --check
sites : 10 pinned disp32 references verified (old form)
verify: old disp eliminated, 10 new disp present, chkstk updated
CHECK ONLY: no file written

$ python3 tools/patch_n4s_engine.py --out /tmp/engine.n4s.dll
disk  : reopened and verified (4817712 bytes, sha256 7086bb4d3098b7496004b90ac494b65c0601e7e3ad39c5a0f19304f4f3f1dda4)
```

写盘路径现在是：内存应用 → 内存复验 → 写入 → **重新读取文件** → 重新解析 PE → 逐站点复验
→ `chkstk` 复验 → sha/长度比对。

## 3 合并构建（下一步，未做）

review 的两条约束已记录：

1. **从审计原版出发、单次构建应用两组补丁**，不把 `engine.4096.dll` 再过 `--allow-hash`；
2. 新合并器**读取现有 `engine/manifest.json`** 作为存储层补丁定义，不调用
   `engine/verify_pe.py` 的「重建 manifest」路径——该路径会覆盖 N10 新增的
   `verified` / `verification_scope` / 数据流说明。

计划产物：`out/engine.4096.n4s.dll`，并附独立 `out/manifest.4096.n4s.json`，记录：

- 输入 `engine.dll` 的 SHA-256（与 `data/artifacts.json` 基线一致）；
- 输出 SHA-256、大小；
- 两组补丁（存储层 11 条 + N4-S 11 个操作数）的逐站点回读结果；
- PE 预检结果（`.edict2` 段、重定位、头空间）。

`tools/check_artifacts.py --record` 只记录输入基线，不被输出覆盖。

## 4 复现

```bash
python3 tools/patch_n4s_engine.py --check
python3 tools/patch_n4s_engine.py --out /tmp/engine.n4s.dll
```
