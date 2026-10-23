# N27-D19：`0x1BC301` 间接调用机制静态复原

**分析对象**

| 项 | 值 |
|---|---|
| 文件 | `…/steamapps/common/Left 4 Dead 2/bin/engine.dll`（Windows 32 位 client engine） |
| SHA-256 | `8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86` |
| imagebase | `0x10000000`（`ida_nalt.get_imagebase()` 实测） |
| 分析工具 | IDA Pro 9.5 + idalib（IDA MCP，`ida-domain` API），只读，未修改二进制 |
| 约束 | 纯静态；未运行客户端/服务器；未 patch |

> 坐标约定：本文 `RVA = VA − 0x10000000`。D18 运行期地址 `0x79Exxxxx` 对应 `RVA = 0x79Exxxxx − 0x79E00000`
> （例如 `0x79E4E510 → RVA 0x4E510`）。

---

## 0. 结论摘要（TL;DR）

1. `0x1BC301` 是一条 **vtable slot 3（字节偏移 `+0xC`）的虚调用**：
   `eax = [ [esi] + 0xC ]; ecx = esi; call eax`。
2. `esi` **不是** client frame 对象，而是 **`INetMessage*`（net message 对象）**，
   由 `CNetChan` 按消息类型在 `sub_101B3E60` 中查表得到（`0x1BBFE5` 调用、`0x1BBFEA mov esi,eax`）。
3. 四个运行期目标分别是 **四个具体消息类** 的 slot-3 覆写（RTTI 已验证）：

   | 运行期目标 | RVA | 类 | 类型号 | slot-3 实现 |
   |---|---|---|---|---|
   | `0x79E4E510` | `0x4E510` | `NET_Tick` | 4 | 转发 `[msg+0x50]->vtbl[0x04]` |
   | `0x79E4EE80` | `0x4EE80` | `SVC_GameEvent` | 25 | 转发 `[msg+0x50]->vtbl[0x50]` |
   | `0x79E56E60` | `0x56E60` | `SVC_UserMessage` | 23 | 转发 `[msg+0x50]->vtbl[0x54]` |
   | `0x79E53FE0` | `0x53FE0` | `SVC_PacketEntities` | 26 | 转发 `[msg+0x50]->vtbl[0x5C]` |

4. `[msg+0x50]` 在 `sub_10056EE0`（`CBaseClientState` vtable slot 1；命名推断为 `ConnectionStart`）里被写成
   **`clientstate + 8`**，即 `IServerMessageHandler`（继承 `INetMessageHandler`）子对象指针
   （RTTI base PMD `mdisp = 8` 已验证）。因此 slot 3 的语义是：
   **「把本条消息派发给客户端状态对应的消息处理函数」**，返回值为「处理是否成功」。
5. 于是 `0x1BC301` 是 **按消息类型多目标的通用派发点**，不是「实体更新专用调用」。
   D18 中 frameonly 观察不到 `0x56E60`，等价于 **该轮没有 `svc_UserMessage` 被派发**，
   不是该调用点本身失效（详见 §5）。
6. F2 相关性：**四个转发器函数与其 vtable 本身完全不碰 `CClientFrame`**；
   只有 `svc_PacketEntities` 的派发目标（`0x53FE0 → 0x101EBD60 → 0x10077140 CL_ProcessPacketEntities`）
   进入 `CClientFrameManager` / `CClientFrame` 链（`+0x114` next、`+8` tick）。
   同一路径还暴露一个 **2048 硬编码**实体指针表拷贝（`0x10053440`，常量 `0x800` @ `0x53463`），
   与 F2/实体扩容相关但不是 `CClientFrame` 位图本身（见 §6）。

---

## 1. 字节级验证（任务 1）

`sub_101BBCF0`：`0x101BBCF0–0x101BC616`（含该调用点）。

