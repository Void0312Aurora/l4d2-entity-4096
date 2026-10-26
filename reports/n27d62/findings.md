# N27-D62：实体表分区、实际释放和断线重连动态验收

日期：2026-10-26。接续 `06c209d`，只在隔离 Linux/Proton 副本实验。

## 结论及证据边界

修复 D61 的三类漏补丁后，网络 `0..4095`、保留 `4096`、非网络
`4097..8191` 的分区在真实运行中成立。M1、M2 有创建、实际 Remove、serial、
链表和复用证据；M4、M5 在新服务端镜像上完成受调试器观察的 E 循环，另在正常
watchdog 的 G 上完成未附加调试器的生命周期与断线重连循环。
这不是对所有句柄候选点或长期稳定性的全面认证。

| 目标 | 已观察结果 | 限制 |
|---|---|---|
| M1 分区 | PASS：2048/2049/2095/2096/4095 与真实 CSkyCamera 同时存在，无覆盖 | 指定地图和受控负载 |
| M2 释放/句柄 | PASS：网络五个槽及非网络 4416 实际移除、serial+1、正常重新分配、旧句柄失效 | 未穷举 serial 回绕和全部无效哨兵消费者 |
| M3 Proton 正控 | PASS：补齐隔离 UGC 缓存后两个全新客户端均 active、接收低实体、正常退出，启动观察约 141/461 秒 | 缓存固定条件下的短时重复；未修大文件下载器本身 |
| M4 双端生命周期 | PASS：五个目标均有客户端 RTTI、坐标更新、删除归零 | 单客户端 |
| M5 断线/重连 | PASS：E/G 保留全部高目标、清理 filler 后断线；sky 完整；新玩家 active、重获目标、更新、删除 | 尚非所有断线变体及并发压力 |

机器可读结果在 [validation.json](validation.json)，由
`tools/linux/check_d62_evidence.py` 从原始内存、函数追踪和客户端槽数据重新计算。
它明确列出 NOT_TESTED，不用“脚本退出正常”代替动态验收。

## 修复了哪些实际缺陷

1. **对象尾部迁移漏了 20 个位移操作数。** 原清单用 IDA 文本匹配，对结构化显示的
   `stru_10008.r_offset[esi]` 等操作数漏检。构造、分配、移除、计数等方法仍读写旧尾部，
   破坏保留槽和 free-list。逐条解码同一组实体表方法的位移，清单从 42 增至 62。
2. **10 个实例方法遗漏内部句柄掩码。** 仅以全局交叉引用选择函数，漏掉接收 `this`
   的枚举/查询方法。`FindEntityByName` 仍以 `0xFFF` 解码高位非网络对象，导致地图模板
   初始化反复枚举。修正 OnAddEntity、NextEnt、AddPostClientMessageEntity 及指定 Find
   消费者后，地图实际进入处理控制台和游戏帧的状态。句柄清单从 8174 增至 8184。
3. **UTIL_EntityByIndex 的网络边界仍为 2047。** 中间构建中，2048 已存在于双端，
   `EntIndexToHScript(2048)` 却为空；另一次高感染者死亡在 PlayerReporter::FireGameEvent
   的 `server+0x8EF0F2` 空解引用。IDA 路径和函数探针指向 UTIL_EntityByIndex 的旧边界。
   只将 `server+0xB1B0BB` 的立即数 `2047 -> 4095`，最终镜像查询返回真实高实体。
   没有增加空指针掩盖补丁。G 专门创建 index 4031 的 infected 并造成致命伤害；真实
   Infected::Event_Killed → PlayerReporter::FireGameEvent → UTIL_EntityByIndex
   查询返回 pointer `272272000`，伤害调用正常返回，原故障路径回归通过。

没有重做 13-bit 协议、TakeTickSnapshot 或 g_EdictFreeTime 的既有修复。
新增清单仍保留输入 SHA 和每处原字节检查；错误输入镜像实测被拒绝且不产生输出。

## 最终二进制和实验身份

| 文件 | SHA-256 |
|---|---|
| Linux server_srv.so | `8575ed52f39b7c85ea776c83960e3ac08f07521b503109e639acdee1e53d5222` |
| Linux engine_srv.so | `79b3966bd9752394beb2f29f0cf0244acedddde15112b4c037535994ecaf8014` |
| Proton EXE | `c1007187e05ed681173b1c44c043980edf72dfcb2183ad90ec8e6d874d1b14e3` |
| Proton engine.dll | `48329969eaaedee94d011957d81cf53b5a06d8c8098a5e548a7e741309994bd9` |
| Proton client.dll | `3e5c3f2ee98c2bfa3f3672c654f7ae8b3ae401cc437a08ae1abbe57a6d363943` |

