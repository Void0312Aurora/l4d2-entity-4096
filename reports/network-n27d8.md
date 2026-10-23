# N27-D8：signon 精确状态与首份快照对比

## 1 探针语义修正

`ProcessSignonState` 现在同时记录：

- `before`：入口时 `client+0xEC`
- `requested`：消息 `+0x4C`
- `after`：返回后 `client+0xEC`
- `retval`：函数返回值

消息偏移由反汇编确认：`mov eax,[esi+0x4C]` 是请求状态，
`[esi+0x50]` 是 num_players。

## 2 修正后的 signon 结果

frameonly（成功连接的会话）：

```
before 2 requested 2 after 2
before 3 requested 3 after 4
before 4 requested 4 after 5
before 5 requested 5 after 6
```

原版：

```
before 2 requested 2 after 2
before 3 requested 3 after 4
before 4 requested 4 after 5
before 5 requested 5 after 6
before 6 requested 6 after 6
```

**两边的服务器都到达了状态 6。** D7 里“frameonly 停在 5”是入口时读取状态造成的
观测偏差，已修正。

真正的差异是：原版还有第 5 次 `ProcessSignonState`（客户端回送状态 6），
frameonly 没有这次调用——客户端没有把最终 signon 消息发回来。

## 3 首份快照

`WriteDeltaEntities` 记录 target/baseline 帧、tick、snapshot 与本次写入 bit 数：

```
frameonly 第一次:  bits=57632  total=72892
原版 第一次:      bits=57565  total=72825
frameonly 第二次:  bits=550    total=620
原版 第二次:      bits=636    total=706
```

首份全量快照相差 67 bit；`NET_SendPacket` 的首个大包长度相同（1047、1041 字节）。
大包前缀对比：

```
frameonly: 0100000001000000 211dd001 180000ca db0240ba ...
原版:     0100000001000000 213f8301 1800007a dc0240bb ...
```

差异集中在前 24 字节的动态字段；后续数据（第二个大包）逐字节相同。
因此还不能判定首份快照内容整体损坏，67 bit 的差异需要按实体流解码确认是
动态状态还是结构性差异。

## 4 结论与下一步

- 服务器 signon 到 6，快照编码与发送都执行；
- 缺口在 **客户端没有回送最终 signon 状态 6**；
- 下一步应解码首份 `svc_PacketEntities` 的实体级 bit 流，判断 67 bit 差异来自
  动态字段还是实体集合/PVS；若实体流一致，则检查客户端为何不消费该快照。