| RVA | 字节 | 反汇编 | 说明 |
|---|---|---|---|
| `0x1BC2E9` | `E8 C2 9C FF FF` | `call sub_101B5FB0` | 条件函数（处理预算检查） |
| `0x1BC2EE` | `84 C0` | `test al, al` | |
| `0x1BC2F0` | `0F 84 38 02 00 00` | `jz 0x101BC52E` | `F6 + 0x238 = 0x101BC52E`（"processing time exceeded" 分支） |
| `0x1BC2F6` | `C6 47 04 01` | `mov byte ptr [edi+4], 1` | `netchan->m_bProcessingMessages = 1` |
| `0x1BC2FA` | `8B 16` | `mov edx, [esi]` | `edx = msg->vftable` |
| `0x1BC2FC` | `8B 42 0C` | `mov eax, [edx+0Ch]` | **slot 3**（第 4 个虚函数） |
| `0x1BC2FF` | `8B CE` | `mov ecx, esi` | `this = msg` |
| `0x1BC301` | `FF D0` | `call eax` | **间接调用本体** |
| `0x1BC303` | `80 7F 05 00` | `cmp byte ptr [edi+5], 0` | 之后按 `[edi+5]/[edi+6]` 处理 shutdown/abort |
| `0x1BC307` | `C6 47 04 00` | `mov byte ptr [edi+4], 0` | `m_bProcessingMessages = 0` |
| `0x1BC30B` | `0F 85 88 02 00 00` | `jnz 0x101BC599` | |

**置信度：高。** 直接字节读取 + IDA 线性反汇编；`jz` 目标与 `call` 目标均按 rel32 手工复核。

对应 Hex-Rays 伪代码（`line 461`）：

```c
v51 = (*(int (__thiscall **)(int))(*(_DWORD *)v32 + 12))(a1: v32);   // v51: char (AL)
...
if ( v51 == 0 ) { ConDMsg("Netchannel: failed processing message %s.\n", v76); ... }
```

`v51` 被 IDA 类型化为 `char`（AL），与 `test al,al` 一致；`v32` 即 `esi`。

条件函数 `sub_101B5FB0`（`0x101B5FB0–0x101B605B`）：读取全局 cvar 指针（`dword_106B21A4`、
`dword_106B24D4`、`dword_106B27A4`）、`this+17092 (0x42C4)`/`this+17004 (0x4270)`、
以及 `this+16992` 上的时间戳，返回「是否仍可继续处理消息」的 bool。
结构上等价于 `CNetChan` 的 **`CanProcessMessages()`**（名称按行为推断，置信度：中高）。

---

## 2. vtable slot 语义与所属类（任务 2）

### 2.1 槽位定义

- 调用点取的是 **vtable 索引 3 / 字节偏移 `+0xC`**。
- 该槽在接口 **`INetMessage`** 中声明：
  - `??_7INetMessage@@6B@` @ `RVA 0x3500A4`；slot 3 = `__purecall`（`0x10310300`）。
- 基类实现 **`CNetMessage`** 提供默认实现（返回 0 = 未处理）：
  - `??_7CNetMessage@@6B@` @ `RVA 0x35031C`；slot 3 = `sub_100025F0`（`return 0;`）。
- 所有具体消息类都覆写该槽。

**RTTI 直接证据（MSVC Complete Object Locator 解析）**

| 类 | vtable | COL | 继承链 |
|---|---|---|---|
| `SVC_UserMessage` | `0x10358EEC` (`0x358EEC`) | `0x10412760` | `SVC_UserMessage ← CNetMessage ← INetMessage` |
| `NET_Tick` | `0x10356CE4` (`0x356CE4`) | `0x10411B08` | `NET_Tick ← CNetMessage ← INetMessage` |
| `SVC_PacketEntities` | `0x103584DC` (`0x3584DC`) | `0x10412620` | `SVC_PacketEntities ← CNetMessage ← INetMessage` |
| `SVC_GameEvent` | `0x10356EB4` (`0x356EB4`) | `0x10411C98` | `SVC_GameEvent ← CNetMessage ← INetMessage` |

（类型描述符名字形如 `.?AVSVC_UserMessage@@`，由 `??_R0…` / `??_R3…` / `??_R2…` 结构解析得到。）

**vtable 交叉引用（`XrefsTo`）——四个槽位唯一且精确命中**：

