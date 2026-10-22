# N24：网络容量字段的生产链、编码语义与客户端解析（IDA）

> 对象：Linux 专用服务器 `engine_srv.so`（sha256 `5fa15f28…`，build 17033453）与
> 原生客户端 `engine.so`（10,436,418 B）。所有地址为 ELF 坐标；IDA 会话见文末。
> 本轮**不修改任何二进制**。

## 0 结论摘要

| 字段 | 位宽结论 | 依据 |
|---|---|---|
| `m_nMaxEntries` | **11 → 13** | 生产值是 `sv.num_edicts` 计数，最大 4096 |
| `m_nUpdatedEntries` | **11 → 13** | 生产值是本次打包的更新条数，最坏 4096 |
| 实体索引 | **无固定 11/12 位字段** | 线上按相邻索引差值 `-1` 用 `WriteUBitVar` 变长编码 |
| 扫描上界 | 需从 `index+1 > 0x7FF` 重新设计 | 位图扫描的局部守卫，非线格式字段 |

## 1 `m_nMaxEntries` 生产链（已确认）

```
sv.num_edicts (sv+0x20C)
  → CFrameSnapshotManager::CreateEmptySnapshot(...,num_edicts)
      *((_DWORD*)snapshot + 3) = num_edicts        ; snapshot+0x0C
  → CBaseClient::SendSnapshot
  → CBaseServer::WriteDeltaEntities (vtable slot 39, 0x1DD830)
      var_2C   = [pFrame+0x118]                    ; pFrame->m_pSnapshot
      var_18C  = [var_2C+0x0C]                     ; snapshot 容量 = num_edicts
      0x1DD9B5 写 11 位（掩码表 dword_3E2DCC）
```

`CreateEmptySnapshot` 里可交叉验证：`*((_DWORD*)v13+3)=a3`，`a3` 即 `TakeTickSnapshot`
传入的 `dword_3A816C`（`sv+0x20C`）。

⇒ 字段语义是**计数 n（0..num_edicts）**，不是 `n-1`。

## 2 `m_nUpdatedEntries` 生产链（已确认）

`WriteDeltaEntities` 采用**先写头、后打包、跳回再写更新数**的顺序：

```
0x1DD91D  写 6 位消息类型
0x1DD9B5  写 11 位 m_nMaxEntries
0x1DDA93  写 1 位 isDelta
   …      进入实体打包分支
0x1DE32B  add [var_14C],1        ; 打包路径 A
0x1DE69E  add [var_14C],1        ; 打包路径 B
0x1DE286 / 0x1DE2AA  jmp 0x1DDB54 ; 打包结束跳回
0x1DDB69  eax = var_14C
0x1DDB9C  写 11 位 m_nUpdatedEntries
0x1DDC24  写 20 位 m_nLength
```

- `var_14C` 初始化为 0（`0x1DD903`），只在上面的两处 +1；
- 头部字段是**一次性写入**，不存在"预留 32 位回填槽"；
- 因此加宽位宽会让后续字段整体后移，但不会破坏预留区——两端同步即可。

## 3 实体索引编码：不是 11/12 位定长

`WriteDeltaEntities` 内 4 处 `bf_write::WriteUBitVar`：

| 调用点 | 传入值 |
|---|---|
| `0x1DE316` | `(curIndex - prevIndex) - 1` |
| `0x1DE67D` | `(curIndex - prevIndex) - 1` |
| `0x1DEE74` | 差值 |
| `0x1DEEAC` | `(curIndex - prevIndex)` |

⇒ **线上索引使用"相邻索引差值−1"的变长（UBitVar）编码**，不存在 11 位定长索引字段，
因此不能由 `cmp 0x7FF` 推出"索引必须扩到 12 位"。

### `0x1DDEEF` 的真实语义

```
0x1DDED8  edx = var_164            ; 位图基址（非空校验）
0x1DDEE6  eax = var_158            ; 当前位号
0x1DDEEF  ecx = eax+1
0x1DDEF5  cmp ecx,7FFh
          jg  loc_1DEF40           ; → var_158 = 9999（哨兵）
```

这条链属于**对 2048 位位图的置位扫描**（`FirstBitInWord` + `g_StartMask`），
`9999` 是"没有下一个"的哨兵，`loc_1DEF40` 把哨兵写回并跳到
`loc_1DDF92`，随后 `if (v42 == 9999) goto LABEL_127` 终止打包循环。

结论：

