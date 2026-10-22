# N25：Linux 快照位图与容量依赖（A/B/C）

> 对象：`engine_srv.so`（sha256 `5fa15f28…`，build 17033453）。
> 全部为 ELF 坐标；`.text` 的 `vaddr == file offset == 0x81850` 起。
> 本轮**未修改任何二进制**。

## 1 已确认的位图语义（A/B 结论）

- 位图位号 **bit = entityIndex 直接相等**；
- 扫描从 `current = -1` 起，`candidate = current + 1`，合法位号 `0..2047`；
- 因此 `0x1DDEF5` 的 `cmp candidate, 0x7FF; jg` 语义正确：
  索引 2047 可处理，2048 才终止（哨兵 9999）。
- 扩容后最大合法位号 4095，所以该处应改为 `cmp 0xFFF; jg`（**仅此一处**，
  不能据此类推替换其它 `0x7FF`）。

## 2 CClientFrame 布局（已恢复）

| 偏移 | 内容 | 大小 |
|---|---|---|
| `+0x00` | vtable | 4 |
| `+0x04/+0x08` | tick 等字段 | 8 |
| `+0x0C` | **内联位图（2048 bit）** | `0x100` |
| `+0x10C` | 指向第二块 256B 位图的指针（借用，指向外部对象 `+0x10C`） | 4 |
| `+0x110` | 指向堆位图的指针（`CopyFrame` 中 `new(0x100)`，析构释放） | 4 |
| `+0x114` | 未命名 | 4 |
| `+0x118` | `CFrameSnapshot*`（引用计数） | 4 |
| `sizeof` | | **`0x11C`** |

证据：

- 构造器 `memset(this+12,0,0x100)`；
- `CopyFrame`：`qmemcpy(this+12,a2+12,256)`、`new(0x100)` + 拷贝 256 字节到 `+0x110`；
- 析构：`operator delete(*(this+68))`（即 `+0x110`），`+0x10C` 不释放（借用指针）；
- `SetSnapshot` 管理 `+0x118`。

## 3 审计矩阵

| 类型 | 原值 | 目标值 | 站点数 | 结论 |
|---|---|---|---|---|
| 最大位号 | `0x7FF` | `0xFFF` | 1 | 必须改（`0x1DDEF5`，`jg` 配合正确） |
| 位图字节数 | `0x100` | `0x200` | 6 | 构造/复制/清零，必须改 |
| DWORD 数量 | `0x40` | `0x80` | 1 | 栈位图清零循环上界，必须改 |
| 帧大小 | `0x11C` | `0x21C` | 4 | 3 个内存池 + 1 个 `operator new` |
| 成员偏移 | `+0x10C..+0x118` | `+0x20C..+0x218` | 217 函数（粗筛上限） | **需类型化枚举，不能按立即数批量改** |
| 位宽 | 11 | 13 | 2 处内联写 + 2 处内联读 | 需重写内联位写入序列，非立即数替换 |

### 3.1 `0x11C` 的四个真站点与一个假阳性

| 地址 | 函数 | 语义 | 结论 |
|---|---|---|---|
| `0x106444` | `CClientState::CClientState` | `CUtlMemoryPool(0x11C,0x80,2)` | 帧池元素大小 |
| `0x1DAC04` | `CGameClient::CGameClient` | 同上 | 帧池元素大小 |
| `0x162780` | `CHLTVServer::CHLTVServer` | 同上 | 帧池元素大小 |
| `0x15D0AE` | `CHLTVClientState::ProcessPacketEntities` | `operator new(0x11C)` | 整帧副本 |
| `0x0FF9C6` | `CBaseServer::WriteTempEntities` | `sub esp,0x11C` | **假阳性**：函数内不构造 `CClientFrame`、不引用其 vtable、无帧拷贝；纯栈局部空间，语义无关 |

### 3.2 栈位图 `var_130`

`WriteDeltaEntities` 入口：

```
lea edi,[ebp+var_130]
mov ecx,0x40
rep stosd              ; 256 字节清零
```

置位点 `0x1DE9D4`：`or [ebp+edx*4+var_130], eax`；
检测点 `0x1DEDEF`：`test [ebp+eax+var_130], ebx`；
另有 `0x1DDE90` 处对帧 `+0x10C` 指针位图做 `memset(...,0x100)`。

扩容到 `0x200` 后，`var_130` 周围局部变量布局必须重排（栈帧增大、部分 `[ebp-...]`
位移变化，可能需要指令加宽），**不能只把 `0x40` 改成 `0x80`**。

## 4 机器可读清单

`data/linux/migration_sites.csv`（21 行）：

| 状态 | 行数 |
|---|---|
| `must_change` | 8 |
| `unresolved` | 9 |
| `no_change` | 4 |

字段：`elf_addr, file_offset, function, object, orig_instr, old_value, new_value,
basis, needs_code_expansion, status`。

其中 4 个 `no_change` 明确记录为"数值相同但语义无关"：
`WriteTempEntities` 栈空间、`20 位 m_nLength`（暂定）、位图位测试基址 `+0x0C`、
析构释放（无立即数）。

## 5 未决项（不得视为无须修改）

1. 帧成员偏移 `+0x10C..+0x118 → +0x20C..+0x218` 的类型化枚举
   （217 函数只是按立即数粗筛的上限，必须用 IDA 类型/调用关系收敛）；
2. `+0x10C` 借用位图的外部所有者与生命周期；
3. 11→13 位内联位写入的替换序列（掩码表 `dword_3E2DCC` 只覆盖 11 位偏移，
   13 位需要新的掩码计算或表项）；
4. `0x3A7F50` 镜像全局的真实读者（当前无绝对引用）；
5. 栈位图扩容后的局部变量重排与指令加宽需求。

## 6 下一步：N25-D

只针对已确认路径验证：

1. `bf_write::WriteUBitVar(4095)` 的编码分支与客户端解码；
2. 20 位 `m_nLength` 在 4096 实体、高更新率下的实际位数；
3. `NET_AllocPayload`/`bf_write` 缓冲上限与分包；
4. 完成后即可把 CSV 的 `unresolved` 收敛为 Phase B 补丁清单。
