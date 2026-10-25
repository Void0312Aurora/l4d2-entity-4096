# N27-D34：PE 校验和修复与首次双端 13-bit 实测

## 0 结论

客户端 13-bit DLL 的 PE 校验和已修正并通过独立校验；首次双端 13-bit 低索引测试
**失败**，客户端明确报告：

```
Netchannel: failed reading message svc_PacketEntities
Bad delta bits
DIDNT FINISH PARSING svc_PacketEntities
Host_Error: CL_CopyExistingEntity: missing client entity 9
```

因此服务端候选 13-bit 写端仍不正确，不能进入高索引测试。

## 1 客户端构建器修正

`tools/net_apply_13bit.py` 修复：

- 安全目录改为 `opt+128`（DataDirectory[4]）；
- 校验和使用补丁后的 `out`，而不是原始 `blob`；
- 校验和算法改为 dword 累加、跳过 checksum dword、按文件长度补齐。

独立 `pefile` 校验：

```
field     0x4A4559
computed  0x4A4559
```

新 DLL：

```
out/engine.4096.13bit.dll
sha256 b143902702ec7affce6adb33df461b008debe192df77b3b928191c56aa71f790
```

## 2 首次双端测试

- 客户端：上述 13-bit `engine.dll`（临时替换，测试后已恢复原版）；
- 服务端：`/tmp/n27/n27_full_4096_13bit.so`
  `sha256 77b04976b57b6b0653504034a3b53ba91ff37675f98094da79f7f4af1bb5af56`
- 低索引地图：`c1m1_hotel`。

结果：客户端进入主菜单并弹出控制台错误，未进入地图。

截图：`data/n27d34/client_parse_error.jpg`

## 3 这意味着什么

客户端确实按 13-bit 格式读取了 PacketEntities，但随后位流边界错位，
说明服务端写端至少有一处没有同步：

- `m_nMaxEntries` 的快速/慢速路径；
- `m_nUpdatedEntries` 的写宽或游标推进；
- 13-bit 掩码列（候选 `0x3E2DD4`）；
- 跨界时慢路径宽度。

本轮候选服务端补丁修改了 9 处（`tools/linux/patch_n27_13bit.py`），但结果证明
补丁仍不完整或掩码列不对，不能作为 13-bit 写端。

## 4 环境状态

- 客户端 `engine.dll` 已恢复：
  `8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86`；
- 服务端测试镜像只存在于 `/tmp`，未安装到生产目录。

## 5 下一步

1. 离线位流回放：对同一组字段值分别用 11-bit 原版与 13-bit 计划编码，逐 bit 比较；
2. 先验证 13 位掩码表项和慢路径，再改服务端；
3. 服务端修好后重复本双端低索引测试，目标是进入地图且无 `failed reading`；
4. 通过后再跨 2048。
