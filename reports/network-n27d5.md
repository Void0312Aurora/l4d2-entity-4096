# N27-D5：用 IDA 与抓包继续定位

## 1 IDA 反编译确认

`CGameClient::GetSendFrame`（0x1D9EB0）伪代码：

```c
if ( ClientFrame && *(_DWORD *)(ClientFrame + 280) != *((_DWORD *)this + 63) )
    return ClientFrame;
```

`280 = 0x118`，正是帧快照指针，确认补到 `+0x218` 的修正是必要的。
`CBaseServer::WriteDeltaEntities` 伪代码同时确认：

```c
memset((char *)a2 + 268, 0, 0x100u);      // a2 = CBaseClient，客户端位图
*((_DWORD *)a3 + 67) = (char *)a2 + 268; // a3 = frame，借用位图指针 +0x10C
```

`CClientFrameManager::GetClientFrame` 伪代码里的 `+276`（0x114）是帧链表 next，
与我们的布局假设一致。

## 2 抓包对照（lo，udp/27016）

| 服务端 | 抓包时长 | 包数 | 典型长度 |
|---|---|---|---|
| 原版 | 27.9 s | 974 | 1000–1200 B（实体快照流） |
| `frameonly` | 77.4 s | 198 | **只有 41/42 B** |

帧偏移镜像下，客户端与服务端只在交换 41/42 字节的控制包，**没有任何实体快照流**。
这解释了“Receiving uncompressed update”之后不再前进：服务器没有把世界数据发出去。

## 3 同时观察到的认证失败

`frameonly` 服务端日志：

```
STEAMAUTH: Client Void0312 received failure code 6
Client "Void0312" connected (10.77.88.2:27005).
```

原版日志没有出现该行。当前还不能区分：

- 帧偏移补丁导致连接进入异常状态，进而认证失败；
- 还是本地 `-insecure` + Steam 会话导致的间歇认证失败，恰好与本次运行重合。

## 4 下一步

1. 抓包从 t=0 开始，用 `tshark` 解码 S2C challenge/connect，确认 41/42 字节包是
   challenge 重试还是已建立连接后的 net tick；
2. 同一客户端连续跑原版/`frameonly` 各两次，记录 STEAMAUTH 是否稳定复现；
3. 若认证失败只出现在帧偏移镜像，用 IDA 检查 `CBaseClient::ProcessSignonState`
   与客户端位图/帧生命周期交叉点。
