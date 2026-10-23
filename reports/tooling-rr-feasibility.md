# rr 部署可行性记录

## 1 安装与基础验证

```
sudo apt-get install -y rr
rr version 5.9.0
```

基础能力验证：

- 32 位静态小程序（`int 0x80` 退出）可 `rr record`，生成 trace 并 `rr replay -a` 正常结束；
- 64 位 `/bin/true` 同样可录制。

说明 rr 在这台 Xeon E5-2696 v4（`perf_event_paranoid=-1`）上的 32 位录制通路是通的。

## 2 专用服务器录制失败

对 `srcds_linux`（32 位 Linux 专用服务器）录制时，rr 在加载阶段中止：

```
[FATAL ./src/record_syscall.cc:6733:rec_process_syscall_arch()]
Assertion `t->regs().syscall_result_signed() == -syscall_state.expect_errno' failed.
Expected EINVAL for 'madvise' but got result 0 (errno SUCCESS); unknown madvise(102)
```

`madvise(102)` 是本机内核（Linux 7.0）新增的 `MADV_GUARD_INSTALL`；
rr 5.9 不认识该 advice，按旧内核行为预期 `EINVAL`，而实际返回 0，于是中止。

尝试过的规避：

- `rr record -n`（禁用 syscall buffer）：同样中止；
- `LD_PRELOAD` 32 位 `madvise` shim（拦截 102/103 返回 EINVAL）：
  无效，目标仍产生同样的 rr 断言，说明 rr 对 preload/直接 syscall 的处理
  绕过了该 shim。

上游已有对应问题：

- [rr issue #4044: MADV_GUARD_INSTALL crashes rr](https://github.com/rr-debugger/rr/issues/4044)
- [rr issue #4075: Unknown madvise(102)](https://github.com/rr-debugger/rr/issues/4075)

## 3 结论

- rr 已安装且基础录制可用；
- 当前游戏/服务器路径会被内核新增的 `MADV_GUARD_INSTALL` 挡住；
- 需要 rr 上游修复，或自行编译 rr 并在 `record_syscall.cc` 中把
  advice 102/103 视为已知成功；这是一次构建级改动，不是配置项；
- 现阶段尚未找到“某个字段变成异常值”的具体目标，rr 的反向 watchpoint
  还没有明确落点。

## 4 建议

暂不把 rr 作为当前主线工具：继续用现有 GDB 跟踪脚本定位
`sub_10056E60` 调用者的条件分支；一旦发现具体异常值或异常写入，
再编译带 102/103 支持的 rr 做反向 watchpoint。

如果决定立即推进 rr，下一步是：

1. 获取 rr 源码并打 patch；
2. 用 `cmake` 构建 32 位支持版本；
3. 先在 `srcds_linux` 上验证能完整录制一次客户端连接；
4. 再决定是否对 Proton 客户端尝试（Wine 多进程会进一步增加不确定性）。
