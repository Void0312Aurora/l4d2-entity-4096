# N27-D32：13-bit PacketEntities 双端同步的静态门槛

## 0 结论

D32-A/B 尚未完成。当前不能把 2048–4095 号实体放入网络快照。

原因不是缺少位宽数字，而是 Linux 服务端的 `WriteDeltaEntities` 对这两个字段
采用**内联掩码写入**，而不是客户端那样的 `WriteUBitLong(push 0xb)` 调用：

- 没有单一的 `11` 立即数可改；
- 位宽同时影响掩码表基址、剩余位检查、慢路径宽度和游标推进；
- 只改一处会静默写错后续字段。

客户端侧已有 `tools/net_patch_plan.py` 的 13/13 计划，但本机没有计划所要求的
`engine.dll` 源文件（sha256 `8a6d4680…`），`out/engine.4096.n4s.dll` 只是
存储层构建，不包含 13-bit PacketEntities。

## 1 服务端 m_nMaxEntries 写入序列

`engine_srv.so+0x1DD988` 起：

```
1DD994  lea    0xb(%esi),%ecx        ; 可用位检查按 11
1DD9B5  and    0x3e2dcc(%edi,%ecx,4),%edx   ; 11 位掩码表
1DD9C8  mov    $0x20,%edx
1DD9CD  sub    %ecx,%edx
1DD9CF  cmp    $0xa,%edx             ; 跨 32 位边界判断
1DD9D8  addl   $0xb,0xc(%eax)        ; 游标 +11
```

慢路径还会使用 `mov $0xb` 与另一张掩码表基址。

因此“把 11 改成 13”至少涉及：

1. 可用位检查 `+11 → +13`；
2. 掩码表选择/索引（13 位对应的表项）；
3. 跨 32 位边界的余量判断；
4. 游标推进 `+11 → +13`；
5. 慢路径的宽度常数与表基址。

## 2 m_nUpdatedEntries 写入序列

同一函数后段再次出现同样的内联模式（`0x3e2dcc` 掩码、`mov $0xb` 慢路径、
`addl $0xb` 推进），不能只改一处。

## 3 客户端计划状态

`tools/net_patch_plan.py` 已包含 13/13 的 13 个改动点：

- 两个写端 `push 0xb → push 0xd`；
- 回填区 `+2` 游标推进；
- 读端两组 `cmp/shr/mask/add` 与慢路径 `numBits=13`。

但执行 `--check` 需要原始 `engine.dll`：

```
sha256 8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86
```

当前配置路径 `/run/media/.../SteamLibrary/.../engine.dll` 不存在，无法完成
客户端构建与低索引双端验证。

## 4 D32 阶段状态

| 阶段 | 状态 |
|---|---|
| A 服务端 13-bit 写端 | 未完成（内联写需重写/掩码表方案） |
| B Proton 客户端 13-bit 读端 | 计划存在，缺源 DLL |
| C 首次跨 2048 | 禁止进行 |
| D 高索引实体 | 禁止进行 |
| E 稳定性 | 未开始 |

在 A/B 完成前，服务端 4096 镜像只能用于低索引存储/帧回归，不能用于高索引联机。

## 5 下一步

1. 从 13 位掩码需求反推服务端掩码表基址，或注入等价 `WriteUBitLong` 调用；
2. 为服务端写端建立与客户端 `net_patch_plan.py` 对称的可执行 patch plan；
3. 恢复 `engine.dll` 源文件后构建 13-bit 客户端；
4. 先低索引双端联机，再按 2047/2048/2049/4095 边界测试。

## 6 构建器小修

`build_n27_4096.py` 不再硬编码 `changed=2`，而是实际统计差异并断言必须为 2。
