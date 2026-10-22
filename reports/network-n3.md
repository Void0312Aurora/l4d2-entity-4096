# N3：`frame+0x118` 写入链、`num_edicts` 载体、接收端 2048 位更新掩码

> 本轮针对 review 的 P0/P1 五项。三条结论被**证据闭合**，一条（虚表归属）结构已定但归属未证。
> 全部地址为 `engine.dll`（build `23990068`，SHA-256 `8a6d4680…0bf7ba86`）中的 VA，静态分析由
> Ghidra 12.1.4 完成，`open_binary` 校验的镜像哈希与 `data/artifacts.json` 一致。

## 0 摘要

| 编号 | review 问题 | 本轮结论 | 等级 |
|---|---|---|---|
| P0-1 | `frame+0x118` 的首次赋值链 | **唯一写入点是帧构造器 `FUN_10093E20`**（`+0x118` = 快照指针）；发送端只**查找**帧，不写该槽 | 已证实 |
| P0-2 | BSS `0x1064576C` 的写入链 | **`0x1064576C = sv.num_edicts`（动态用量）**，唯一写入是 `ED_Alloc` 的 `INC`；快照容量直接取它，**不是固定容量** | 已证实 |
| P0-3 | `[[edi-8]+0x80]` 的真实虚表归属 | `this-8` 处的 vptr 形态与调用形态已证；**vtable 基址/COL 未闭合**，槽位索引不能声称 | 部分 |
| P1-1 | delta 实体索引编解码 | 接收端用 **2048 位掩码 + `FindNextSetBit`（`0x800`/`0x40` 常量）** 推进条目，构成第 4 条 2048 硬边界 | 已证实（新增边界） |
| P1-2 | CSV 校验门禁 | 5 个数据文件全部等宽（6007 行），`check_fields_csv.py` 默认严格、`net_patch_plan.py --check` 先跑结构门禁 | 已闭合（另一提交） |

一句话：**`m_nMaxEntries` 的值域由 `num_edicts` 决定，而 `num_edicts` 随实体分配增长**——这正是 N2 无法从
「`+0xC` 写一次且不收缩」推出「容量固定为 2048」的那一步缺口。缺口现在补上了。

## 1 更正 N2 §14.4/§14.7 的语义边界

N2 的两条陈述仍然成立：

- `+0xC` 在构造时逐字写入（`FUN_1011D320` 的 `arg2`，`0x1011d3c6 mov [esi+0xc],eax`），之后没有改写点；
- 裸流字段就是 `[frame+0x118]+0x0C`，11 位。

但「写一次」只约束**单个快照对象**，不约束**构造参数的取值范围**。本轮把参数追到源头，
得到的是动态量，而不是常量——review 的这条批评成立，N2 §14.4 的措辞按本轮结论收窄为：
「已证实：容量由构造参数直接决定，构造后不重赋值。已证实（N3）：发送端的构造参数是 `num_edicts`。」

## 2 生产者链路（P0-2，已闭合）

### 2.1 `FUN_101254B0` = `SendClientMessages`

`FUN_101254B0` 的 `CVProfile::EnterScope` 参数与遥测字符串给出 `sv_main.cpp` / `"SendClientMessages"` /
`"Networking"`，函数中部调用：

```
iVar7 = FUN_1011d900(in_ECX[3]);          // 建快照
FUN_10127370(local_8, local_b8, iVar7);   // (客户端数, 客户端数组, 快照)
```

### 2.2 `FUN_1011D900` = 服务端快照构建：容量 = `num_edicts`

```
iVar5 = FUN_1011d320(param_1, DAT_1064576c);      // arg2 = 容量
puVar8 = (uint *)(DAT_10645774 - 0x10);           // edicts 数组（步长 0x10）
puVar9 = (undefined4 *)(*(int *)(iVar5 + 8) + -0xc);
if (0 < DAT_1064576c) {
  do {
    if ((puVar8[7] != 0) && ((puVar8[4] >> 1 & 1) == 0)) {   // 槽位在用
      puVar9[4] = puVar8[5];
      uVar6 = (**(code **)(*(int *)puVar8[6] + 4))();        // 类标识
      puVar9[3] = uVar6;
      local_1008[*(int *)(iVar5 + 0x14)] = (short)local_100c; // 栈上 short[2048] 存实体索引
      *(int *)(iVar5 + 0x14) += 1;
    }
    local_100c++;
    puVar8 += 4;  puVar9 += 3;
  } while (local_100c < DAT_1064576c);
}
```

