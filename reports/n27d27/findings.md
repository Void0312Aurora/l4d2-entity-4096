# N27-D27：frameonly 的 ProcessBaselineAck 返回 0

## 0 关键结果

同一次实验中，服务端 `CBaseClient::ProcessBaselineAck` 返回值：

| 镜像 | tick | `ProcessBaselineAck` 返回 | `CLC_BaselineAck::Process` 返回 | Signon 解码 |
|---|---:|---:|---:|---|
| frameonly | 665 | **0** | **0** | 2,3,4,5 |
| pristine | 663 | **1** | **1** | 2,3,4,5,6 |

pristine 后续 BaselineAck 也持续返回 1。

因此：

> frameonly 服务端成功解码了 BaselineAck，但处理函数返回失败；紧随其后的
> SignonState(6) 没有被解析。

这与此前“ACK 之后消息流没有继续”的观察一致，并给出了具体的失败返回点。

## 1 调用链

```
CLC_BaselineAck::ReadFromBuffer → 成功 (tick=665)
CLC_BaselineAck::Process       → 0
CBaseClient::ProcessBaselineAck→ 0
（随后无 NET_SignonState(6) 解码）
```

pristine 同一路径返回 1，并继续解码 Signon 6。

## 2 解释力

`ProcessBaselineAck` 返回 0 很可能导致 `_ProcessMessages` 终止当前消息流；
但本轮**尚未直接观测** `_ProcessMessages` 的退出分支，因此不能把它写成已证实的
唯一原因。

更准确的表述：

> 首个具有明确语义的差异是 `ProcessBaselineAck` 返回值：frameonly 0，pristine 1。
> 该返回值与后续 Signon 6 缺失在时间与调用顺序上吻合。

## 3 下一步

1. 在 `_ProcessMessages` 记录 Process 返回后的分支/是否继续读取下一个类型；
2. 反汇编 `ProcessBaselineAck`（`engine_srv.so+0xE9030`），确认返回 0 的具体条件；
3. 检查该条件读取的 baseline/frame 状态，并与 F2 帧迁移关联；
4. 重复实验确认 0/1 差异稳定。

## 4 限制

- 每镜像一次；
- tick 665 vs 663 很可能只是运行时机差异；
- 尚未证明返回值 0 是 Signon 6 缺失的充分原因；
- 功能正控仍未建立。