| 目标函数 | 被存放到 | = vtable + 0xC |
|---|---|---|
| `0x10056E60` | `0x10358EF8` | `0x10358EEC + 0xC` ✔ |
| `0x1004E510` | `0x10356CF0` | `0x10356CE4 + 0xC` ✔ |
| `0x10053FE0` | `0x103584E8` | `0x103584DC + 0xC` ✔ |
| `0x1004EE80` | `0x10356EC0` | `0x10356EB4 + 0xC` ✔ |

### 2.2 槽语义（由调用点 + 实现共同确定）

- 调用点对返回值判零 → 失败路径 `Netchannel: failed processing message %s.`；
- 四个覆写全部是「转发到客户端状态处理函数」的薄壳（见 §4）；
- 转发目标中 `SVC_GameEvent` 分支的 telemetry 字符串直接写着 **`"CClientState::ProcessGameEvent"`**（`sub_101EBBF0`）。

因此 slot 3 的语义是 **`INetMessage` 的「处理/派发」虚函数**（成功返回非 0）。
**注意**：二进制无 PDB/导出符号，槽位的 C++ 源码级函数名（如 `Process()`）无法从符号恢复，
该命名属于按行为推断（置信度：高；名称本身：推断）。

---

## 3. 四个目标函数（任务 3）

四个函数都是 **14 字节的等价转发壳**（`0x10056E60`、`0x1004E510`、`0x10053FE0`、`0x1004EE80`），
模式统一：

```asm
mov  eax, ecx            ; eax = this (INetMessage*)
mov  ecx, [eax+50h]      ; ecx = this->m_pHandler  (IServerMessageHandler*)
mov  edx, [ecx]          ; edx = handler->vftable
push eax                 ; arg = this (消息对象)
mov  eax, [edx+K]        ; K 因类而异
call eax                 ; handler->vtable[K](msg)
ret
```

| RVA | 类（RTTI） | vtable | slot | 类型号 | 内部转发 K | 派发目标 | 目标语义 | 置信度 |
|---|---|---|---|---|---|---|---|---|
| `0x4E510` | `NET_Tick` | `0x10356CE4` | 3 | 4 | `+0x04` | `0x101EB7D0` | 处理 tick：读 `msg+84` tick、`msg+88/92` 帧时间浮点，调用 `[clientstate+16]->vtbl[0x110]`，更新 `clientstate+18984` 与全局时间（`flt_10426618`/`dword_106A6624`），恒返回 1 | 高（结构）/中（命名） |
| `0x4EE80` | `SVC_GameEvent` | `0x10356EB4` | 3 | 25 | `+0x50` | `0x101EBBF0` | **`CClientState::ProcessGameEvent`**（telemetry 字符串自证），经 `off_1042FCFC` 事件系统派发 | 高 |
| `0x56E60` | `SVC_UserMessage` | `0x10358EEC` | 3 | 23 | `+0x54` | `0x101EC1D0` | 用户消息派发：经 `dword_104EE780->vtbl[140]`（client mode）派发；失败打印 `"Couldn't dispatch user message (%i)"`，返回 0/1 | 高（结构）/中（命名） |
| `0x53FE0` | `SVC_PacketEntities` | `0x103584DC` | 3 | 26 | `+0x5C` | `0x101EBD60` → `0x10077140` | **`CL_ProcessPacketEntities`**：实体增量更新入口，进入 `CClientFrameManager`/`CClientFrame`（见 §5） | 高 |

类型号来源：各类 slot 8（`+0x20`）= `GetType` 常量：
`0x10056E30→23`、`0x1004E4E0→4`、`0x10053FB0→26`、`0x1004EE50→25`。
名字来源：各类 slot 10（`+0x28`）= `GetName`，如 `0x10056E40 → "svc_UserMessage"`。

### 3.1 它们是不是「同一虚函数的不同类实现」？

**是。** 四者都是 **`INetMessage` 的 slot 3** 在四个具体消息类中的实现，模式完全一致（转发到
`[msg+0x50]` 的处理接口），但**转发到的具体处理函数不同**（`ProcessTick` / `ProcessGameEvent` /
`ProcessUserMessage` / `ProcessPacketEntities`）。它们不是无关函数，也不是同一份代码的别名
（IL 不同、各自独立函数、各自 vtable 槽位）。

---

## 4. 接收者类型与 `esi` 的来龙去脉（任务 4）

