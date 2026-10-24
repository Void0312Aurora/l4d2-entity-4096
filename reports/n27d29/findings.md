# N27-D29：单站点修复恢复 BaselineAck 与 Signon 6

## 0 结论

将 `ProcessBaselineAck` 中唯一的帧成员读取从旧偏移迁移到新偏移：

```
engine_srv.so+0xE90A3
- 8B 88 18 01 00 00   mov ecx,[eax+0x118]
+ 8B 88 18 02 00 00   mov ecx,[eax+0x218]
```

结果：

| 镜像 | PBA 返回 | 服务端 Signon 解码 |
|---|---|---|
| frameonly（旧） | 0 | 2,3,4,5 |
| frameonly + fix | **1** | **2,3,4,5,6** |
| pristine | 1 | 2,3,4,5,6 |

两次独立修复运行均得到 PBA=1、Signon 2–6，未再命中 `snapshot_null`。

## 1 因果链

```
F2 将 CClientFrame.snapshot 从 +0x118 迁移到 +0x218
ProcessBaselineAck 仍读取 +0x118
→ 读到 0（或位图内容）
→ +0xE933F snapshot_null
→ return 0
→ CLC_BaselineAck::Process = 0
→ 当前消息流结束
→ SignonState(6) 不再解析
```

单站点修复直接打断了这条链，构成干预实验证据。

## 2 构建集成

`data/linux/n27b_frame_member_sites.csv` 已加入：

```
function  _ZN11CBaseClient18ProcessBaselineAckEP15CLC_BaselineAck
elf_addr  0xE90A3
old_disp  0x118
new_disp  0x218
old_bytes 8B 88 18 01 00 00
```

`build_n27_frame.py` 重新构建的镜像与手工单点补丁 SHA-256 完全一致：

```
24a246933e5ca3b9c5c30bccd5d0c4656a284f4ccc717d916914610ed60471db
```

changed_bytes 从 59 变为 60。

## 3 重要限制

- 协议链恢复，但客户端 console 仍停在 `Receiving uncompressed update from server`；
- 因此不能宣布 75% 卡载入或 4096 联机已经修复；
- 两次运行都是协议层验证，不是完整功能验证；
- `ProcessBaselineAck` 内是否还有其他旧偏移读取尚未完成全量审计；
- 功能正控（原版进入地图）仍未建立。

## 4 下一步

1. 对 `ProcessBaselineAck` 内所有 `CClientFrame*` 访问做操作数级审计；
2. 检查其他未迁移帧成员读取（静态门禁）；
3. 恢复功能正控，确认协议修复是否同时改善实际加载；
4. 若加载仍卡住，继续定位下一个独立故障。