- 不是错误处理，也**不会崩溃**；
- 超过 2046 的实体索引会被**静默跳过**（数据丢失，而非报错）；
- 位图使用 bit 1..2047（bit 0 未用），因此 `index+1` 与 2047 比较。
  扩到 4096 时，位图尺寸、哨兵值（不能与合法索引冲突）与循环终止条件必须一起重做，
  这属于 N25 的快照/位图研究范围。

## 4 客户端（`engine.so`）验证

### 4.1 线格式与服务端一致

通过 RTTI `18SVC_PacketEntities` 找到客户端 vtable `0x7F81C0`：

| slot | 函数 | 尺寸 | 角色 |
|---|---|---|---|
| 6 | `sub_2387A0` | 2295 | `ReadFromBuffer`（与服务端 `0xA5170` 同尺寸） |
| 7 | `sub_22D930` | 967 | `WriteToBuffer`（与服务端 `0x9A300` 同尺寸） |

客户端 `ReadFromBuffer` 的关键指令：

```
sub ecx,0Bh ; shr edx,0Bh ; mov [esi+4Ch],eax   ; m_nMaxEntries 11 位
mov [esi+54h],al                                ; isDelta
mov [esi+5Ch],eax / 0FFFFFFFFh                  ; deltaFrom
mov [esi+58h],eax                               ; baseline
sub ecx,0Bh ; shr edx,0Bh ; mov [esi+50h],eax   ; m_nUpdatedEntries 11 位
sub ecx,14h ; shr edx,14h ; mov [esi+60h],eax   ; m_nLength 20 位
mov [esi+55h],cl ; and byte [esi+55h],1         ; updateBaseline
```

⇒ 客户端与服务端字段、位宽、顺序完全一致。

### 4.2 `+0x4C` 的客户端消费者

- 客户端 `ProcessPacketEntities`（`sub_2E6D60`，648 B）只检查 `+0x54`（isDelta）与连接状态；
- `_CL_ParsePacketEntities`（`sub_333750`，2257 B，`cl_ents_parse.cpp:578`）使用
  `+0x54/+0x5C/+0x58/+0x55/+0x50`，**没有读 `+0x4C`**；
- 在普通客户端路径上**未发现 `m_nMaxEntries` 的业务消费者**。

但这不影响结论：**即使值不被使用，读取位宽也必须与写入位宽一致**，
否则后续 `m_nUpdatedEntries`、`m_nLength`、数据区的读取位置全部错位。

## 5 边界矩阵（原版语义）

| 场景 | `m_nMaxEntries`（11 位） | `m_nUpdatedEntries`（11 位） | 索引扫描 `index+1 > 0x7FF` |
|---|---|---|---|
| 2046 | 2046 | 2046 | 通过 |
| 2047 | 2047 | 2047 | 通过 |
| 2048 | **截断为 0** | **截断为 0** | 通过 |
| 4094 | 截断（4094&0x7FF=2046） | 截断 | **哨兵 9999，停止** |
| 4095 | 截断 | 截断 | **哨兵 9999，停止** |
| 4096 | 截断为 0 | 截断为 0 | **哨兵 9999，停止** |

可见原版在 2048 处就已经发生静默截断；4096 目标下 11 位完全不可用。

## 6 位宽决策（N24 定稿）

| 字段 | 决策 | 排除理由 |
|---|---|---|
| `m_nMaxEntries` | **13 位** | 计数语义，値域 0..4096；12 位最大 4095，不足 |
| `m_nUpdatedEntries` | **13 位** | 同上；12 位在"全部实体更新"时溢出 |
| 实体索引 | **不设固定位宽** | 现网为 UBitVar 差值编码；需确认 UBitVar 对 4096 差值的编码上限，但不存在 11/12 位定长字段 |
| 扫描上界/哨兵 | **待 N25 重设计** | 与位图尺寸、bit 0 保留、哨兵 9999 强耦合 |

## 7 仍存风险

1. 位图（`var_188` 指向的 2048 位结构）在扩容后的尺寸与 bit 0 语义；
2. `WriteUBitVar` 对最大差值（4095）的编码是否完整（需查其实现分支）；
3. `m_nLength` 的 20 位上限（1,048,575 位）在 4096 实体下是否仍足够；
4. 动态首次发包验证仍需真实客户端（Steam 环境阻塞）。

## 8 复现

- 服务端：`evidence/linux/`（N23 快照）+ IDA 会话 `32bce8aece6d`；
- 客户端：IDA 会话 `ee584e5b445c`，`engine.so` sha256 建议加入 `tools/linux/extract_evidence.sh`（下一步）。
