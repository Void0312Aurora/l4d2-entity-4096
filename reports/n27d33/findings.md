# N27-D33：客户端 13-bit DLL 已生成；服务端写端仍未闭环

## 0 结论

本轮完成了客户端侧的实际补丁构建，但没有完成服务端 13-bit 写端，因此**没有**进行
双端 13-bit 联机测试，也没有跨 2048。

## 1 客户端源文件已恢复

此前 D32 认为 `engine.dll` 缺失，实际标准安装路径存在：

```
/home/void0312/.steam/debian-installation/steamapps/common/Left 4 Dead 2/bin/engine.dll
sha256 8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86
```

与 `net_patch_plan.py` 记录的 build 完全一致。

`net_patch_plan.py --check` 对真实 DLL 运行结果：

- 13 个站点全部 `ok`；
- 字段位置不变量全部通过；
- 掩码 `0x1FFF @0x103ECE84` 存在；
- `check PASSED`。

## 2 客户端 13-bit DLL 已生成

新增 `tools/net_apply_13bit.py`：

- 校验源 DLL SHA；
- 逐站点校验 `expect` 字节；
- 应用 13 个补丁；
- 重算 PE checksum；
- 输出 `out/engine.4096.13bit.dll`。

结果：

```
applied 13 sites, 18 changed bytes
out sha256 757867dd8a60c422aa99273b285989b2028db38eedac23a8615189d997466404
```

这是可加载的客户端候选，但尚未替换 Steam 安装。

## 3 服务端写端仍缺可验证补丁

服务端 `WriteDeltaEntities` 使用内联掩码表写入：

- 11 位：`0x3e2dcc`
- 6 位：`0x3e2db8`
- 20 位：`0x3e2df0`

基址随位宽每 bit 相差 4 字节，提示表布局存在“位宽列”。如果该假设成立，13 位可能对应：

```
0x3e2dcc + 2*4 = 0x3e2dd4
```

但同时还必须改：

- 可用位检查 `lea 0xb` → `lea 0xd`；
- 跨界判断 `cmp $0xa` → `cmp $0xc`；
- 游标推进 `addl $0xb` → `addl $0xd`；
- 慢路径宽度常数与掩码表。

**这些尚未被运行时验证，不能直接应用。**

掩码表位于 `.bss`，静态文件里没有内容；本轮尝试 attach/dump 运行时表未成功
（ptrace 限制/加载时序），因此没有完成“13 位掩码地址正确”的证明。

## 4 阶段状态

| 项 | 状态 |
|---|---|
| 客户端 13-bit DLL | 已生成，未安装 |
| 客户端计划校验 | PASS |
| 服务端 13-bit 写端 | 未完成 |
| 双端低索引联机 | 未测试 |
| 跨 2048 | 未测试 |

## 5 下一步

1. 在可控制的服务端启动方式下 dump 运行时掩码表，确认 13 位基址和索引公式；
2. 建立服务端 patch plan（与客户端 13 站点对称）；
3. 先做**离线位流回放**：11-bit 原版 vs 13-bit 新格式，逐字段比较；
4. 双端低索引进图通过后，再跨 2048。
