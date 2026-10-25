# N27-D47：PTY 高索引会话工具通过三次保持运行；client.4096 启动期崩溃

## 1 M1：PTY 高索引会话工具

新增 `tools/linux/run_highindex_session.py`：

- 使用真实 PTY，等待 `Initializing Director's script`；
- 发送 `sv_cheats 1` / `script_execute d50_session`；
- 只接受 `D50_BEGIN` + `D50_TARGET` + `D50_DONE`；
- 断言 target >= 2048；
- `--keep` 保留服务端，返回 PID/端口/run ID；
- 超时、目标不符、服务器退出分别返回不同非零码。

连续三次独立运行：

```
RUN_ID=20261025-214028-4a14e6 PID=384120 TARGET=2048 DONE=True RC=0
RUN_ID=20261025-214040-4722ba PID=384286 TARGET=2048 DONE=True RC=0
RUN_ID=20261025-214051-12768f PID=384409 TARGET=2048 DONE=True RC=0
```

每次均真实创建 index 2048 目标实体，并保持服务端运行（端口 27021 监听）。

## 2 客户端 A/B：候选 client.4096 启动期退出

使用同一 direct Proton 命令、同一低索引服务器、同一 engine：

- 原版 `client.dll`：`left4dead2.exe` 进程存在，窗口出现；
- `client.4096.dll`：DXVK 初始化到 swapchain 后进程退出，没有窗口；
- 日志最后阶段为 D3D9/DXVK，未打印 Wine Unhandled exception；
- 因此候选不是“完全无法被 PE 加载”，而是在客户端初始化后段退出。

该失败仍缺少首次 fault PC；下一步用 winedbg/自定义 SEH 探针抓取。

## 3 未完成

- 客户端未完成 signon/进图正控；
- SendServerInfo 崩溃 A/B 未完成；
- 无 index ≥2048 客户端创建证据。

## 4 环境

- engine.dll 8a6d4680…
- client.dll c0a8e1e8…
- 测试服务器已停止。
