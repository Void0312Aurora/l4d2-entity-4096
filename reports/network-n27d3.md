# N27-D3：干净环境 A/B 对照，故障范围缩到帧字段偏移迁移

## 1 干净环境

`/tmp/cleanrun` 逐项 symlink 原安装内容，**排除 `addons`**（因此不再加载
SourceMod/Metamod）；其余地图、pak、cfg 与原安装一致。客户端不变，地址不变。

## 2 对照矩阵（客户端均从 75% 载入点开始观察）

| 服务端 ELF | 改动 | 结果 |
|---|---|---|
| 原版 `5fa15f28…` | 无 | **进入地图**（MOTD/角色字幕） |
| `sizeonly d4b1b762` | 仅帧大小 0x11C→0x21C（池/new） | **进入地图** |
| `stackonly ad7fcdfc` | 仅 WDE 栈位图迁到 `-0x3CC` | **进入地图**（需 `sv_consistency 0`） |
| `frame_offsets ecf149e7` | 帧大小 + 帧字段偏移，位图仍 0x100 | 卡 75% |
| `frameonly 89152442` | 帧大小 + 字段偏移 + 位图 0x200 | 卡 75% |
| D2 全量 | 上述 + 客户端位图指针化 | 卡 75% |

结论：**栈位图迁移、帧大小、客户端位图指针化都不是卡载入的原因；范围收敛到
`CClientFrame` 字段 `+0x10C/+0x110/+0x114/+0x118 → +0x20C/+0x210/+0x214/+0x218`
这组偏移迁移。**

## 3 客户端侧证据

用 `-condebug` 重连后，客户端 console.log 最后一行是：

```
Receiving uncompressed update from server
```

之后无任何报文/解析错误，载入条停在 75%。说明服务器已发出 signon 的未压缩更新，
客户端收到后没有继续 signon 流程。

## 4 同时修掉的工程问题

- 构造桩加入 mmap2 失败硬门禁：`cmp eax,0xFFFFF001; jb ok; ud2`。
  首版误用 `test eax,eax; jns`，高端地址（符号位为 1）会被当成错误，
  真实客户端连接时触发 `ud2`（Illegal instruction），已改为无符号区间判断。
- `build_n27_frame.py` 清理废弃的 212 条迁移循环，说明改成“位图在帧下方”；
- `build_n27_full.py` 文档改为 mmap2/munmap；
- `verify_n27_patched.py` 输出改为 `0x3CC base`；
- 构建器增加 `N27_SKIP_FRAME/N27_SKIP_F2/N27_SKIP_F3/N27_SKIP_STACK`
  以便做上述对照。

## 5 下一步

对 F2 的 47 条偏移迁移做子集对照（先只迁 `+0x118→+0x218`，再 `+0x10C`，
再 `+0x110/+0x114`），配合客户端 `-condebug` 日志定位是哪一类字段读取
导致 signon 停在 “Receiving uncompressed update”。
