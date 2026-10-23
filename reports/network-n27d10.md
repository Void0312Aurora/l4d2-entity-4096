# N27-D10：可执行客户端跟踪脚本与 FULL 返回确认

## 1 交付物

- `tools/linux/gdb/client_trace.py`：gdb Python 跟踪器，记录
  `SetSignonState` 入口与 `FinishBreakpoint` 返回、`ProcessPacketEntities`
  入口/抽样，带毫秒级时间戳。
- `tools/linux/gdb/run_client_trace.sh <pid> <engine_base> <out> [sec]`：
  可直接执行，自动附加、设置 gdb 信号处理并输出日志。

客户端：L4D2 build 23990068（Proton），`engine.dll` 映射基址 `0x79e00000`。
RVA 由 IDA 校验：`ProcessPacketEntities=0x77140`，`SetSignonState=0x93140`。

## 2 frameonly 客户端事件（脱敏）

```
t=15.705  ENTER signon this=0xb7f0018 before=0 req=1
t=15.726  RETURN signon before=0 req=1 after=1
t=16.179  ENTER signon before=1 req=2
t=16.184  RETURN signon before=1 req=2 after=2
t=20.477  ENTER signon before=2 req=3
t=25.823  ENTER signon before=3 req=4
t=25.857  ENTER signon before=4 req=5
t=26.703  ENTER ppe n=1
t=26.724  ENTER signon before=5 req=6
t=27.076  RETURN signon before=5 req=6 after=6
t=27.138  ENTER ppe n=2
...
t=37.035  ENTER ppe n=200
```

结论：`SetSignonState(5→6)` **返回后状态字段确实为 6**，并且客户端持续进入
`ProcessPacketEntities`（200+ 次）。客户端不是卡在 signon，也不是完全没消费实体更新。

## 3 仍存在的观测缺陷

- `FinishBreakpoint.return_value` 在 32 位 Proton 进程上取不到（日志 `rv=None`）；
- `ProcessPacketEntities` 的 `arg0` 不是 signon 状态对象，`arg0+0x68` 读出的值无效
  （60154/481/190…），不能用来轮询状态；需要先确认该函数的真实 this/参数。

因此“FULL 后状态是否持续为 6”还没有独立采样证据，只有 `SetSignonState`
返回时的 `after=6`。

## 4 下一步

1. 用 IDA 确认 `ProcessPacketEntities` 的 this 指针来源，改为在正确的
   `CClientState` 对象上采样 `+0x68`；
2. 在客户端 `LevelInitPreEntity/PostEntity` 与加载界面关闭路径下断点
   （`LevelInitPreEntity` 字符串已定位在 `SetSignonState` 内部，
   `LevelInitPostEntity` 不在 engine.dll，需要查 client.dll）；
3. 对照原版与 frameonly 在 FULL 后的首个差异事件，而不是继续比较包长。
