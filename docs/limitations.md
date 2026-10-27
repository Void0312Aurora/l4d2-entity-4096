# Limitations

The project is intentionally published as an experimental single-client release candidate.

| Item | Status | Consequence |
| --- | --- | --- |
| Wire serial (10-bit) wrap | PASS for one high slot | 1024 natural reuse cycles at index 2229; see D66 raw-evidence checker |
| Internal serial (15-bit) wrap | NOT_TESTED | No claim about the 32768-cycle boundary |
| Bounded soak | PASS_BOUNDED | 317.5 seconds, 10 full samples, 3 delete/recreate rounds on one map |
| Repeated map changes with 512 props | PARTIAL | D66 combined runs stopped on harness/visibility assertions; not a stable-soak claim |
| Multi-hour soak | NOT_TESTED | No leak or long-term stability claim |
| Two real Steam clients | NOT_TESTED | No concurrent-client claim |
| All 4096 network slots occupied | NOT_TESTED | Index 4095 was reached by normal allocation, not full occupancy |
| Windows native dedicated server | NOT_TESTED | Linux dedicated server is the supported server path |
| Windows native client runtime | NOT_TESTED | The Windows image is runtime-tested through Proton |
| Linux native client | NOT_TESTED | Windows/Proton is the tested client path |
| VAC/public matchmaking | NOT_TESTED | Use private, non-public test environments |
| Other native extensions | NOT_TESTED | SourceMod result is limited to the D65 probe scope |

The source build is tied to L4D2 build `23990068`. A Steam update invalidates the byte manifests until a new audit and runtime regression are completed. The project does not distribute complete Valve DLLs or bypass Steam checks.
