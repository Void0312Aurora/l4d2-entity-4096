# N27-D11：FULL 持续性已确认，客户端世界加载阶段待拆分

## 1 跟踪器修正

- `run_client_trace.sh` 用脚本自身目录解析 Python 路径，不再硬编码仓库绝对路径；
- 日志直接写入用户传入的 `$OUT`，不再出现 `$OUT` 为空、内容跑到 `$OUT.gdb` 的问题；
- 去掉无必要的 `chmod 666`；
- `SetSignonState` 在请求 6 且返回后状态为 6 时缓存 `this`，
  之后每次 PPE 抽样直接读取该对象的 `+0x68`。

## 2 frameonly 客户端结果

```
ENT signon t=26.109 before=4 req=5
ENT ppe   t=27.002 n=1
ENT signon t=27.023 before=5 req=6
RET signon t=27.384 before=5 req=6 after=6
FULL_CACHED t=27.384 this=0xb7f0018
ENT ppe   t=27.464 n=2 state=6
ENT ppe   t=27.556 n=4 state=6
ENT ppe   t=32.329 n=100 state=6
ENT ppe   t=37.359 n=200 state=6
```

结论：客户端 FULL 状态**持续保持为 6**，并持续处理至少 200 次
`ProcessPacketEntities`；加载界面仍停在 75%。

`ProcessPacketEntities` 的 `ecx`/`arg0` 不是 `CClientState`（分别为 0x13c、
0x240cdc0），D10 之前用 `arg0+0x68` 采样无效；缓存 `SetSignonState` 的
`this` 后采样结果稳定为 6。

## 3 客户端游戏模块

`left4dead2/bin/client.dll` 中存在：

```
LevelInitPreEntity - CacheUsedMaterials - Start/Finish
LevelInitPreEntity - PreCache - Start/Finish
m_loadingProgress
LoadingProgress
```

`LevelInitPostEntity` 没有以字符串形式出现，需要下一轮在 IDA 中按调用关系或
`LevelInitPreEntity` 的 xref 定位客户端关卡初始化路径，并跟踪：

1. `LevelInitPreEntity` 调用顺序（原版 vs frameonly）；
2. 本地玩家实体创建/绑定；
3. 加载界面解除（`m_loadingProgress` / LoadingProgress 状态）。

## 4 当前边界

- 连接、认证、signon、FULL 持续性均已验证；
- 快照编码与发送已执行；
- 剩余差异只在 **FULL 后的世界加载/加载界面解除**；
- 尚不能区分“实体创建失败”与“加载完成通知未发出”。

## 5 下一步

在 IDA 中打开 `client.dll`，定位 `LevelInitPreEntity` 及其调用者，
记录原版/frameonly 的事件时间线，找第一个缺失或顺序变化的事件；
若关卡初始化与玩家实体都正常，再查加载界面关闭路径。
