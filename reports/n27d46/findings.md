# N27-D46：client.4096 可加载；高索引连接出现 SendServerInfo 崩溃/签名停滞

## 1 client.4096.dll 实际可加载

此前“候选 DLL 加载失败”主要由 Steam 启动链造成。改用直接 Proton 启动：

```
proton run ./left4dead2.exe -steam -novid -console -condebug
```

得到：

- `left4dead2.exe` 真实进程；
- 游戏窗口；
- 菜单/Bink 正常。

因此 `client.4096.dll` 至少能够被 PE 加载并运行到主菜单。
`client.dll` 的加载失败不是当前第一阻塞点；Steam 的 `-applaunch` 转发才是。

## 2 高索引目标

PTY 服务端中真实创建：

```
D47_FILL n=986 last=2047
D47_TARGET idx=2048
```

服务端快照跨 2048 不再在 TakeTickSnapshot 崩溃。

## 3 新失败：预存高索引时客户端连接崩溃

服务端先持有 index 2048，再让客户端连接，服务端崩溃，回溯：

```
CFrameSnapshotManager? no
Host_CountVariablesWithFlags
Host_BuildConVarUpdateMessage
CBaseClient::SendServerInfo
CBaseServer::SendPendingServerInfo
CBaseServer::RunFrame
SV_Frame
```

即崩溃发生在 **SendServerInfo / cvar 更新构建**，不是快照栈数组。
目前没有该次崩溃的 core（apport 未写新文件），需要 PTY 下的 preload 探针再次复现。

## 4 正常连接顺序的现状

客户端先启动（direct Proton），再启动服务端：

- 客户端 `Connected to 10.77.88.2:27021`；
- 服务端 `status` 仍显示 `0 humans, hibernating`；
- 客户端停在“正在加入一场游戏/载入中”，没有完成 signon。

直接 Proton 启动缺少 Steam 启动链提供的客户端票据/登录上下文，导致连接停在认证/signon，
因此不能用它完成网络同步验收。

## 5 环境

- `engine.dll` 恢复 `8a6d4680…`；
- `client.dll` 恢复 `c0a8e1e8…`；
- 测试服已停止。
