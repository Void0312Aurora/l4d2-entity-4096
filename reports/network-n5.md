# N5：`0x1011A061` 的 `EBX` 不是帧——交叉证据被证伪

> 本轮只做两件小事：把 `FUN_10119F50` 里 `0x1011A025 → 0x1011A061` 这段的 `EBX` 数据流逐字节定案；
> 并按 review 意见修正 N4-S 的工作量口径。结论与 review 的推测相反，但因此排除了一个陷阱。

## 0 结论

| 项 | 结论 | 等级 |
|---|---|---|
| `0x1011A025` 的 `[ebx+0x118]` | `EBX` = `arg3` = **帧**，此处读帧的快照指针，成立 | 已证实 |
| `0x1011A061` 的 `[ebx+0x10C]` | `EBX` 在 `0x1011A04B` 被**重新赋值**为 `arg1`，**不是帧** | **已证实（证伪）** |
| 帧内 `+0x0C` 256 字节的消费者 | 仍未找到；`+0x10C` 这条线索与帧无关 | 未闭合 |
| N4-S 工作量口径 | 7 个机器码操作数 + 1 个必须不变的 cookie 校验点 | 已修正 |

## 1 逐字节解码：`EBX` 在 `lea` 前两条指令被换掉

`read_bytes(0x1011A008, 96)` 的原始字节，按指令边界还原（关键区段）：

```
0x1011a008  84 c0                 TEST AL, AL
0x1011a00a  74 0f                 JZ   0x1011a01b
0x1011a00c  83 3d 5c556410 02     CMP  dword [0x1064555c], 2
0x1011a013  0f 9d c0              SETGE AL
0x1011a016  88 45 f8              MOV  [EBP-8], AL
0x1011a019  eb 04                 JMP  0x1011a01f
0x1011a01b  c6 45 f8 01           MOV  byte [EBP-8], 1
0x1011a01f  33 c0                 XOR  EAX, EAX
0x1011a021  3b d8                 CMP  EBX, EAX
0x1011a023  74 18                 JZ   0x1011a03d
0x1011a025  8b 8b 18 01 00 00     MOV  ECX, [EBX+0x118]        ; <<< 帧快照
0x1011a02b  c6 85 acfeffff 01     MOV  byte [EBP-0x154], 1
0x1011a032  89 9d b0feffff        MOV  [EBP-0x150], EBX
0x1011a038  89 4d e4              MOV  [EBP-0x1C], ECX
0x1011a03b  eb 0f                 JMP  0x1011a04c
0x1011a03d  88 85 acfeffff        MOV  [EBP-0x154], AL
0x1011a043  89 85 b0feffff        MOV  [EBP-0x150], EAX
0x1011a049  89 45 e4              MOV  [EBP-0x1C], EAX
0x1011a04c  8b 9d a0feffff        MOV  EBX, [EBP-0x160]        ; <<< EBX 重新定义 = arg1
0x1011a052  83 bb 08 01 00 00 ff  CMP  dword [EBX+0x108], -1
0x1011a059  89 85 c8feffff        MOV  [EBP-0x138], EAX
0x1011a05f  75 25                 JNZ  0x1011a086
0x1011a061  8d b3 0c 01 00 00     LEA  ESI, [EBX+0x10C]        ; <<< 目标是 arg1+0x10C
```

两处 `EBX` 的定名：

| 地址 | 指令 | `EBX` 的来源 |
|---|---|---|
| `0x10119f67` | `MOV EBX,[EBP+0x10]` | **`arg3`（帧）** |
| `0x10119f6b` | `MOV [EBP-0x160], EAX`，其中 `EAX=[EBP+8]` | 保存 **`arg1`** |
| `0x1011a04c` | `MOV EBX,[EBP-0x160]` | **`arg1`**（重新赋值） |
| `0x1011a061` | `LEA ESI,[EBX+0x10C]` | 因此 = `arg1+0x10C` |

`arg1` 是调用方传入的第一个参数：`FUN_10119f50(DAT_10695860+0x21c, param_1, iVar1, local_24)`，
即 `[0x10695860]+0x21c` 处的对象（客户端/连接侧），与 `arg3` 的帧不是同一类。

## 2 后果

1. **证伪**：review 提出的「`0x1011A025` 与 `0x1011A061` 之间没有重定义，所以 `EBX` 一直是帧」
   不成立——`0x1011a04c` 就是那次重定义，落在两条证据之间。
2. **保留**：`0x1011A025` 的 `[ebx+0x118]` 确实是**帧**的快照读取（`arg3` 语义由
   `FUN_101860C0` 的调用点独立确认），这条不影响它。
3. **`+0x10C` 归属**：属于 `arg1` 类，不进帧迁移清单；`mov [edx+0x10C], esi` 保存的是
   `arg1+0x10C` 的地址，仍需单独做别名分析，但对象类型已从「帧」改判为「客户端侧对象」。
4. **仍未闭合**：帧内 `+0x0C` 的 256 字节消费者。`+0x10C` 这条线索关闭后，下一步应直接从
   `LEA <reg>,[frame+0x0C]` 与 `[frame+0x0C + (i>>5)*4]` 两类寻址去找，而不是沿 `+0x10C` 追。

## 3 N4-S 口径修正（按 review）

- 工作量按**机器码操作数**计：`0x1011d903`(imm)、`0x1011d925`、`0x1011d940`、`0x1011d94e`、
  `0x1011d9d2`、`0x1011d9c0`、`0x1011d9ff` —— **7 处改写**；
- `EBP-0x4` 的 cookie 是**必须保持不变**的校验点，不计入改写；
- N4 §8.3 的「4 处偏移 + 1 处栈探测 + 4 处基址平移」是分类描述，与 7 处操作数不是同一口径，
  已在 N4 正文标注修正。

### 生成器断言（写入 patch 脚本时强制）

```python
OLD_FRAME, NEW_FRAME = 0x1010, 0x2010
OLD_BASE,  NEW_BASE  = -0x1004, -0x2004
assert NEW_FRAME - OLD_FRAME == 0x1000
assert NEW_BASE + 4096 * 2 == -4          # 数组尾正好抵到 cookie 之前
assert NEW_BASE - OLD_BASE == -0x1000
```

另外在生成补丁前，对 `FUN_1011D900` 的**全部 EBP 相对内存操作**做一次解码枚举
（`procedure_assembly` 已可提供完整 457 字节列表），确认没有第 8 个需要平移的局部引用。

## 4 N4-A 的入口已经定位（下一轮）

`SV_SpawnServer` 的两个字符串已取出：

```
0x1037ac20  "SV_SpawnServer -- Finished"
0x1037af14  "SV_SpawnServer(%s)"
```

下一步：对这两个地址取 `xrefs` → 定位 `SV_SpawnServer` 函数体 → 把 `0x800` 常量的数据流追到
`[0x10645770]` 的写入（预计不在 `ED_Alloc` 侧，而在 spawn 初始化侧）。

## 5 复现

```bash
# REA 会话内
#   procedure_assembly(0x10119F50)   -> 头部 0x10119f50..0x1011a00c 的 EBX/参数保存
#   read_bytes(0x1011A008, 96)       -> 关键区段原始字节
#   search_strings("SpawnServer", literal) -> 0x1037ac20 / 0x1037af14
```