原始证据根目录：`/home/void0312/l4d2_test/runs/d62/`。
完整日志、逐槽快照、进程映射及追踪留在本地；仓库只收录紧凑摘录与 SHA，不提交 Valve
二进制、大型 core 或下载的工坊资产。

| 实验 | run ID / PID | 监听端口 | 条件 |
|---|---|---|---|
| E | `20261026-180017-5f08ea` / 493508 | 27050 | 最终镜像、`-nowatchdog`、GDB 实际函数追踪 |
| F | `20261026-180748-dceaa0` / 501192 | 27051 | 同一最终镜像、正常 watchdog、无服务端调试器，网络槽复用 |
| G | `20261026-181814-54edc9` / 512062 | 27052 | 同一最终镜像、正常 watchdog，冷启动和原生双端补测 |
| 长客户端 | launcher 483719 / game 483884 | netcon 27146 | 同一进程连接 B/D/E，约 17 分钟，主动 quit 返回 0 |

服务端均绑定 `192.168.123.104`。客户端工具现在启动前核对实际 srcds UDP 地址和端口；
`127.0.0.1:27050` 的错误目标实测被拒绝，正确 LAN 地址通过。地图“Initializing Director's
script”不再当作 ready，必须收到随后实际处理的 `status` hostname 回复。

## 初始实体表与迁移

E 的实际 server base 为 `0xE7D59000`，gEntList 为 `0xE8DB9000`，数组范围
`[0xE8DB9004, 0xE8DD9004)`，8192 个 16-byte CEntInfo，整个对象大小 `0x20038`。
初始 205 个已占用非网络对象实际位于 `4097..4357`；未假定 sky-camera 仍在 2095。

CSkyCamera 实际 index **4143**，pointer `0x0F19A6B0`，serial `0x15CA`，
EHANDLE `0x02B9502F`。整个 E 验收区间内这些值保持不变，真实 GetCurrentSkyCamera
返回探针 188 次均返回该对象。网络 2095 和它同时存在。

保留槽 4096：pointer=0，serial=19004，prev/next 均自指。
active head/tail、非网络 free head/tail 及全部节点在原始快照中。探针检查 prev/next、
循环、重复、遗漏、占用关系及空闲集是否恰好等于 `4097..8191` 减去非网络已占用集。
网络 edict 分配由引擎 ED_Alloc 管理；CBaseEntityList 中没有第二条“网络 free-list”，
不能把非网络链表伪称为两个池的链表。网络路径用真实 AddNetworkableEntity 返回地址、
移除后自链接空槽和正常 edict 再分配证明。

E/F 六次、G 五次外部内存快照各对 **587 个** R_386_RELATIVE 迁移值逐一比较
`runtime_word == load_base + file_addend`，全部匹配。重定位和对象实际映射均有动态证据。

## 创建、实际移除和复用

E 验收区间在 `E-deleted.json` 的时间 **1793009207.02742** 截止：

- 6947 次 AddEntityAtSlot 入口均为空槽；通过调用返回 PC 区分网络/非网络分配，全部在各自区间。
- 6947 次完成后，新返回句柄、对象句柄、槽号、serial 满足往返不变量。
- 6945 次实际 Remove 完成后 pointer 清零，serial 按 15-bit 加一，旧句柄失效。
- 23 个 E/F 内存快照的链表、句柄、分区和 sky 检查全部通过。

网络目标的服务端 serial：

| index | 创建 | 实际删除后 | F 正常复用 |
|---|---|---|---|
| 2048 | 7225 | 7226 | 7226 |
| 2049 | 3693 | 3694 | 3694 |
| 2095 | 23375 | 23376 | 23376 |
| 2096 | 8205 | 8206 | 8206 |
| 4095 | 8659 | 8660 | 8660 |

Kill 后立即查询均为 true，说明请求本身不是移除。随后追踪到正常 GameFrame 清理路径的
Remove；延迟旧 VScript 引用均为 false。F 开启正常 watchdog，内存快照确认五个槽
空出并 serial+1，再由正常 Spawn 复用，旧引用仍 false。没有手写实体表或绕过分配器。

