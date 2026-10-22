# N10：`SV_SpawnServer` 的直接调用点已找到 —— 别名闭合

> 纠正 N9 的扫描方法（VA = ImageBase + 节 RVA + 偏移，此前误把节头 RVA 当 VA），
> 全 `.text` 反查 `E8` 得到 **2 个直接调用点**，两处都在调用前紧邻 `MOV ECX,0x10645558`。
> 容量别名由此闭合；`capacity_imm` 恢复 `verified: true`（覆盖级别 1）。

## 0 结论

| 命题 | 结果 |
|---|---|
| `call 0x10123B20` 的直接调用点 | **2 处**：`0x1018D239`、`0x1018ECAB` |
| 调用时 `ECX` | 两处均为 `MOV ECX,0x10645558`，且与 `CALL` 之间无其他 `CALL` |
| `SV_SpawnServer` 的 `this` | **`0x10645558`**（正常初始化路径） |
| `[this+0x218]` | **= `[0x10645770]`**（`0x10645558 + 0x218`） |
| `capacity_imm` | **恢复 `verified:true`**，覆盖范围=「正常 spawn 路径」（级别 1） |
| 虚表/thunk 路径 | 对这两个调用点不适用；完整覆盖仍需级别 2 |

## 1 方法修正

N9 的扫描把节头里的 `VirtualAddress`（RVA）直接当成了 VA，导致 `E8` 目标计算与绝对指针搜索
全部落在错误地址上。正确关系是：

$$ \mathrm{VA} = \mathrm{ImageBase} + \mathrm{SectionRVA} + \mathrm{offset} $$

按此重算：`.text` RVA `0x1000`、`ImageBase` `0x10000000`，对每个 `E8 rel32` 校验
`(va+5+rel) == 0x10123B20`，得到 2 个命中；全镜像 dword `= 0x10123B20` 仍为 0 命中。

## 2 调用点 A：`0x1018D239`

调用前 96 字节的尾部：

```
... 8b bd d8 fe ff ff   MOV EDI,[EBP-0x128]
    57                  PUSH EDI
    8d 4d 9c            LEA  ECX,[EBP-0x64]
    51                  PUSH ECX
    b9 58 55 64 10      MOV  ECX,0x10645558        ; <<< this = sv
    e8 e2 68 f9 ff      CALL 0x10123B20            ; SV_SpawnServer
```

- `B9` 位于调用前 **10 字节**，`E8` 位于调用前 **5 字节**，两者紧邻；
- 最近的更早一次 `CALL` 在 **调用前 26 字节**（`0x101686A0`），位于 `B9` 之前，
  因此不存在「中间函数改 `ECX`」的问题；
- 目标校验：`0x1018D23E - 0x6971E = 0x10123B20`。

## 3 调用点 B：`0x1018ECAB`

```
... 6a 00               PUSH 0
    56                  PUSH ESI
    b9 58 55 64 10      MOV  ECX,0x10645558        ; <<< this = sv
    e8 70 4e f9 ff      CALL 0x10123B20            ; SV_SpawnServer
```

- `B9` 在调用前 **10 字节**，`E8` 在调用前 **5 字节**；
- 更早一次 `CALL`（`0x10283300`）在 **调用前 18 字节**，同样位于 `B9` 之前；
- 目标校验：`0x1018ECB0 - 0x6B190 = 0x10123B20`。

两处形态一致：**把 `sv` 基址装进 `ECX`，压入 2 个参数，直接 `CALL`**，与 C++ 成员函数的
`this`-call 完全吻合。

## 4 别名链闭合

```
CALL 0x10123B20   (ECX = 0x10645558)
  └─ FUN_10123B20 序言: MOV ESI,ECX          ; ESI = 0x10645558
       └─ 0x10123DA2: MOV EAX,0x800
       └─ 0x10123DA7: MOV [ESI+0x218],EAX    ; = [0x10645770] = sv.max_edicts
       └─ 0x10123DAD: MOV [0x10429308],EAX
       └─ 之后: alloc([0x10645770] << 4)      ; edicts
       └─ 之后: alloc([0x10645770] * 4)       ; edictchangeinfo
```

因此把立即数 `0x800` 改成 `0x1000`，两笔分配自动得到 4096；`capacity_imm` 的原始意图成立，
N6 提出的「容量传播缺口」由对象别名解释，**不是缺陷**。

## 5 验证覆盖范围（写进 manifest）

- **级别 1（已完成）**：正常初始化路径上存在真实调用点，`ECX=0x10645558`，容量写入在首次分配之前；
- **级别 2（未完成）**：全部可达调用路径的枚举，以及初始化之后是否存在其他写覆盖
  `[0x10645770]`。当前证据：该全局 8 处引用全为读，唯一写就是本处（经 `ESI` 相对寻址，
  绝对 xref 不可见）。

## 6 对 N9 结论的更正

N9 写「`SV_SpawnServer` 不是虚函数、不在任何分发表」过强。正确表述：

- **已证实**：镜像内没有任何直接保存 `0x10123B20` 的绝对函数指针；
- **高度可信**：正常路径通过直接 `E8` 调用（本轮已找到 2 处）；
- **未严格排除**：经调整 thunk（`add ecx,N; jmp 0x10123B20`）或其他间接入口的调用。
  本轮找到了直接调用点，因此不再需要为别名去扫 thunk；但「不存在其他入口」仍未证明。

## 7 复现

```bash
# 纯标准库（无需 pefile/capstone）
python3 - <<'PY'
import struct, pathlib
b = pathlib.Path(".../engine.dll").read_bytes()
e = struct.unpack_from("<I", b, 0x3C)[0]
nsec = struct.unpack_from("<H", b, e+6)[0]; optsz = struct.unpack_from("<H", b, e+20)[0]
ib = struct.unpack_from("<I", b, e+24+28)[0]; so = e+24+optsz
for i in range(nsec):
    o = so+i*40
    vsz, rva, rawsz, rp = struct.unpack_from("<IIII", b, o+8)
    for j in range(rawsz-4):
        if b[rp+j] == 0xE8:
            va = ib + rva + j
            if (va+5+struct.unpack_from("<i", b, rp+j+1)[0]) & 0xFFFFFFFF == 0x10123B20:
                print(hex(va))
PY
# -> 0x1018d239  0x1018ecab
```
