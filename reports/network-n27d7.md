# N27-D7：Frida 探针正向校验，signon 在 5 停住

## 1 可复现性修正

`tools/linux/frida/run_attach.py` 现在：

- 从仓库路径读取 `n27_frame_hooks.js`，不再读 `/tmp` 副本；
- 记录脚本 SHA-256 到输出首行；
- 每 5 秒输出一次完整 `counts` 事件；
- 所有 hook 安装失败会以 `hook_error` 事件记录（本轮 `hook_errors=0`）。

## 2 正向校验：原版 + Frida 必须命中

原版服务器、同一客户端、Frida 附加 70 秒：

```
wde=440  send=457  alloc=457  setsnap=912  signon=5
connect=1  finishcert=1  authresp=1
```

signon 序列：

```
2 → 3 → 4 → 5 → 6
```

说明探针覆盖了连接、帧分配、快照发送、signon 全路径。

## 3 frameonly + Frida：连接成功，但 signon 停在 5

同一套探针，服务端换成 `frameonly`：

```
wde=353  send=369  alloc=369  setsnap=735  signon=4
connect=1  finishcert=1  authresp=1
```

signon 序列：

```
2 → 3 → 4 → 5   （没有 6）
```

客户端日志仍反复 `Connected` / `timed out`，但这次服务端确实执行了
帧分配与快照发送。也就是说：

- D6 的“全部 0 命中”是一次**连接未完成**的会话（认证/握手失败）；
- 连接成功时，frameonly 的差异精确落在 **signon 5 → 6 的跃迁**；
- 服务器持续发送快照，但客户端没有完成 FULL 状态。

## 4 修正后的结论

不是“帧补丁导致连接失败”，而是：

1. 连接与认证可以成功；
2. 帧分配、快照发送都执行；
3. 客户端收到快照后没有进入 FULL；
4. 下一步应直接对比两种镜像发出的第一个全量快照内容。

## 5 下一轮

1. 对同一客户端抓 `frameonly` 成功连接后的 `svc_PacketEntities`，
   与 原版/`sizeonly` 的同位置包做长度与字节差异；
2. 用 IDA 对照 `CBaseServer::WriteDeltaEntities` 写出的 bit 流，
   定位是实体数、PVS 位图还是 delta 基线字段不同；
3. 确认差异后，再决定帧字段布局是否继续保留。
