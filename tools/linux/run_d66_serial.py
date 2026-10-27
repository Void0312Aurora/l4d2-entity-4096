#!/usr/bin/env python3
"""Run a bounded, real-client serial lifecycle probe on an isolated server.

The runner samples the ordinary allocator around the 10-bit network-serial
boundary. It does not write serials or indices. Internal 15-bit wrap is not
attempted by this runner because it would require 32768 lifecycles.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import time

from d65_runtime import console, snapshot


def sample(session: Path, server_pid: int, client_pid: int, index: int, out: Path, label: str) -> dict:
    return snapshot(server_pid, client_pid, [index], out, label, session)


def row(frame: dict, index: int) -> dict:
    server = next(x for x in frame["server"]["slots"] if x["index"] == index)
    client = next(x for x in frame["client"]["slots"] if x["index"] == index)
    return {
        "server_pointer": server["pointer"],
        "server_serial": server["serial"],
        "client_pointer": client["pointer"],
        "client_serial": client["serial"],
        "client_stable_slot": client.get("stable_slot", False),
        "network_serial_match": bool(client["pointer"] and client["serial"] == (server["serial"] & 1023)),
        "index": index,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session", type=Path, required=True)
    ap.add_argument("--server-root", type=Path, required=True)
    ap.add_argument("--client-pid", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cycles", type=int, default=1024)
    ap.add_argument("--sleep", type=float, default=.28)
    ap.add_argument("--delete-sleep", type=float, default=1.15,
                    help="wait for the normal allocator free-time gate before reuse")
    a = ap.parse_args()
    if a.cycles < 1024:
        ap.error("at least 1024 ordinary reuse cycles are required")
    meta = json.loads((a.session / "session.json").read_text())
    server_pid = int(meta["pid"])
    script = a.server_root / "left4dead2/scripts/vscripts/d66_wrap.nut"
    script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).parent / "vscript" / "d66_wrap.nut", script)
    a.out.mkdir(parents=True, exist_ok=True)
    log = (a.out / "serial-commands.log").open("w", buffering=1)

    def cmd(text: str) -> str:
        result = console(a.session, [text], .12)
        log.write(result)
        return result

    cmd("script_execute d66_wrap")
    time.sleep(.8)
    cmd("script d66_prepare()")
    time.sleep(.8)
    first_create_log = cmd("script d66_spawn()")
    time.sleep(a.sleep)
    match = re.search(r"D66_WRAP_CREATE idx=(\d+)", first_create_log)
    if not match:
        raise RuntimeError("initial D66 wrap allocation did not produce an index")
    target_index = int(match.group(1))
    first = sample(a.session, server_pid, a.client_pid, target_index, a.out, "serial-first-created")
    first_row = row(first, target_index)
    start_serial = first_row["server_serial"]
    offset_to_zero = (1024 - (start_serial & 1023)) % 1024
    if offset_to_zero == 0:
        offset_to_zero = 1024
    sample_cycles = {1, offset_to_zero - 1, offset_to_zero,
                     offset_to_zero + 1, 1023, 1024}
    records = [{"cycle": 0, "phase": "initial", **first_row,
                "snapshot": "serial-first-created.json"}]
    failures = []
    if not first_row["network_serial_match"] or not first_row["client_stable_slot"]:
        failures.append("initial client/server serial or slot mismatch")

    for cycle in range(1, a.cycles + 1):
        cmd("script d66_kill()")
        time.sleep(a.delete_sleep)
        deletion_log = cmd("script d66_old_check()")
        if "D66_WRAP_OLD valid=0" not in deletion_log:
            failures.append(f"cycle {cycle}: old VScript reference stayed valid")
        if cycle in sample_cycles:
            deleted = sample(a.session, server_pid, a.client_pid, target_index, a.out, f"serial-cycle{cycle:04d}-deleted")
            deleted_row = row(deleted, target_index)
            deleted_row.update(cycle=cycle, phase="deleted", snapshot=f"serial-cycle{cycle:04d}-deleted.json")
            deleted_row["server_deleted"] = not deleted_row["server_pointer"]
            deleted_row["client_deleted"] = not deleted_row["client_pointer"]
            records.append(deleted_row)
            if not deleted_row["server_deleted"] or not deleted_row["client_deleted"]:
                failures.append(f"cycle {cycle}: deleted object remained visible")
        cmd("script d66_spawn()")
        time.sleep(a.sleep)
        if cycle in sample_cycles:
            created = sample(a.session, server_pid, a.client_pid, target_index, a.out, f"serial-cycle{cycle:04d}-created")
            created_row = row(created, target_index)
            created_row.update(cycle=cycle, phase="created", snapshot=f"serial-cycle{cycle:04d}-created.json")
            records.append(created_row)
            if not created_row["network_serial_match"] or not created_row["client_stable_slot"]:
                failures.append(f"cycle {cycle}: client/server serial or slot mismatch")

    created_by_cycle = {r["cycle"]:r for r in records if r["phase"] == "created"}
    result = {
        "schema": "l4d2-d66-network-serial-wrap-v1",
        "cycles": a.cycles,
        "index": target_index,
        "start_server_serial": start_serial,
        "start_network_serial": start_serial & 1023,
        "first_zero_network_cycle": offset_to_zero,
        "sampled": records,
        "network_serial_repeat_after_1024": created_by_cycle[1024]["client_serial"] == (start_serial & 1023)
            and created_by_cycle[offset_to_zero]["client_serial"] == 0,
        "all_sampled_client_server_matches": not failures,
        "internal_serial_wrap": "NOT_TESTED",
        "failures": failures,
    }
    (a.out / "serial-wrap-results.json").write_text(json.dumps(result, indent=2) + "\n")
    cmd("script d66_cleanup()")
    print(json.dumps({k: result[k] for k in ["cycles", "start_server_serial", "first_zero_network_cycle",
                                             "network_serial_repeat_after_1024", "all_sampled_client_server_matches",
                                             "internal_serial_wrap", "failures"]}, indent=2))
    return 0 if not failures and result["network_serial_repeat_after_1024"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
