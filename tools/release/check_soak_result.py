#!/usr/bin/env python3
"""Recompute the bounded D66 soak from every 512-slot raw snapshot."""
import argparse
import hashlib
import json
from pathlib import Path

from check_raw_lifecycle import check_frame


def verify(path):
    result=json.loads(path.read_text())
    samples=result["samples"]
    if result["result"] != "PASS_BOUNDED" or result["errors"] or len(samples) < 3:
        raise ValueError("run failed or has insufficient samples")
    if result["requested_duration_seconds"] < 300 or result["actual_duration_seconds"] < 300:
        raise ValueError("bounded acceptance requires at least 300 seconds")
    ticks=[]
    hashes={}
    for item in samples:
        raw=(path.parent/item["snapshot"]).read_bytes()
        frame=json.loads(raw)
        slots=check_frame(frame)
        if len(slots) != 512 or not all(s["pointer"] for s in slots.values()):
            raise ValueError("a raw sample does not have 512 live synchronized props")
        hashes[item["snapshot"]]=hashlib.sha256(raw).hexdigest()
        ticks.append(frame["client"]["observation_tick"])
    if not result["map_transitions"] and any(a>=b for a,b in zip(ticks,ticks[1:])):
        raise ValueError("client observation tick did not progress")
    rss=[x["server_metrics"]["rss_kib"] for x in samples]
    return {"result":"PASS_BOUNDED", "requested_duration_seconds":result["requested_duration_seconds"],
            "actual_duration_seconds":result["actual_duration_seconds"],
            "observed_sample_span_seconds":samples[-1]["elapsed_seconds"]-samples[0]["elapsed_seconds"],
            "sample_count":len(samples),"entities_per_sample":512,
            "recycle_rounds":result["recycle_rounds"],"map_transitions":result["map_transitions"],
            "server_rss_kib":{"first":rss[0],"last":rss[-1],"minimum":min(rss),"maximum":max(rss)},
            "snapshot_sha256":hashes,"errors":[],"multi_hour_soak":"NOT_TESTED",
            "coverage_gaps":result["coverage_gaps"]+["repeated 512-entity map transitions remain PARTIAL"]}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results",type=Path,required=True)
    ap.add_argument("--write",type=Path)
    a=ap.parse_args()
    try:
        report=verify(a.results)
    except Exception as exc:
        report={"result":"FAIL","error":f"{type(exc).__name__}: {exc}"}
    print(json.dumps(report,indent=2))
    if a.write:
        a.write.write_text(json.dumps(report,indent=2)+"\n")
    return int(report["result"] != "PASS_BOUNDED")


if __name__ == "__main__":
    raise SystemExit(main())
