# N27-D35：13-bit 双端低索引联机成功

## 0 结论

客户端 13-bit DLL + 服务端 13-bit 写端首次在 Proton 环境进入地图。

- 客户端 `engine.dll`：`b143902702ec7affce6adb33df461b008debe192df77b3b928191c56aa71f790`
- 服务端镜像：`8b81e755e2fb42e9788f8671bf8a35d2c05ce6dbb8432f4d4cb8143204ee905f`
- 地图：`c1m1_hotel`
- 截图：`data/n27d35/13bit_map.jpg`

客户端没有出现 `failed reading svc_PacketEntities` / `Bad delta bits`。

## 1 服务端补丁修正

D34 的 9 站点版本在客户端解析 PacketEntities 时失败。D35 增加两处 **34 位保留区**修正：

```
0x1DDABA  lea 0x20(%esi) -> lea 0x22(%esi)   ; 保留区可用位检查 +2
0x1DDB1A  addl $0x20,0xc(%eax) -> $0x22      ; 游标推进 32 -> 34
```

原因：13-bit `m_nMaxEntries` 与 13-bit `m_nUpdatedEntries` 使回填区从 32 位变为
34 位（13+20+1），body 起点必须后移 2 位。仅改字段宽度会导致客户端在 body 处
错位，正是 D34 的 `Bad delta bits`。

服务端最终 11 个站点：

- max 写宽/掩码/跨界/推进/慢路径；
- updated 写宽/掩码/跨界/慢路径；
- 保留区检查与游标 +2。

## 2 验收

- 客户端进入地图；
- 无 PacketEntities 解析错误；
- 服务端 `Host_NewGame` 正常；
- 基线 ACK 持续处理（本轮未单独统计，但地图内无网络错误）。

## 3 限制

- 本轮仍是低索引实体（<2048）；
- 客户端 DLL 只含 13-bit 协议补丁，不含 Windows 4096 存储扩容；
- 尚未构造 index ≥2048 的真实网络实体；
- 尚未验证更新/删除/重连。

## 4 下一步

1. 将 13-bit 与 `engine.4096.n4s.dll` 存储补丁合并；
2. 构造真实高索引实体（非篡改 num_edicts）；
3. 验证服务端快照、客户端解析与实体创建；
4. 更新/删除、边界与稳定性。