三个观察互锁：

1. 容量参数是 `DAT_1064576c`，**原样**传给 `FUN_1011D320`（落 `+0x0C`）；
2. 同一值又是遍历 edict 数组的**上界**；
3. 条目只对在用槽位生成，未用槽位跳过——所以 `+0xC`（容量）与 `+0x14`（条目计数）含义不同，
   容量是「遍历范围」，不是「实际条目数」。

### 2.3 `0x1064576C` 的唯一写入点 = `ED_Alloc` 的自增

`xrefs(0x1064576C)` 共 17 处，逐条解码后只有一处是写：

| 地址 | 指令 | 类型 |
|---|---|---|
| `0x101E02F1` | `INC dword ptr [0x1064576C]` | **READ_WRITE（唯一写）** |
| `0x1011D917/954/9D8`、`0x1012365E`、`0x1018BFD7`、`0x101DFF31` 等 16 处 | `MOV/CMP` | 只读 |

补充扫描否证了另外三种绝对地址写编码（全部 **0 命中**）：

```
C7 05 6C 57 64 10   (mov dword [abs], imm32)      -> 0
89 ?? 6C 57 64 10   (mov [abs], r32)              -> 0
A3 6C 57 64 10      (mov moffs32, eax)            -> 0
81 05 6C 57 64 10   (add dword [abs], imm32)      -> 0
```

`0x101E02F1` 属于 `FUN_101E0170`，其字符串常量直接给出身份：`"ED_Alloc( %d ) - invalid edict index
specified."`、`"ED_Alloc: No edicts yet"`、`"ED_Alloc: no free edicts"`。关键分支：

```c
if (-1 < param_1) {                       // 指定索引分配
    if (param_1 < DAT_1064576c) { ... }   // 合法索引 < num_edicts
    ...
}
...
if (DAT_10645770 <= DAT_1064576c) {       // max_edicts <= num_edicts -> 失败
    ... FUN_101fc620("ED_Alloc: no free edicts");
}
DAT_1064576c = DAT_1064576c + 1;          // 否则扩一格
```

由此三条全局语义闭合：

| 地址 | 语义 | 依据 |
|---|---|---|
| `0x1064576C` | **`num_edicts`（当前 edict 数，动态）** | 唯一写点是 `ED_Alloc` 的 `INC`；作为合法索引上界与遍历上界 |
| `0x10645770` | **`max_edicts`（容量上限）** | 与 `num_edicts` 比较决定能否再扩；8 处引用全部为读 |
| `0x10645774` | **edicts 数组基址**（步长 `0x10`） | `ED_Alloc` 的 `param_1 * 0x10 + [0x10645774]` 与构建器的同一表达式 |

### 2.4 对位宽的直接后果

$$
N_{\text{snapshot}} \;=\; \text{num\_edicts} \;\le\; \text{max\_edicts}
$$

- 目前 `max_edicts` 的取值来自运行时初始化（`0x10645770` 在镜像里为 0，8 处引用均为读），
  所以「2048 这个常数在哪写」仍需追 `ED_Init` 一类初始化函数——本轮**没有**把这个数钉死。
- 但无论上限是 2048 还是 4096，`N` 都是**动态值**，不是常量容量。因此：
  - 若 `max_edicts = 2048` 且 `num_edicts` 可达 2048，则 11 位字段已经**存在值域溢出**
    （`2048 & 0x7FF = 0`）；这需要运行时探针确认 `num_edicts` 是否真的能到 2048，
    本轮不下结论，只登记为 C5 待测；
  - 扩容到 4096 时 `w_max = ⌈log2(4096+1)⌉ = 13`；若上限改为 4095（最大索引语义）则 `w_max = 12`。
    **仍取决于 `max_edicts` 的语义（计数 vs 最大索引）**，这正是 §6 的待测项。

## 3 `frame+0x118` 的写入链（P0-1，已闭合）

### 3.1 唯一写入点：帧构造器 `FUN_10093E20`

