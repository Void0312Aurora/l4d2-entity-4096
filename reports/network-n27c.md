# N27-C：`WriteDeltaEntities` 栈位图迁移与 N27-B 的 P0 修正

> 原版 `engine_srv.so`（sha256 `5fa15f28…309b7`）。本轮只做指令级分析与清单修正，
> 不构建镜像；N27-D 前必须通过本文件的验收门禁。

## 0 N27-B 的三个 P0 修正

### P0-1 `cmp eax,0x40 → 0x80` 不能等长替换

`83 F8 40` 是 `83 /7 ib`，立即数按有符号 8 位符号扩展，`0x80` 会变成 `-128`。
受影响：`0xE90E6`、`0xE91E2`、`0xE91FF`。

采用的等长变换（不改指令长度）：

```
83 F8 40          cmp eax, 0x40
        ↓
A8 80 90          test al, 0x80 ; nop
```

并把紧随其后的 `je rel32`（`0F 84`）改为 `jne rel32`（`0F 85`），
只改 opcode 字节 `84 → 85`：

| 地址 | 原 | 新 |
|---|---|---|
| `0xE90E6` | `83 F8 40` | `A8 80 90` |
| `0xE90E9` | `0F 84` | `0F 85` |
| `0xE91E2` | `83 F8 40` | `A8 80 90` |
| `0xE91E5` | `0F 84` | `0F 85` |
| `0xE91FF` | `83 F8 40` | `A8 80 90` |
| `0xE9202` | `0F 84` | `0F 85` |

正确性：`eax` 从 1 递增，测试点最大为 128；`al < 0x80` 时 ZF=1，`jne` 不跳转；
`eax == 128` 时 `al & 0x80 != 0`，ZF=0，`jne` 退出循环。
`eax` 不会在测试点超过 128，因此 `test al,0x80` 与 `cmp eax,128` 等价。

### P0-2 `0x1DDE90` 归属冲突

该处 `eax` 是 `CBaseClient*`（见 N27-A 数据流），只能按 C3 处理：

```
lea edx,[eax+10Ch]  →  mov edx,[eax+10Ch]
```

已从 `data/linux/n27b_frame_member_sites.csv` 删除（帧成员表从 48 条降为 47 条），
仅保留在 C3；新增 `tools/linux/check_patch_sites.py`，对补丁表做
“同一指令字节区间不得被不同组重复占用”的硬检查，当前结果 `PASS`。

### P0-3 分配桩必须恢复 `rep stosd` 的寄存器状态

`operator new` 会改写 `EAX/ECX/EDX`；原构造器随后执行 `mov edi,edx` 与 `rep stosd`，
其中 `EAX` 是填充值（必须为 0），`ECX` 是 DWORD 数（必须为 0x80）。
修正后的桩：

```
stub_alloc:
  push 0x200
  call operator new          ; _Znwj
  add  esp,4
  mov  [ebx+0x10C],eax
  mov  edx,eax
  mov  ecx,0x80              ; rep stosd 次数
  xor  eax,eax               ; 填充值必须为 0
  ret
```

返回后原 `mov edi,edx` 设置 `EDI`；`ECX/EAX` 已由桩恢复。
仍需在 N27-D 决定分配失败（`EAX==0`）时是否 `Sys_Error`；
栈对齐由 `push/call/add` 自平衡，桩不改变调用者的 EBP/ESP 关系。

## 1 `WriteDeltaEntities` 栈帧事实

入口序列（原始字节）：

```
1DD833  b9 40 00 00 00        mov ecx,0x40
1DD83C  8d bd d0 fe ff ff     lea edi,[ebp-0x130]
1DD843  81 ec cc 01 00 00     sub esp,0x1CC
1DD850  f3 ab                 rep stosd
```

位图区间：`[EBP-0x130, EBP-0x31]`（256 B，64 DWORD）。
迁移目标：`[EBP-0x230, EBP-0x31]`（512 B，128 DWORD），即
**保持位图结束位置不变、起点下移 0x100**。