真实非网络 `logic_relay` 的内部槽是 **4416**，其 `GetEntityIndex()` 为 0（无 edict），
不能用该 VScript 值当作内部索引。追踪得到 serial `24258 -> 24259 -> 24260`：
第一次 Kill 实际清空；根据实际 free FIFO 的 3889 个节点创建真实 relay 轮转，尾部槽
4416 正常复用；新对象句柄为 `198734144`，旧引用 false、新引用 true；分批清理后再次
正常移除。free FIFO 临时耗尽时仍有完整性快照。

内部句柄采用 13-bit index + 15-bit serial；网络上传输 serial 的低 10 位。客户端各目标
serial 与服务端低 10 位相等。这一差异是明确的截断，未把内部 serial 与 wire serial 混用。

## 双端及断线证据

E 客户端实际对象均为 C_DynamicProp。第一次所有对象坐标增量 `(0,96,32)`；断线后客户端
槽归零，服务端对象继续存在；客户端重新达到 userid 7 active，五个已存目标重新出现，
坐标与第一次更新一致；再次增量 `(0,96,32)`；最终五槽客户端归零且 serial 递增。

断线前已逐批删除全部 filler，保留全部五个高索引目标。服务端 status 处理正常、sky
返回继续有效、链表不变，新玩家占用低索引并换 serial。既覆盖旧冲突 2095，也保留最高
4095；不是靠没生成冲突对象而避开旧路径。尚未单独穷举“只预存某一个高目标”的各变体。

G 重复通过同一双端循环：创建/更新、断线/重连和删除阶段均未附加调试器，保持正常
watchdog。仅在两次感染者事件定点检查时短暂附加 GDB，随后 detach；没有在全阶段
追踪每次实体操作。客户端 game PID 523833，netcon 27154；重连 status userid **9 active**。
before-disconnect、after-disconnect、after-delete 快照的 sky pointer `261309776`、serial
5578、handle `45699119` 均不变；最终五个网络目标在双端真实清空、serial 递增。
完整检查结果包含 `NATIVE_HIGH_INDEX_LIFECYCLE_OK`、`NATIVE_DISCONNECT_SAFE`、
`NATIVE_RECONNECT_ACTIVE`，均由 G 自身证据计算，不沿用 E 的 PASS。

## Proton 环境与 UGC 故障

版本 `1791989105 experimental-11.0-20261014-x86_64`，复用 App 550 compatdata/prefix。
桌面为 GNOME Wayland/Xwayland；启动环境 DISPLAY=:0，
XAUTHORITY=/run/user/1000/.mutter-Xwaylandauth.711SX3，XDG_SESSION_TYPE=tty。
完整命令、工作目录、模块实际加载事件、环境和监听匹配在各 `run.json` 中。
本轮未再观察到 D61 的焦点停滞；没有证据把旧焦点等待认定为已定位的根因。

新启动 native 和 native-r2 均曾到 active/低索引实体，随后约 40–50 秒发生同一软件 OOM。
新增准确断点在 tier0+0x7680（内存分配失败回调），捕获首次失败请求 **819396884**，
而非等待一个不会发生的 Unix SIGSEGV。调用栈：

```
tier0+0x7680
... allocation/reallocation ...
engine+0x28A9FB   CUtlBuffer allocation
engine+0x231941  UGC download completion: allocate file_size + 1
engine+0x2315DD  Steam call-result dispatch
SteamAPI_RunCallbacks
```

IDA 确认 file_size 来自 Steam UGC 文件详情，不是实体表索引。缺失缓存
`3577759004.vpk` 在 Steam 原目录已存在，恰为 **819396883** 字节。将 18 个缺失文件
约 4.03 GB 复制至隔离 addons/workshop，保留原 mtime；写隔离 addonlist 将 82 项全部
禁用。没有修改 Steam 订阅、原目录或二进制，也没有跳过图形/网络初始化。
`show_addon_load_order` 实测仅基础游戏/DLC 包。缓存修复后的首个新进程已稳定联机约
141 秒（含初始化）并主动退出返回 0；第二个新进程约 461 秒，完成 G 高实体和断线循环后主动退出
返回 0。`CLIENT_COLD_START_REPEAT` 同时要求真实模块加载、低实体和 active 证据。
工坊大文件下载器本身的内存策略未修改，缓存缺失时仍可能触发原 OOM；不能宣称其全面修复。

## 失败和作废试验

