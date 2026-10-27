#!/usr/bin/env python3
"""Recompute selected D65 lifecycle claims from raw dual-end snapshots.

This checks the five ladder levels and the natural 4095 lifecycle. It does
not independently validate special-infected events or arbitrary extensions.
"""
import argparse
import json
from pathlib import Path


def rows(frame, side):
    items = frame[side]["slots"]
    result = {x["index"]: x for x in items}
    if len(result) != len(items):
        raise ValueError("duplicate slot indices")
    return result


def check_frame(frame):
    server = frame["server"]
    if server["max_edicts"] != 4096 or server["errors"] or server["handle_errors"]:
        raise ValueError("server capacity or invariant errors")
    if not server["assertions"] or not all(server["assertions"].values()):
        raise ValueError("server list/free-list/sky invariant failed")
    if server["relocations"]["checked"] != 587 or not server["relocations"]["passed"]:
        raise ValueError("relocation verification failed")
    ss, cs = rows(frame, "server"), rows(frame, "client")
    if ss.keys() != cs.keys():
        raise ValueError("client/server index sets differ")
    for i, s in ss.items():
        c = cs[i]
        if not 2048 <= i <= 4095 or not c.get("stable_slot"):
            raise ValueError(f"invalid or unstable high-index slot {i}")
        if bool(s["pointer"]) != bool(c["pointer"]):
            raise ValueError(f"client presence mismatch at {i}")
        if c["serial"] != (s["serial"] & 1023):
            raise ValueError(f"wire serial mismatch at {i}")
        if s["pointer"]:
            if s["handle"] != (s["serial"] << 13) | i:
                raise ValueError(f"internal handle mismatch at {i}")
            if s["edict_pointer"] != server["edict_base"] + i * 16:
                raise ValueError(f"edict back-reference mismatch at {i}")
            if s["edict_words"][1] & 1023 != c["serial"]:
                raise ValueError(f"edict wire serial mismatch at {i}")
            if "DynamicProp" not in s["rtti"] or "DynamicProp" not in c["rtti"]:
                raise ValueError(f"unexpected entity class at {i}")
            if max(abs(a-b) for a, b in zip(s["origin"], c["origin"])) > .04:
                raise ValueError(f"origin mismatch at {i}")
    return ss


def lifecycle(root, prefix, count, boundary=False):
    names = ["created"] + [f"seq{i}" for i in range(1, 7)] + ["deleted", "reused"]
    frames = {}
    for phase in names:
        name = "boundary-natural-created.json" if boundary and phase == "created" else f"{prefix}-{phase}.json"
        frames[phase] = json.loads((root/name).read_text())
        check_frame(frames[phase])
    created = rows(frames["created"], "server")
    if boundary:
        selected = {4095}
    else:
        selected = set(created)
        if len(selected) != count:
            raise ValueError(f"expected {count} initial slots, got {len(selected)}")
    removed = set()
    for i in selected:
        old = created[i]
        if not old["pointer"]:
            raise ValueError(f"missing created object at {i}")
        origins = []
        for phase in names[1:7]:
            s = rows(frames[phase], "server")[i]
            if not s["pointer"] or s["handle"] != old["handle"]:
                raise ValueError(f"object identity changed during update at {i}")
            origins.append(tuple(s["origin"]))
        if len(set(origins)) < 2:
            raise ValueError(f"no observed server movement at {i}")
        deleted = rows(frames["deleted"], "server")[i]
        reused = rows(frames["reused"], "server")[i]
        if not deleted["pointer"]:
            removed.add(i)
            if deleted["serial"] != ((old["serial"] + 1) & 32767):
                raise ValueError(f"delete serial increment mismatch at {i}")
            if not reused["pointer"] or reused["serial"] != deleted["serial"]:
                raise ValueError(f"slot not reused at {i}")
            if reused["handle"] == old["handle"]:
                raise ValueError(f"old handle aliases reused object at {i}")
        elif reused["handle"] != old["handle"]:
            raise ValueError(f"unremoved object unexpectedly changed at {i}")
    expected_removed = 1 if boundary else count // 2
    if len(removed) != expected_removed:
        raise ValueError(f"expected {expected_removed} removals, got {len(removed)}")
    return {"count": count, "slots_checked": len(selected), "removed_and_reused": len(removed),
            "snapshots_checked": len(names), "status": "PASS"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-root", type=Path, required=True)
    ap.add_argument("--write", type=Path)
    args = ap.parse_args()
    results, failures = [], []
    for n in [16, 64, 128, 256, 512, 4095]:
        try:
            prefix = "boundary" if n == 4095 else f"load{n}" + ("-actual" if n != 16 else "")
            results.append(lifecycle(args.evidence_root, prefix, 1 if n == 4095 else n, n == 4095))
        except Exception as exc:
            failures.append({"case": n, "error": f"{type(exc).__name__}: {exc}"})
    report = {"result": "FAIL" if failures else "PASS", "cases": results, "failures": failures,
              "scope": "raw ladder and natural 4095 dual-end lifecycle only"}
    print(json.dumps(report, indent=2))
    if args.write:
        args.write.write_text(json.dumps(report, indent=2) + "\n")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