```c
void FUN_10093e20(int param_1) {          // param_1 = 快照
  *in_ECX = &PTR_FUN_1036ac28;            // vptr
  _memset(in_ECX + 3, 0, 0x100);          // +0x0C..+0x10B 清零
  in_ECX[1] = 0;                          // +0x04
  in_ECX[0x44] = 0; in_ECX[0x43] = 0;     // +0x110, +0x10C
  in_ECX[2] = *(undefined4 *)(param_1+4); // +0x08 = 快照 tick
  in_ECX[0x46] = 0;                       // +0x118 先清
  FUN_1011c290();
  if (in_ECX[0x46] != 0) FUN_1011db40();  // 旧快照 release
  in_ECX[0x46] = param_1;                 // <<< +0x118 = 快照（首次、唯一赋值）
  in_ECX[0x45] = 0;
}
```

`0x46 * 4 = 0x118`，与 §14.5 的 `frame = 0x11C` 布局一致。对象尺寸由两处池初始化旁证：
`FUN_10093970` 与 `FUN_10118E00` 都执行 `FUN_1028a300(0x11c,0x80,2,0,0)`。

### 3.2 接收端：`FUN_101846C0`（原「站点 4」）

```c
local_4058 = FUN_1011d320(*(in_ECX+0xbc), *(param_1+0x54));  // 容量 = 报文 +0x54
iVar1      = FUN_101ae9b0(0x11c);                            // 新 frame
uVar2      = FUN_10093e20(local_4058) -> *(in_ECX+0x49f0);   // ctor 安装 +0x118
...
local_4060 = *(*(in_ECX+0x49f4) + 0x118);                    // 上一帧的快照
puVar3 = *(local_4058+8); puVar4 = *(local_4060+8);          // 按 +0xC 条数逐条拷贝
for (...) { puVar3[1] = puVar4[1]; *puVar3 = *puVar4; ... }  // 12 字节条目
```

接收端的容量来源 `[msg+0x54]` 与 N2 §15 一致；`+0x54` 只用于分配（`FUN_1011D320` 的 `arg2`），
不参与 §5 的位图迭代——**这一点由本轮 §5 独立复核，N2 §15.7 成立**。

### 3.3 发送端：帧是**查**出来的，不是**造**出来的

`FUN_101860C0` 的字符串常量是 `"CHLTVDemo::RecordFrame"`，它：

```c
iVar1 = FUN_10093c80(*(in_ECX+0x588), 1);   // 按 tick 在帧链表里查找
FUN_10119f50(..., param_1, iVar1, local_24);// param3 = 帧
uVar2 = (iVar1 == 0) ? 0 : *(iVar1+0x118);  // 从帧取快照
FUN_101398e0(..., *(param_1+0x118), uVar2, ...);
```

`FUN_10093C80` 是**有序链表查找**，不是构造函数：

```c
if (param_1 < 0) return 0;
uVar3 = *(uint *)(in_ECX + 4);                       // 头结点
while (uVar2 = uVar1, *(int *)(uVar2 + 8) < param_1) { // 结点 +0x08 = tick
    uVar1 = *(uint *)(uVar2 + 0x114);                 // 结点 +0x114 = next
    ...
}
if (*(int *)(uVar2 + 8) == param_1) return uVar2;     // 精确命中
return (param_2 != 0) - 1 & uVar3;                    // 否则返回前驱（param_2=1 时）
```

所以发送路径对 `+0x118` 只读；该槽的内容在帧被创建时（§3.1）就已固定。**不存在第二条晚绑定写入**。

## 4 接收端更新迭代与 2048 位掩码（P1-1，新边界）

### 4.1 `FUN_101196C0`：条目存在性 → ParseDelta → 找下一置位

```c
uVar3 = 1;
if (*(char *)(in_EAX + 4) != '\0') {
    iVar2 = *(int *)(in_EAX + 0x14);                     // 当前条目索引
    if (entry_A[iVar2] == 0 && iVar2 < count_B &&
        entry_B[iVar2] != 0) {
        puVar1 = (uint *)(in_EAX + 0x3c + (iVar2 >> 5) * 4);
        uVar3 = 3;
        *puVar1 |= 1 << (iVar2 & 0x1f);                  // 置位：2048 位掩码
    }
}
FUN_10119370(*(in_EAX + 0x14), uVar3);                   // ParseDelta(index, flags)
if (*(int *)(in_EAX + 8) != 0) {
    iVar2 = FUN_1004e310(*(in_EAX + 0x14) + 1);          // 下一个置位
    *(in_EAX + 0x14) = iVar2;
    if (-1 < iVar2) return;
}
*(in_EAX + 0x14) = 9999;                                 // 终止哨兵
```

