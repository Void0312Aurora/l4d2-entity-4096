# N7：`sv+0x218` 的写入是寄存器基址，`0x10645558` 别名假设被强支持

> 回应 review：`SV_SpawnServer` 的 `this+0x218` 很可能就是 `0x10645770`。本轮把写入指令的
> 基址寄存器、函数序言与全局单例寻址习惯都取到了字节级证据。结论：**假设成立的可能性很高，
> 但仍差最后一步——证明调用方传入的 `ECX == 0x10645558`**。因此 manifest 维持 `verified:false`，
> 同时把它从「补丁可能无效」改判为「待证别名」。

## 0 结论

| 命题 | 结果 |
|---|---|
| `in_ECX[0x86] = 0x800` 的真实指令 | `MOV ESI,ECX`（序言）→ `MOV [ESI+0x218],EAX`（`0x10123DA7`） |
| 基址寄存器 | **ESI = this**，不是绝对地址 |
| `0x10123DA2` 的 `0x800` 去向 | `[this+0x218]` 与 `[0x10429308]` |
| `this` 是否为 `0x10645558` | **强支持，未证明**（见 §3） |
| N6 的「补丁可能无效」 | 回落为「若别名成立则补丁正确」 |

## 1 写入指令的字节级形态

```
0x10123da0  ff d0                 CALL EAX
0x10123da2  b8 00 08 00 00        MOV  EAX,0x800
0x10123da7  89 86 18 02 00 00     MOV  [ESI+0x218],EAX     <<< 基址是 ESI
0x10123dad  a3 08 93 42 10        MOV  [0x10429308],EAX
0x10123db2  8b 16                 MOV  EDX,[ESI]
0x10123db4  8b 42 14              MOV  EAX,[EDX+0x14]
0x10123db7  8b ce                 MOV  ECX,ESI
0x10123db9  ff d0                 CALL EAX                  ; 虚调用，ECX=this
```

序言（`0x10123B20`）：

```
0x10123b20  55                    PUSH EBP
0x10123b21  8b ec                 MOV  EBP,ESP
0x10123b23  81 ec 80 02 00 00     SUB  ESP,0x280
0x10123b29  a1 98 dd 43 10        MOV  EAX,[0x1043dd98]     ; __security_cookie
0x10123b2e  33 c5                 XOR  EAX,EBP
0x10123b30  89 45 fc              MOV  [EBP-4],EAX
0x10123b33  8b 45 0c              MOV  EAX,[EBP+0xC]
0x10123b36  53 56 57              PUSH EBX; PUSH ESI; PUSH EDI
0x10123b39  8b 7d 08              MOV  EDI,[EBP+8]
0x10123b3c  8b f1                 MOV  ESI,ECX             <<< ESI = this
```

所以 `[ESI+0x218]` 就是 `this+0x218`，且该写入发生在**第一次 edict 分配之前**
（分配在 `0x10123e1a` 之后：`DAT_10645774 = alloc([0x10645770]<<4)`），时序符合
「容量必须先写、分配后读」的要求。

## 2 四个字段的算术完全对齐

设 `this = 0x10645558`，则：

| 字段 | VA | 相对 `0x10645558` | 已确认语义（N3） |
|---|---|---|---|
| `num_edicts` | `0x1064576C` | `+0x214` | `ED_Alloc` 唯一 `INC` |
| `max_edicts` | `0x10645770` | `+0x218` | 索引排他上界 |
| `edicts` | `0x10645774` | `+0x21C` | `i*0x10 + base` |
| `edictchangeinfo` | `0x10645778` | `+0x220` | `alloc(max*4)` |

四字段连续、差值精确，是「同一个 `sv` 结构体」的最自然解释。

## 3 全局单例寻址习惯的字节证据

`MOV ECX,0x10645558`（`B9 58 55 64 10`）在 `.text` 中**大量出现**（首页 20 条仍未穷尽，
搜索返回 `complete:false` 并带 cursor），例如：

```
0x10002805  b9 58 55 64 10        MOV ECX,0x10645558
0x1000280a  89 5d b8              MOV [EBP-0x48],EBX
...
```

这正是「这个全局对象的成员函数以 `this`-call 方式调用」的编译形态：先把单例地址装进 `ECX`，
再压参、`CALL`。`SV_SpawnServer` 也是这种成员函数。

**但这一步仍不是证明**：尚未抓到「某个调用点把 `ECX=0x10645558` 之后调用 `0x10123B20`」的
直接序列。`procedure_callers(0x10123B20)` 返回的两个地址（`0x1018CF90`、`0x1018EA70`）
落在 `INT3` 填充/函数尾部，不能作为有效调用点；需要用 `E8 rel32` 的目标反查来定位真正调用者。

## 4 因此对 N6 的修正

N6 的表述应收紧为：

> `capacity_imm` 修改的立即数写入的是 `this+0x218`；只有当 `SV_SpawnServer` 的 `this` 等于
> `0x10645558` 时，它才等价于写 `[0x10645770]`。截至目前，四字段算术与全局单例调用形态
> **强烈支持**该别名，但缺少最后一条调用点证据。

风险等级从「补丁可能无效」下调为「待证别名」；manifest 仍保持 `verified:false`，并在
`verification_note` 中记录别名假设与验证方法。

## 5 下一步（唯一待办）

1. 在 `.text` 中查找 `E8 rel32`，其 `rel` 指向 `0x10123B20`（即 `call SV_SpawnServer`）；
2. 对每个命中点，取前 8 字节，检查是否为 `B9 58 55 64 10`（`mov ecx, offset sv`）；
3. 命中即完成证明：`[this+0x218] == [0x10645770]`，`capacity_imm` 恢复为已验证，
   N6 的容量传播缺口随之关闭；
4. 若命中点的 `ECX` 来自其他寄存器/参数而非该常量，则 N6 的缺口维持，需要另找初始化写点。

## 6 复现

```bash
# REA 会话内
#   read_bytes(0x10123DA0, 40)   -> MOV EAX,0x800; MOV [ESI+0x218],EAX; MOV [0x10429308],EAX
#   read_bytes(0x10123B20, 48)   -> 序言 MOV ESI,ECX
#   search_bytes("B9 58 55 64 10") -> 大量命中，0x10645558 作为 this 使用
#   procedure_pseudo_code(0x10123B20) -> SVM_SpawnServer 中 sv+0x218 与两次 Hunk_Alloc
```
