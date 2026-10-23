# N27-D14：事件身份确认与触发链

## 1 断点移到事件专属分支

`sub_101A0A70` 是通用事件分发器；`OnEngineLevelLoadingFinished` 的专属分支在：

```
0x101A0FB7  test eax,eax
0x101A0FB9  jnz  0x101A0D40     ; 不是该事件
0x101A0FBF  call sub_1019FAE0   ; 是该事件
```

因此把断点从函数入口 `0x1A0A70` 移到 `client.dll+0x1A0FBF`，只统计真正的
`OnEngineLevelLoadingFinished` 分支。

## 2 结果

| 镜像 | 事件分支命中 | 时间 | FULL 返回 |
|---|---|---|---|
| 原版 | **1** | t=24.819 | t=21.617 |
| frameonly | **0** | — | t=22.120 |

D13 的“93 次 vs 92 次”是通用分发器调用次数差异；现在确认真正的
`OnEngineLevelLoadingFinished` 在原版发生 1 次、frameonly **一次都没有**。

## 3 原版调用栈

```
#0 client.dll    0x747D0FBF   事件分支
#1 matchmaking.dll 0x74FC6F85
#2 engine.dll    0x79ED32F8   RVA 0x0D32F8（sub_100D3210 内）
#3 engine.dll    0x79FEC294   RVA 0x1EC294（sub_101EC1D0 内）
#4 engine.dll    0x79E56E6D   RVA 0x056E6D（sub_10056E60 内）
```

Windows 客户端 `engine.dll` 的 IDA 对应函数：

```
0x100D32F8  sub_100D3210
0x101EC294  sub_101EC1D0
0x10056E6D  sub_10056E60
```

事件是由 matchmaking 层经引擎路径派发到客户端游戏事件处理器的。

## 4 结论

- 事件身份已确认，不是通用分发器噪声；
- frameonly 缺少这次 `OnEngineLevelLoadingFinished`；
- 调用链已定位到引擎侧 `engine.dll` 的三个函数，下一步可从
  `sub_100D3210`/`sub_101EC1D0` 反查加载完成条件；
- 仍不能确定该事件是加载完成的原因还是结果；需要检查引擎侧触发条件是否
  在 frameonly 中不满足。

## 5 下一步

1. 反编译 `sub_100D3210`、`sub_101EC1D0`、`sub_10056E60`，找事件发出条件；
2. 在该条件处设断点，比较原版与 frameonly 的输入状态；
3. 若引擎条件满足但事件未派发，检查 matchmaking 层；
4. 若条件本身不满足，沿条件依赖回到世界/玩家初始化。
