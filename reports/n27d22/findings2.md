# N27-D22 第二轮：服务端解析语义校准完成

## 0 结论

修正 Linux 服务端 `NET_SignonState` 的对象偏移后，服务端 `ReadFromBuffer` 的
解码状态可以语义化读取：

| 镜像 | `ReadFromBuffer` 解码出的 state | `ProcessSignonStateMsg` |
|---|---|---|
| frameonly | **2, 3, 4, 5** | 2, 3, 4, 5 |
| pristine | **2, 3, 4, 5, 6** | 2, 3, 4, 5, 6 |

因此现在可以确认：

> frameonly 的客户端已提交 `NET_SignonState(6)`，但服务端连 6 的位流解码都没有发生；
> pristine 在相同条件下能解码并处理 6。

首个已确认缺失点从 `ProcessSignonStateMsg(6)` 前移到 **服务端 `ReadFromBuffer`**。

## 1 偏移修正

Windows 客户端对象布局不能照搬到 Linux 服务端。反汇编 `engine_srv.so+0xA8080` 显示：

- 错误路径：`xor eax,eax; mov eax,0x54(%esi)`；
- 成功路径：`mov %eax,0x54(%esi)` 之前的状态实际存放在 **`+0x4C`**。

实测返回对象字段：

| 偏移 | 值（frameonly） |
|---|---|
| `+0x4C` | 2, 3, 4, 5 |
| `+0x50` | 0xFFFFFFFF, 1, 1, 1 |
| `+0x54` | 0 |

所以此前读取 `+0x54` 得到 0 是对象布局错误，不是解析失败。

## 2 客户端序列化探针仍无效

客户端 `engine+0x50320` 的 `WriteToBuffer` 探针在两镜像都只看到 state
`0/3/4/5`，没有 2 和 6；pristine 也没有 6。因此该探针仍然不能用于判断
Signon 6 是否序列化。

客户端已确认的事实仍只有：

- 构造并提交 `SendNetMsg(NET_SignonState(6))`；
- 返回值为 1；
- 本地状态到 6。

## 3 当前证据链

| 环节 | frameonly | pristine |
|---|---|---|
| 客户端提交 6 | 有 | 有 |
| 客户端写位流 | 未观测（探针无效） | 未观测 |
| 服务端解码 6 | **无** | **有** |
| 服务端处理 6 | 无 | 有 |

因此消息丢失发生在：

> 客户端 `SendNetMsg` 之后、服务端 `ReadFromBuffer` 之前。

可能包括客户端发送队列/序列化、UDP 传输、服务端收包或消息类型分发。

## 4 下一步

1. 修正客户端序列化探针，确认 6 是否进入发送缓冲；
2. 在服务端 `_ProcessMessages` 记录消息类型 ID，确认 6 是否出现在类型流；
3. 对 pcap 按连接、方向、序列号归一化，统计客户端提交 6 前后的上行包；
4. 若 6 从未进入任何上行数据，检查 netchan 可靠队列与发送窗口。
