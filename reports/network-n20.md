# N20：动态分析环境打通与阻塞点记录（Windows engine.dll / Proton）

> 本轮目标是把 N4-F 的运行时验证从静态推进到动态。结论：**运行时加载、基址换算、内存读取链路全部打通**，
> 但 Steam API 初始化在 Proton 下失败，`SV_SpawnServer` 未执行，`sv` 全局仍为 0。

## 0 环境事实

| 项 | 值 |
|---|---|
| 客户端 | Left 4 Dead 2，build **23990068**，安装在移动硬盘 NTFS 库 |
| `bin/engine.dll` | sha256 `8a6d468059394bf4cfce32f11dcba12ef45de88da1373084d5a2916d0bf7ba86`，4,817,712 B |
| 备份 | `samples/engine.23990068.dll`、`server.23990068.dll`、`client.23990068.dll`（与磁盘一致） |
| Steam 客户端 | build 1792618285，gameoverlayui `20261021210950` |
| Proton 试过 | Experimental `11.0-20261014`、GE-Proton10-28、GE-Proton9-13 |
| 宿主 | Ubuntu 26.04，Xwayland `:0`，RTX 3090 / 580.178.04 |

## 1 运行时加载与基址换算（已验证）

Wine 会重定位 PE 镜像，`engine.dll` 各次运行基址不同（实测 `0x79E00000`、`0x79E30000`、`0x79E60000`）。

校验方法：比较 `base + RVA` 的代码字节与文件同 RVA 字节。

```
runtime  base+0x123B20 = 55 8b ec 81 ec 80 02 00 00 a1 98 dd 23 7a
file      RVA+0x123B20 = 55 8b ec 81 ec 80 02 00 00 a1 98 dd 43 10
```

唯一差异是 `MOV EAX,[0x1043DD98]` 的绝对操作数被重定位为 `0x7A23DD98`：

```
0x1043DD98 - 0x10000000 + 0x79E00000 = 0x7A23DD98   # 完全自洽
```

⇒ 运行时地址 = `base + (VA - 0x10000000)`，其中 `base` 从 `/proc/<pid>/maps` 的 `engine.dll` 首行取得。

## 2 运行内存读取通道（已验证可用，但值为 0）

`/proc/<pid>/mem` 直接预读，无需调试器：

| 符号 | 静态 VA | 运行时值（服务器未 spawn） |
|---|---|---|
| `num_edicts` | `0x1064576C` | 0 |
| `max_edicts` | `0x10645770` | 0 |
| `pEdicts` | `0x10645774` | 0 |
| `pChangeInfo` | `0x10645778` | 0 |

读取成功、地址映射有效，说明**通道本身没有问题**；0 值的唯一解释是 `SV_SpawnServer` 尚未执行。

## 3 阻塞点：Steam API 在 Proton 下初始化失败

三个 Proton 版本、两条路径（Steam 启动 / 直接 Proton 启动）全部同一症状，游戏弹 `Engine Error`：

> Steam is not running. You must start Steam in order to play this game.

`console-linux.txt` 伴随断言：

```
IPC call to IClientUtils::GetConnectedUniverse returned failure code 12
Unknown IPC call IClientUtils::0x33788031 / 0xf90fd2b9
IClientNetworkingUtils_Create - Don't know Steam universe. Order of init bug?
IPC call to IClientUtils::SetAppIDForCurrentPipe returned failure code 12
```

社区同类记录：

- Source-1-Games #4708（L4D2 + `-safe` 时同句报错）
- CachyOS 论坛 `Unable to create interface ISteamUser`（`lsteamclient` override 方案）
- Steam 社区「failed to locate universe / 客户端更新后应用静默崩溃」

`WINEDLLOVERRIDES="lsteamclient=d"` 已实测：游戏能进到开场动画（D3D9 窗口、存活 4 分钟），
但动画结束后仍报同一错误 ⇒ override 不足以解决。

## 4 环境侧已修复的两个坑

### 4.1 NTFS 不支持 `dosdevices/c:` 符号链接

外部库的 `compatdata/550/pfx/dosdevices/c:` 创建失败：

```
OSError: [Errno 22] Invalid argument: '../drive_c' -> '.../pfx//dosdevices/c:'
```

原因：NTFS（fuseblk）不允许文件名含冒号。修复：把外部库 `compatdata/550` 改为指向 ext4 主目录的符号链接，
前缀实际落在 ext4 上，Steam 视角路径不变。

### 4.2 depot 平台切换

Linux Steam 对 L4D2 默认使用**原生 Linux 构建**。未强制 Proton 时 Steam 会下载 Linux depot
（`hl2_linux`、`engine.so` 等，16:47 落盘）；一旦设置 CompatToolMapping→Proton，Steam 提交
`0 updated, 0 moved, 55 deleted files`，删除 Linux 文件并挂回 Windows depot。

⇒ 当前磁盘上**只有 Windows 版**，原生 Linux 二进制需切回原生后重新下载。

## 5 对 N4-B / N4-F 的影响

- 动态验证（`max_edicts` 实际值、帧位图写者、2048 边界）**依赖 `SV_SpawnServer` 执行**，
  在 Steam API 修复前无法推进；
- 已备好的工具：`tools/dyn/env.sh`、`launch_game.sh`、`restart_and_launch.sh`、
  `launch_proton2.sh`、`launch_plain.sh`、`launch_symlink.sh`、`launch_ge9.sh`、`wait_launch.sh`、`attach_gdb.sh`；
- 基址换算与 `/proc/pid/mem` 读取脚本已验证，修复后可直接复用。

## 6 待选路线

1. **修 Steam 侧**：切客户端测试分支 / 重新登录 / 用另一个 Windows 游戏做对照，确认是否客户端级故障；
2. **走原生 Linux 语义验证**：切回原生（重新下载 Linux depot），在 `engine.so` 上定位对应函数，
   验证 2048 边界与位图写者，再回到 Windows 补丁；
3. **暂停动态、推进静态**：N4-F 指令表（真实反汇编）、N4-B/N4-D 的迁移清单。
