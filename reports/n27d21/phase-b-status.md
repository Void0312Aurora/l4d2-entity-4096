# N27-D21 Phase B：客户端 Signon 6 发送探针状态

## 1 已实现

新增 `tools/n27d21_client_signon.py`：

- 在客户端 `CClientState::SetSignonState`（`engine.dll+0x93140`）入口记录：
  - `this`、目标 state、当前 state；
  - `CNetChan*` 与发送槽 `vtable+0xA4` 的运行时地址；
- 动态在该发送函数下断点；
- 对 `NET_SignonState`（vtable RVA `0x3575CC`）读取对象内：
  - `+0x54` = state；
  - `+0x58` = spawn count；
- 用 `FinishBreakpoint` 记录 `SetSignonState` 返回值。

IDA 依据：

- `CClientState::SetSignonState` 末尾对 `this+16`（netchan）的 `vtable+0xA4`
  调用，参数为 `NET_SignonState` 对象；
- `sub_10050330` 是 `NET_SignonState` 构造器，state 写在 `+0x54`。

## 2 实际运行结果

多次尝试在服务端启动前附加客户端探针，但客户端进程生命周期与模块加载时机不稳定：

- 早期抓到的 `left4dead2.exe` PID 尚未映射 `engine.dll`，断点插入失败：
  `Cannot insert breakpoint -14. Cannot access memory at address 0x79e93140`；
- 等待 45 s 后，该 PID 已不再映射 `engine.dll`（进程被 Proton 替换/退出），
  无法计算基址；
- 因此本轮**尚未取得客户端 `SendNetMsg(NET_SignonState(6))` 的原始记录**。

服务端侧仍稳定复现：首次连接 signon 2→3→4→5，无 6；frameonly 首次连接
`SendNetMsg` 仅 7 条。

## 3 结论状态

- 服务端局部正控成立：原版首次连接处理 signon 6；
- 客户端发送探针代码已就绪，但尚未拿到“发送/未发送”的证据；
- 现在不能断言 frameonly 客户端没有发送 signon 6。

## 4 下一步

使用 D19 运行器中已验证的“等待 `engine.dll`/`client.dll` 基址”逻辑附加客户端，
而不是按进程名抓 PID：

1. 轮询 `/proc/<pid>/maps` 直到出现 `bin/engine.dll`，再计算基址；
2. 或复用 `run_experiment.py` 的 `module_base()` 等待循环；
3. 客户端探针先于服务端启动安装，再启动服务端；
4. 采集后按连接对象与消息字段关联，而不是按墙钟时间。
