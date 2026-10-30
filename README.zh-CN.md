# L4D2 实体上限扩容：2048 → 4096

L4D2-4096 是面向《Left 4 Dead 2》build `23990068` 的非官方、版本绑定扩容项目。它把网络实体索引从 `0..2047` 扩展到 `0..4095`，把内部实体表从 4096 槽扩展到 8192 槽，同时保留原有 Source 实体语义。

当前版本是面向**私有测试环境**的实验性发布候选，不是 Valve 产品，不绕过 Steam 所有权或认证，也不包含 Valve 二进制。在使用2048及以上网络实体索引时，客户端与专用服务器需要兼容的扩容补丁；低索引场景下的基本联机可用性属于范围更窄的验证结论。

## 当前状态

**PARTIALLY_READY：一个客户端连接独立专用服务器的实验性测试，并非单人模式验收。** 已验证路径是 Linux 专用服务器配合 Proton 运行 Windows 客户端。同一 Windows 模块 manifest 可供原生 Windows 测试，但该运行环境尚未独立验收。D65 已经完成真实 `16/64/128/256/512` 阶梯、索引 `4095`、六类特殊感染者、客户端同步和一次地图切换。D66 增加了真实 1024 次网络 serial 回绕试验、317.5 秒有界 512 实体运行、安装器、SourceMod 可复现构建和原始证据验收门禁。另有 2026-10-31 在 `c6m1_riverbank` 实际游玩会话中的辅助填充测试，观测到普通感染者占用索引 `2158`；这属于有界服务端运行时观测，不等于该次测试已独立验证客户端高索引同步或长时间稳定性。

**Linux 原生客户端的验证边界：**已有与服务器联机并实际游玩的用户报告，故先前一概标为“未测试”不准确。但仓库没有该次客户端完整轨迹或索引超过2047的同步证据，也不能据此声称未经扩容的 Linux 原生客户端能够解码高索引。游玩中偶尔出现加载或渲染异常，发生较少、尚未系统复现或归因，不能认定是补丁引起的。基本联机可用不以高负载验收为必要前提；若要宣称该客户端完整支持4096索引，仍需独立验证高索引同步。

