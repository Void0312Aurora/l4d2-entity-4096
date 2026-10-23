# N27-D6：补装 Frida 并做运行时探针

## 1 Frida 安装

系统原本没有 Frida；本轮装在隔离 venv：

```
/tmp/frida-venv/bin/frida --version   → 17.24.3
```

hook 脚本与驱动已放进仓库：

- `tools/linux/frida/n27_frame_hooks.js`
- `tools/linux/frida/run_attach.py`

对 `engine_srv.so` 的偏移做了字节校验，确认 hook 地址正确：

```
WDE      base+0x1DD830: 55 31 c0 b9 40 00 00 00
SendSnap base+0x0EA970: 55 89 e5 57 56 53 81 ec
AllocFrm base+0x1058F0: 55 89 e5 83 ec 18 8b 45
Signon   base+0x0E73B0: 55 89 e5 57 56 53 83 ec
```

## 2 探针覆盖

- `CClientFrameManager::AllocateFrame` 0x1058F0
- `CClientFrame::SetSnapshot` 0x105630
- `CGameClient::GetSendFrame` 0x1D9EB0
- `CBaseClient::SendSnapshot` 0xEA970
- `CBaseServer::WriteDeltaEntities` 0x1DD830
- `CBaseClient::ProcessSignonState` 0xE73B0

## 3 frameonly 运行结果

客户端连接窗口内 75 秒：

```
SendSnapshot 命中 0
AllocateFrame 命中 0
WriteDeltaEntities 命中 0
ProcessSignonState 命中 0
```

同时：

- 客户端 `console.log` 反复 `Connected to 10.77.88.2:27016` 与
  `Server connection timed out.`；
- 服务端日志出现 `STEAMAUTH: Client Void0312 received failure code 6`，
  没有 `Client "Void0312" connected`；
- 抓包只有 41/42 字节的握手重试，没有实体流。

## 4 结论

frameonly 的失败点在**帧分配与 signon 之前**：客户端根本没有完成连接，
所以 WDE/SendSnapshot 一次都没有执行。此前把原因归到“快照编码/帧字段读取”
并不成立；至少要先把**连接/认证路径**与帧补丁分开。

下一轮：

1. 同一客户端连续跑原版与 frameonly 各两次，记录 STEAMAUTH 是否稳定复现；
2. 若认证失败只跟随 frameonly，检查连接接受路径（`CGameClient` 构造、
   `FinishCertificateCheck`）在帧字段布局变化下的行为；
3. 若原版也间歇认证失败，则先修测试环境（Steam 会话/`-insecure` 认证），
   再谈帧补丁。
