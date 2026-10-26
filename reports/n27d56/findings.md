# N27-D56：4096 edict 扩容与服务端实体列表槽位冲突

## 结论

已把已知的 `ClientData_Update` sky-camera 崩溃追到一个比空指针检查更早的状态破坏：engine 的 edict 容量已扩到 4096，但 `server_srv.so` 中 `CBaseEntityList` 仍按原版 4096 个总槽位划分，其中网络实体使用 `0..2047`，非网络实体使用 `2049..4095`（`2048` 是空洞）。扩容后的网络 edict 会占用后一区间，并直接覆盖其中已有的非网络实体句柄槽。

`c1m1_hotel` 的 sky-camera 句柄为 `0x05b4f82f`，索引 `2095`、serial `0x5b4f`。隔离复现的 GDB 断点在创建 `info_target` filler 时捕获 `CBaseEntityList::AddEntityAtSlot` 将新实体写入 #2095；当时该槽仍有非空指针和 serial `0x5b4f`，调用栈来自 `CInfoTarget::Create`，此前没有对应的 `RemoveEntityAtSlot(2095)`。另一次稳定地图观察显示同一槽有对象指针，但 engine `sv.num_edicts=1511`、`edict[2095].flags=0`，符合该对象来自非网络实体槽池，而非已分配的 engine edict。

这为旧 core 中的 stale sky-camera handle 提供了直接的结构性解释：高索引网络实体覆盖了 camera 的实体列表槽，却没有执行 camera 的正常移除路径；如果之后该 filler 被释放，槽位 serial 会递增，而遗留在 sky-camera 类链表中的对象仍持有旧 handle，`ClientData_Update` 便可能遇到空的 `GetCurrentSkyCamera()` 并在指针变化分支解引用空指针。当前没有抓到 #2095 filler 的实际释放调用，因此从槽位覆盖到旧 core 崩溃的最后一步仍属强推断，不能称完整动态因果链已闭合。故障不能归类为单纯的断线时序问题，也不能用只给 `ClientData_Update` 加空指针检查来视为修复。

## 静态与运行时证据

- `server_srv.so` SHA-256：`18407a811c64593835907dc36395d123858aa69e73f6a651824a302c5f601a81`；engine SHA-256：`79b3966bd9752394beb2f29f0cf0244acedddde15112b4c037535994ecaf8014`。
- `CBaseEntityList::CBaseEntityList`（server RVA `0x43a3e0`）初始化 4096 个 `CEntInfo`，并把从索引 `2049` 开始的 2047 个槽链接进非网络实体 free list。
- `CBaseEntityList::RemoveEntityAtSlot`（RVA `0x43a620`）只在 `index > 2047` 时把释放槽放回该非网络 free list；`AddEntityAtSlot`（RVA `0x43a490`）按 edict 索引直接写指针，不检查目标槽是否已有对象。
- 受控服务端 run `20261026-142815-91aa5f`（PID `291768`，port `27035`）的断点记录：

  ```text
  D56_TRACE ADD_2095 ... index=2095 serialarg=-1 old_slot_ptr=0xdcbe850 old_slot_serial=23375
  #0 CBaseEntityList::AddEntityAtSlot
  #1 CBaseEntityList::AddNetworkableEntity
  #2 CBaseEntity::PostConstructor
  #3 CEntityFactory<CInfoTarget>::Create
  ```

  其中 `23375 == 0x5b4f`。本轮 VScript 继续完成 filler 到 4094、目标实体到 4095 的服务端创建；未连接客户端，因此本轮不是断线验收。
- 延迟 6 秒的低索引地图观察 run `20261026-143311-26932f`（PID `296565`，port `27037`）读到 `gEntList[2095]` 非空，serial `0x5b4f`；engine edict 数为 `1511`，`edict[2095].flags=0`。这与非网络实体占用句柄槽相符。
- 相关原始记录保存在隔离测试目录：`/home/void0312/l4d2_test/runs/d56/F-low/edict.gdb.log`、`/home/void0312/l4d2_test/runs/d56/F-low/pty.log`、`/home/void0312/l4d2_test/runs/d56/H-low/pty.log`。未把环境日志或二进制复制进仓库。
- 一轮按类扫描删除 filler 的脚本只报告删除 1730 个实体；条件断点没有捕获 #2095 的移除。该结果不证明目标 filler 未被释放，可能受延迟删除、实体枚举或本轮未等到实际移除影响，因此仍需修复专用脚本/断点时序后补齐这段动态证据。

## 修复边界与验收状态

当前构建只把 engine edict 上限提高到 4096；实体表仍是 4096 槽，因此它无法同时容纳 4096 个网络 edict 和原有非网络实体池。正确修复必须在服务端实体列表中为非网络实体保留独立槽区，并同步处理列表容量、free-list 边界和 EHANDLE 的索引位宽。当前 `build_highindex.py` 没有这组 server entity-list 迁移补丁。

本轮没有修改二进制补丁，也没有把 S1（断线安全）标为通过。之前观察到的断线崩溃仍未修复；重连、槽位复用、多实体同步和真实地图长稳测试都应在实体列表隔离修复后继续。未复现“正常移除 camera”的调用栈；当前证据证明的是高索引网络实体可覆盖仍占用的非网络槽。
