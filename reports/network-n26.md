# N26：Linux edict 存储与分配器的 4096 隔离运行动态验证

> 镜像：`engine_srv_both.so` / `engine_srv_p2only.so`，由
> `tools/linux/build_n26_capacity.py` 从原始 `engine_srv.so`
> （sha256 `5fa15f2820ab67b955ff227a20dbb3fda54d463f3799f33d71b6fd6f38e309b7`）
> 仅改两处 32 位立即数生成。原始安装文件在实验前后均为同一 SHA-256。

## 1 隔离方式

- 运行目录 `/tmp/n26run`：`srcds_linux` 与 `bin/engine_srv.so` 都是**实体文件副本**，
  其余库从原安装目录只读引用；
- 启动后由 `/proc/<pid>/maps` 确认实际加载
  `/tmp/n26run/bin/engine_srv.so`；
- 全程不连接客户端；B2 结束后直接 `kill` 实验进程，不让高索引实体进入正常 tick。

## 2 B1：`SpawnServer` 初始化（both）

加载路径与 SHA-256：

```
/tmp/n26run/bin/engine_srv.so  e738c71b6bb626cbadd6e6ae666160a21e14ffcb67c3b6eea7dd28e5db737398
```

gdb 实测（`c1m1_hotel` 加载完成后）：

| 字段 | 值 |
|---|---|
| `sv.num_edicts` (`+0x20C`) | 1528 |
| `sv.max_edicts` (`+0x210`) | **4096** |
| `sv.pEdicts` (`+0x214`) | `0xd9253020` |
| `sv.g_EdictFreeTime` (`+0x218`) | `0xd9263020`（= pEdicts + 0x10000） |
| 镜像全局 `0x3A7F50` | **4096** |
| `EDICT_NUM(2047)` | `0xd925b010` |
| `EDICT_NUM(2048)` | `0xd925b020`（越过旧边界，连续） |
| `EDICT_NUM(4095)` | `0xd9263010` = pEdicts + 0xFFF0 |

同一镜像的 Hunk 分配（gdb 断点 `Hunk_AllocName`，`both`）：

```
HUNK size=0x10000 name=edicts
HUNK size=0x4000  name=edictchangeinfo
```

即 4096×16 = 0x10000、4096×4 = 0x4000。

## 3 B2：真实 `ED_Alloc` 增长到 index 4095（both）

在同一隔离进程上暂停后，反复调用 `ED_Alloc(-1)`：

```
B2_START num=1528 max=4096 pEdicts=0xd9253020
GROWTH calls=3054 num=4096 max=4096 first_num_gt_2048=(1007, 2049)
SLOT4095 flags=0x0 freebit=0 serial=-1
EDICT_NUM_4095=0xd9263010
```

要点：

- 从 1528 增长到 4096 需要 4096−1528 = **2568** 次新槽分配，
  总调用 3054 次，因此有 3054−2568 = **486** 次走了空闲槽复用；
- 第 1007 次调用时 `num` 首次超过 2048（=2049），
  这 1007 次中已包含 486 次复用和 521 次新槽增长（1528+521=2049）；
- 第 3054 次分配后 `sv.num_edicts` 达到 **4096**；
- 最后一个新槽 `pEdicts + 4095*16` 的 `flags` 为 0（`FL_FREE` 位已清），
  说明 index 4095 已真实分配；
- 分配完成后立即 `kill`，未恢复主循环。

安全性观察：容量已满时（`num == max == 4096`）再调用一次会走到
`ED_Alloc: no free edicts` 的 `Error()` 路径，这是容量上限的预期行为，
不是内存越界。

## 4 `p2only` 对比（只改 `sv+0x210`）

SHA-256：`552b1a96cdc65d1a12e5272c288620c58bde53fced9299897dd5900028b5dbb5`

B1：

| 字段 | 值 |
|---|---|
| `max_edicts` | **4096** |
| 镜像 `0x3A7F50` | **2048**（保持原值） |
| `freeTime - pEdicts` | `0x10000` |
| `EDICT_NUM(4095)` | = pEdicts + 0xFFF0（有效） |

增长（只验证跨越旧边界）：

```
P2G_START num=1528 max=4096 mirror=2048
P2G calls=1005 num=2049 max=4096
```

结论：镜像全局 `0x3A7F50` 对 B1 与"分配越过 2048"不是必要条件；
但它的**读取方**尚未穷举，不能据此断言对后续所有功能无影响，保持 `unresolved`。

## 5 结论

隔离运行测试通过：

- `max_edicts = 4096`；
- `ED_Alloc` 能沿真实增长分支分配出 index 4095（`num_edicts` 实际到 4096）；
- 原始安装文件未被修改（SHA-256 与实验前一致）。

这证明 **Linux edict 存储与分配器的 4096 扩容在存储/分配层面成立**。

## 6 仍未完成（不得跳过）

- `CClientFrame` 内联位图仍为 2048 位，快照/帧结构尚未迁移；
- 迁移表 `data/linux/migration_sites.csv` 中的 `unresolved` 项仍待处理；
- 因此**不允许**让 >2048 实体进入快照或网络路径；本轮全程无客户端、无 tick 携带高索引实体。
