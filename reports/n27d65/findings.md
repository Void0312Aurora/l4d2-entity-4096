# N27-D65 真实高索引负载、客户端同步与模组兼容性验证

日期：2026-10-27。测试只使用 `/home/void0312/l4d2_test/d65` 下的私有副本和独立端口；Valve 原始安装没有被改写。原始日志、进程元数据和内存快照保存在 `/home/void0312/l4d2_test/runs/d65`，仓库只提交轻量脚本、报告和摘要。

本轮的核心 P0 结果是通过的。扩容服务端在真实游戏连接和 Proton 客户端下，按实际分配索引完成 16、64、128、256、512 个网络实体的创建、六次确定性坐标更新、删除和正常分配器复用。512 档中实体索引从 2048 起，实际分配器产生的空洞被保留为实际索引清单，而不是把连续区间当作通过条件。删除目标的客户端槽位归零，旧引用失效，重建后的内部 serial 增加 1，客户端 serial 与服务器网络 serial 的低 10 位一致。每个阶段均检查实体指针、edict 反向指针、class/RTTI、句柄、free-list、sky-camera 和 587 个重定位字。

Proton 客户端直接观察到高索引对象。客户端更新采样包含 `observation_tick`，并与 Frida 的 `WriteDeltaEntities` tick 做了近邻比较；一次代表性采样为客户端 1660、服务端观察 1663。4095 使用独立边界实验：通过正常分配器把高水位推进到 4095，同时保留约 1000 个网络槽位；该对象完成客户端创建、六次更新、删除和再次分配。SDKHooks 兼容副本同时记录了 4095 的 `OnEntityCreated` 和 `SpawnPost`，不是通过直接写实体表实现。

在 512 个高索引对象存活期间，合法 `ZSpawn` 逐类生成 Hunter、Spitter、Smoker、Boomer、Charger、Jockey。每一类都取得了预期模型、玩家型感染者槽位和健康值，先记录 10 点伤害，再执行致死伤害；VScript 事件回调记录了 `player_hurt` 和 `player_death`。这证明的是高索引负载与正常特殊感染者路径并发，特殊感染者自身仍使用低索引 player 槽位。

按正确的私有启动顺序（在首张地图激活前设置 LAN 模式）完成了 `c1m1_hotel → c1m2_streets`。客户端重新进入 active，旧脚本对象被清理，换图后重新建立 2048–2063 的 16 个对象并完成客户端同步。早先两个换图崩溃现场落在 `CSteamWorksGameStatsUploader::GetInterface`；原版服务端在相同重连路径也复现了失效 Steam 接口指针，因此它们被归类为实验启动顺序/Steam 统计生命周期问题，不能作为扩容实体表缺陷。修正启动顺序后的真实换图证据已单独保存。

模组对照给出了一个明确的兼容边界。官方 SourceMod 核心在扩容引擎上可以加载，但其高索引实体引用 API 返回无效索引；未修改 SDKHooks 在读取旧的 Linux `EntityListeners=65572` 时于 `CUtlVector::InsertBefore` 崩溃。独立兼容构建只改 SDK 头文件的 `MAX_EDICT_BITS 11 → 12`，保留原有 15-bit 内部 serial 语义，并把 SDKHooks 的 Linux gamedata 偏移改为 131108。该副本中 SourceMod 核心、SDKTools、SDKHooks 及 D65 探针加载成功，2047/2048/2049 引用往返正确，4095 创建和生成回调也能运行。这个结论只覆盖已测试的组件和 API，不扩展到其他原生扩展。

`WIRE_SERIAL_WRAP`、`INTERNAL_SERIAL_WRAP`、双 Steam 客户端并发和长时间 soak 没有执行，报告中保持 `NOT_TESTED`。4095 结果也不等同于占满 4096 个网络槽位。完整机器可读断言见 [validation.json](validation.json)，代表性实体台账见 [entity-ledger.json](entity-ledger.json)。证据检查器为 [check_d65_evidence.py](../../tools/linux/check_d65_evidence.py)，动态工具和脚本位于 `tools/linux/` 与 `tools/sourcemod/`。
