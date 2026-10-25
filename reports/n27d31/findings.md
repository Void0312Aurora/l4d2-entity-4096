# N27-D31：完整 4096 镜像集成与低索引功能回归

## 0 结论

将 N27 帧/C1/C3 与 N26 容量补丁合并为单个镜像：

| 组成 | 内容 |
|---|---|
| F1/F2/F3 | CClientFrame 扩容、成员迁移、4096 内联位图 |
| S1/S2/S3 | 帧下方位图/栈迁移 |
| C1/C3 | CBaseClient 位图指针化与 mmap/munmap 桩 |
| N26 | `0x800 → 0x1000` 两处容量立即数 |

镜像：

```
/tmp/n27/n27_full.so       b870d950c5f19b723b380f695e8cf54ae2200f34720d0db6411a6ec61f872e15
/tmp/n27/n27_full_4096.so  fa46e782cd6ed8a9dfdc37a398155628864ea0d94fac610fb25c0916d08f5c62
```

相对 full 镜像只多 2 字节改动。

## 1 构建

新增可复现构建器：

```
python3 tools/linux/build_n27_4096.py /tmp/n27/n27_full_4096.so
```

它调用 `build_n27_full.py`，然后校验并替换两处 N26 立即数。

## 2 动态结果

- 服务端启动：`Host_NewGame on map c1m1_hotel`，无崩溃；
- Proton 客户端 client-first 连接；
- 客户端进入地图（截图 `data/n27d30/functional/full4096.jpg`）。

因此完整 4096 镜像在**低实体索引、2048 以下网络负载**下可正常进入地图。

## 3 未验证的线格式门槛

当前镜像**没有修改网络线格式**：

- `SVC_PacketEntities::m_nMaxEntries` 仍为 11 bit；
- `m_nUpdatedEntries` 仍为 11 bit；
- 实体索引差值编码仍按原协议读取；
- 客户端 Proton 二进制未同步 13-bit 解析。

因此不能把第 2048–4095 号实体放进网络快照；这会导致服务端写端/客户端读端不一致。
本轮的“4096”只覆盖存储、帧布局、位图指针化和低索引联机。

## 4 F2 审计门禁

`tools/linux/audit_frame_consumers.py` 已改为：

- 校验原始 `engine_srv.so` SHA-256；
- 按 `elf_addr` 去重；
- 出现未归类项时返回非零。

最新结果：

| 分类 | 唯一站点 |
|---|---:|
| F2 covered | 48 |
| C3 covered | 5 |
| unclassified | 0 |

## 5 下一步

1. 服务端写端 11→13 bit（`m_nMaxEntries` / `m_nUpdatedEntries`）；
2. 同步客户端读端线格式（Proton 客户端二进制或替代方案）；
3. 按 2047/2048/2049/4095 边界构造实体，做第一次跨 2048 网络快照；
4. 通过后再做长时间、多客户端、断线重连回归。

在这些完成前，不应把高索引实体加入正式服务器。