### 4.1 调用点上下文

`sub_101BBCF0` 的字符串（伪代码内直接出现）：
`"Netchannel: failed reading message %s from %s.\n"`、
`"Netchannel: unknown net message (%i) from %s.\n"`、
`"Netchannel: failed processing message %s.\n"`、`"Blocking message %s\n"`。
→ 该函数为 **`CNetChan::ProcessMessages(bf_read&)`**（按字符串推断，置信度：高；无符号）。

寄存器角色（`0x1BC301` 处）：

| 寄存器 | 含义 | 证据 |
|---|---|---|
| `edi` | `CNetChan* this` | `[edi+4]`/`[edi+5]`/`[edi+6]` 布尔标志；`[edi+0x420C]` 为 handler 指针 |
| `esi` | **`INetMessage* msg`** | 见 §4.2 |
| `ecx` | `msg`（thiscall） | `0x1BC2FF mov ecx, esi` |

### 4.2 `esi` 的赋值（指令级）

```
001BBFDC  8B 45 FC              mov  eax, [ebp+var_4]        ; eax = CNetChan*
001BBFDF  8B 88 40 42 00 00     mov  ecx, [eax+4240h]        ; ecx = *(netchan+0x4240) = netchan（自指针）
001BBFE5  E8 76 7E FF FF        call sub_101B3E60            ; CNetChan::FindNetMessage(type)
001BBFEA  8B F0                 mov  esi, eax                ; *** esi = INetMessage* ***
001BBFEC  85 F6                 test esi, esi
001BBFEE  0F 84 8D 00 00 00     jz   0x101BC081             ; unknown net message 分支
001BBFF4  8B 16                 mov  edx, [esi]
001BBFF6  8B 42 28              mov  eax, [edx+28h]          ; slot 10 = GetName()
001BBFF9  8B CE                 mov  ecx, esi
001BBFFB  FF D0                 call eax
```

- `CNetChan` 构造器（`sub_101BA6D0`）在 `0x1BA87E` 写入 `[esi+4240h] = esi`（**自指针**），
  所以 `ecx` 实参就是 netchan 本身，不是额外对象。
- `sub_101B3E60`（`0x101B3E60–0x101B3EBD`）遍历 `chan+0x4210` 指针数组（元素数 `chan+0x421C`），
  对每个 `INetMessage*` 调用 `[msg->vtbl + 0x20]`（slot 8 = `GetType()`）并与消息类型号比较。

### 4.3 消息对象的创建与 `+0x50` 绑定

| 步骤 | 位置 | 说明 |
|---|---|---|
| 创建 + 绑定 | `sub_10056EE0`（`0x56EE0`，`CBaseClientState/CClientState/CHLTVClientState` vtable **slot 1**） | 逐个 `new`/构造全部消息类，写入 `msg+0x50 = clientstate + 8` |
| 注册 | 同上，调用 `[CNetChan vtable + 0x74]` = **slot 29 = `sub_101BA220`** | 把 `msg` 追加进 `chan+0x4210` 数组，并对 `msg->vtbl[1]`（`0x100025E0`）传 `chan` → `msg+8 = chan` |
| `+0x50` 绑定点 | GameEvent `0x57550`；UserMessage `0x57584`；PacketEntities `0x575EC`；NET_Tick `0x56F4B` | 指令形如 `mov [eax+50h], ecx`，`ecx = clientstate+8` |

`clientstate + 8` 的身份由 RTTI 确认：`CBaseClientState` / `CClientState` / `CHLTVClientState`
的基类 PMD 中 **`INetMessageHandler` 与 `IServerMessageHandler` 的 `mdisp` 都是 8**
（`IServerMessageHandler` 内含 `INetMessageHandler`）。`CClientState` 构造器（`sub_10093890`）
在 `[edi+8]` 写入二级 vtable `0x1036A814`（`0x938A8` / `0x939B6` 两处）。

二级 vtable `0x1036A814` 的槽位解析：