### 4.2 `FUN_1004E310`：`FindNextSetBit`，硬上界 `0x800`

```c
int FUN_1004e310(uint start) {
  if ((int)start < 0x800) {          // <<< 2048 位
    iVar2 = start >> 5;
    uVar3 = MASK[(start & 0x1f)] & word[iVar2];
    do {
      if (uVar3) { ... return iVar2*0x20 + bit; }
      uVar3 = word[++iVar2];
    } while (iVar2 < 0x40);          // <<< 64 个 dword = 2048 位
  }
  return -1;
}
```

**结论（对 review 第二节的收紧）**：

- `+0x58` **不是**「本包读取多少个更新头的循环上界」，至少在本函数里，迭代由
  **2048 位置位掩码**驱动，`+0x58` 没有出现在这条迭代路径上；
- 「控制更新条目数 ≠ 控制实体编号上界」成立，并且本轮给出反例方向的证据：
  这条路径的硬上界是**掩码宽度 2048**，与实体编号本身无关；
- 实体编号的真实上界仍要追 `FUN_10119370`（ParseDelta）与更上游的解码器——本轮**未**完成，
  登记为 C6。

### 4.3 新增的 2048 硬边界（第 4 条）

| # | 位置 | 形式 | 扩容到 4096 的改动面 |
|---|---|---|---|
| 1 | `FUN_10093970` / `FUN_10118E00` | 池尺寸 `0x11c` 参数 | 帧尺寸不变，仅是旁证 |
| 2 | `FUN_1011D900` | 栈上 `short[2048]`（实体索引表） | **2048 → 4096 项** |
| 3 | `FUN_1004E310` | `start < 0x800` 与 `iVar2 < 0x40` | **`0x1000` / `0x80`** |
| 4 | `FUN_101196C0` | 掩码基址 `+0x3c` 起的 256 字节位图 | **256 → 512 字节**，并挪动后续成员 |

## 5 `[[edi-8]+0x80]` 的归属（P0-3，部分）

### 5.1 已证

`FUN_101846C0`（628 字节、15 个基本块、非 thunk、无解析调用者 → 只能经函数指针/虚表进入）内的调用形态：

```
(**(code **)(*(int *)(in_ECX + -8) + 0x80))(&local_4054);
```

- `in_ECX` 是 `this`；先读 `[this-8]` 得到一个指针，再取该指针 `+0x80` 处的函数指针调用
  ——**形态与「vptr 在 `this-8` 的多重继承子对象」一致**；
- 实参是栈上 0x40 字节结构（`local_4054`…`local_4014`），字段来源明确：

| 结构偏移 | 值来源 |
|---|---|
| `+0x00` | `&PTR_FUN_1036350c`（vtable 形状的常量） |
| `+0x04` | `local_405c`（`FUN_10093c80(msg+0x64,1)` 查到的旧帧） |
| `+0x08` | `*(in_ECX+0x49f0)`（**本函数刚建的新帧**） |
| `+0x0C`–`+0x14` | `0xffffffff` ×3 |
| `+0x1C` | `param_1 + 0x6c` |
| `+0x24` | `[msg+0x58]` |
| `+0x28` | `[msg+0x5c]` |
| `+0x2c` | `[msg+0x5d]` |
| `+0x30` | `[msg+0x60]` |
| `+0x38` | 常量 `3` |

调用后 `FUN_1011db40()` 释放旧帧、`FUN_10053250(param_1)` 收尾——回调消费的是「新旧帧对」，
与「把本包应用到实体系统」的职责吻合。

### 5.2 未证

`.rdata` 中**唯一**出现 `0x101846C0` 指针的位置是 `0x10389080`：

