# N27-D66 发布候选工程化、边界验收与公开展示

日期：2026-10-27。D66 继续使用 build `23990068` 的隔离副本；Steam 原始安装未写入，仓库不提交 Valve 的完整二进制、凭据、核心转储或大型原始录像。

## 当前交付

D66 建立了面向外部用户的两套发布 manifest：`release/manifests/windows-client.json` 和 `release/manifests/linux-server.json`。manifest 只包含源文件身份、输出身份和旧/新字节差分。`tools/release/install.py` 在写入前验证源 SHA-256，在临时副本中应用差分并验证输出哈希，然后原子替换目标；目标带有私有副本标记和 receipt，`restore` 可以恢复备份或删除本次新建副本。Windows/Proton 安装、Linux 专用服务器安装、干跑、哈希失败拒绝和最小 fixture 恢复已经执行。

`tools/release/check_rc.py` 把构建身份、manifest、D65 证据完整性、原始生命周期语义、仓库二进制门禁和未测试范围分开报告。D65 证据检查和独立原始快照复算均返回 `PASS`，整体发布判断保持 `PARTIALLY_READY`。

## 边界试验

D66 新增 `tools/linux/run_d66_serial.py` 和 `tools/linux/vscript/d66_wrap.nut`。它们通过普通分配器固定一个高索引槽位，等待既有 free-time 门限后反复删除/重建，不直接写索引或 serial，围绕网络 10-bit serial 的归零和 1024 周期重复采集服务端/客户端快照。内部 15-bit serial 回绕不以公式替代端到端结果。

独立的 `tools/release/check_serial_arithmetic.py` 已生成 [serial-arithmetic.json](serial-arithmetic.json)，只验证编码公式并明确 `runtime_claim: NONE`。

网络 10-bit serial 试验已完成：固定索引 `2229` 通过普通分配器完成 1024 次删除/重建，实际运行约 1811.5 秒。服务端内部 serial 从 2218 到 3242；客户端观测到创建序列 `170, 171, 1023, 0, 1, 169, 170`，服务端/客户端每个关键样本匹配，删除时双端指针清空，旧 VScript 引用均为无效。`check_serial_result.py` 从 1025 个创建事件、1024 个删除事件和 13 份原始快照重新计算并返回 `PASS`。这只验证一个自然复用槽位的网络 serial 回绕，内部 15-bit serial 仍为 `NOT_TESTED`。

`tools/linux/run_d66_soak.py` 提供有界的 512 实体重复更新、周期性内存指标、客户端同步检查和可选地图切换采样。单地图、无换图变量的正式运行实际 317.5 秒，10 个采样点和 3 次删除/恢复均为 `PASS_BOUNDED`；服务端 RSS 为 313284→313308 KiB。三次换图尝试保留为失败现场：`soak1` 在客户端加载前用默认坐标创建；`soak3` 的固定槽位复用假设受到地图正常分配影响；`soak4` 换图后 512 个服务端对象只出现 224 个客户端对象，缺失沿空间区域连续分布，疑似 PVS/可见性影响但未做完整同条件对照，根因未定。多次换图加 512 实体组合保持 `PARTIAL`，没有折算成稳定性通过。多小时 soak、特殊感染者 churn 和断线重连仍单独保持未测试。

## SourceMod 与产物身份

`tools/sourcemod/build_compat.py` 验证固定的 SourceMod、Metamod、SDK 提交及递归子模块，只应用 SDK `MAX_EDICT_BITS 11→12`，复编译 Linux x86/L4D2 核心、SDKTools、SDKHooks 和 `.sp` 探针并安装 gamedata 偏移。完整命令见 [兼容构建说明](../../tools/sourcemod/d65_compatibility.md)。本轮新核心、两项扩展、探针与构建记录哈希一致的私有实例通过 2048 引用往返、SDKHook 注册、删除后旧引用 `-1` 及双端快照检查，见 [sourcemod-build.json](sourcemod-build.json) 和 [sourcemod-smoke.json](sourcemod-smoke.json)。不分发这些游戏或扩展二进制。

两个发布 manifest 重建的输出哈希保持 D65 动态验收身份：Windows engine `48329969…`、client `3e5c3f2e…`；Linux engine `79b3966b…`、server `8575ed52…`。完整 SHA-256 在 `release/manifests/`；本轮未改变这些引擎补丁内容。

## 对外展示

| 改造前 | D66 交付后 |
| --- | --- |
| README 混合内部研究过程、旧结论与操作入口 | 英文与中文首页明确功能、平台、安装和限制 |
| 安装依赖多个内部生成器和手工步骤 | 两套固定版本 manifest、一个 CLI、预检/恢复演练 |
| 验收主要依赖摘要和文件存在性 | 原始双端生命周期、网络回绕、有界运行独立复算 |
| 历史报告分散、入口状态难辨 | 保留原路径，增加研究索引与实际引用分类清单 |
| 展示以文字为主 | 三张架构 SVG、两张真实数据图、录制脚本和分镜 |

首页已经改为面向玩家、开发者和 Source 社区的入口，保留中文版 [README.zh-CN.md](../../README.zh-CN.md)。新增文档层级覆盖安装、兼容性、架构、验证、限制、排错、开发和研究索引。`tools/release/build_assets.py` 从 D65 记录生成三张架构 SVG、阶梯图、边界图和紧凑 JSON 源数据；图中区分网络索引、内部索引、网络 serial、内部 serial 和 PacketEntities 字段宽度。

仓库审计清单由 `tools/release/audit_repository.py` 生成：[repository-inventory.md](repository-inventory.md) 和 [repository-inventory.json](repository-inventory.json)。它把当前入口、参考资料、历史证据、废弃但保留的流程、生成物和未知项分开；没有因为 D 编号而删除旧文件。

当前没有声称真实游戏视频。Xwayland 根窗口的 FFmpeg 试录结果为黑帧，无法证明采集到游戏画面；仓库提供了不启动或停止游戏的 `tools/release/capture_demo.sh`、60–90 秒分镜和由真实 D65 原始数据生成的 SVG 图，避免伪造截图或提交大型录制文件。

## 结论

D66 改善了安装、恢复、版本识别、验收解释和外部阅读路径，并为单客户端私有测试提供了网络 serial 回绕和有界稳定性证据，但尚未把项目变成“全部测试完成”。实验性单客户端私有测试可以进入 `PARTIALLY_READY` 发布候选；内部 serial 回绕、多小时运行、双客户端、完整 4096 槽位占用、原生 Windows 运行、Linux 原生客户端和任意第三方原生扩展仍是明确边界。
