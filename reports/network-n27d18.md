# N27-D18：修正计数后，分支条件两边都通过，差异在虚调用目标

## 1 P0 观测缺陷已修正

原 `COND.n` 统计的是进程启动以来的累计命中，FULL 前命中 8 次后，FULL 后
不再输出日志。D17 的“frameonly 未到达 0x1BC2F0”因此不成立。

新探针为每个地址分别维护 `total` 与 `post`，并在 `post<=8` 时输出
`post/total/al/eflags/edi`，避免抽样限制被误读为零命中。

## 2 四个探针

| RVA | 记录 |
|---|---|
| `0x1BC2E9` | 调用条件函数前的 `EDI` |
| `0x1BC2EE` | 返回后的 `AL` |
| `0x1BC2F0` | `jz` 前的 `AL`、`EFLAGS` |
| `0x1BC301` | 最终虚调用前的 `EAX`（目标）、`EDX`、`ESI` |

## 3 frameonly 结果

```
PROBE callCond  post=1 total=54  edi=114501184
PROBE afterCond post=1 total=54  al=1
PROBE jzCond    post=1 total=54  al=1 eflags=2097666
PROBE finalCall post=1 total=54  eax=0x79E4E510 edi=114501184
...
PROBE finalCall post=347 total=400
```

即：

- 条件函数被调用；
- 返回 `AL=1`；
- `jz` 不跳转；
- **最终虚调用确实执行**；
- 但 `sub_10056E60` 入口仍是 0 次。

frameonly 观察到的虚调用目标包括：

```
0x79E4E510
0x79E53FE0
```

都不是 `0x79E56E60`。

## 4 原版结果

同样的四个探针在 FULL 后都命中，`AL=1`，且 `sub_10056E60` 入口命中
（本轮日志前 3 次，D16 为 22 次）。原版观察到的目标还包括：

```
0x79E4EE80
```

说明这个 `call eax` 是一个多目标虚调用点，`sub_10056E60` 只是原版会选中的
目标之一。

## 5 结论

D17 的“在 0x1BC2F0 之前提前离开 `sub_101BBCF0`”应撤销。实际是：

> 两边都通过条件并执行虚调用，但 frameonly 的虚调用目标集合里没有
> `sub_10056E60`。

下一步不是继续扫分支，而是记录完整的 `EAX` 目标直方图以及 `EDX`（虚表）、
`ESI`（对象）对应关系，确认：

1. `sub_10056E60` 在哪个虚表/对象类型下被选中；
2. frameonly 的同一对象为什么走另一目标；
3. 该对象状态是否来自客户端首次快照/实体更新。
