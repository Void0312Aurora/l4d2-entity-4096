# N27-D1：完整补丁镜像构建与静态/装载验收

> 原版基线 sha256 `5fa15f28…309b7`。D1 镜像只做结构迁移（帧、栈位图、
> 客户端基线位图指针化），**不含 N26 的 4096 capacity 补丁**。

## 1 构建分层

| 脚本 | 职责 |
|---|---|
| `tools/linux/build_n27_frame.py` | D1-A：F1/F2/F3 + S1/S2/S3 + 212 条 EBP 位移 |
| `tools/linux/build_n27_full.py` | D1-B/C：在 D1-A 上应用 C1/C3、注入构造/析构桩、扩展 ELF |

D1-A 产物 `/tmp/n27/engine_srv_n27a.so`：`changed_bytes=284`。
D1-C 产物 `/tmp/n27/engine_srv_n27d1.so`。

## 2 ELF 代码桩：不复制 TEXTREL 指令

原始析构入口 `0xEB2F0` 的 `mov eax,[0x2A0070]` 带 `R_386_RELATIVE`
（该 DSO 有 TEXTREL），直接复制机器码会失去重定位。采用**入口钩子**：

```
EB2F0: E9 rel32        jmp dtor_stub
EB2F5: 83 EC 10        sub esp,0x10   （原位保留）
EB2FB: A1 70 00 2A 00  mov eax,[0x2A0070]  （原位保留，重定位不动）
```

桩内重放 `push ebp; mov ebp,esp; push esi; push ebx`，从 `[ebp+8]` 取 `this`，
释放后 `jmp 0xEB2F5`，让原 `sub esp,0x10` 与后续 TEXTREL 指令照常执行。

构造钩子 `0xEB3F3` 替换 6 字节 `lea edx,[ebx+0x10C]`：

```
push 0x200
call malloc@plt (0x817C0)
add esp,4
mov [ebx+0x10C],eax
mov edx,eax
mov ecx,0x80
xor eax,eax
ret
```

随后原 `mov edi,edx` + `rep stosd` 以 `EAX=0`、`ECX=0x80` 清零 512 字节。
分配/释放使用 `malloc/free` 的 PLT 入口，不引入新的文本重定位；
`0xEB3E3` 的 `mov ecx,0x40` 同时改为 `0x80`（作为二重保障）。

## 3 新代码段与 NOTE 迁移

`.text` 内无 ≥64 字节填充，因此追加独立段：

| 项 | 值 |
|---|---|
| 文件偏移 | `0x3DE000` |
| 虚拟地址 | `0x400000` |
| 大小 | `0x47` |
| 权限 | `R E` |
| Program header | 第 9 个 `PT_LOAD` |

原 `PT_NOTE` 从 `0x134` 移到文件尾 `0x3DE048 / 0x400048`，空出的
phdr 槽位写入新 `PT_LOAD`；第二个 `LOAD` 保持原始 `filesz/memsz/RW`，
避免把 `.bss` 当成文件数据映射（首版曾因此早崩）。

## 4 静态门禁结果

```
PASS: pristine bytes, spans, frame/stack coverage all consistent
counts: {'below_bitmap_shift': 212, 'bitmap_base': 3, 'above_bitmap_keep': 24, 'arg_keep': 23}
explicit spans: 42 frame: 47 stack: 262

PASS: no residual old EBP displacement, nine 0xFFF bounds, 0x230 base
```

桩反汇编确认：`malloc@plt=0x817C0`、`free@plt=0x81800`、
`je` 跳过释放后仍执行 `jmp 0xEB2F5`。

## 5 装载与初始化验收（D1-C）

隔离目录启动后：

```
---- Host_NewGame ----
Host_NewGame on map c1m1_hotel
num_edicts=1528 max_edicts=2048 pEdicts=0xdd672020
```

运行期映射确认新段已装载：

```
e85ff000-e8600000 r-xp 003de000 /tmp/n27run/bin/engine_srv.so
```

（engine base `0xe81ff000`，即 `base+0x400000`。）

## 6 尚未验证

- 客户端构造/析构桩尚未被真实客户端触发（本轮无客户端连接）；
- `ProcessBaselineAck` 指针扫描、baseline ack、快照发送未做运行回归；
- bit 2047/2048/4095 边界测试未开始；
- D1 镜像不含 4096 capacity，`max_edicts` 仍为 2048，符合预期。

## 7 下一步 D2

1. 用已打通的 Proton 原版客户端连接该 D1 服务端（2048 容量下），
   验证客户端创建、快照、baseline ack、断线重连；
2. 在暂停进程中检查客户端 `+0x20C` 借用位图指针与 0x200 清零；
3. 通过后合并 N26 capacity 补丁做 D2-C 的高索引位图边界测试。
