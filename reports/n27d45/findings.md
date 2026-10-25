# N27-D45：恢复 VScript 执行链；客户端启动被 Steam 登录状态阻塞

## 1 根因：FIFO 不是 TTY

此前 `tail -f file | srcds` 的注入方式不稳定：srcds 只把 **TTY stdin** 当作控制台。
没有 TTY 时命令可能被忽略，表现为“脚本没执行/没有日志”，而不是脚本本身失败。

现已改用 PTY 启动器：

```
tools/linux/run_vscript_pty.py <port> <script> <timeout>
```

它负责：

- 用 `pty.openpty()` 给 srcds 一个真实控制台；
- 等待 `Initializing Director's script`；
- 发送 `sv_cheats 1` 和 `script_execute ...`；
- 捕获 `D37_` / `D46_` / `D47_` 标记；
- 结束进程组并返回非零码表示未执行。

## 2 连续复现

同一入口连续运行：

```
run_vscript_pty.py 27021 d37_batch 100
  D37_BATCH n=64 min=402 max=513

run_vscript_pty.py 27021 d37_batch 100
  D37_BATCH n=64 min=402 max=513

run_vscript_pty.py 27021 d46_cross 120
  D46_FILL n=983 last=2044
```

另外，交互 PTY 会话中已得到精确边界：

```
D46_TARGET idx=2045
D47_FILL n=2 last=2047
D47_TARGET idx=2048
```

这些是真实 `SpawnEntityFromTable` 实体，不是修改 `num_edicts`。

## 3 客户端启动：被 Steam 登录状态阻塞

重启 Steam 后：

```
steam ... -applaunch 550 ...
steamwebhelper ... -steamid=0 ...
```

没有产生 `left4dead2.exe` / Proton 游戏进程。  
原版 `client.dll` 与 `client.4096.dll` 候选都得到相同结果，因此当前无法把
“游戏未启动”归因于客户端 DLL。

需要 Steam 客户端处于已登录状态后，才能继续：

1. 原版 client.dll 正控；
2. client.4096.dll 候选；
3. 首次加载失败阶段。

## 4 环境

- `engine.dll` 已恢复 `8a6d4680…`；
- `client.dll` 已恢复 `c0a8e1e8…`；
- 无测试 srcds 残留；
- Steam 进程仍在运行（steamid=0，等待登录）。
