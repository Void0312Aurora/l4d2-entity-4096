# N27-D63：后续系统级稳定性与兼容性验证

日期：2026-10-26。接续 [N27-D62](../n27d62/findings.md)，使用既有隔离 Linux 服务端和 Proton 客户端副本。原版 Steam 游戏文件未修改。

## 结论

D62 回归保持 **24 PASS / 5 NOT_TESTED**。D63 当前结果为 **3 PASS / 1 FAIL / 7 NOT_TESTED**。单客户端在 2048–2063 创建并保留 16 个高索引实体，完成 30 次约 1 Hz 的服务端更新；额外一次服务端位置更新后，客户端同一批 16 个槽位均观察到 Z 坐标增加 32。这个结果证明了该受控负载下的创建、存活和一次网络更新，不表示多人兼容、4096 个实体容量或长时间稳定性。

失败项是高索引 Hunter 生成：`NUM_FOR_EDICT: bad pointer`，GDB 栈经过 `CVEngineServer::SetFakeClientConVarValue` 和 `BossZombiePlayerBot::Spawn`。另跑了独立普通感染者控制组：在索引 2048 创建成功，随后服务器仍能返回地图和玩家状态；该受控进程之后由测试端主动停止。Hunter 日志中也有普通感染者创建标记，但它与 Hunter 尝试处于同一进程，不能单独视为控制组。现有证据支持普通 infected 路径与该 Hunter 失败路径表现不同，不足以定位根因或推广到所有特殊感染者；没有据此修改二进制。

双客户端联机按用户要求暂缓；本轮没有邀请朋友连接。Windows 独立副本加入包已在本地准备：[L4D2-4096-D63-Windows.zip](../../out/L4D2-4096-D63-Windows.zip)，SHA256 `0104575899fbd0ea043f53c20e16f251988b53f23f2b76200f348ea3836597b9`；本轮没有交付或实际使用。D62 断线重连结果仍有效，它属于单客户端循环，不替代 D63 多客户端重连验收。

## D63 验收矩阵

| 项目 | 结果 | 证据与边界 |
|---|---|---|
| 多客户端同时在线 | NOT_TESTED | 按用户要求暂缓；不能用服务器 BOT 或单客户端代替 |
| 多客户端高索引同步 | NOT_TESTED | 没有第二个真实客户端 |
| 多客户端断线重连 | NOT_TESTED | 没有第二个真实客户端 |
| 实际游戏实体路径 | FAIL | 独立普通 infected 控制组在 2048 创建成功且随后服务器可响应状态；Hunter 在 `NUM_FOR_EDICT` 报 bad pointer 后服务端崩溃。独立控制组不能消除 Hunter 路径失败 |
| 单客户端实体压力 | PASS | 16 个真实 `C_DynamicProp` 位于 2048–2063；30 次 1 Hz 更新，约 29.0 秒；客户端在另一条受控连接中观察到一次全体 Z+32 更新 |
| 网络 serial 回绕 | NOT_TESTED | 未执行 10-bit wire serial 回绕测试 |
| 内部 serial 回绕 | NOT_TESTED | 未执行 15-bit 内部 serial 回绕测试 |
| 无效索引边界 | PASS | VScript 查询 0、1、2048、4096、4097、8191、-1；无效及越界返回 NULL；4095 的真实实体生命周期由 D62 客户端证据覆盖。此项不构造任意陈旧 `CBaseHandle` |
| 句柄候选静态审计 | PASS（静态） | 8184/8184 候选均有指令字节及候选类别；人工查看 5 个重点函数，另保留 1 个空壳提取。动态执行为 0/8184，边界执行为 0/8184 |
| 地图切换 | NOT_TESTED | 未执行跨图测试 |
| 长时间运行 | NOT_TESTED | 未执行长时间 soak |

压力阶段 31 个进程指标样本中，服务器 RSS 从 194312 KiB 到 194324 KiB。按 UDP 27105 过滤的 loopback 抓包在约 31.9 秒内观察到服务端入站 959 个包/44122 UDP 负载字节、出站 639 个包/49959 UDP 负载字节。抓包和系统指标只描述这个单客户端本地阶段。

## Hunter 失败证据

普通 infected 独立控制组记录了 `D63_INFECTED_ONLY_CREATED idx=2048 valid=true`；之后 `status` 返回测试地图 `c1m1_hotel`、0 名玩家，进程在测试端主动停止前仍可查询。Hunter 运行也曾记录普通 infected 创建标记，但该标记发生在同一 Hunter 测试会话中；Hunter 尝试随后出现 `NUM_FOR_EDICT: bad pointer`，GDB 栈包含 `CVEngineServer::SetFakeClientConVarValue(edict_t*, ...)`、`BossZombiePlayerBot::Spawn()` 和 `DispatchSpawn`。这证明当前候选构建中的该 Hunter 路径失败，不能定位引擎一般性 edict 映射根因，也不证明所有特殊感染者都失败。

## 构建与环境身份

测试运行环境为 Linux Dedicated，服务器状态报告版本 `2.2.4.3 9309`，地图 `c1m1_hotel`。D63 压力和普通感染者控制组使用同一隔离副本引擎，`engine_srv.so` SHA256 为 `79b3966bd9752394beb2f29f0cf0244acedddde15112b4c037535994ecaf8014`；扩容 `server_srv.so` 为 `8575ed52f39b7c85ea776c83960e3ac08f07521b503109e639acdee1e53d5222`。压力移动观察客户端为 Proton 副本，已加载的 `left4dead2.exe`、`engine.dll`、`client.dll` 哈希与机器结果中的构建身份一致；这仍是单客户端验证。

## 静态句柄审计边界

8184 个指令候选按所在函数名和候选指令类型整理为风险类别；`other_unknown` 的 4226 项保留为未知，没有按猜测归类成已理解。分类不是语义或运行覆盖证明。检查了五个重点伪代码函数：实体槽添加、移除、析构、句柄设置和当前 sky-camera 查询；第六个提取是接口空壳。没有把这些静态内容表述为 8184 个运行时消费者已经过测。

## D62 回归和可复现检查

机器可读结果在 [validation.json](validation.json)。校验器通过 `--d63-root` 追加 D63 结果；D62 顶层断言与原 [D62 验证文件](../n27d62/validation.json) 保持一致。由于 Hunter 为真实失败，D63 部分按预期包含一个 `FAIL`；校验器进程退出码仍为 0，因为顶层 D62 基线没有失败。

复算命令：

```bash
python3 tools/linux/classify_handle_sites.py \
  --ida /home/void0312/l4d2_test/runs/d63/handle-instructions-ida.json \
  --out /home/void0312/l4d2_test/runs/d63/handle-audit.json
python3 tools/linux/check_d62_evidence.py /home/void0312/l4d2_test/runs/d62 \
  --native --d63-root /home/void0312/l4d2_test/runs/d63 \
  --out reports/n27d63/validation.json
```

该命令会因已记录的 Hunter 路径 `FAIL` 返回退出码 1；这表示验收发现真实失败，机器结果仍会完整写出，不代表校验器运行异常。D62 顶层基线仍为 24 项通过、5 项未测。

原始 D63 日志、内存快照、进程指标、抓包和 GDB 输出保留在
`/home/void0312/l4d2_test/runs/d63/`，未将游戏二进制或大型运行数据放入仓库。
