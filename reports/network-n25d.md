# N25-D：传输层容量与 13 位掩码复用验证

> 对象：`engine_srv.so`（build 17033453）。未修改任何二进制。
> 运行时数据来自 gdb 断点 `CGameServer::SpawnServer`（静态初始化完成后）。

## 1 13 位掩码：已可复用（原"必须扩容"结论修正）

### 1.1 表结构与初始化

`CBitWriteMasksInit::CBitWriteMasksInit()`（`0x234B40`，125 B）：

```c
for (i = 0; i != 32; ++i) {            // bit offset
  v3 = (1 << i) - 1;
  for (j = 0; j != 33; ++j) {          // field width
    g_BitWriteMasks[j + i*33] = v3;
    if (j + i <= 0x1F)
      g_BitWriteMasks[j + i*33] |= -(1 << (i + j));
  }
}
```

- 符号 `g_BitWriteMasks` 位于 `0x3E2DA0`，大小 **4224 = 32×33×4**；
- 行内第 `j` 个 dword 即"宽度 j、起始位偏移 i"的清除掩码；
- 6 位基址 `0x3E2DB8 = 0x3E2DA0 + 6*4`，11 位 `0x3E2DCC = +11*4`，
  20 位 `0x3E2DF0 = +20*4` —— 与指令位移完全吻合；
- **13 位基址 `0x3E2DD4` 是表的合法列，无需新增表项。**

### 1.2 运行时验证

| 索引 | 地址 | 值 | 含义 |
|---|---|---|---|
| offset0,width11 | `0x3E2DCC` | `0xFFFFF800` | 清 bit0..10 |
| offset0,width13 | `0x3E2DD4` | `0xFFFFE000` | 清 bit0..12 |
| offset1,width13 | `0x3E2E58` | `0xFFFFC001` | 清 bit1..13 |
| offset31,width13 | `0x3E3DD0` | `0x7FFFFFFF` | 只剩 bit31 |
| offset0,width20 | `0x3E2DF0` | `0xFFF00000` | 清 bit0..19 |

### 1.3 补丁形态（固定长度操作数，非代码扩容）

11→13 位需要同时改：

| 位置 | 原 | 新 |
|---|---|---|
| 掩码位移 | `dword_3E2DCC` | `dword_3E2DD4` |
| 位宽常量 | `0xB` | `0xD` |
| 跨 DWORD 判定 | `cmp edx, 0xA` | `cmp edx, 0xC` |
| 第二字掩码索引 | `[11 - (32-v7)]` | `[13 - (32-v7)]` |
| bit cursor 推进 | `add [..+0xC],0xB` | `0xD` |

全部是立即数/位移替换，**指令长度不变**。原 CSV 的 `needs_code_expansion=yes`
已修正为 `no`（仍需多点一致修改与回归验证）。

## 2 WriteUBitVar：4095 无损

`bf_write::WriteUBitVar`（`0x230F50`）分支：

| 输入范围 | 编码 | 位数 |
|---|---|---|
| `≤0xF` | 前缀 `00` + 4 位 | 6 |
| `≤0xFF` | 前缀 `01` + 4+8 位 | 10 |
| `≤0xFFF` | 前缀 `10` + 12 位 | 14 |
| `>0xFFF` | 前缀 `11` + 28 位 | 34 |

解码 `old_bf_read::ReadUBitVar`（`0x2333E0`）用 6 位选择子
（`&0x30` → `0x10/0x20/0x30` 分支）完全对称。

4096 实体的最大差值为 **4095**，落在 `≤0xFFF` 的 14 位分支，**无损**。
4096 本身不会出现在差值中（`value = cur - prev - 1`，最大 4095）。

客户端 `engine.so` 为 stripped，`ReadUBitVar` 的字节级对称性尚未确认，
但协议格式固定且同源构建，风险低；标记为 `unresolved`（需字节模式匹配复核）。

## 3 长度与缓冲

| 限制 | 值 | 结论 |
|---|---|---|
| `m_nLength` 字段 | 20 位 = 1,048,575 bit ≈ **128 KiB** | 上限充足 |
| `NET_AllocPayload` 分配 | `operator new(0x37AB8)` ≈ **222 KiB** | 大于 128 KiB |
| 分片 | `CNetChan::CreateFragmentsFromBuffer` 存在 | 支持超过单包上限的消息 |

三个容量限制分离：

- 字段容量（128 KiB）< 缓冲容量（约 222 KiB），长度字段不是瓶颈；
- 真正的瓶颈是 netchan 单包上限/分片与实体体实际大小；
- 4096 实体全量快照的实际位数**尚未实测**，无法静态断言不超过 20 位。

因此 `m_nLength` 在 CSV 中由 `no_change` 改为 **`unresolved`**。

## 4 本轮后冻结的网络结论

1. `m_nMaxEntries`：13 位，生产链确认；
2. `m_nUpdatedEntries`：13 位，计数确认；
3. 实体索引：UBitVar 差值（最大 4095，14 位分支）；
4. 位写入：13 位掩码可复用，固定长度操作数替换；
5. 长度字段：20 位保留，实测待做；
6. 分片路径存在，缓冲大于字段上限。

结构性工作（帧布局迁移、成员偏移、栈重排、借用位图生命周期）不在本轮范围，
继续按类型/函数推进。

## 5 剩余风险

- 客户端 `ReadUBitVar` 的字节级对称性；
- 4096 实体全量快照的实际位数与分片行为；
- `NET_AllocPayload` 立即数 `0x37AB8` 的语义（IDA 以 `stru_37AB8` 符号显示，
  位于 .bss，需动态确认实际分配大小）。
