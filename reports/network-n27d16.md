# N27-D16：frameonly 在 FULL 后甚至没有进入 sub_10056E60

## 1 断点地址核实

D15 的三个地址确实是 `call` 指令起点（`call eax`/`call edx`，2 字节），
与 D14 栈返回地址相差 2 字节吻合：

```
0x56E6B call eax   → 返回 0x56E6D
0x1EC292 call edx  → 返回 0x1EC294
0x0D32F6 call eax  → 返回 0x0D32F8
```

D15 的结论因此应收窄为“没有走到这些调用点”，而不是“函数完全没执行”。
本轮增加 `sub_10056E60` **入口**断点（RVA 0x56E60）并记录返回地址与栈回溯。

## 2 入口与调用点对照

| 镜像 | E56E60 入口（FULL 后） | E56E60 调用点 | E1EC1D0 调用点 | E0D3210 调用点 | 事件 |
|---|---|---|---|---|---|
| 原版 | 22 | 22 | 22 | 1 | 1 |
| frameonly | **0** | 0 | 0 | 0 | 0 |

frameonly 在 FULL 之后**连 `sub_10056E60` 入口都没有命中**，因此问题不在函数
内部条件，而在它的调用者。

## 3 原版调用者栈

```
#0 engine.dll 0x79E56E60  sub_10056E60 入口
#1 engine.dll 0x79FBC8F2  sub_101BC800 内
#2 engine.dll 0x79FBCFA8  sub_101BCA20 内
#3 engine.dll 0x79FCE177  sub_101CDDF0 内
返回地址 0x79FBC303（sub_101BBCF0 内，rc=0x1BC303）
```

对应 IDA 函数：

```
sub_101BBCF0
sub_101BC800
sub_101BCA20
sub_101CDDF0
```

## 4 结论

第一个已确认的差异点进一步前移：

> frameonly 在 FULL 之后没有执行到 `sub_10056E60` 的调用者路径。

下一步直接检查 `sub_101BBCF0` / `sub_101BC800` 中调用 `sub_10056E60` 的条件分支，
比较两个镜像进入该分支前的输入状态；不再继续向下分析三个被调函数。
