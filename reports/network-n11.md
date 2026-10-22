# N11：N4-S 落地——11 个操作数的补丁工具、双重校验与计数修正

> review 要求把 N4-S 从方案变成可应用补丁。本轮交付 `tools/patch_n4s_engine.py`：
> SHA-256 硬门禁 + 指令字节校验 + 全函数 EBP 访问枚举 + 不变量断言，`--check` 与 `--out` 两模式。
> 同时修正一个计数错误：**不是 7 处，而是 10 处 disp32 + 1 处立即数 = 11 个操作数**。

## 0 结论

| 项 | 结果 |
|---|---|
| 补丁工具 | `tools/patch_n4s_engine.py`（纯标准库，无需 pefile/capstone） |
| 输入门禁 | SHA-256 必须等于 `8a6d4680…`，否则 `REFUSED`（`--allow-hash` 才可绕过） |
| `__chkstk` 立即数 | `0x1011D903` `b8 10 10 00 00` → `b8 10 20 00 00` |
| disp32 引用 | **10 处**（不是 7 处）：`f0`×2、`f4`×2、`f8`×4、`fc`×2 |
| 数组范围 | `[EBP-0x2004, EBP-0x4)`，8192 字节，正好 4096 个 `short`，止于 cookie 之前 |
| cookie | 用 `disp8 0xfc` 访问，不进入 disp32 补丁面，**结构上不可能被误改** |
| 写盘验证 | `/tmp/engine.n4s.dll`，sha256 `7086bb4d…` |

## 1 计数修正：7 → 10 处 disp32

N4 的「7 处」只数了**写**（4 个标量的 store + 2 个数组访问 + 1 个 chkstk），漏掉了**读**。
按「函数体内所有 EBP 相对访问」枚举后：

| disp32 | 新值 | 语义 | 出现次数 | 地址 |
|---|---|---|---|---|
| `f0 ef ff ff` | `f0 df ff ff` | `local_1010` 保存的 `ECX` | 2 | `0x1011D927`（存）、`0x1011DA5A`（取） |
| `f4 ef ff ff` | `f4 df ff ff` | `local_100c` `max_clients` | 2 | `0x1011D942`（存）、`0x1011D97B`（比较） |
| `f8 ef ff ff` | `f8 df ff ff` | `local_1008` 循环索引 | 4 | `0x1011D950`、`0x1011D9B7`、`0x1011D9CD`、`0x1011D9D4` |
| `fc ef ff ff` | `fc df ff ff` | 数组基址 `-0x1004` | 2 | `0x1011D9C4`（写）、`0x1011DA01`（`LEA` 取址） |

加上 `0x1011D903` 的立即数，**共 11 个机器码操作数**。这正是 review 提醒的
「不能只改循环边界」：漏掉任何一处读，都会出现「数组搬了、索引还在旧位置」的错配。

## 2 工具的两层校验

**第一层：字节级**

- 输入 SHA-256 硬门禁（不匹配直接退出，不写文件）；
- `__chkstk` 指令完整匹配 `b8 10 10 00 00`；
- 每处 disp32 的 4 字节完整匹配 `?? ef ff ff` 形态；
- 写盘后重新读取函数体，断言**旧 disp32 全部消失**、新 disp32 计数与命中数一致。

**第二层：函数级**

- 以 `FUNC_START=0x1011D900`、`FUNC_END=0x1011DAC9` 为界枚举全部 EBP 相对访问；
- 断言至少存在一处数组基址引用（`fc ef ff ff`）；
- 断言新数组范围 `-0x2004 + 4096*2 = -0x4`，即止于 cookie 前一个字节；
- cookie 使用 `disp8 0xfc`，不在 disp32 映射表中，天然不受影响。

## 3 运行结果

```
$ python3 tools/patch_n4s_engine.py --check
sha256: 8a6d4680…  (match)
chkstk: 0x1011D903 b810100000 -> b810200000
disp32 references found in FUN_1011D900: 10
  ... 10 lines ...
new disp counts: {'f0dfffff': 2, 'f4dfffff': 2, 'f8dfffff': 4, 'fcdfffff': 2}
CHECK ONLY: no file written

$ python3 tools/patch_n4s_engine.py --out /tmp/engine.n4s.dll
wrote /tmp/engine.n4s.dll (4817712 bytes, sha256 7086bb4d3098b7496004b90ac494b65c0601e7e3ad39c5a0f19304f4f3f1dda4)
```

## 4 与存储层补丁的合并（未做，下一步）

`engine/manifest.json` 已含 11 条存储层补丁（verified 状态各自独立）。最终实验 DLL 必须
**先应用存储层 11 条，再应用 N4-S 的 11 个操作数**，只产出一份合并样本；否则会出现
「只扩了数组没扩索引」或「只扩了容量没扩栈数组」的半成品，测试结论不可用。

合并脚本的下一个动作：

1. 复用存储层已有的字节补丁清单（`engine/manifest.json` 的 `patches`）；
2. 以同一 SHA-256 门禁加载原版 → 顺序应用 → 输出 `out/engine.4096.n4s.dll`；
3. 对输出做二次校验：`check_fields_csv` 不涉及，但需 `check_artifacts` 记录新哈希 + 逐站点回读。

## 5 manifest 一致性修正

`capacity_imm` 的旧 `note` 仍写 `sole writer`，与 `verified=true` + `level1` 的范围冲突；
已改为：

```
"note": "mov eax,0x800 -> 0x1000 (sv.max_edicts at normal SpawnServer path; this+0x218 with ECX=0x10645558)"
```

`verified`、`verification_scope`、`verification_note` 均保留不变。

## 6 复现

```bash
python3 tools/patch_n4s_engine.py --check
python3 tools/patch_n4s_engine.py --out /tmp/engine.n4s.dll
sha256sum /tmp/engine.n4s.dll   # 7086bb4d3098b7496004b90ac494b65c0601e7e3ad39c5a0f19304f4f3f1dda4
```
