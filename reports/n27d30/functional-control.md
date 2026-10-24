# N27-D30 补充：功能正控建立，D29 修复镜像可进入地图

## 0 结论

此前反复出现的 `Receiving uncompressed update` 停滞，主要不是游戏卡死，而是测试
流程问题：

1. **server-first** 启动时，Steam 把 `srcds_linux`（命令行含 `left4dead2`）误认成
   App 550，导致客户端启动被跳过；
2. D21 遗留的 **27020 端口测试服务器** 没有被清理，后续手动实验实际连到了旧
   服务器；
3. `console.log` 最后一行的 `Receiving uncompressed update` 不能代表画面状态。

清理端口并改为 **client-first + 不附加调试器** 后：

- pristine + Proton 客户端：进入地图（MOTD/游戏画面）；
- D29 修复镜像 + Proton 客户端：同样进入地图。

## 1 启动顺序

```
1. 启动 Proton 客户端（+connect 27020，此时无服务器）
2. 等待游戏进程/窗口出现
3. 启动测试服务器
4. 发送 sv_lan 1 / sv_password "" / sv_consistency 0
5. 等待并截图游戏窗口
```

窗口可通过以下方式确认：

```
xdotool search --name "Left 4 Dead 2"   # 0x6000003
xwininfo -root -tree                    # "Left 4 Dead 2 - Direct3D 9" 1920x1080
```

## 2 证据

- pristine 截图：`data/n27d30/functional/pristine.jpg`
- D29 修复镜像截图：`data/n27d30/functional/fixed.jpg`

两张都是游戏内画面（第三方服务器 MOTD / 地图场景），不是主菜单或加载界面。

## 3 对 D29 的意义

D29 的 `ProcessBaselineAck +0x118→+0x218` 修复不仅恢复 Signon 6，还没有破坏
实际加载；修复镜像可以完成进入地图。

因此此前“协议修复但加载仍卡住”的判断，至少在当前 Proton 环境中不成立。

## 4 仍需验证

- 旧 frameonly（未修复）在相同 client-first 流程下是否确实卡住；
- 4096 实体容量、2048 边界和高索引快照；
- 长时间运行、断线重连；
- 原生 Windows 客户端组合（可选）。

## 5 环境清理教训

所有手动实验必须：

- 启动前检查 27020 是否已被占用；
- 只杀本次进程组/端口对应 PID；
- 运行后清理 FIFO 和 server；
- 不把 `console.log` 最后一行当作画面状态。
