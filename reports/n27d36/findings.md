# N27-D36：高索引实体构造尝试（未达成）

## 1 已完成

D35 的 13-bit 双端低索引联机已通过：

- 客户端 `engine.dll` 13-bit：`b143902702ec7affce6adb33df461b008debe192df77b3b928191c56aa71f790`
- 服务端 13-bit 4096：`8b81e755e2fb42e9788f8671bf8a35d2c05ce6dbb8432f4d4cb8143204ee905f`
- 地图 `c1m1_hotel`，无 `failed reading svc_PacketEntities`。

## 2 高索引构造尝试

目标：在不篡改 `num_edicts` 的前提下生成 index ≥2048 的真实实体。

尝试路径：

1. 服务端 console `ent_create info_target`
   - 命令存在，但描述为“where the player is looking”，无玩家视角时不创建。
2. VScript `SpawnEntityFromTable`
   - 服务端 console 内 `script printl("...")` 可用；
   - `script_execute d36_spawn` 在无客户端时成功打印 4 次 `D36_SPAWNED`；
   - 但在 client 连接后的 FIFO 命令时序中，批量脚本没有产生 `D36_BATCH` 输出，
     无法确认实体是否创建。
3. `sv_hibernate_when_empty 0` 服务端-only 测试出现一次启动期 segfault，
   不能作为稳定路径。

因此**没有**得到 index ≥2048 的实体，也没有做高索引网络验证。

## 3 环境状态

- 客户端 `engine.dll` 已恢复原版：
  `8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86`
- 没有残留测试服务器。
- 没有修改生产目录。

## 4 下一步

1. 用服务端-only + `sv_hibernate_when_empty 0`（确认稳定版本）执行 VScript 批量生成；
2. 或写一个最小 VScript 循环，每次 50 个，打印 `e.entindex()`，确认跨 2048；
3. 确认服务端快照包含高索引实体；
4. 合并客户端 13-bit 与 `engine.4096.n4s.dll` 存储补丁，再做客户端解析验证。

在没有真实实体索引证据前，不宣称跨 2048 成功。
