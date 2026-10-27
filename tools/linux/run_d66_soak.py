#!/usr/bin/env python3
"""Run a bounded 512-entity lifecycle soak with periodic memory checks.

This is intentionally a bounded runner.  Its result records the actual
duration and samples; it does not turn a ten-minute run into a multi-hour
stability claim.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import time

from d65_runtime import console, snapshot


def metrics(pid: int) -> dict:
    status = Path(f"/proc/{pid}/status").read_text()
    rss = next((int(x.split()[1]) for x in status.splitlines() if x.startswith("VmRSS:")), None)
    stat = Path(f"/proc/{pid}/stat").read_text().split()
    uptime = float(Path("/proc/uptime").read_text().split()[0])
    ticks = int(stat[13]) + int(stat[14])
    hz = os.sysconf("SC_CLK_TCK")
    start = float(stat[21]) / hz
    return {"rss_kib": rss, "cpu_ticks": ticks, "clock_ticks_per_second": hz,
            "process_start_seconds": start,
            "system_uptime": uptime}


def status(session: Path) -> str:
    return console(session, ["status"], .3)


def wait_map(session: Path, map_name: str, timeout: float = 120) -> str:
    end = time.monotonic() + timeout
    text = ""
    while time.monotonic() < end:
        text = status(session)
        if re.search(rf"\nmap\s+:\s+{re.escape(map_name)}\b", text) \
                and re.search(r"STEAM_\S+[^\r\n]*\bactive\b", text):
            return text
        time.sleep(.5)
    raise RuntimeError(f"map/player did not become active: {map_name}\n{text[-1000:]}")


def load_512(session: Path) -> list[int]:
    console(session, ["script_execute d65_load"], .3)
    time.sleep(.8)
    console(session, ["script d65_create(512)"], .3)
    time.sleep(1.0)
    report = console(session, ["script d65_report()"], .5)
    ids = [int(i) for i in re.findall(r"D65_TARGET idx=(\d+)", report)]
    if len(ids) != 512:
        raise RuntimeError(f"expected 512 targets after load, got {len(ids)}")
    return ids


def synchronized(frame: dict, ids: list[int]) -> bool:
    server = {x["index"]: x for x in frame["server"]["slots"]}
    client = {x["index"]: x for x in frame["client"]["slots"]}
    return all(server[i]["pointer"] and client[i]["pointer"]
               and client[i].get("stable_slot")
               and client[i]["serial"] == (server[i]["serial"] & 1023)
               and max(abs(a-b) for a,b in zip(server[i]["origin"],client[i]["origin"])) < .04
               for i in ids) and all(frame["server"]["assertions"].values()) \
        and not frame["server"]["errors"] and not frame["server"]["handle_errors"] \
        and frame["server"]["relocations"]["passed"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session", type=Path, required=True)
    ap.add_argument("--client-pid", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--duration", type=float, default=300,
                    help="bounded duration in seconds; default 300")
    ap.add_argument("--sample-interval", type=float, default=30)
    ap.add_argument("--map-interval", type=float, default=0,
                    help="experimental map interval; 0 disables (accepted single-map scope)")
    ap.add_argument("--recycle-interval", type=float, default=90)
    ap.add_argument("--initial-map", default="c1m1_hotel")
    args = ap.parse_args()
    meta = json.loads((args.session / "session.json").read_text())
    server_pid = int(meta["pid"])
    args.out.mkdir(parents=True, exist_ok=True)
    started = time.time()
    samples = []
    errors = []
    transitions = []
    last_map = args.initial_map
    wait_map(args.session, last_map)
    ids = load_512(args.session)
    sample_ids = ids
    initial = metrics(server_pid)
    next_sample = time.monotonic()
    next_map = time.monotonic() + args.map_interval if args.map_interval else float("inf")
    next_recycle = time.monotonic() + args.recycle_interval
    recycling = []
    sequence = 0
    deadline = time.monotonic() + args.duration
    try:
        while time.monotonic() < deadline:
            sequence = sequence % 6 + 1
            console(args.session, [f"script d65_step({sequence})"], .2)
            time.sleep(.35)
            now = time.monotonic()
            if now >= next_sample:
                frame = snapshot(server_pid, args.client_pid, sample_ids, args.out,
                                 f"soak-{len(samples):04d}", args.session)
                ok = synchronized(frame, sample_ids)
                item = {"elapsed_seconds": time.time() - started,
                        "server_pid": server_pid, "client_pid": args.client_pid,
                        "server_metrics": metrics(server_pid),
                        "client_metrics": metrics(args.client_pid),
                        "client_tick": frame["client"]["observation_tick"],
                        "server_tick": None,
                        "live_network_entities": frame["server"]["network_occupied"],
                        "active_test_entities": sum(bool(x["pointer"]) for x in frame["server"]["slots"]),
                        "allocated_edicts": frame["server"]["num_edicts"],
                        "snapshot_size_bytes": (args.out/f"soak-{len(samples):04d}.json").stat().st_size,
                        "entity_list_invariants": frame["server"]["assertions"],
                        "network_statistics": "NOT_COLLECTED",
                        "snapshot": f"soak-{len(samples):04d}.json",
                        "synchronized": ok}
                samples.append(item)
                if not ok:
                    errors.append({"elapsed_seconds": item["elapsed_seconds"],
                                   "error": "sampled client/server state mismatch"})
                next_sample = now + args.sample_interval
                (args.out/"samples.json").write_text(json.dumps(samples, indent=2)+"\n")
                if not ok:
                    break
            if now >= next_recycle:
                console(args.session, ["script d65_remove()"], .3)
                time.sleep(1.2)
                old = console(args.session, ["script d65_old_check()"], .3)
                if not re.search(r"D65_OLD_CHECK total=256 valid=0", old):
                    raise RuntimeError("deleted VScript references remained valid")
                # Live map logic may claim a freed slot. The soak requires
                # 512 ordinary high-index allocations, not ownership of a
                # specific free slot (the separate serial runner tests that).
                console(args.session, ["script d65_create(512)"], .5)
                time.sleep(.8)
                report = console(args.session, ["script d65_report()"], .4)
                ids = [int(i) for i in re.findall(r"D65_TARGET idx=(\d+)", report)]
                if len(set(ids)) != 512:
                    raise RuntimeError("recycling failed to restore 512 distinct targets")
                sample_ids = ids
                recycling.append({"elapsed_seconds": time.time()-started, "restored_count": len(ids)})
                next_recycle = time.monotonic() + args.recycle_interval
            if now >= next_map:
                target = "c1m2_streets" if last_map == "c1m1_hotel" else "c1m1_hotel"
                console(args.session, [f"changelevel {target}"], .3)
                text = wait_map(args.session, target)
                transitions.append({"from": last_map, "to": target,
                                    "elapsed_seconds": time.time() - started,
                                    "status_excerpt": text[-400:]})
                ids = load_512(args.session)
                sample_ids = ids
                last_map = target
                next_map = time.monotonic() + args.map_interval
                next_recycle = time.monotonic() + args.recycle_interval
    except Exception as exc:
        errors.append({"elapsed_seconds": time.time() - started,
                       "error": f"{type(exc).__name__}: {exc}"})
    finally:
        try:
            console(args.session, ["script d65_remove()"], .2)
        except Exception as exc:
            errors.append({"elapsed_seconds": time.time() - started,
                           "error": f"cleanup: {type(exc).__name__}: {exc}"})
    finished = time.time()
    result = {
        "schema": "l4d2-d66-bounded-soak-v1",
        "requested_duration_seconds": args.duration,
        "actual_duration_seconds": finished - started,
        "sample_interval_seconds": args.sample_interval,
        "initial_server_metrics": initial,
        "final_server_metrics": metrics(server_pid) if Path(f"/proc/{server_pid}").exists() else None,
        "samples": samples,
        "map_transitions": transitions,
        "recycle_rounds": recycling,
        "coverage_gaps": ["multi-hour duration", "special-infected churn", "disconnect/reconnect",
                          "server tick and network counters"],
        "errors": errors,
        "result": "PASS_BOUNDED" if samples and not errors else "FAIL",
        "multi_hour_soak": "NOT_TESTED",
    }
    (args.out / "soak-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ["requested_duration_seconds", "actual_duration_seconds",
                                             "result", "multi_hour_soak", "errors"]}, indent=2))
    return 0 if result["result"] == "PASS_BOUNDED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
