# L4D2 实体上限扩容：2048 → 4096

L4D2-4096 是面向《Left 4 Dead 2》build `23990068` 的非官方、版本绑定扩容项目。它把网络实体索引从 `0..2047` 扩展到 `0..4095`，把内部实体表从 4096 槽扩展到 8192 槽，同时保留原有 Source 实体语义。

当前版本是面向**私有测试环境**的实验性发布候选，不是 Valve 产品，不绕过 Steam 所有权或认证，也不包含 Valve 二进制。在使用2048及以上网络实体索引时，客户端与专用服务器需要兼容的扩容补丁；低索引场景下的基本联机可用性属于范围更窄的验证结论。

## 当前状态

**PARTIALLY_READY（实验性）。** Linux 专用服务器与 Windows/Proton 客户端已通过最高索引 `4095` 的同步测试；Windows 原生客户端也已连接 Linux 服务器并实际游玩。在该原生 Windows 游玩测试中，通过隐藏实体辅助填充，服务端 Logger 记录 `Networked: 2159`，最大实体索引 `2158`（普通感染者）。

- **Linux 原生客户端：** 已完成实际联机游玩；高索引兼容性尚未验证，偶发加载或渲染异常待排查。
- **Windows 单人模式：** 暂不支持 4096 实体的本地 Listen Server，当前发布未包含 Windows `server.dll` 补丁。
- **尚待验证：** Windows 原生客户端侧高索引同步专项记录、双客户端、长时间稳定性及 4096 槽满载。详见[兼容性说明](docs/compatibility.md)与[项目限制](docs/limitations.md)。

## 平台支持边界

| 组件 | 状态 | 证据范围 |
| --- | --- | --- |
| Linux 专用服务器 | 实验性支持 | D65 真实 Proton/客户端会话；`engine_srv.so` 与 `server_srv.so` |
| Windows 原生客户端 | 已实际联机游玩 | 连接 Linux 扩容服务器并进行超过2048的游戏内服务端测试；客户端侧高索引追踪待补充 |
| Proton Windows 客户端 | 实验性支持 | 连接、更新、删除、复用和地图切换端到端通过 |
| Windows 原生专用服务器 | 未测试 | 不列为支持平台 |
| Linux 原生客户端 | 已实际联机游玩 | 高索引兼容性未验证；偶发加载/渲染异常待排查 |
| Windows 单人模式 / 内置 Listen Server | 暂不支持 | 本版未包含 Windows `server.dll` 补丁 |
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

[2026-10-31 实际游玩证据](artifacts/entity-index-20261031/README.md)：[Logger 日志](artifacts/entity-index-20261031/entity_limit_2026-10-31_00-20-00.log)、[索引扫描](artifacts/entity-index-20261031/runtime-index-scan.txt)及[测试脚本](artifacts/entity-index-20261031/entity_index_fill.nut)。

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
- 网络 serial 按预期在 1024 次复用后重复；内部 15-bit 回绕仍为 `NOT_TESTED`。
- 4096 槽满载、长时间稳定性及 Linux 原生客户端的高索引同步尚未验证。
- VAC 安全性、公开匹配和正式公开 Release 均未验证。
- 其他 SourceMod 原生扩展不在兼容构建结论内。
- 当前安装器仅在匹配版本的游戏目录中原位替换 manifest 指定模块；操作前关闭游戏，保留 `*.l4d2-4096.bak` 与 receipt，并仅在私有测试环境使用。

## 贡献与许可

欢迎提交 Bug 报告、兼容性测试结果和 Pull Request。请参阅[贡献指南](CONTRIBUTING.md)、[Issue 模板](.github/ISSUE_TEMPLATE/)与[开发说明](docs/development.md)。接受经过贡献者检查与验证的 AI 辅助贡献。

仓库原创内容采用 [MIT 许可证](LICENSE)；Valve 游戏二进制及其他第三方资产、代码不属于该授权范围。

仓库只包含研究数据、差分 manifest、脚本和文档，不包含 Valve 原始或修改后的完整游戏二进制。历史证据链见[研究索引](docs/research-index.md)。
