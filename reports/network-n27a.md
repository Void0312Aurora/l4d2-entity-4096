# N27-A：`CClientFrame` 类型化引用闭环与借用位图生命周期

> 对象：原版 `engine_srv.so`（sha256 `5fa15f28…309b7`），ELF 坐标。
> 本轮只做类型化还原，不修改二进制。

## 1 `CClientFrame` 成员表（修正 N25）

| 偏移 | 大小 | 语义 | 所有权 |
|---|---|---|---|
| `+0x000` | 4 | vtable | — |
| `+0x004` | 4 | 整型字段（`C1(int)` 写入） | 值 |
| `+0x008` | 4 | 快照 tick（来自 `CFrameSnapshot+4`） | 值 |
| `+0x00C` | `0x100` | 内联实体位图（2048 bit） | 内联 |
| `+0x10C` | 4 | **借用指针**：指向 `CBaseClient+0x10C` | 不拥有、不释放 |
| `+0x110` | 4 | **拥有指针**：`CopyFrame` 中 `new(0x100)` | `~CClientFrame` 释放 |
| `+0x114` | 4 | **帧链表 next**（N25 原记“未命名”） | `CClientFrameManager` |
| `+0x118` | 4 | `CFrameSnapshot*`（引用计数） | `SetSnapshot` 管理 |
| `sizeof` | `0x11C` | | |

### 1.1 构造/复制/析构

- `CClientFrame::C1(int)` `0x105560`：`memset(this+0x0C,0,0x100)`，
  `+0x10C/+0x110/+0x114/+0x118` 全部清零；
- `CClientFrame::C2(CFrameSnapshot*)` `0x105710`：同上并调用 `SetSnapshot`；
- `SetSnapshot` `0x105630`：比较 `+0x118`，`AddReference` / `ReleaseReference`；
- `CopyFrame` `0x105780`：复制 `+0x004/+0x008`、`SetSnapshot`、
  `qmemcpy(+0x0C, …, 0x100)`；若源 `+0x110` 非空则 `new(0x100)` 并复制；
- `~CClientFrame` `0x1056A0`：`SetSnapshot(nullptr)`，仅释放 `+0x110`，
  **不释放 `+0x10C`**；
- `CClientFrameManager`（`0x105890` 起）用 `+0x114` 维护链表。

## 2 借用位图的真实所有者（N25 未决项 2 闭环）

`CBaseServer::WriteDeltaEntities` 中的关键序列（`0x1DDE90`）：

```asm
lea edx, [eax+10Ch]      ; eax = client
mov ecx, 40h
xor eax, eax
mov edi, edx
rep stosd                ; memset(client+0x10C, 0, 0x100)
mov eax, [ebp+10h]       ; eax = frame
mov [eax+10Ch], edx      ; frame+0x10C = &client->0x10C
```

后续 `0x1DE522`：`mov eax,[eax+0x10C]`，再按位 `or` 置位，
即**帧通过借用指针直接写客户端位图**。

因此：

- 借用位图不是独立堆对象，而是 **`CBaseClient` 内联的 2048 bit 位图**，
  位于 `CBaseClient+0x10C`，长度 `0x100`；
- 生命周期等于 `CBaseClient` 对象；帧不得比客户端活得久（当前调用关系满足）；
- 该位图同时被 `CBaseClient` 自己的基线逻辑使用：
  - 构造器 `0xEB3F3`：`memset(this+0x10C,0,0x100)`；
  - `FreeBaselines` `0xE75B6`：`memset(this+0x10C,0,0x100)`；
  - `ProcessBaselineAck` `0xE90B1/0xE90B7`：从 `+0x10C` 起按 64 个 dword 扫描；
  - `WriteDeltaEntities` `0x1DDE90`：同上 memset。

### 2.1 布局后果

`CBaseClient` 在位图之后仍有字段：

- `+0x20C`：基线 ack 计数（`ProcessBaselineAck` 中 `this+131`）；
- 更远处直到 `+0x1D6E4` 量级的字段（构造/析构中可见 `+30137`、`+30143` 等索引）。

所以 **不能把 `CBaseClient+0x10C` 原地扩到 0x200**：那会整体推移
0x20C 之后的全部字段，涉及数百处引用，不属于可补丁范围。

## 3 迁移设计建议（供 N27-B）

### 3.1 帧内联位图

`0x100 → 0x200`，帧大小 `0x11C → 0x21C`，四个成员整体后移 0x100：

```
+0x10C → +0x20C   (borrowed ptr)
+0x110 → +0x210   (owned ptr)
+0x114 → +0x214   (next link)
+0x118 → +0x218   (snapshot ptr)
```

已类型化的访问点集中在 10 个函数内（见 `data/linux/clientframe_fields.csv`），
其中 `0x114` 链表访问 5 处、`0x110` 4 处、`0x118` 6 处、`0x10C` 3 处。

### 3.2 客户端借用位图

推荐把 `CBaseClient+0x10C` 从**内联数组**改为**指针**（4 字节），
指向单独分配的 `0x200` 位图：

1. 构造器：分配 0x200 并清零，存入 `+0x10C`；析构释放；
2. `FreeBaselines` / `WriteDeltaEntities`：改为对指针目标 memset 0x200；
3. `WriteDeltaEntities` 把该指针写入 `frame+0x20C`；
4. `ProcessBaselineAck`：把“从 `this+0x10C` 起按 dword 扫描”改为
   “先取指针，再按 dword 扫描 0x80 个 dword”。

这样 `CBaseClient` 的其它字段偏移完全不动，避免大对象整体重排。

风险：`ProcessBaselineAck` 是直接位扫描，重写需要保持位序与哨兵语义一致；
必须在 N27-D 的隔离镜像里单独回归。

## 4 本轮结论

- `CClientFrame` 四个尾部成员已全部类型化，`+0x114` 确认为帧链表；
- `+0x10C` 借用指针的**所有者、生命周期与读写点**已闭环：
  所有者是 `CBaseClient`，帧只写不拥有；
- 由此确定 N27 的真正难点不在“外部堆位图”，而在
  **CBaseClient 内联位图无法原地扩容**，需要指针化改造；
- N25 的两项未决（借用位图生命周期、类型化成员枚举）就此关闭。

下一步 N27-B：按 §3 设计对象迁移与客户端位图指针化，
形成可执行的补丁清单，再进入 N27-C（栈位图重排）与 N27-D（隔离 ELF 构建）。