| 槽 | 偏移 | 函数 | 被哪个消息类使用 |
|---|---|---|---|
| 1 | `0x04` | `0x101EB7D0` | `NET_Tick` |
| 19 | `0x4C` | `0x101EBB30` | `SVC_BSPDecal`（同类模式，非本次运行期目标） |
| 20 | `0x50` | `0x101EBBF0` | `SVC_GameEvent` |
| 21 | `0x54` | `0x101EC1D0` | `SVC_UserMessage` |
| 23 | `0x5C` | `0x101EBD60` | `SVC_PacketEntities` |

**结论：** `0x1BC301` 的接收者是 **`INetMessage*`**（`esi`），其运行期具体类型由流中的消息类型字节决定；
`+0x50` 才是指向客户端状态处理接口（`IServerMessageHandler*`）的指针。

---

## 5. 对 D18 现象的解释

D18 记录：frameonly 下 `0x1BC301` 的 `eax` 目标为 `0x79E4E510`(NET_Tick)、`0x79E53FE0`(SVC_PacketEntities)；
原版另有 `0x79E4EE80`(SVC_GameEvent) 与 `0x79E56E60`(SVC_UserMessage)。

由 §2–§4：

- 该 `call eax` 是 **按消息类型分派** 的多目标点，目标集合 = 本轮实际被派发的消息类型集合；
- `0x56E60` 缺失 ⇔ **本轮没有 `svc_UserMessage` 被派发**（或更上游就没有进入派发分支），
  并不表示该调用点被跳过或损坏（D18 已证明调用点本身命中、`AL=1`、`jz` 未跳）；
- 因此 D18 的分歧点应继续向上游找：`svc_UserMessage` 是否到达 `ProcessMessages`
  （例如消息被 `msg bind` 拒绝、`ReadFromBuffer` 失败、或在更上游被过滤），
  而不是继续检查 `0x1BC301` 本身。

**置信度：高**（槽位/类映射为静态确定；"本轮未派发该类型" 是对目标集合差异的直接推论）。

---

## 6. F2 帧迁移相关性（任务 5）

### 6.1 直接结论（负结果，重要）

- 四个转发器函数（`0x4E510`/`0x4EE80`/`0x56E60`/`0x53FE0`）都只有 14 字节，
  **不包含任何 `CClientFrame` 引用**（无 `CClientFrame` vtable 引用、无 `+0x10C/+0x110/+0x114/+0x118` 偏移访问）。
- 四个类 vtable（`0x10356CE4`/`0x10356EB4`/`0x10358EEC`/`0x103584DC`）同样**不含** `CClientFrame` 相关项。
- 因此 **F2 的帧结构加宽不会改变 `0x1BC301` 的目标选择逻辑**；目标只取决于消息类型与注册表。

### 6.2 唯一进入帧代码的分支：`svc_PacketEntities`

`0x53FE0` → `[clientstate+8]->vtbl[0x5C]` = `0x101EBD60` → `0x10077140`（**`CL_ProcessPacketEntities`**，
字符串 `"cl_ents_parse.cpp"`、`"CL_ProcessPacketEntities: frame window too big (>%i)"`）。
该函数内可直接观察到的帧相关调用：

| RVA | 观察到的行为 | 与 `CClientFrame` 的关系 |
|---|---|---|
| `0x10093C80` | 按 tick 沿链表查找：读 `[frame+8]`（与消息 tick 比较，推断为帧 tick 字段）、`[frame+276]`（`+0x114` = next，仓库 N27 已验证） | **直接使用 `CClientFrame` 链表字段** |
| `0x100940E0` | 以 `clientstate+18936 (0x49F8)` 为 `this`（`CClientFrameManager` 子对象，RTTI `mdisp=18936`） | 帧管理器 |
| `0x10093F20` / `0x10093CD0` | 帧管理器的窗口/计数操作（`0x10093CD0` 返回值与 128 比较 → `"frame window too big"`） | 帧管理器 |
| `0x10053440` | 拷贝两份 2048 项实体指针表：`clientstate+0x1E0` / `clientstate+0x21E0`，块步长 `0x2000`（`shl …,0Dh` @ `0x5344A`/`0x5344D`），循环常量 `0x800`(=2048) @ **`0x53463`** | 不是 `CClientFrame` 位图，但为**实体基线指针表的 2048 硬编码** |

