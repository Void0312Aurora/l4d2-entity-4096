# Limitations

The project is intentionally published as an experimental **single-client plus separate Linux dedicated-server** release candidate. This does **not** include client-hosted single-player/listen-server support.

| Item | Status | Consequence |
| --- | --- | --- |
| Wire serial (10-bit) wrap | PASS for one high slot | 1024 natural reuse cycles at index 2229; see D66 raw-evidence checker |
| Internal serial (15-bit) wrap | NOT_TESTED | No claim about the 32768-cycle boundary |
| Bounded soak | PASS_BOUNDED | 317.5 seconds, 10 full samples, 3 delete/recreate rounds on one map |
| Gameplay-assisted crossing of index 2047 | PASS_BOUNDED (server observation) | 2026-10-31 `c6m1_riverbank`: Logger `Networked: 2159`; VScript max 2158 was an `infected`, after hidden filler creation |
| Natural-only gameplay load above 2047 | NOT_TESTED | The 2026-10-31 crossing used persistent hidden props; `z_common_limit=500` is a cap, not a measured count |
| Same-run high-index client trace | NOT_TESTED for 2026-10-31 | D65/D66 covered selected high-index client paths separately; no new client packet/visibility record from this run |
| Repeated map changes with 512 props | PARTIAL | D66 combined runs stopped on harness/visibility assertions; not a stable-soak claim |
| Multi-hour soak | NOT_TESTED | No leak or long-term stability claim |
| Two real Steam clients | NOT_TESTED | No concurrent-client claim |
| All 4096 network slots occupied | NOT_TESTED | Index 4095 was reached by normal allocation, not full occupancy |
| Windows native dedicated server | NOT_TESTED | Linux dedicated server is the supported server path |
| Windows client-hosted single-player / listen server | **NOT_IMPLEMENTED / NOT_VALIDATED** | Windows release manifest does not include `server.dll`; historical static 808-site prototype was neither integrated nor accepted in a local single-player runtime |
| Windows native client runtime | NOT_TESTED | The Windows image is runtime-tested through Proton |
| Linux native client | **LIMITED PLAYTEST (user-reported)** | Successful server connection and gameplay reported; no independently archived high-index client evidence or high-load acceptance, and no Linux-native client patch in release manifests |
| Intermittent native Linux loading/rendering issues | **OBSERVED BY USER / UNTRIAGED** | A few irregularities during play; sparse observations with no controlled reproduction, causal attribution or measured frequency |
| VAC/public matchmaking | NOT_TESTED | Use private, non-public test environments |
| Other native extensions | NOT_TESTED | SourceMod result is limited to the D65 probe scope |

Basic Linux-native client/server gameplay is distinct from a native client accepting high-index network entities. High-load testing is not a prerequisite to describing basic playability, but the absence of a Linux-native client patch/trace means **full 4096-index compatibility remains unverified**. The reported occasional display/loading anomalies are not currently attributable to the expansion.

The 2026-10-31 Logger report's 28-minute snapshot interval is not measured time above 2047. Its `All: 2374`, `Networked: 2159` and the VScript scan's `count=2397`, `unique=2127`, `over2047=105` have different counting semantics; do not present them as an independently audited simultaneous count of distinct network edicts. See [the published evidence](../artifacts/entity-index-20261031/README.md).

The [historical Windows `server.dll` study](../reports/report.md), [prototype manifest](../manifests/server.json) and [builder](../tools/build_server.py) are real static work, not proof of a released listen-server implementation. The [N26 loopback experiment](../reports/network-n26-baseline.md) involved **separate processes** and cannot diagnose a fault in the client's in-process listen-server transport. No control experiment establishes whether ordinary under-2048 single-player works with the current Windows client patch, or why an expanded local server would fail. See [compatibility](compatibility.md#single-player-and-listen-server-scope).

The source build is tied to L4D2 build `23990068`. A Steam update invalidates the byte manifests until a new audit and runtime regression are completed. The project does not distribute complete Valve DLLs or bypass Steam checks.
