# N27-D28：ProcessBaselineAck 返回 0 的具体分支与字段

## 0 结论

frameonly 的 `CBaseClient::ProcessBaselineAck` 在以下位置返回 0：

```
engine_srv.so+0xE933F  (snapshot_null 分支)
→ ProcessBaselineAck = 0
→ CLC_BaselineAck::Process = 0
→ 后续 NET_SignonState(6) 未被解析
```

pristine 走正常路径（`+0xE9287`），返回 1，并继续解码 Signon 6。

## 1 关键字段

在 `+0xE90AB`（读取帧快照指针之前）捕获 frame 对象：

| 字段 | frameonly | 含义 |
|---|---:|---|
| `frame+0x118` | **0** | `ProcessBaselineAck` 实际读取的偏移 |
| `frame+0x218` | 138517848 | F2 迁移后的 snapshot 指针 |
| `frame+0x10C` | 0 | 旧位图/引用偏移 |
| `frame+0x20C` | 235493084 | F2 迁移后的对应字段 |

`ProcessBaselineAck` 的未修改代码读取 `frame+0x118`，得到 0，进入 snapshot_null
分支并返回 0。

## 2 与 F2 的关系

F2 将 `CClientFrame` 成员整体后移 `0x100`：

- snapshot 指针 `+0x118` → `+0x218`；
- 其他帧成员同理。

但 `ProcessBaselineAck` 不在 frameonly 的 F1/F2/F3 补丁范围内，仍按旧偏移
`+0x118` 读取。补丁后的帧在该位置为 0，于是：

```
ACK 处理读到空 snapshot
→ 返回 0
→ CLC_BaselineAck::Process 返回 0
→ 当前消息流提前结束
→ 同批次的 SignonState(6) 不再被解析
```

这是目前第一条把 F2 帧迁移、BaselineAck 失败和 Signon 6 缺失直接连起来的证据。

## 3 静态路径

`engine_srv.so+0xE9030`：

- `+0xE90A3`：`mov 0x118(%eax),%ecx`（eax = CClientFrame*）
- `+0xE90A9`：`test ecx,ecx`
- `+0xE90AB`：`je 0xE933F`（snapshot 为空）
- `+0xE933F`：记录日志后 `return 0`

## 4 限制

- 每镜像一次；需重复 A/B；
- 只证明 frameonly 在 `+0x118` 读到 0，尚未逐个核对 F2 计划表是否包含
  `ProcessBaselineAck` 所需的全部帧字段读取；
- 尚未直接观测 `_ProcessMessages` 的退出分支，但返回值链已完整；
- 功能正控仍未建立。

## 5 下一步

1. 重复 frameonly/pristine，确认 `+0x118=0、+0x218≠0` 稳定；
2. 枚举 `ProcessBaselineAck` 中所有 CClientFrame 字段读取，核对哪些仍用旧偏移；
3. 将这些读取加入 F2 补丁表（或确认应由后续 C3 覆盖）；
4. 重新构建并验证 Signon 6 与服务端消息流恢复。
