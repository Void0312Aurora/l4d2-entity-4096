# N27-D43：真实高索引分配成功，但 2048 快照路径崩溃

## 0 结论

服务端能真实分配超过 2048 的实体索引（最高观察到 2917），但一旦客户端连接并
生成快照，服务端在跨越 2048 时崩溃：

```
CFrameSnapshotManager::TakeTickSnapshot(int)+340
0x1E2864: mov 0x40B0(%eax),%esi
```

因此没有完成客户端高索引同步；这是服务端快照路径问题，不是 13-bit 客户端解析问题。

## 1 已建立的能力

- 13-bit 双端低索引联机：D35；
- 客户端 13-bit + 4096 存储集成 DLL：
  - `out/engine.4096.13bit.n4s.dll`
  - `sha256 37ccc4caf31fdc3e91d4b6c06a47ad5701bb1ea107f3e3fe77a1d114cf2e1fde`
  - PE checksum 与独立 pefile 一致；
- 集成 engine + 原版 client.dll 低索引进图成功；
- 服务端 VScript 可真实创建实体并读取 `GetEntityIndex()`：
  - 首批索引 402；
  - 分批 64 个可稳定增长。

## 2 高索引分配

服务端-only 分批生成，`info_target` 索引持续增长到：

```
D37_BATCH n=64 min=2854 max=2917
```

说明 4096 分配器本身可越过 2048。

## 3 崩溃点

客户端连接后，同一分批脚本在批次 `1982..2045` 之后崩溃：

```
D37_BATCH n=64 min=1982 max=2045
Segmentation fault (core dumped)
```

Core 回溯：

```
#0 CFrameSnapshotManager::TakeTickSnapshot(int)+340
   0x1E2864: mov 0x40B0(%eax),%esi
```

对应服务端 `engine_srv.so` VA `0x1E2864`。崩溃发生在下一批实体索引进入
2048+ 后创建快照时，而不是 VScript 分配本身。

## 4 已尝试的路线

- `ent_create`：需要玩家视角，服务端 console 不适用；
- VScript `SpawnEntityFromTable`：可用，并已实现分批与索引记录；
- 客户端 `client.4096.dll` 候选：加载即失败，已回退原版；
- 集成 engine DLL 低索引回归通过，高索引在服务端快照阶段崩溃。

## 5 未达成

- index ≥2048 的实体未进入客户端；
- 未验证高索引快照发送/客户端解析；
- 未做更新、删除、4095 边界。

## 6 下一步

1. 解析 `TakeTickSnapshot+340` 的 `0x40B0(%eax)` 对象与数组容量；
2. 检查 `CFrameSnapshotManager` 的实体列表/快照数组是否仍按 2048 分配；
3. 修复后重复本报告的分批脚本，直到客户端创建高索引实体；
4. 再合并客户端 `client.dll` 4096 补丁。

## 7 环境

- 客户端 `engine.dll` 已恢复 `8a6d4680…`；
- `client.dll` 已恢复 `c0a8e1e8…`；
- 无残留测试服务器。
