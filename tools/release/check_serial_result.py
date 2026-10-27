#!/usr/bin/env python3
"""Recompute the D66 wire-serial boundary result from raw snapshots and log."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def verify(run):
    log = (run/"serial-commands.log").read_text()
    creates = [(int(i), int(c)) for i,c in re.findall(r"D66_WRAP_CREATE idx=(\d+) cycle=(\d+)", log)]
    deletes = [int(c) for c in re.findall(r"D66_WRAP_DELETE idx=\d+ cycle=(\d+)", log)]
    olds = [(int(v), int(c)) for v,c in re.findall(r"D66_WRAP_OLD valid=(\d+) cycle=(\d+)", log)]
    if len(creates) != 1025 or [c for _,c in creates] != list(range(1,1026)):
        raise ValueError("expected 1025 consecutive natural creates")
    index = creates[0][0]
    if not 2048 <= index < 4096 or any(i != index for i,_ in creates):
        raise ValueError("allocator changed the tested high-index slot")
    if deletes != list(range(1,1025)) or olds != [(0,c) for c in range(1,1025)]:
        raise ValueError("delete/invalid-old-reference events are incomplete")
    first = json.loads((run/"serial-first-created.json").read_text())
    start = first["server"]["slots"][0]["serial"]
    zero = (-start) & 1023 or 1024
    cases = [(0,"initial","serial-first-created.json")]
    for c in sorted({1,zero-1,zero,zero+1,1023,1024} & set(range(1,1025))):
        cases += [(c,p,f"serial-cycle{c:04d}-{p}.json") for p in ["deleted","created"]]
    files, low_values = {}, {}
    for cycle,phase,name in cases:
        raw = (run/name).read_bytes()
        files[name] = hashlib.sha256(raw).hexdigest()
        d = json.loads(raw)
        s,c = d["server"]["slots"][0],d["client"]["slots"][0]
        if s["index"] != index or c["index"] != index or not c.get("stable_slot"):
            raise ValueError(f"slot or stability mismatch: {name}")
        expected = (start+cycle) & 32767
        if s["serial"] != expected or (c["serial"] & 1023) != (expected & 1023):
            raise ValueError(f"serial mismatch: {name}")
        server = d["server"]
        if server["max_edicts"] != 4096 or not all(server["assertions"].values()) \
                or server["errors"] or server["handle_errors"] or not server["relocations"]["passed"]:
            raise ValueError(f"server invariant failed: {name}")
        if phase == "deleted":
            if s["pointer"] or c["pointer"]:
                raise ValueError(f"object remained after deletion: {name}")
        else:
            if not s["pointer"] or not c["pointer"] or c["serial"] != (expected & 1023):
                raise ValueError(f"created object missing or decoded incorrectly: {name}")
            if s["handle"] != ((expected << 13) | index):
                raise ValueError(f"internal handle mismatch: {name}")
            if max(abs(a-b) for a,b in zip(s["origin"],c["origin"])) > .04:
                raise ValueError(f"created origin mismatch: {name}")
            low_values[cycle] = c["serial"]
    if low_values[1024] != (start & 1023) or low_values[zero] != 0:
        raise ValueError("wire serial did not repeat or cross zero")
    last = json.loads((run/"serial-cycle1024-created.json").read_text())
    return {"result":"PASS", "index":index, "cycles":1024, "snapshots_checked":len(cases),
            "actual_duration_seconds":last["time"]-first["time"],
            "start_internal_serial":start, "end_internal_serial":(start+1024)&32767,
            "start_wire_serial":start&1023, "first_zero_cycle":zero,
            "observed_created_wire_serials":low_values,
            "log_sha256":hashlib.sha256((run/"serial-commands.log").read_bytes()).hexdigest(),
            "snapshot_sha256":files,
            "empty_slot_note":"client may cache 1024 immediately after deleting serial 1023; its pointer is null and the next created object decodes wire serial 0",
            "internal_serial_wrap":"NOT_TESTED"}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--write", type=Path)
    a=ap.parse_args()
    try:
        result=verify(a.run)
    except Exception as exc:
        result={"result":"FAIL","error":f"{type(exc).__name__}: {exc}"}
    print(json.dumps(result,indent=2))
    if a.write:
        a.write.write_text(json.dumps(result,indent=2)+"\n")
    return int(result["result"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