```
0x10389040: 0x10183420 0x10052140 0x10183590 0x10052180
0x10389050: 0x10182d80 0x10053180 0x10183750 0x10183770
0x10389060: 0x101837f0 0x10183720 0x101838a0 0x101838c0
0x10389070: 0x101838e0 0x10183900 0x10183a80 0x10183b10
0x10389080: 0x101846c0 0x10183bc0 0x10183880 0x10183ba0
0x10389090: 0x10185570 0x10055e30 0x100523b0 0x10053510
```

函数指针与 `0x1005xxxx` 调整 thunk 交替出现，符合多重继承 vtable 的形状，但**没有定位到 COL**
（`vtable[-1]`），因此：

- 不能计算 `0x10389080` 的槽位索引（因而不能把「+0x80 = 第 32 槽」当成已证事实）；
- 不能把该表直接等同为 `[this-8]` 指向的那张表（`FUN_101846C0` 自身所在的表 ≠ 它内部调用的表，
  这正是 review 强调的「函数所属类 ≠ 虚调用接收者类」）。

**下一步（唯一缺口）**：从 `0x10389080` 向前定位 `vtable[-1] = COL` → `COL+0xC = TypeDescriptor` →
`TD+8` 的类名；得到基址后读 `[base+0x80]` 目标函数，再判它是否消费实体索引。

## 6 结论等级与待测项

| 编号 | 命题 | 等级 |
|---|---|---|
| C1′ | `m_nMaxEntries` 的构造参数 = `num_edicts`，随分配增长 | **已证实** |
| C2′ | `+0xC` 单对象写一次、不重赋值（N2 §14.4 维持） | 已证实 |
| C3 | `frame+0x118` 只在 ctor 赋值；发送端只读 | **已证实** |
| C4 | 接收端 `+0x54` 只用于分配，不进 §4 迭代 | 已证实 |
| C5 | `num_edicts` 可达 2048 ⇒ 现有 11 位字段值域溢出 | **未测**（需运行时探针） |
| C6 | delta 实体编号的真实解码上界 | **未测**（`FUN_10119370` 及上游） |
| C7 | `[[edi-8]+0x80]` 的类归属与槽位目标 | **未证**（缺 COL） |
| C8 | `max_edicts`（`0x10645770`）的写入点与常数 | **未定位**（本轮 8 处引用均为读） |

对 `13/13` 的立场：**仍不升级为已证实方案**。但现在可以给出更硬的表述：

$$
N_{\max} = \text{max\_edicts},\qquad
w_{\max} = \lceil \log_2(N_{\max}+1) \rceil,\qquad
U_{\max} \le 2048 \;(\text{§4 位图宽度})
$$

`U_max = 2048` 是本轮唯一被证到的上界；`N_max` 还差 C5/C8 两个点。

## 7 复现

```bash
# 1) 确认镜像
python3 tools/check_artifacts.py            # engine.dll: OK

# 2) 本轮用到的 REA 调用（地址为 VA）
#   open_binary(engine.dll, provider=ghidra)
#   xrefs(0x1064576C)                       -> 17 refs，唯一写点 0x101E02F1
#   procedure_pseudo_code(0x101E0170)       -> ED_Alloc
#   procedure_pseudo_code(0x101254B0)       -> SendClientMessages
#   procedure_pseudo_code(0x1011D900)       -> 快照构建（容量 = [0x1064576C]）
#   procedure_pseudo_code(0x101846C0)       -> 接收端 frame 安装 + vtable 调用
#   procedure_pseudo_code(0x10093E20)       -> 帧构造器（+0x118 = 快照）
#   procedure_pseudo_code(0x10093C80)       -> 按 tick 查找帧
#   procedure_pseudo_code(0x101196C0)       -> 掩码迭代
#   procedure_pseudo_code(0x1004E310)       -> FindNextSetBit(0x800)
#   read_bytes(0x10389040, 96)              -> .rdata 函数指针表
```

## 8 与 N2 的关系

- **撤回**：N2 §14.4 的推论「容量不随用量变化」——写一次成立，但参数本身是动态的；
- **保留**：N2 §15 的接收端判定（`+0x54` 只用于分配）、§13 的 32 位回填区机制、§11.3 的
  `bCheckRange` 失效；
- **新增**：`ED_Alloc` → `num_edicts` → 快照容量的完整链路；接收端 2048 位掩码边界；
  发送端帧的 tick 查找语义。
