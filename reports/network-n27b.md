# N27-B：`CClientFrame` 与客户端基线位图的指令级补丁清单

> 原版 `engine_srv.so`（sha256 `5fa15f28…309b7`），ELF 坐标；本轮不部署、不构建镜像。

## 1 先修正 N27-A CSV 的归属错误

| 地址 | 实际指令 | 归属 |
|---|---|---|
| `0x1DE9D4` | `or %eax,-0x130(%ebp,%edx,4)` | **栈位图**（N27-C） |
| `0x1DEDEF` | `test %ebx,-0x130(%ebp,%eax,1)` | **栈位图**（N27-C） |
| `0x1DEDFE` | `test %ebx,0xc(%esi,%eax,1)` | 帧内联位图 |

原始字节：

```
1DE9D4  09 84 95 D0 FE FF FF
1DEDEF  85 9C 05 D0 FE FF FF
1DEDFE  85 5C 06 0C
```

`data/linux/clientframe_fields.csv` 已修正，栈位图单独成行。

## 2 客户端位图消费者闭环（硬门禁 1）

对全二进制做两类穷举：

1. 所有 `lea/add reg,[reg+0x10C]` 取地址点；
2. 所有以 `+0x10C` 为位移的读写点，并与基线字段 `+0x104/+0x108/+0x20C` 交叉过滤。

结果：真正把 `CBaseClient+0x10C` 当位图使用的函数只有 4 个：

| 函数 | 站点 | 作用 |
|---|---|---|
| `CBaseClient::CBaseClient` | `0xEB3E3/0xEB3F3` | 清零 0x100 |
| `CBaseClient::FreeBaselines` | `0xE75B6/0xE75BC` | 清零 |
| `CBaseClient::ProcessBaselineAck` | `0xE90B1/0xE90B7/0xE90CC/0xE90D2/0xE90E6/0xE91E2/0xE91FF` | 位图扫描 |
| `CBaseServer::WriteDeltaEntities` | `0x1DDE90/0x1DDE96/0x1DDEA4/0x1DE522` | 清零并写入帧借用指针 |

排除的假阳性：

- `CGameServer::SpawnServer` 的 `0x10C/0x20C` 是 `movss` 浮点字段，不是客户端位图；
- `CHLTVServer::StartRelay/StartMaster` 的 `add [ebx+0x10C],1` 是 HLTV 对象计数器；
- `CBaseServer::C1` 的 `0x10C` 是服务器对象字段。

## 3 客户端对象生命周期（硬门禁 2）

构造：

- `CGameClient::C1(int,CBaseServer)` `0x1DABCF` → `CBaseClient::CBaseClient()`；
- `CHLTVClient::C1(int,CBaseServer)` `0x158C35` → 同上。

析构：

- `CGameClient::D1/D0` → `CBaseClient::~CBaseClient`；
- `CHLTVClient::D1/D0` → 同上；
- 构造失败路径 `0x158D3C`、`0x1DAD16` 也会调用基类析构；
- `_ZThn4_` / `_ZThn8_` 只是跳转 thunk，不会重复析构。

初始化顺序要求：

1. 指针槽 `+0x10C` 必须在任何“原位图清零”之前被赋值；
2. 原构造器在 `0xEB3E3` 设 `ecx=0x40`，`0xEB3F3` 取 `this+0x10C` 地址，随后 `rep stosd`；
   指针化后必须改为“先分配 0x200、存指针、再清零堆内存”，不能先清零后存指针。

## 4 补丁分组

完整逐站点清单：`data/linux/n27b_patch_sites.csv`；
帧成员位移 48 条：`data/linux/n27b_frame_member_sites.csv`。

### F1 · 帧尺寸 `0x11C → 0x21C`（4 处，等长）

`0x106444`、`0x1DAC04`、`0x162780` 的 `CUtlMemoryPool` 元素大小，
以及 `0x15D0AE` 的 `operator new(0x11C)`，全部是 imm32，直接改 `1C 01 00 00 → 1C 02 00 00`。

### F2 · 帧成员整体后移 `0x100`（48 处，等长）

