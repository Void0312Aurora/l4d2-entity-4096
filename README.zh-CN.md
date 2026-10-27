# L4D2 实体上限扩容：2048 → 4096

L4D2-4096 是面向《Left 4 Dead 2》build `23990068` 的非官方、版本绑定扩容项目。它把网络实体索引从 `0..2047` 扩展到 `0..4095`，把内部实体表从 4096 槽扩展到 8192 槽，同时保留原有 Source 实体语义。

当前版本是面向**隔离副本**的实验性发布候选，不是 Valve 产品，不绕过 Steam 所有权或认证，也不包含 Valve 二进制。客户端和专用服务器必须使用相互匹配的扩容文件。

## 当前状态

**PARTIALLY_READY：单客户端实验性测试。** 已验证路径是 Linux 专用服务器配合 Proton 运行 Windows 客户端。同一 Windows 模块 manifest 可供原生 Windows 测试，但该运行环境尚未独立验收。D65 已经完成真实 `16/64/128/256/512` 阶梯、索引 `4095`、六类特殊感染者、客户端同步和一次地图切换。D66 增加了真实 1024 次网络 serial 回绕试验、317.5 秒有界 512 实体运行、隔离副本安装器、SourceMod 可复现构建和原始证据验收门禁。

以下内容不属于当前发布声明：内部 15-bit serial 回绕、多小时运行、两名真实 Steam 用户、同时占满 4096 个网络槽位、原生 Windows 运行验收、Linux 原生客户端以及任意第三方原生扩展。

## 平台支持边界

| 组件 | 状态 | 证据范围 |
| --- | --- | --- |
| Linux 专用服务器 | 实验性支持 | D65 真实 Proton/客户端会话；`engine_srv.so` 与 `server_srv.so` |
| Windows 客户端文件 | 实验性；原生运行未验收 | 通过 Proton 观察到 2048、2049、4095 槽位 |
| Proton Windows 客户端 | 实验性支持 | 连接、更新、删除、复用和地图切换端到端通过 |
| Windows 原生专用服务器 | 未测试 | 不列为支持平台 |
| Linux 原生客户端 | 未测试 | 不列为支持平台 |
| SourceMod/SDKTools/SDKHooks | 限定兼容构建 | 仅覆盖 D65 探针中的 API 和回调 |

## 安装隔离副本

需要 Python 3 和合法安装的 build `23990068`。安装器会先校验源文件哈希，再应用 `release/manifests/` 中的字节差分，校验输出哈希，最后写入独立目标目录；默认不会修改源目录，也不需要 IDA、GDB 或十六进制编辑器。

先预检 Windows 或 Proton 客户端：

```bash
python3 tools/release/install.py check \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2"
```

预览并创建副本：

```bash
python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2" \
  --target "$HOME/L4D2-4096-client" --dry-run

python3 tools/release/install.py install \
  --manifest release/manifests/windows-client.json \
  --game "/path/to/Left 4 Dead 2" \
  --target "$HOME/L4D2-4096-client"
```

Linux 专用服务器使用 `release/manifests/linux-server.json`。目标目录中的 receipt 保存源文件和输出文件哈希；恢复已有备份：

```bash
python3 tools/release/install.py restore \
  --receipt "$HOME/L4D2-4096-client/l4d2-4096-install.json"
```

如果目标是本次新建且没有旧备份，恢复时加 `--remove-created`。完整流程见[安装说明](docs/installation.md)。

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
- VAC 安全性、公开匹配和正式公开 Release 均未验证。
- 其他 SourceMod 原生扩展不在兼容构建结论内。
- 不要把扩容文件覆盖到 Steam 原始库，始终使用隔离副本并保留 receipt。

仓库只包含研究数据、差分 manifest、脚本和文档，不包含 Valve 原始或修改后的完整游戏二进制。历史证据链见[研究索引](docs/research-index.md)。