**Windows 客户端内置单人模式（Listen Server）的 4096 扩容尚未实现、尚未验收。** 当前 Windows 发布清单只包含 `bin/engine.dll` 和 `left4dead2/bin/client.dll`，没有纳入本地服务端所需的 `left4dead2/bin/server.dll`。历史上虽已研究该模块并生成静态实验补丁，但没有集成到现行发布。见[兼容性说明](docs/compatibility.md#single-player-and-listen-server-scope)。

以下内容不属于当前发布声明：内部 15-bit serial 回绕、多小时运行、两名真实 Steam 用户、同时占满 4096 个网络槽位、原生 Windows 运行验收、**Linux 原生客户端的高索引/高负载验收**以及任意第三方原生扩展。

## 平台支持边界

| 组件 | 状态 | 证据范围 |
| --- | --- | --- |
| Linux 专用服务器 | 实验性支持 | D65 真实 Proton/客户端会话；`engine_srv.so` 与 `server_srv.so` |
| Windows 客户端文件 | 实验性；原生运行未验收 | 通过 Proton 观察到 2048、2049、4095 槽位 |
| Proton Windows 客户端 | 实验性支持 | 连接、更新、删除、复用和地图切换端到端通过 |
| Windows 原生专用服务器 | 未测试 | 不列为支持平台 |
| Linux 原生客户端 | **已有实际联机游玩（用户报告，有限范围）** | 已连接服务器并游玩；高索引/高负载未验收，偶发加载或渲染异常尚未排查 |
| Windows 单人模式 / 内置 Listen Server | **未实现、未验收** | 当前发布未集成 Windows `server.dll` 扩容补丁；仅有历史静态实验成果 |
| SourceMod/SDKTools/SDKHooks | 限定兼容构建 | 仅覆盖 D65 探针中的 API 和回调 |

## 安装补丁模块

需要 Python 3 和合法安装的 build `23990068`。安装器会先校验源文件哈希，只备份清单中的 DLL，再在 Steam 游戏目录原位替换模块；不会复制整棵游戏目录，也不会复制 addons。

先预检 Windows 或 Proton 客户端：

```bash
python3 tools/release/install.py check \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

预览但不修改文件：

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2" \
  --dry-run

python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

Linux 专用服务器使用 `release/manifests/linux-server.json`。安装器会在每个 DLL 旁写入 `*.l4d2-4096.bak`，并在游戏目录写入 receipt。恢复原始模块：

```bash
python3 tools/release/install.py restore \
  --receipt "/path/to/Left 4 Dead 2/l4d2-4096-install.json"
```

替换模块时必须关闭游戏。Steam 更新后可能覆盖补丁，需要重新运行 `check` 和 `install`。完整流程见[安装说明](docs/installation.md)。

## 已验证内容

![实体容量对比](docs/assets/diagrams/capacity.svg)

![网络路径和位宽](docs/assets/diagrams/protocol.svg)

![高索引实体生命周期](docs/assets/diagrams/lifecycle.svg)

![D65 实体阶梯](docs/assets/benchmark/d65-ladder.svg)

![边界覆盖](docs/assets/benchmark/d65-boundary.svg)

| 边界或负载 | 结果 |
| --- | --- |
| `2047` | 原版最高索引和 API 控制 |
| `2048` | 首个新增索引，客户端创建/更新/删除 |
| `2049` | 高索引客户端观察和复用 |
| `16/64/128/256/512` | 真实会话中的创建、六次更新、删除、复用 |
| `4095` | 自然分配边界，创建、六次更新、删除、复用和 SDKHooks 回调 |
| 特殊感染者 | 512 个高索引实体存活期间验证 Hunter、Spitter、Smoker、Boomer、Charger、Jockey |
| 地图切换 | `c1m1_hotel → c1m2_streets` 后重新建立并同步高索引实体 |
| 网络 serial 回绕 | 索引 2229 自然复用 1024 次，双端 `1023 → 0 → 1`，最终回到初始网络 serial |
| 实际游玩中辅助填充跨越 2048 | `c6m1_riverbank`：Logger `All: 2374`、`Networked: 2159`；VScript `max=2158`、`maxclass=infected`、`over2047=105`。通过持续保留隐藏物件产生压力；仅为服务端观测，不代表纯自然负载或该次客户端同步验收 |

新增的 [2026-10-31 实际运行证据](artifacts/entity-index-20261031/README.md) 提供 [Logger 原始记录](artifacts/entity-index-20261031/entity_limit_2026-10-31_00-20-00.log)、[VScript 扫描输出](artifacts/entity-index-20261031/runtime-index-scan.txt)、[填充与清理脚本](artifacts/entity-index-20261031/entity_index_fill.nut)及[扫描脚本](artifacts/entity-index-20261031/entity_index_scan.nut)。扫描中 `count=2397` 与 `unique=2127` 不同，不能直接等同于同时占用的独立网络槽位数；日志的快照间隔也不是越过 2047 的持续时间。

D65 的机器可读记录见 [reports/n27d65/validation.json](reports/n27d65/validation.json)，叙述报告见 [reports/n27d65/findings.md](reports/n27d65/findings.md)。D66 的发布判断见 [reports/n27d66/release-readiness.md](reports/n27d66/release-readiness.md)，最终门禁见 [reports/n27d66/validation.json](reports/n27d66/validation.json)，并附有[网络 serial](reports/n27d66/network-serial.json)、[有界运行](reports/n27d66/bounded-soak.json)和 [SourceMod smoke](reports/n27d66/sourcemod-smoke.json)记录。

## 文档入口

- [英文技术报告](docs/technical-report.md)
- [补丁技术映射](docs/patch-map.md)
- [证据与复现说明](docs/evidence-and-reproduction.md)
- [架构与位宽](docs/architecture.md)
- [安装、恢复与卸载](docs/installation.md)
- [兼容性矩阵](docs/compatibility.md)
- [验收和证据模型](docs/verification.md)
- [限制](docs/limitations.md)
- [故障排查](docs/troubleshooting.md)
- [开发与可复现构建](docs/development.md)
- [研究索引](docs/research-index.md)
- [演示分镜与录制脚本](docs/demo/storyboard.md)

运行发布候选门禁：

```bash
python3 tools/release/check_rc.py \
  --manifest release/manifests/windows-client.json \
  --manifest release/manifests/linux-server.json \
  --evidence-root /path/to/runs/d65
```

门禁会分别报告静态身份、manifest、证据完整性和端到端范围；某一层通过不会替代其他未测试层。

## 重要限制

- 所有地址和字节断言绑定 build `23990068`，游戏更新后即失效。
- 原版客户端无法解码 `2048` 及以上网络索引。
- **单客户端≠单人模式**：当前验收依赖独立 Linux 专用服务器，不包含 Windows 客户端内置的单人本机服务器。也尚未实测当前补丁对普通2048以下单人启动有何影响；不能将单人扩容未实现直接解释为单人游戏必然无法启动。
- 网络 serial 按预期在 1024 次复用后重复；内部 15-bit 回绕仍为 `NOT_TESTED`。
- 最新的真实游玩测试借助隐藏实体辅助跨越 2047，尚不能证明自然刷怪单独突破原版限制、4096 个槽位同时占满或持续高负载稳定性；该次无独立的客户端高索引同步轨迹，不能替代 D65/D66 的端到端证据。
- VAC 安全性、公开匹配和正式公开 Release 均未验证。
- 其他 SourceMod 原生扩展不在兼容构建结论内。
- 当前安装器仅在匹配版本的游戏目录中原位替换 manifest 指定模块；操作前关闭游戏，保留 `*.l4d2-4096.bak` 与 receipt，并仅在私有测试环境使用。

仓库只包含研究数据、差分 manifest、脚本和文档，不包含 Valve 原始或修改后的完整游戏二进制。历史证据链见[研究索引](docs/research-index.md)。