- 最初对原 D61 附加 GDB 时，调试表达式误调用了 sky-camera 析构路径并导致 SIGSEGV；
  该次崩溃属于调试器引入，已排除出根因证据。
- 仅修成员位移的中间构建仍卡在 FindEntityByName。早期 Director 日志不能证明地图就绪。
- B 在 GDB 下集中移除 3033 个 filler 时进程消失，未取得首次 fault；watchdog 只是怀疑，
  原因保留 UNKNOWN，不能声称已解释。最终 E 使用 -nowatchdog 并逐批清理，F/G 做原生对照。
- C 高感染者死亡出现真实 PlayerReporter 空解引用；G 的 index 4031 致命伤害定点追踪
  现已补齐该路径回归，实际查询返回非空且调用正常结束。
- E 在上述验收结束后，复用驱动把多条 Squirrel 语句写进一条 console 命令，Source 按分号
  拆开，错误填满 edict 并触发 ED_Alloc no free edicts。该复用试验作废，改用独立 .nut 后
  在 F 重跑通过。E 后段不得算入通过区间。
- F 正确复用后又填至 4095，未先腾出玩家所需 edict 就尝试新连接，触发同样容量致命错误。
  这是满表连接条件的失败，不是“4096 实体时仍有无限新增容量”。有效复用快照在此前；
  断线/重连验收必须先分批清理 filler、保留目标并留出玩家分配空间。

## 复现与检查

```bash
python3 tools/linux/build_highindex.py --out /tmp/l4d2-d62-build
# 仅安装到已有隔离 cleanrun，确认没有运行中的服务端再替换私有镜像。
python3 tools/linux/run_highindex_session.py --ip 192.168.123.104 --port 27052 \
  --no-script --keep --session-dir /home/void0312/l4d2_test/runs/d62/repro
sudo -n python3 tools/linux/read_server_entities.py PID --out initial.json
sudo -n env D62_SESSION=SESSION_DIR D62_NONNET_INDEX=4416 gdb -q -batch \
  -ex 'attach PID' -x tools/linux/gdb/entitylist_trace.py
```

受 GDB 逐函数追踪时用新会话目录并加 `--no-watchdog`，原生回归保持 watchdog。
通过 session 的 AF_UNIX 控制 socket 逐行发送 console 命令，不在一条 script 命令中放分号。
先实际 active，再按阶段设置 n27_first_index 为 2048、2095、4095，各执行 d62_create。
必须等待每一阶段 D62_DONE；更新执行 d62_update。删除执行 d62_delete，等待实际
Remove/内存清空，再检查旧引用。F 复用测试只先删除最后 64 个 filler，执行
d62_reuse_targets；后续连接前再逐批 d62_free_batch 清理 filler。
非网络复用次数必须从当次实际 FIFO 长度读出，不能把 3889 硬用于其他运行。

```bash
python3 tools/linux/run_proton_client.py --client out/client.4096.dll \
  --engine out/engine.4096.13bit.baselines.dll --connect 192.168.123.104:27052 \
  --out /home/void0312/l4d2_test/runs/d62/repro-client --duration 300 --netcon-port 27154
sudo -n python3 tools/linux/read_client_entities.py PID 0 1 2048 2049 2095 2096 4095 --out client.json
python3 tools/linux/check_d62_evidence.py /home/void0312/l4d2_test/runs/d62 \
  --native --out reports/n27d62/validation.json
python3 tools/check_fields_csv.py
L4D2_ENGINE_BIN='/home/void0312/.steam/steam/steamapps/common/Left 4 Dead 2/bin' \
L4D2_GAMEDLL_BIN='/home/void0312/.steam/steam/steamapps/common/Left 4 Dead 2/left4dead2/bin' \
  python3 tools/net_patch_plan.py --check
```

静态协议预检通过；字段表 5 文件/6007 行通过；改动 Python 编译和 diff whitespace 检查
通过。故意在内存中的证据副本将一次 NO_SLOT_OVERWRITE 改为 false，校验器实测返回 1
并标 FAIL，原始文件未修改。运行时数值不变量及生命周期才是本报告 PASS 的依据。

待测：serial 32767→0 回绕、所有无效句柄消费者、8184 个候选逐点语义审计、多客户端
并发、换图、长时间 soak。未将这些内容标为通过。

修复及 E/F 首批证据已提交并推送为 `acfde60`；随后继续执行上述 G/缓存/感染者补测。
本轮实验进程均已停止，隔离镜像和本地原始证据保留，未覆盖 Steam 原版文件。
