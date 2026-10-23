#!/usr/bin/env python3
"""Differential analysis for N27-D19 client probe JSONL.

Usage:
  python3 diff_traces.py --runs DIR [DIR ...] --out reports/n27d19/diff.md --json data/n27d19/diff.json

Accepts run directories containing metadata.json and events.jsonl.
Normalizes all code pointers to module+RVA using metadata bases.
Never compares raw heap addresses as identities.
"""
import argparse, json, collections, re
from pathlib import Path

MODS = {"engine": 0x800000, "client": 0x900000}

def load_jsonl(p):
    rows = []
    for line in Path(p).read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: pass
    return rows

def norm(addr, meta):
    if not isinstance(addr, (int, float)): return None
    a = int(addr)
    if a < 0: return None
    for name in ("engine", "client"):
        base = meta.get(f"{name}_base")
        if base is None: continue
        b = int(base, 16) if isinstance(base, str) else int(base)
        if b <= a < b + MODS[name]:
            return f"{name}+0x{a-b:X}"
    return f"abs:0x{a:X}"

def norm_event(ev, meta):
    out = dict(ev)
    if ev.get("target_rva") is not None and ev.get("target_module"):
        out["target"] = f"{ev['target_module']}+0x{int(ev['target_rva']):X}"
    elif ev.get("target") is not None:
        out["target"] = norm(ev.get("target"), meta)
    if ev.get("edx_rva") is not None and ev.get("edx_module"):
        out["edx"] = f"{ev['edx_module']}+0x{int(ev['edx_rva']):X}"
    if ev.get("esi_rva") is not None and ev.get("esi_module"):
        out["esi"] = f"{ev['esi_module']}+0x{int(ev['esi_rva']):X}"
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", required=True)
    args = ap.parse_args()

    runs = {}
    for d in args.runs:
        d = Path(d)
        mp = d/"metadata.json"
        if not mp.exists(): continue
        meta = json.loads(mp.read_text())
        ev = [norm_event(e, meta) for e in load_jsonl(d/"events.jsonl")]
        runs[d.name] = {"meta": meta, "events": ev}

    by_image = collections.defaultdict(list)
    for name, r in runs.items(): by_image[r["meta"].get("image", "?")].append((name, r))

    targets = collections.defaultdict(lambda: collections.Counter())
    vtables = collections.defaultdict(lambda: collections.Counter())
    e56 = collections.defaultdict(lambda: collections.Counter())
    for image, rs in by_image.items():
        for name, r in rs:
            for e in r["events"]:
                if e.get("event") == "hit" and e.get("probe") == "finalCall" and e.get("full_state"):
                    targets[image][e.get("target_key") or "?"] += 1
                if e.get("event") == "hit" and e.get("probe") == "finalCall":
                    t = e.get("target_key") or e.get("target") or "?"
                    vtables[image][e.get("edx") or "?"] += 1
                    if "0x56E60" in t:
                        e56[image][(t, e.get("edx"), e.get("esi"))] += 1

    lines = ["# N27-D19 differential report", ""]
    lines.append(f"Runs: {len(runs)}; images: {', '.join(sorted(by_image))}")
    lines.append("")
    for image in sorted(by_image):
        lines.append(f"## {image}")
        lines.append("")
        lines.append("| run | ok | connect | events | engine_base | client_base |")
        lines.append("|---|---|---|---|---|---|")
        for name, r in by_image[image]:
            m = r["meta"]
            lines.append(f"| {name} | {m.get('ok')} | {m.get('connect_ok')} | {len(r['events'])} | {m.get('engine_base')} | {m.get('client_base')} |")
        lines.append("")
        lines.append("### finalCall target histogram")
        lines.append("")
        lines.append("| target | hits |")
        lines.append("|---|---|")
        for t, n in targets[image].most_common(20):
            lines.append(f"| `{t}` | {n} |")
        lines.append("")

    all_targets = set().union(*[set(c) for c in targets.values()]) if targets else set()
    lines.append("## Target set comparison")
    lines.append("")
    for t in sorted(all_targets):
        bits = [f"{img}={targets[img].get(t,0)}" for img in sorted(by_image)]
        lines.append(f"- `{t}`: " + ", ".join(bits))
    lines.append("")
    lines.append("## E56 target objects (target, vtable, object)")
    lines.append("")
    for img in sorted(e56):
        for (t, edx, esi), n in e56[img].most_common(10):
            lines.append(f"- {img}: target={t} edx={edx} esi={esi} hits={n}")
    if not e56:
        lines.append("- no E56 target observed in any run")

    md = "\n".join(lines) + "\n"
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(md)
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps({
        "runs": {n: {"image": r["meta"].get("image"), "ok": r["meta"].get("ok"),
                     "events": len(r["events"])} for n, r in runs.items()},
        "targets": {img: dict(c) for img, c in targets.items()},
        "vtables": {img: dict(c) for img, c in vtables.items()},
    }, indent=2))
    print(md)

if __name__ == "__main__":
    main()
