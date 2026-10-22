# N14：生成器验收补齐；位图扫描器的基址是「调用方传入的 ECX」

> 两件事：(1) 按 review 给合并生成器补「整文件哈希相等」断言与逐站点 manifest；
> (2) 回到位图归属，先确定 `FUN_1004E310` 的石蕊——它是**由调用方通过 ECX 传入位图基址**，
> 而不是读全局。这一步不解决归属，但把下一步的取证点缩到每个调用点的 `ECX`。

## 0 生成器补齐（已提交）

| 项 | 处理 |
|---|---|
| 写盘后只比长度与站点，未比整文件哈希 | 增加 `expected_sha = sha256(memory)`；读回后若 `sha256(disk) != expected_sha` 直接 `REFUSED` |
| 输出 manifest 只有组摘要 | 增加 `source_manifest`（`engine/manifest.json` 的 sha256）、`n4s_sites`（10 条：va / file_offset / disp_old / disp_new / verified_on_disk）、`checksum` |
| `engine/` 与 `out/` 两份 manifest 靠手工复制 | 生成器**同一份 payload 写两处**，消除版本漂移 |

重建后合并产物哈希不变：`b23788c8bb5c62d6864867953b69d36494a7726d3ead04be1714d087066764c4`。

## 1 `FindNextSetBit` 的真实契约

`FUN_1004E310(start)` 的反编译：

```c
int FUN_1004e310(uint start) {
  if ((int)start < 0x800) {
    iVar2 = start >> 5;
    puVar4 = (uint *)(in_ECX + iVar2 * 4);          // <<< 位图基址来自 ECX
    uVar3 = DAT_10424e50[(start & 0x1f) * 4/4] & *puVar4;
    do {
      if (uVar3) { ... return iVar2*0x20 + iVar1; }
      uVar3 = puVar4[1]; puVar4++; iVar2++;
    } while (iVar2 < 0x40);
  }
  return -1;
}
```

三条硬结论：

1. **位图基址是调用方放进 `ECX` 的指针**，函数本身不引用任何全局对象（只有掩码表 `0x10424E50`）；
2. 上界 `start < 0x800`，块扫描最多 `0x40` 个 dword —— 2048 位；
3. 返回 `-1` 表示「后面没有置位」，不是 0。

因此「位图属于哪个对象」完全由每个调用点的 `ECX` 决定，不能靠函数体推断。

## 2 `FUN_101196C0`：一个持有内联位图的对象

```c
void FUN_101196c0(void) {           // 对象在 EAX
  if (*(char*)(EAX + 4)) {          // 开关
    i = *(int*)(EAX + 0x14);        // 当前实体索引
    if (old->array[i*0xC] == 0 && i < new->count && new->array[i*0xC] != 0) {
      p = (uint*)(EAX + 0x3C + (i>>5)*4);
      *p |= 1 << (i & 0x1F);        // 置位：对象内联位图，+0x3C 起 256 字节
    }
  }
  FUN_10119370(i, flags);           // 写 delta 流
  if (*(int*)(EAX + 8)) {
    i = FUN_1004e310(i + 1);        // ECX 由调用点提供
    *(int*)(EAX + 0x14) = i;
    if (i >= 0) return;
  }
  *(int*)(EAX + 0x14) = 9999;       // 终止哨兵
}
```

对象布局（已确认部分）：

| 偏移 | 语义 |
|---|---|
| `+0x04` | 开关字节 |
| `+0x08` | 是否继续扫描 |
| `+0x14` | 当前实体索引 |
| `+0x3C` | **内联位图**（256 字节 = 2048 位） |
| `+0x13C` | 指向「新快照」：`+0x0C` 计数，`+0x08` 数组（步长 `0xC`） |
| `+0x140` | 指向「旧快照」，仅用其数组头 |

注意：`+0x3C` 的位图与 `CFrame+0x0C` 的 256 字节**大小相同但对象不同**——本对象是
「delta 编码器」，`CFrame` 是「帧快照容器」。这一步只确认了「存在第二个 2048 位内联位图」，
不构成两者同一的证据。

## 3 `FindNextSetBit` 的 8 个调用点

```
0x1004f190  0x10091f50  0x10119490  0x101196c0
0x10119f50  0x10184ea0  0x101850b0  0x10185330
```

其中 `0x10119f50` 是已确认的发送端（读 `param2->0x118` 取快照、写 `MSGPACKETIZER`），
`0x10184ea0`/`0x101850b0`/`0x10185330` 在接收端区域。下一轮只需对每个调用点取
「`CALL` 前的 `ECX` 定义」，就能回答两件事：

1. 被扫描的位图是 `delta 编码器 +0x3C`、`CFrame+0x0C`，还是第三个对象；
2. 发送端（`0x10119f50`）与接收端（`0x10184e..`）是否用同一个位图基址。

判据固定为：`CALL 0x1004E310` 之前 32 字节内不得存在其他 `CALL`，且 `ECX` 必须由
`LEA reg,[obj+disp]` 或 `MOV ECX,[...]` 明确给出。

## 4 仍未闭合

| 项 | 状态 |
|---|---|
| `CFrame+0x0C` 是否为实体位图 | **未证**；本轮只证明了「另有对象在 `+0x3C` 持 2048 位位图」 |
| `0x11C→0x21C` 迁移 | 维持条件方案，不进入 manifest |
| `FindNextSetBit` 扩容 | 需同步：`0x800 → 0x1000`、`0x40 → 0x80` 块数、以及每个调用点的位图容量 |
| `m_nUpdatedEntries` 上界 | 仍开放 |

## 5 复现

```bash
python3 tools/build_engine_4096.py    # 合并构建 + 整文件哈希断言 + 双写 manifest
# REA 会话内
#   procedure_pseudo_code(0x1004E310) -> ECX = 位图基址；start < 0x800；0x40 dwords
#   procedure_pseudo_code(0x101196C0) -> +0x3C 内联位图；+0x13C/+0x140 快照指针
#   procedure_callers(0x1004E310)     -> 8 个调用点
```
