# N27-D30：F2 有界审计与功能正控尝试

## 0 结论

- `ProcessBaselineAck` 内确认只有一处 `CClientFrame*` 尾部读取（`+0x118`），已在 D29 迁移；
- 对 35 个帧消费者函数做位移扫描，发现 78 个旧位移样式的操作数，其中 16 个不在 CSV；
- 16 个中大多数是 `-0x118(%ebp)` 之类的栈局部变量，不是帧成员；
- 一个需要继续确认的真实候选：
  `CBaseServer::WriteDeltaEntities+0x1DDE90` 的 `lea 0x10C(%eax)`，
  随后 `rep stosd` 清零 256 字节，疑似旧内联实体位图；
- 功能正控仍未建立：无原生 Windows 客户端；Proton + pristine 无调试器仍停在
  `Receiving uncompressed update`，且 `xdotool` 未找到游戏窗口。

## 1 D29 修复的回归强度

两次修复运行：

- BaselineAck 全部返回 1（25/25、10/10）；
- Signon 2–6 全部解码；
- `snapshot_null` 命中 0；
- 后续 BaselineAck 持续处理。

因此 D29 不只是“让 6 出现”，而是恢复了基线确认交互。

## 2 审计方法

对包含以下符号的函数做有界扫描：

- `CClientFrame*`、`ClientFrameManager`；
- `SendSnapshot`、`WriteDeltaEntities`、`ProcessBaselineAck`。

在反汇编中匹配 `0x10C/0x110/0x114/0x118(%e...)`，并与
`n27b_frame_member_sites.csv` 的 `elf_addr` 对比。

## 3 审计结果

| 类别 | 数量 |
|---|---:|
| 扫描函数 | 35 |
| 命中操作数 | 78 |
| 不在 CSV | 16 |
| 其中栈局部（`-0x118(%ebp)` 等） | 多数 |
| 需进一步确认的真实候选 | `WriteDeltaEntities+0x1DDE90` |

`ProcessBaselineAck+0xE90B1/0xE90CC` 的 `+0x10C/+0x110` 基址是
`CBaseClient*`（`esi`），属于客户端内联位图/C3 范围，不是 `CClientFrame*`，
因此不应加入 F2。

## 4 WriteDeltaEntities 候选

```
1dde90: lea 0x10c(%eax),%edx
1dde96: mov $0x40,%ecx
1dde9b: xor %eax,%eax
1dde9d: mov %edx,%edi
1dde9f: rep stos %eax,%es:(%edi)   ; 清零 0x100 字节
1ddea1: mov 0x10(%ebp),%eax
1ddea4: mov %edx,0x10c(%eax)
```

CSV 已覆盖 `0x1DDEA4` 的 `+0x10C` 存储，但没有覆盖 `0x1DDE90` 的 `lea`。
它是否属于 `CClientFrame*` 仍需按参数/对象类型确认；若确认，则是第二个
与 D29 同类的遗漏（引用的是旧位图区域而非迁移后的字段）。

## 5 功能正控

尝试：

- 原版 Linux 服务端；
- Proton 客户端；
- 不附加 GDB；
- `sv_lan 1`、`sv_password ""`、`sv_consistency 0`。

结果仍为：

```
Receiving uncompressed update from server
```

`xdotool search --name "Left 4 Dead 2"` 没有找到窗口，无法用截图确认画面状态。

因此当前环境不能作为功能正控；需要原生 Windows 客户端或可用的图形会话。

## 6 下一步

1. 确认 `WriteDeltaEntities+0x1DDE90` 的对象类型，必要时加入 F2；
2. 完成其余 16 个候选的栈局部/对象成员分类，形成静态门禁；
3. 在原生 Windows 客户端 + 原版 Linux 服务端上建立功能正控；
4. 正控成立后再测试 D29 修复镜像与 4096 实体容量。
