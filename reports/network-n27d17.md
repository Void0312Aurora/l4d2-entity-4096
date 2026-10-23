# N27-D17：调用链已确认，差异在 sub_101BBCF0 内部更早处

## 1 调用者歧义已解决

用入口 `[esp]` 返回地址连接各层：

| 函数 | 入口 `[esp]` 返回地址 | 调用者 |
|---|---|---|
| `sub_101CDDF0` | `0x79F25985`（RVA 0x125985） | 更高层 |
| `sub_101BCA20` | `0x79FCE177`（RVA 0x1CE177） | `sub_101CDDF0` |
| `sub_101BC800` | `0x79FBCFA8`（RVA 0x1BCFA8） | `sub_101BCA20` |
| `sub_101BBCF0` | `0x79FBCFFF`（RVA 0x1BCFFF） | `sub_101BC800` |
| `sub_10056E60` | `0x79FBC303`（RVA 0x1BC303） | `sub_101BBCF0` |

所以 `sub_10056E60` 的**直接调用者**是 `sub_101BBCF0`，不是
`sub_101BC800`；D16 栈回溯里的 `#1 0x1BC8F2` 是上一层的返回地址。

完整链：

```
sub_101CDDF0 -> sub_101BCA20 -> sub_101BC800 -> sub_101BBCF0 -> sub_10056E60
```

## 2 FULL 后入口对照

| 位置 | 原版 | frameonly |
|---|---|---|
| CDDF0 入口 | 有 | 有 |
| BCA20 入口 | 有 | 有 |
| BC800 入口 | 有 | 有 |
| BBCF0 入口 | 有 | 有 |
| E56E60 入口 | 22 | **0** |

frameonly 已经进入 `sub_101BBCF0`，但没有进入 `sub_10056E60`。

## 3 条件点检查

`sub_101BBCF0` 内调用前的关键分支：

```
0x1BC2E7 mov ecx, edi
0x1BC2E9 call sub_101B5FB0
0x1BC2EE test al, al
0x1BC2F0 jz loc_101BC52E      ; al==0 时跳过虚调用
...
0x1BC301 call eax             ; 调用 sub_10056E60
```

在 `0x1BC2F0` 设断点后，frameonly 在 FULL 后**没有命中该指令**。
说明差异不在“`test al,al` 的结果”，而是执行流在到达该指令之前就已经
从 `sub_101BBCF0` 更早的位置离开。

## 4 结论

- 调用链不再是歧义；
- 首个控制流差异位于 `sub_101BBCF0` 内部、`0x1BC2F0` 之前；
- 下一步应在 `sub_101BBCF0` 内按基本块/早期返回点设少量断点，
  找原版到达、frameonly 未到达的第一条指令，而不是继续看虚调用目标。

## 5 下一步

1. 在 `sub_101BBCF0` 的早期分支目标（如 `loc_101BC52E` 及函数开头几条
   `call/test/jz`）设断点；
2. 原版与 frameonly 各跑一次，找第一个“原版命中、frameonly 未命中”的块；
3. 对该块的判断操作数做值对照。
