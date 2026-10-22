# N13：合并构建完成——存储层 11 条 + N4-S 11 个操作数，单次输入产出单一 DLL

> 回应 review：修正 N12 的哈希转录错误、补上站点数量/唯一性断言，并完成合并构建。
> 关键回归：**内存中的存储层阶段哈希 `3ac18292…` 与既有产物完全一致**，
> 证明新合并器忠实复现了此前已校验的存储层二进制。

## 0 结果

| 项 | 值 |
|---|---|
| 输入 `engine.dll` SHA-256 | `8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86` |
| 存储层阶段 SHA-256 | `3ac18292d746d1d33445b82e83c237fa25b7a3daab5968c18ddf42144059012e`（**与记录一致**） |
| 合并产物 | `out/engine.4096.n4s.dll`，4,817,712 字节 |
| 合并产物 SHA-256 | `b23788c8bb5c62d6864867953b69d36494a7726d3ead04be1714d087066764c4` |
| N4-S 单独产物（回归用） | `7086bb4d3098b7496004b90ac494b65c0601e7e3ad39c5a0f19304f4f3f1dda4` |
| 输出 manifest | `engine/manifest.4096.n4s.json`（入库），`out/` 下为同一份副本 |

## 1 N12 的三处收尾

| 问题 | 处理 |
|---|---|
| 报告哈希 `6d5c9f5e…` 与实测不符 | 更正为 `7086bb4d…`；本轮再次实测同一值，确认是转录错误 |
| 站点数量未独立断言 | 增加 `len(sites)==10` 且 `len(set(vas))==10`，否则 `REFUSED` |
| `context` 字段未校验 | 在 **old 形态**下额外核对 disp 前 4 字节（`context[:4]`）；new 形态跳过，因为相邻站点的窗口会互相覆盖（`0x1011D9C4` 的补丁字节落在 `0x1011D9CD` 的窗口内） |

## 2 合并构建的实现要点

`tools/build_engine_4096.py`：

1. **读取现有 `engine/manifest.json`** 作为存储层定义，不调用 `verify_pe.py`（该脚本会重建并覆盖
   manifest，从而丢掉 N10 的 `verified` / `verification_scope` / 数据流说明）；
2. 从审计原版出发，先在内存中应用存储层 11 个 dword + `.edict2` 段头 + `SizeOfImage` /
   `SizeOfUninitializedData`，并**复用 `verify_pe.py` 的 `pe_checksum` 函数**（`ast` 提取后单独 exec，
   不执行其模块级流程）；
3. **回归断言**：该阶段 SHA-256 必须等于 `3ac18292…`，否则拒绝继续；
4. 再应用 N4-S：`chkstk` 立即数 + 10 个 disp32，逐站点校验前缀与旧位移；
5. 对合并后的镜像**重新计算 PE CheckSum**（存储层算过的那份已失效，因为之后又改了 11 个操作数）；
6. 写盘后重新打开文件、重解析 PE、逐站点复验 `chkstk` 与 10 处新位移，校验长度与哈希。

运行输出：

```
storage stage sha256: 3ac18292d746d1d33445b82e83c237fa25b7a3daab5968c18ddf42144059012e
recorded    sha256: 3ac18292…  (MATCH)
n4s stage: 11 operands applied
disk verify: 4817712 bytes, sha256 b23788c8bb5c62d6864867953b69d36494a7726d3ead04be1714d087066764c4
```

## 3 输出 manifest 的内容

`engine/manifest.4096.n4s.json` 记录：

- 输入 SHA、存储层阶段 SHA、最终 SHA、文件大小；
- `storage_reproduced_recorded_sha256: true`（回归证据）；
- 两组补丁：`storage_layer`（11 条，含 `.edict2` 与头部/校验和）与 `n4s_stack_array`（11 个操作数）；
- 最终 PE CheckSum 的值与字段偏移。

## 4 仍未做 / 风险

| 项 | 说明 |
|---|---|
| 运行时验证 | 未加载游戏；校验和按算法复算，未经加载器实际校验 |
| 原版基线记录 | `check_artifacts.py --record` 只记输入，输出不覆盖基线（本轮未重跑，无需变更） |
| N4-S 语义 | 只把**快照构建器**的索引容量扩到 4096；第 2049 个实体能否同步仍取决于 `CFrame` 位图与 delta 扫描器 |

## 5 复现

```bash
python3 tools/patch_n4s_engine.py --check          # N4-S 独立校验
python3 tools/patch_n4s_engine.py --out /tmp/engine.n4s.dll
python3 tools/build_engine_4096.py                 # 合并构建
sha256sum out/engine.4096.n4s.dll                  # b23788c8…
```

## 6 下一步

按 review 的建议，回到真正决定 4096 实体能否同步的三项：

1. `CFrame+0x0C` 的 256 字节是否为实体位图（决定 `0x11C→0x21C`）；
2. `FUN_1004E310` 的 `0x800/0x40` 扫描器与所属位图对象的容量；
3. `m_nUpdatedEntries` 的真实上界（决定 `13/12` 还是 `13/13`）。
