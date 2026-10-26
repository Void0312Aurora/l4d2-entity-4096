# N27-D49/D50：2048/2049 与 4095 客户端实体生命周期通过

## 1 构建

`tools/linux/build_highindex.py` 从原始 Linux 服务端候选重建容量、13-bit、快照和
传输补丁，输出哈希记录到 `out/linux/sha256.json`。本轮稳定产物为：

```text
engine capacity  22d8e8a8366c81b561c9459005a1e314c811e708a2483075e5879c31dc051154
engine final     79b3966bd9752394beb2f29f0cf0244acedddde15112b4c037535994ecaf8014
server final     18407a811c64593835907dc36395d123858aa69e73f6a651824a302c5f601a81
client           3e5c3f2ee98c2bfa3f3672c654f7ae8b3ae401cc437a08ae1abbe57a6d363943
engine PE final  48329969eaaedee94d011957d81cf53b5a06d8c8098a5e548a7e741309994bd9
```

客户端 PE 还应用了两组边界修复：接收端 CClientFrame 位图由 256 扩至 512 字节，
以及 CBaseClientState 的 2048 项 baseline 指针数组改为单独的 4096 项分配区。

## 2 2048/2049 真实生命周期

服务器在已有玩家 signon 后执行 `d55_create`，日志确认：

```text
D55_TARGET idx=2048 class=prop_dynamic
D55_TARGET idx=2049 class=prop_dynamic
D55_DONE first=2048 count=2
```

`tools/linux/read_client_entities.py` 随后直接读取客户端 `CClientEntityList`：两个槽位均
为非空 `C_DynamicProp`，并与服务端实体坐标一致。执行 `d55_update` 后，客户端读取到
两个 origin 均增加 `(0, 96, 32)`；执行 `d55_delete` 后两个槽位 pointer 变为 `0`，
serial 分别递增。完整 JSON 保存在 `/home/void0312/l4d2_test/runs/d50/baselinesC/`。

这是真实客户端创建、状态更新和删除证据，超出了仅收到 `svc_PacketEntities` 的层次。

## 3 4095 真实生命周期

D50 新建隔离会话 `/home/void0312/l4d2_test/runs/d50/server4095`，客户端先完成
signon 后才设置 `n27_first_index=4095` 并执行 `d55_create`。服务器日志确认 filler 到
4094，目标落在 4095；随后客户端 `CClientEntityList[4095]` 读取为非空
`C_DynamicProp`，坐标与服务器一致。`d55_update` 后客户端坐标增加 `(0,96,32)`；
`d55_delete` 后槽位指针归零、serial 从 467 增至 468。JSON 证据在
`/home/void0312/l4d2_test/runs/d50/boundary4095/{created,updated,deleted}.json`，PTY
记录在 `server4095/pty.log`。

因此客户端侧真实创建、更新、删除已覆盖 2048、2049 和 4095。该结果证明最高合法
网络索引的单实体生命周期可用，但尚未证明并发高索引密集负载或断线重连安全。

较早一次 4095 压力测试仍捕获了独立服务端空 sky-camera 故障：`ClientData_Update`
在 `GetCurrentSkyCamera()` 返回空指针后解引用；现场 active handle 为 `0x05b4f82f`，
对应实体槽 serial 不匹配。core 保存在
`/home/void0312/l4d2_test/runs/d49/serverCache2/server.core`。本次受控单目标生命周期未
重现此故障，故不能称该潜在故障已修复。

## 4 客户端原版/候选 A/B 与重连限制

固定 Proton `1791989105 experimental-11.0-20261014-x86_64`、prefix
`compatdata/550`、同一隔离服务器、engine PE SHA `48329969…`、参数和 55 秒观测窗口：

- A 原版 client SHA `c0a8e1e8…`，PID 148706，加载 EXE/engine/client，连接 `27022`，
  服务端达到 `active`，客户端收到地图更新。
- B 候选 client SHA `3e5c3f2e…`，PID 149815，加载同一模块，连接 `27022`，服务端
  达到 `active`，客户端收到地图更新。

两组均未观察到启动异常。它澄清了先前偶发的 swapchain 退出不能在本固定组合中重现，
但两次样本不足以证明总体启动稳定性。

重连探测分成了两个结果，均不能算重连通过：

1. 第一会话把低索引 filler 一直分配到 4094，并保留 4095 目标，实际上占满了全部
   4096 个 edict。之后出现 `ED_Alloc: no free edicts`，kernel 记录一次
   `engine_srv.so` 内 SIGSEGV（IP `0xf07dc109`）。这是满容量下仍有系统逻辑尝试分配
   的压力结果，不是正常地图上的重连对照；没有 core，无法进一步定因。
2. 第二会话显式释放 3035 个 filler、保留 index 4095 目标后，停止客户端触发服务端
   SIGSEGV。kernel PC 为 `server_srv.so+0x7b506b`，与前述 core 中
   `ClientData_Update+43` 完全一致；旧 core 已证明这里是空
   `GetCurrentSkyCamera()` 结果被解引用。这个新运行没有保存 core，客户端尚未重新
   连接，因此这里只能报告 disconnect 路径仍触发已知 sky-camera 故障，不能声称重连成功。

## 5 可重复检查

```bash
python3 tools/linux/build_highindex.py
python3 tools/patch_engine_receive.py out/engine.4096.13bit.n4s.dll /tmp/engine.receive.dll
python3 tools/patch_engine_baselines.py /tmp/engine.receive.dll /tmp/engine.baselines.dll
python3 tools/net_patch_plan.py --check
python3 tools/check_fields_csv.py
python3 -m py_compile tools/linux/build_highindex.py tools/linux/run_highindex_session.py tools/linux/run_proton_client.py tools/linux/read_client_entities.py tools/patch_engine_receive.py tools/patch_engine_baselines.py
```

本轮 A/B 客户端均在自动清理后退出；Steam 游戏安装目录 `client.dll` 保持原版 SHA
`c0a8e1e8…`。测试期间的高索引 server 由独立 keep-alive 会话管理，完成报告后需确认已停止。
