# N27-D4：帧字段迁移的进一步定位（GetSendFrame 漏点与运行期探测）

## 1 新增对照

| 服务端 ELF | 内容 | 客户端 |
|---|---|---|
| `frame_offsets` | F1 + F2（位图仍 0x100） | 卡 75% |
| `frame_fixed` | F1 + F2 + F3，并补 `CGameClient::GetSendFrame` | 卡 75% |

`frame_fixed` 已经补上此前漏掉的帧访问：

```
0x1D9F5C  cmp DWORD PTR [eax+0x118],edi   →  cmp DWORD PTR [eax+0x218],edi
```

这是 `CGameClient::GetSendFrame()` 在 `CClientFrameManager::GetClientFrame`
返回后比较帧快照指针的指令；函数名不含 `CClientFrame`，所以早先的
名字过滤扫描漏掉了它。

## 2 运行期探测：旧偏移已无访问者

对 122 个仍访问 `+0x10C/+0x110/+0x114/+0x118` 的候选点安装 gdb 探针，
在**客户端连接前**挂上，条件为“基址寄存器指向的对象首 DWORD ==
CClientFrame vtable（engine_base+0x299e60）”。

结果：客户端完成连接、服务器 signon 状态到 6 的整个窗口内，
**没有任何一处命中**。也就是说，补丁镜像里已经不存在对旧帧偏移的
帧对象访问；卡 75% 不是“漏改某个旧偏移读取”的直接结果。

## 3 服务器侧状态

在卡载入期间读取 `CGameClient`：

```
this=0xdefec80  signon=6  delta=0x8c33xxx  baseline=0x8c32c2c
```

`signon=6`（SIGNONSTATE_FULL），说明服务器认为客户端已完全进入；
`GetSendFrame` 与 `WriteDeltaEntities` 持续运行，快照指针非空。
客户端 console.log 仍停在：

```
Receiving uncompressed update from server
```

## 4 结论

- 栈位图迁移、帧大小扩容、客户端位图指针化都已通过干净环境对照；
- 唯一会触发卡载入的是 **把 `CClientFrame` 的四个字段整体后移 0x100**；
- 旧偏移访问者已补全并验证不存在，因此问题更可能是
  **帧对象布局/大小与某个按固定步长或固定块处理帧的代码路径不兼容**，
  而不是单条漏改指令。

继续在这个方向上逐指令扫描的收益已经很低，下一轮应改为：

1. 在 `frameonly` 与 `sizeonly` 两个镜像上抓同一次连接的
   `svc_PacketEntities`/signon 包序列（大小、实体数、是否重复全量）；
2. 若包序列一致，则问题在帧对象内存布局（池步长/对齐/越界写）；
3. 若不一致，则按第一个差异包定位到具体字段。

## 5 运行期探针脚本

探针生成与 gdb 脚本逻辑见本轮记录；122 个候选点由
`/tmp/frame_sites.json` 生成，条件为对象首 DWORD 等于帧 vtable。
该探针在真实连接窗口内零命中，是本轮最重要的否证证据。
