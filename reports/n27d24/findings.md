# N27-D24：Signon 6 写入具体 netchan 发送缓冲

## 0 结论

两种镜像的客户端行为完全一致：

| 状态 | 写入缓冲 | bit cursor 前 → 后 | delta | 返回 |
|---|---|---|---:|---:|
| Signon 5 | netchan+0x20 | 0 → 142 | 142 | 1 |
| Signon 6 | netchan+0x20 | **39 → 181** | **142** | **1** |

因此 Signon 6 已经进入 **netchan+0x20 的发送缓冲**，bit cursor 前进 142 位，
返回值 1；frameonly 与 pristine 在这一层没有差异。

服务端：

- frameonly 解码 2,3,4,5；
- pristine 解码 2,3,4,5,6。

首个异常边界现在精确定位为：

> **Signon 6 写入 netchan+0x20 之后、服务端 ReadFromBuffer 之前。**

即 datagram 组装/发送、网络传输、服务端收包/可靠重组/消息类型流。

## 1 P0 修复

`tools/n27d21_run_signon.py` 的镜像安装改为：

- `tempfile.mkstemp(dir=dst.parent)` 创建不可预测的临时文件，避免固定 `.tmp` 符号链接；
- 写入后 `flush` + `fsync`；
- `os.replace()` 原子替换；
- 源镜像可选 `--expect-sha256` 校验；
- 目标必须为普通文件且与源哈希一致；
- 记录 `image.json`（源/目标路径、哈希）。

## 2 数据来源

每镜像一次，采集包含：

- 客户端 `SetSignonState`、`SendNetMsg`、`WriteToBuffer`；
- netchan 三个候选 `bf_write` 的 bit cursor（偏移 32/68/104，字段 +12）；
- 服务端 `ReadFromBuffer` 的 `+0x4C` 解码状态；
- 服务端 `ProcessSignonStateMsg`。

## 3 限制

- 缓冲偏移是根据当前二进制反汇编与实测确定的经验值，不是公开 SDK 布局；
- bit cursor 前进只证明写入，不证明 datagram 已发出；
- 每镜像仍为一次运行；
- 时间/包关联尚未建立到具体 datagram。

## 4 下一步

1. 在同一缓冲上 hook datagram 组装/发送，记录 `SendDatagram` 序列号与缓冲消耗；
2. 服务端记录包内消息类型流，确认 6 是否出现；
3. 若 6 从未出现在任何出站 datagram，检查可靠队列/发送窗口。
