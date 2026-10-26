# N27-D64：Hunter 动态根因定位与真实路径回归

日期：2026-10-26。D64 接续 D63，使用原版和扩容版 Linux Dedicated 隔离副本；没有修改原版 Steam 文件，也没有修改扩容二进制。

## 结论

D63 的 Hunter `FAIL` 来自不合格的 VScript 调用方式，而不是已经证明的高索引扩容缺陷。`SpawnEntityFromTable("hunter", ...)` 在原版低索引和扩容版低索引都复现 `NUM_FOR_EDICT: bad pointer`；动态调用链落在 `SetFakeClientConVarValue`，输入是空 `edict_t*`。这条路径没有建立 Hunter 所需的 fake-client/player 绑定，不能作为正常特殊感染者生成路径。

改用游戏提供的 `ZSpawn({type=3,...})` 后，原版低索引、扩容版低索引和扩容版高实体压力场景均返回成功。Hunter 的实际玩家槽位是 `idx=1`，不是高索引槽位；高索引压力只把普通 filler 推到 `idx=2047`。扩容版高压力日志记录 `D64_HUNTER_HIGH_FILLERS=1021 LAST_IDX=2047`、`D64_HUNTER_HIGH_RETURN=true`，没有复现 D63 的崩溃。

同一合法生成机制下，扩容版高压力 Spitter 也通过：1020 个 filler 到 `idx=2047` 后，`ZSpawn(type=4)` 返回 true，实际玩家 `idx=1 type=4 health=100 valid=true`。这验证了至少一条不同的玩家型特殊感染者路径在 4096 表压力下可运行，但不能推广到尚未逐类验证的 Charger/Jockey。

## 动态工具结果

- **Frida CLI**：本机 `/home/void0312/.local/bin/frida` 17.24.3 可用。通过 `sudo -n frida -p <srcds_pid>` 附加到 IA-32 `srcds_linux`，读取了 `Hunter::AllocatePlayerEntity`、`NUM_FOR_EDICT`、`SetFakeClientConVarValue` 符号以及运行时 edict 表全局。扩容版高压力会话读到 `edict_base=0xe341a020`、`num_edicts=2080`、`max_edicts=4096`、`stride=16`；地址是本次进程的 ASLR 值，不能当作固定地址。
- **REA**：`mcp__rea__binary_session` 的能力报告把 `instrument_with_frida`、`load_frida_script`、`resume_frida_session`、`list_frida_processes` 等 native-provider 操作标为 `available=true`。当前 MCP 可调用表只暴露 REA 的静态分析接口和 `binary_session`，没有暴露这些 Frida 函数名，因此本轮没有把 REA 动态接口写成已执行结果；实际运行时证据来自 Frida CLI。
- 动态观察与游戏日志相互独立：合法 Hunter 走玩家分配器并得到非空低槽位；D63 保留的 GDB 断点记录在 `SetFakeClientConVarValue` 入口直接显示 `edict=(nil)`，调用栈随后进入 `NUM_FOR_EDICT`。Frida 本轮用于确认符号、模块基址、运行时表容量和合法路径的挂钩条件；非法路径的精确空指针值以 GDB 记录为准。D63 的历史日志和失败机器结果保留，不被本报告覆盖。

## D64 验收矩阵

| 项目 | 结果 | 证据与边界 |
|---|---|---|
| 非法 `SpawnEntityFromTable("hunter")` 对照 | RECLASSIFIED | 原版、扩容版低索引均出现 `NUM_FOR_EDICT: bad pointer`；应视为无效生成方式，保留 D63 历史 FAIL |
| 原版低索引合法 Hunter | PASS | `ZSpawn(type=3)` 返回 true；实际 player 槽位为 idx=1 |
| 扩容版低索引合法 Hunter | PASS | `ZSpawn(type=3)` 返回 true；idx=1、`type=3`、health=250 |
| 扩容版高压力合法 Hunter | PASS | 1021 filler 到 idx=2047 后仍返回 true；Hunter 仍使用低位玩家槽位 |
| `NUM_FOR_EDICT` 首个异常输入 | PASS | GDB 断点记录 `SETFAKE edict=(nil)`，并有 `SetFakeClientConVarValue → NUM_FOR_EDICT` 调用栈；未把报错文本当作唯一证据 |
| 扩容版运行时 edict 表 | PASS | Frida 读取到 4096 上限、16 字节步长及当前表基址；本次进程 `num_edicts=2080` |
| Hunter 小额伤害 | PASS | 合法 Hunter 从 health=250 变为 240；仅覆盖伤害写入，不覆盖完整 AI 攻击 |
| 扩容版高压力 Spitter | PASS | filler 最后索引 2047；`ZSpawn(type=4)` true，idx=1/type=4/health=100 |
| 其余特殊感染者类型 | PARTIAL | 批量探索日志确认 type=1/2/3 的玩家类型；type=4 有独立高压力证据。批量请求的 type=4/5/6 查询结果为 type=9，不能当作这些类型的通过；type=5/6 未以独立合法场景验收 |
| Hunter 死亡、释放、槽位复用 | NOT_TESTED | 监听器接口在该测试副本不可用，未取得完整死亡事件与释放链证据 |
| 客户端可见 Hunter/Spitter 行为 | NOT_TESTED | 本轮没有真实连接客户端 |
| 原版高压力合法 Hunter 对照 | NOT_TESTED | 原版 2048 上限无法加载与扩容版同等 filler 压力，不能伪装成对照通过 |
| 双客户端、断线重连、多客户端同步 | NOT_TESTED | 按用户要求后置 |

## 证据文件

运行日志保存在 `/home/void0312/l4d2_test/runs/d64/`，包括非法路径原版/扩容版、合法 Hunter 原版/扩容版低索引和高压力日志、高压力 Spitter 日志、标记为探索性质的 `special-matrix-exploratory.log`，以及 `invalid-hunter-setfake.gdb.txt` 的空指针断点记录。可复用的 Frida 脚本为 [`tools/linux/frida/d64_capture_slots.js`](../../tools/linux/frida/d64_capture_slots.js)；本轮交互会话还使用了临时的符号枚举脚本，未将其作为验收工具保留。

机器可读汇总见 [validation.json](validation.json)。D62 仍为 24 PASS / 5 NOT_TESTED；D63 历史结果仍为 3 PASS / 1 FAIL / 7 NOT_TESTED，D64 只对失败路径的测试资格和根因证据作补充归类。
