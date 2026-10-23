# N27-D2：联机回归与四次真实故障的定位

> 本轮从 D1 镜像直接进入真实客户端联机，连续排掉四个独立故障。
> 最终服务端在真实客户端连接后 **稳定运行 5 分钟以上**、
> `WriteDeltaEntities` 调用 9000+ 次无崩溃，但客户端仍停在载入 75%。

## 1 故障一：运行目录里是旧镜像

`/tmp/n27run/bin/engine_srv.so` 的 sha 是 `34969e…`，而新构建是 `cd5ab4…`。
所有“新桩仍然崩溃”的实验实际上都在跑旧的 PLT 版本。同步后 ctor 桩第一次真正执行。

## 2 故障二：PLT 调用把 `this` 当 GOT 基址

i386 PLT 入口依赖 `EBX = _GLOBAL_OFFSET_TABLE_`，而 `CBaseClient` 构造器里
`EBX = this`，`call malloc@plt` 直接跳飞（EIP=0）。改为 `int 0x80`：

```
ctor: pushad; mmap2(NULL,0x200,RW,PRIVATE|ANON,-1,0); popad;
      mov [ebx+0x10C],eax; mov edx,eax; mov ecx,0x80; xor eax,eax; ret
dtor: pushad; munmap(ptr,0x200); popad; mov [ebx+0x10C],0
```

不依赖 EBX/GOT，也不再复制 `0x2A0070` 的 TEXTREL 指令。

## 3 故障三：`WriteDeltaEntities` 早期返回路径的 `add esp,0x1CC`

帧扩大到 `0x2CC` 后，函数中部还有一条 `add esp,0x1CC`（`0x1DDCD3`）没有同步，
早期返回路径栈失衡，返回地址被踩成 0。补成 `add esp,0x2CC`。

## 4 故障四：栈位图与 `CEntityWriteInfo` 局部对象重叠

把 `var_130` 位图原地扩到 `0x200`、其余局部下移 `0x100` 的方案有结构性错误：
`CEntityWriteInfo` 位于 `ebp-0x16C`，字段 `+0x13C` 正好落在旧位图上方，
下移后与扩大后的位图重叠，`SV_DetermineUpdateType` 读到空 `pSnapshot` 崩溃。

改为**位图整体下移到帧底**，原局部一律不动：

| 项 | 旧 | 新 |
|---|---|---|
| 位图基址 | `ebp-0x130` | `ebp-0x3CC` |
| 清零范围 | `-0x130..-0x31` | `-0x3CC..-0x1CD` |
| 帧大小 | `sub esp,0x1CC` | `sub esp,0x3CC` |
| 早期返回 | `add esp,0x1CC` | `add esp,0x3CC` |

局部变量、结构体布局完全保持原样，静态门禁改为“拒绝残留 `-0x130`、要求 `-0x3CC`”。

## 5 最终运行结果

```
CTOR_ENTRY this=0xe6b0d50
CTOR_STORE ptr=0xed460000
HIT WriteDeltaEntities  （9000+ 次，无崩溃）
客户端：Connected to 10.77.88.2:27016 / clc_BaselineAck 持续交换
```

客户端停在“正在加入…载入中 75%”，服务端进程保持存活。

## 6 对照实验：原版引擎同样崩溃

用 **未打补丁** 的 `engine_srv.so`（sha `5fa15f28…`）在同一隔离目录启动，
真实客户端连接后同样 SIGSEGV：

```
19:12:16 PreMinidumpCallback
19:12:16 Segmentation fault (core dumped)
```

说明“连接即崩”至少有一部分来自隔离环境（addons/SourceMod/目录结构），
不是本补丁独有。需要干净环境才能把剩余问题归因。

## 7 下一轮

1. 建无 addons/SourceMod 的干净服务端目录（逐项 symlink，排除 `addons`），
   原版/补丁版各跑一次同客户端，先确认基线是否稳定；
2. 若干净环境原版稳定而补丁版卡载入，再查 signon/全量快照路径；
3. 客户端侧同时用无 Workshop 的干净配置做对照。