## 2 EBP 布局映射

对全函数逐条解码，共 **44 个不同的 EBP 位移**（`data/linux/n27c_stack_map.csv`）：

| 区间 | 处理 | 例子 |
|---|---|---|
| `-0x130` | 位图基址 → `-0x230` | `lea edi,[ebp-0x130]`；`[ebp+edx*4-0x130]`；`[ebp+eax-0x130]` |
| `-0x1B0 .. -0x134` | **下移 0x100** | `-0x14C→-0x24C`、`-0x158→-0x258`、`-0x188→-0x288`、`-0x19C→-0x29C` |
| `-0x30 .. -0x1C` | 保持 | `var_30/var_2C/var_28/var_24/var_20/var_1C` |
| `+0x8 .. +0x18` | 保持（参数） | `this/arg_4/arg_8/arg_C/arg_10` |

栈帧预留量：`sub esp,0x1CC → 0x2CC`。

## 3 编码与别名检查

- 所有需要下移的局部变量原位移已超出 `disp8`，编码本来就是 `disp32`，
  新位移仍在 `disp32` 范围，**指令长度不变**；
- 位图索引形式 `[ebp+edx*4-0x130]`、`[ebp+eax-0x130]` 也是 `disp32`，等长；
- 解码器曾把这两条误判为 ESP 基址（`o_displ` 的 `reg` 字段对带比例索引不直观），
  以反汇编文本为准：两条都是 `ebp`，**函数内没有负向 ESP 相对局部变量**；
- `lea` 形成的局部对象指针（如 `[ebp+var_184]`、`[ebp+var_180]`）随位移一起迁移，
  无第二套别名；
- 相对跳转/调用目标不因本轮修改而移动（无长度变化）。

## 4 位图语义点

| 项 | 站点 | 修改 |
|---|---|---|
| 清零 | 0x1DD833 / 0x1DD83C / 0x1DD850 | `ecx=0x80`，`edi=-0x230`，`eax=0` |
| 置位 | 0x1DE9D4 | 基址 `-0x130 → -0x230` |
| 测试 | 0x1DEDEF | 基址 `-0x130 → -0x230` |
| 位号上限 | 9 处 `cmp r32,0x7FF` | `0xFFF`（imm32，等长） |

9 处上限地址：
`0x1DDEEF`、`0x1DDFA1`、`0x1DE0CD`、`0x1DE17F`、`0x1DE5A5`、
`0x1DE6B6`、`0x1DE777`、`0x1DE827`、`0x1DEB41`。

帧内联位图的测试点 `0x1DEDFE` 使用 `[esi+eax+0x0C]`，位图起点不变，
本轮不需要改位移，只需保证帧位图已扩到 0x200（F3）。

## 5 验收门禁（N27-D 前必须全绿）

| 项目 | 标准 |
|---|---|
| 栈布局 | 新位图 `[-0x230,-0x31]` 与下移局部变量 `≤-0x234` 不重叠 |
| 位图清零 | `rep stosd` 覆盖 128 DWORD，`EAX=0` |
| 置位/测试 | 两条索引指令基址均为 `-0x230` |
| 循环边界 | 9 处 `0x7FF` 全部为 `0xFFF`，且语义逐一复核 |
| 寄存器/指针 | 无残留 `-0x130` 位图别名；`lea` 指针全部同步 |
| 指令布局 | 无长度变化；跳转/调用目标不变 |
| 补丁冲突 | `check_patch_sites.py` 通过 |
| 运行回归 | 地图加载、快照、baseline ack、客户端创建/断线/重连 |

## 6 结论

N27-C 的栈迁移方案已收敛为**等长位移替换**：
3 个 prologue 站点、2 个位图索引站点、9 个边界站点，其余 44 个 EBP 位移按
`n27c_stack_map.csv` 统一迁移。P0-1/P0-2/P0-3 已修正并进入补丁表；
N27-D 可以在静态门禁通过后构建隔离镜像。