其余三个派发目标无帧访问：
- `0x101EB7D0`（Tick）：时间/全局变量；
- `0x101EBBF0`（GameEvent）：事件系统；
- `0x101EC1D0`（UserMessage）：client mode 派发。

### 6.3 给 F2/实体扩容的提示（超出严格问题范围，标注为观察）

`0x10053440` 中的 **2048** 常量位于 `svc_PacketEntities` 派发路径上，是实体基线指针表的循环上界；
若 F2 只加宽 `CClientFrame` 内联位图（`+0x10C`）而该表仍为 2048，实体索引 ≥2048 时此拷贝会截断。
**置信度：中**（2048 常量与调用路径已确认；"基线指针表" 为按分配尺寸/拷贝语义的推断，
尚未用其他证据闭环其确切成员名）。

---

## 7. 未知与限制（显式）

1. **无符号/PDB**：slot 3 的源码级函数名、`sub_101BBCF0`、`sub_101B3E60`("FindNetMessage")、
   `sub_101BA220`("RegisterNetMessage")、`sub_10056EE0`("ConnectionStart") 的名称均为按字符串/行为/接口槽位推断；
   RTTI 仅提供类名，不提供成员函数名。
2. **`0x101EBD60` 之后到 `CClientFrame` 分配/拷贝点（`0x1055xx`、`0x1058xx`）的完整链路未逐一闭环**；
   本文只报告 `0x10077140` 的**直接**被调函数（静态 callee 列表已核对：不含 `0x105xxx`），
   更深层为推断。
3. **消息对象 `+0x50` 的绑定只验证了 `CBaseClientState::ConnectionStart` 创建的实例**；
   其他构造路径（如 `0x101845A0` 另行构造 `NET_Tick`，可能属于 demo/HLTV 所有者）未逐一验证。
4. 运行期目标 ↔ 类型号的对应为**静态**映射；与 D18 目标集合一致，但本轮未做运行期复验。
5. `sub_101B5FB0` 的语义名（`CanProcessMessages`）为推断。

---

## 8. 复现命令（IDA Domain API）

```python
import ida_nalt, ida_bytes, idc, ida_funcs
from idautils import XrefsTo
base = ida_nalt.get_imagebase()          # 0x10000000
print(ida_bytes.get_bytes(base+0x1BC2F0, 0x10).hex(' '))
print(idc.GetDisasm(base+0x1BC301))      # call eax
print(hex(ida_funcs.get_func(base+0x1BC301).start_ea))   # 0x101bbcf0

# vtable -> slot 3
for vt in (0x10358EEC, 0x10356CE4, 0x103584DC, 0x10356EB4):
    print(hex(vt), hex(vt+0xC), idc.GetDisasm(int.from_bytes(
        ida_bytes.get_bytes(vt+0xC, 4), 'little')))
```

---

## 附录 A：地址速查

| 项 | RVA |
|---|---|
| 调用点 / `call eax` | `0x1BC301` |
| `jz` 目标（超时分支） | `0x1BC52E` |
| 条件函数 | `0x1B5FB0` |
| 调用者 `CNetChan::ProcessMessages` | `0x1BBCF0` |
| 消息查表 `0x1B3E60`（命名推断：FindNetMessage） | `0x1B3E60` |
| `esi` 赋值 | `0x1BBFEA` |
| 消息注册 `0x1BA220`（命名推断：RegisterNetMessage） | `0x1BA220` |
| 消息创建/绑定（`ConnectionStart`） | `0x56EE0` |
| `+0x50 = clientstate+8` 绑定 | `0x56F4B`(Tick)、`0x57550`(GameEvent)、`0x57584`(UserMessage)、`0x575EC`(PacketEntities) |
| `CClientState` 二级 vtable（`+8`） | `0x36A814` |
| 派发：Tick / GameEvent / UserMessage / PacketEntities | `0x1EB7D0` / `0x1EBBF0` / `0x1EC1D0` / `0x1EBD60` |
| `CL_ProcessPacketEntities` | `0x77140` |
| 帧链表查找（`+0x114` next） | `0x93C80` |
| 2048 实体指针表拷贝 | `0x53440`（常量 `0x800` @ `0x53463`） |