`+0x10C/+0x110/+0x114/+0x118 → +0x20C/+0x210/+0x214/+0x218`，全部 disp32，
逐条替换即可；`+0x0C` 内联位图起点不变，因此位图访问指令本身不需要改位移。

### F3 · 帧内联位图 `0x100 → 0x200`（7 处，等长）

三个构造器的 `mov ecx,0x40`、`CopyFrame` 的三处 `mov ecx,0x40` 改 `0x80`；
`CopyFrame` 的 `operator new(0x100)` 改 `0x200`。

### C1 · 客户端构造分配（需要代码桩）

`0xEB3F3` 的 `lea edx,[ebx+10Ch]` 改为 `call stub_alloc`（5 字节）+ `nop`，
桩放在新增代码段：

```
stub_alloc:
  push 0x200
  call operator new          ; _Znwj
  add  esp,4
  mov  [ebx+0x10C],eax
  mov  edx,eax
  ret
```

随后原 `0xEB3FF mov edi,edx` 与 `rep stosd` 继续执行，`ecx` 由 `0xEB3E3` 改为 `0x80`。

### C2 · 客户端析构释放（需要代码桩）

在 `0xEB2FB` 用 `call stub_free` 替换 `mov eax,[0x2A0070]`，
桩内先释放再补执行原指令：

```
stub_free:
  mov  eax,[ebx+0x10C]
  test eax,eax
  jz   .skip
  push eax
  call operator delete       ; _ZdlPv
  add  esp,4
  mov  dword [ebx+0x10C],0
.skip:
  mov  eax,[0x2A0070]
  ret
```

### C3 · 位图消费者（等长替换，无需扩容）

- `FreeBaselines`：`lea → mov` 取指针，清零计数 `0x40 → 0x80`；
- `ProcessBaselineAck`：
  - `0xE90B1` 改为 `mov eax,[esi+10Ch]`（取指针）；
  - `0xE90B7` 改为 `mov edx,[eax]` + 4×`nop`（bitmap[0]）；
  - `0xE90CC/0xE90D2` 改为 `[eax+4]` + `nop`；
  - 三处 `cmp eax,0x40` 改 `0x80`；
  - 第二段扫描使用的 `-0x20(%ebp)` 基址正是 `0xE90BD` 保存的指针，改后自动指向堆位图；
- `WriteDeltaEntities`：
  - `0x1DDE90` `lea → mov` 取指针；
  - `0x1DDE96` 计数 `0x40 → 0x80`；
  - `0x1DDEA4`、`0x1DE522` 帧字段位移 `0x10C → 0x20C`。

### C4 · 完整性门禁（静态）

补丁后必须重新扫描并确认：

1. 全二进制不存在 `lea/add reg,[reg+0x10C]` 指向客户端位图的残留；
2. 上述四个函数内不再有 `[reg+0x10C]` 形式的位图 dword 访问；
3. `+0x110..+0x20B` 的旧内联区不再被任何位图代码引用；
4. 构造/析构桩只在 `CBaseClient` 基类层出现一次，派生类不重复分配/释放。

## 5 风险与未决

- `operator new` 失败时指针为空：当前桩未处理，N27-D 需决定是 `Sys_Error` 还是保留空指针；
- `ProcessBaselineAck` 第二段扫描依赖 `-0x20(%ebp)` 保存基址，补丁后必须复核该保存点未被其它路径覆盖；
- `WriteDeltaEntities` 的 `rep stosd` 计数与 `edx` 指针必须保持同源，不能再出现“指针 + 原位图地址”混用。

## 6 验证顺序（N27-D/E）

| 验证 | 要求 |
|---|---|
| 原版容量回归 | 地图加载、正常快照、baseline ack |
| 客户端生命周期 | 创建、断线、重连、释放，无泄漏/重复释放 |
| 帧管理 | 新增、复制、删除，链表与引用计数正确 |
| 4096 位图边界 | bit 2047/2048/4095 置位与读取 |
| 高索引快照 | 等 N27-C 与游戏逻辑模块迁移后再启用 |

本轮只产出清单，不构建镜像；N27-C 完成栈位图重排后再统一进 N27-D。
