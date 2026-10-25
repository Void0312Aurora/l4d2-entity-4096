# N27-D44：修复 TakeTickSnapshot 2048 栈数组溢出；快照崩溃前移

## 1 根因

D43 core 中 `CFrameSnapshotManager::TakeTickSnapshot+340` 的 EAX 为
`0x081F081E`，不是普通空指针，而是被实体索引写坏的栈数据。

反汇编显示：

```
1E2718  sub esp,0x102C
1E27D5  mov %si,-0x1018(%ebp,%eax,2)   ; uint16 实体索引栈数组
```

`-0x1018` 到 `ebp` 只有 `0x1018` 字节 = **2060 个 uint16 槽位**。
当 `sv.num_edicts` 超过 2060，索引写入越过数组，覆盖保存的寄存器、
返回地址和参数，最终在 `mov 0x40B0(%eax),%esi` 处崩溃。

## 2 修复

把帧从 `0x102C` 扩到 `0x302C`，数组移到 `ebp-0x3018`（可容纳 4096 个
uint16 + 余量）：

```
1E2718  81 EC 2C 10 00 00 -> 2C 30 00 00
1E27D5  66 89 B4 45 E8 EF FF FF -> E8 CF FF FF
1E2827  8D 8D E8 EF FF FF -> E8 CF FF FF
1E28B7  81 C4 2C 10 00 00 -> 2C 30 00 00
```

产物：

```
d0975da61fe8ae85e7dac0b489cd1e0deb48c4a5867e8cea498b760166ecfd5e
```

## 3 动态结果

双端（集成 engine + 原版 client.dll + v3 服务端）分批生成：

```
D37_BATCH min=1984 max=2047
D37_BATCH min=2048 max=2111
D37_BATCH min=2112 max=2175
...
D37_BATCH min=2688 max=2751
```

`TakeTickSnapshot` 不再在 2048 崩溃。

## 4 新的失败点

继续生成约 2700 个实体后崩溃，回溯在游戏 DLL：

```
server_srv.so GetPushawayEnts / AvoidPushawayProps
CCSPlayerMove::SetupMove
```

这是玩家移动时对大量同点实体的 push-away 处理，不是快照容量问题。
下一步应避免在同一点生成大量 filler（或使用非实体填充方式），并先只生成
目标实体附近的少量实体。

## 5 客户端

`client.4096.dll` 候选仍加载失败，已回退原版；集成 engine 低索引正控通过。
高索引客户端解析尚未验证。

## 6 环境

- `engine.dll` 恢复 `8a6d4680…`；
- `client.dll` 恢复 `c0a8e1e8…`；
- 无残留测试服务器。
