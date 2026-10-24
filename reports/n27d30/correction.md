# D30 更正：0x1DDE90 属于 C3，不是新的 F2 漏迁

## 结论

`CBaseServer::WriteDeltaEntities+0x1DDE90` 是 **C3 客户端位图消费者**，不是
`CClientFrame` 尾部成员读取。

- `data/linux/n27b_patch_sites.csv` 已包含：
  - `0x1DDE90`：`lea -> mov`（客户端位图指针）；
  - `0x1DDE96`：`mov ecx` 计数 `0x40 -> 0x80`。
- `0x1DDEA4` 才是 `CClientFrame*` 的 `+0x10C -> +0x20C`，已在 F2 表中。

两个 `eax` 不是同一对象：

```
1DDE90: lea edx,[eax+0x10C]   ; eax = CBaseClient*
...
1DDEA1: mov eax,[ebp+0x10]    ; eax = CClientFrame*
1DDEA4: mov [eax+0x10C],edx
```

因此不应把 `0x1DDE90` 加入 F2，也不能把它的位移改成 `+0x20C`。

## 审计修正

新增 `tools/linux/audit_frame_consumers.py`，按正向位移扫描 35 个消费者函数，
并优先用 F2/C3 登记表分类；负位移 `-0x118(%ebp)` 不再计入。

输出 `data/linux/n27d30_frame_audit.csv`：

| 分类 | 数量 |
|---|---:|
| F2 covered | 62 |
| C3 covered | 5 |
| unclassified | 0 |

因此这一范围内的正向旧位移操作数已全部有补丁归属。
