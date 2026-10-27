#!/usr/bin/env python3
"""Generate the small, source-backed SVGs used by the public documentation."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from check_raw_lifecycle import lifecycle as verify_lifecycle


ROOT = Path(__file__).resolve().parents[2]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg(title: str, width: int, height: int, body: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{esc(title)}</title>
  <desc id="desc">L4D2-4096 technical diagram. Values are tied to build 23990068.</desc>
  <style>
    :root {{ color-scheme: light dark; }}
    text {{ font-family: Inter,Segoe UI,Arial,sans-serif; fill: #17202a; }}
    .bg {{ fill: #f7f9fb; }} .panel {{ fill: #ffffff; stroke: #b9c4cf; stroke-width: 1.5; }}
    .old {{ fill: #e8edf2; stroke: #667687; stroke-width: 1.5; }}
    .new {{ fill: #d9f3e5; stroke: #2c8b57; stroke-width: 1.5; }}
    .wire {{ fill: #dceafe; stroke: #356eb8; stroke-width: 1.5; }}
    .label {{ font-size: 16px; font-weight: 500; }} .small {{ font-size: 13px; }}
    .muted {{ font-size: 12px; fill: #526273; }} .arrow {{ stroke: #425466; stroke-width: 2; fill: none; marker-end: url(#arrow); }}
    .good {{ fill: #2c8b57; }} .axis {{ stroke: #748394; stroke-width: 1; }}
    @media (prefers-color-scheme: dark) {{ text {{ fill: #e8eef5; }} .bg {{ fill: #151b22; }} .panel {{ fill: #1e2732; stroke: #718096; }} .old {{ fill: #303b47; stroke: #9aa9b8; }} .new {{ fill: #19452f; stroke: #68d391; }} .wire {{ fill: #17375f; stroke: #73a7ed; }} .muted {{ fill: #b4c0cc; }} .axis {{ stroke: #95a4b4; }} .arrow {{ stroke: #c1cfdd; }} }}
  </style>
  <defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#425466"/></marker></defs>
  <rect class="bg" width="100%" height="100%"/>
{body}
</svg>
'''


def capacity() -> str:
    body = '''
  <text x="40" y="38" class="label">Entity capacity before and after</text>
  <text x="40" y="62" class="muted">Source build 23990068 · network and internal tables have different limits</text>
  <rect x="40" y="90" width="320" height="280" rx="12" class="panel"/>
  <text x="64" y="126" class="label">Vanilla L4D2</text>
  <rect x="64" y="150" width="272" height="42" rx="7" class="old"/>
  <text x="78" y="176" class="small">network edicts · 0–2047</text>
  <rect x="64" y="208" width="272" height="42" rx="7" class="old"/>
  <text x="78" y="234" class="small">internal slots · 0–4095</text>
  <text x="64" y="282" class="muted">network index: 11 bits</text>
  <path d="M390 200 H470" class="arrow"/>
  <rect x="500" y="90" width="320" height="280" rx="12" class="panel"/>
  <text x="524" y="126" class="label">L4D2-4096</text>
  <rect x="524" y="150" width="272" height="42" rx="7" class="new"/>
  <text x="538" y="176" class="small">network edicts · 0–4095</text>
  <rect x="524" y="208" width="272" height="42" rx="7" class="new"/>
  <text x="538" y="234" class="small">internal slots · 0–8191</text>
  <text x="524" y="282" class="muted">index: 12-bit network / 13-bit internal</text>
  <text x="64" y="316" class="small">reserved slot: 2048</text>
  <text x="64" y="342" class="small">non-network pool: 2049–4095</text>
  <text x="524" y="316" class="small">reserved slot: 4096</text>
  <text x="524" y="342" class="small">non-network pool: 4097–8191</text>
  <text x="40" y="412" class="muted">Internal EHANDLE: 13-bit index + 15-bit serial · network serial: 10 bits</text>
  <text x="40" y="438" class="muted">Source: D61 partition and D62/D65 runtime evidence · see docs/architecture.md</text>
'''
    return svg("Entity capacity before and after", 860, 470, body)


def protocol() -> str:
    body = '''
  <text x="40" y="38" class="label">Network path and width boundaries</text>
  <text x="40" y="62" class="muted">The packet count, entity index, and serial are separate fields</text>
  <rect x="40" y="110" width="220" height="150" rx="12" class="panel"/>
  <text x="64" y="146" class="label">Linux Dedicated</text>
  <text x="64" y="178" class="small">allocate / snapshot</text>
  <text x="64" y="202" class="small">server edict index 0–4095</text>
  <text x="64" y="226" class="muted">patched engine + game DLL</text>
  <path d="M270 184 H350" class="arrow"/>
  <rect x="370" y="98" width="290" height="174" rx="12" class="wire"/>
  <text x="394" y="134" class="label">PacketEntities</text>
  <text x="394" y="166" class="small">entry/count fields · 13 bits</text>
  <text x="394" y="190" class="small">entity index · 12 bits</text>
  <text x="394" y="214" class="small">network serial · 10 bits</text>
  <text x="394" y="246" class="muted">no single “entity width”</text>
  <path d="M670 184 H750" class="arrow"/>
  <rect x="770" y="110" width="220" height="150" rx="12" class="panel"/>
  <text x="794" y="146" class="label">Patched client</text>
  <text x="794" y="178" class="small">decode / create / update</text>
  <text x="794" y="202" class="small">client slots 0–8191</text>
  <text x="794" y="226" class="muted">Windows or Proton</text>
  <path d="M880 290 V340 H150 V290" class="arrow"/>
  <text x="40" y="372" class="muted">Client and server must use matching expansion images; vanilla clients cannot decode index ≥ 2048.</text>
'''
    return svg("Network path and width boundaries", 1030, 410, body)


def lifecycle() -> str:
    body = '''
  <text x="40" y="38" class="label">High-index entity lifecycle</text>
  <text x="40" y="62" class="muted">Representative D65 boundary: index 4095, normal allocator, no direct slot writes</text>
  <g transform="translate(42,112)">
    <rect x="0" y="0" width="130" height="60" rx="10" class="new"/><text x="65" y="35" text-anchor="middle" class="small">Allocate</text>
    <rect x="160" y="0" width="130" height="60" rx="10" class="panel"/><text x="225" y="35" text-anchor="middle" class="small">Create</text>
    <rect x="320" y="0" width="160" height="60" rx="10" class="wire"/><text x="400" y="35" text-anchor="middle" class="small">Server snapshot</text>
    <rect x="510" y="0" width="145" height="60" rx="10" class="wire"/><text x="582" y="35" text-anchor="middle" class="small">Client create</text>
    <rect x="685" y="0" width="130" height="60" rx="10" class="panel"/><text x="750" y="35" text-anchor="middle" class="small">Update ×6</text>
    <path d="M132 30 H157" class="arrow"/><path d="M292 30 H317" class="arrow"/>
    <path d="M482 30 H507" class="arrow"/><path d="M657 30 H682" class="arrow"/>
    <path d="M815 30 H875 V125 H745" class="arrow"/>
    <rect x="610" y="95" width="145" height="60" rx="10" class="panel"/><text x="682" y="130" text-anchor="middle" class="small">Delete</text>
    <path d="M608 125 H445" class="arrow"/>
    <rect x="250" y="95" width="195" height="60" rx="10" class="new"/><text x="347" y="130" text-anchor="middle" class="small">Client remove</text>
    <path d="M248 125 H125 V190 H250" class="arrow"/>
    <rect x="250" y="190" width="310" height="60" rx="10" class="new"/><text x="405" y="225" text-anchor="middle" class="small">Serial increment / slot reuse</text>
  </g>
  <text x="42" y="402" class="muted">Old references become invalid; serial repetition after its finite period is expected and must be checked by lifecycle state.</text>
'''
    return svg("High-index entity lifecycle", 930, 440, body)


def ladder_chart(data: dict) -> str:
    rows = data["ladder"]
    width, height = 820, 430
    left, top, chart_w, chart_h = 76, 94, 700, 250
    maxv = max(r["count"] for r in rows)
    marks = []
    for i, row in enumerate(rows):
        x = left + (i + 0.5) * chart_w / len(rows)
        h = chart_h * row["count"] / maxv
        y = top + chart_h - h
        marks.append(f'<rect x="{x-34:.1f}" y="{y:.1f}" width="68" height="{h:.1f}" rx="5" fill="#2c8b57" opacity="0.88"/>')
        marks.append(f'<text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" class="small">{row["count"]}</text>')
        marks.append(f'<text x="{x:.1f}" y="{top+chart_h+26}" text-anchor="middle" class="small">{row["count"]} props</text>')
        marks.append(f'<text x="{x:.1f}" y="{top+chart_h+47}" text-anchor="middle" class="muted">{esc(row["status"])}</text>')
    body = f'''
  <text x="40" y="38" class="label">D65 real-entity ladder</text>
  <text x="40" y="62" class="muted">Each marked level records create, six updates, delete, and allocator reuse</text>
  <line x1="{left}" y1="{top+chart_h}" x2="{left+chart_w}" y2="{top+chart_h}" class="axis"/>
  <line x1="{left}" y1="{top}" x2="{left}" y2="{top+chart_h}" class="axis"/>
  <text x="{left-46}" y="{top+10}" class="muted">512</text>
  <text x="{left-36}" y="{top+chart_h+4}" class="muted">0</text>
  {''.join(marks)}
  <text x="{left+chart_w/2}" y="{height-18}" text-anchor="middle" class="muted">Network entities held in the private test session</text>
'''
    return svg("D65 real-entity ladder", width, height, body)


def boundary_chart(data: dict) -> str:
    points = data["boundary"]
    width, height = 1000, 300
    x0, x1, y = 140, 860, 140
    xs = [x0 + i * (x1-x0)/(len(points)-1) for i in range(len(points))]
    body = [
        '<text x="40" y="38" class="label">Boundary coverage</text>',
        '<text x="40" y="62" class="muted">Categorical anchors (not to scale) · not full simultaneous occupation of 4096 slots</text>',
        f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" class="axis"/>',
    ]
    for x, p in zip(xs, points):
        body.append(f'<circle cx="{x:.1f}" cy="{y}" r="10" class="new"/>')
        body.append(f'<text x="{x:.1f}" y="{y-24}" text-anchor="middle" class="label">{p["index"]}</text>')
        body.append(f'<text x="{x:.1f}" y="{y+38}" text-anchor="middle" class="small">{esc(p["label"])}</text>')
        body.append(f'<text x="{x:.1f}" y="{y+58}" text-anchor="middle" class="muted">{esc(p["result"])}</text>')
    body.append('<text x="100" y="246" class="muted">2047 is the vanilla ceiling · 2048 is the first added index · 4095 is the highest valid network index</text>')
    return svg("Boundary coverage", width, height, "\n".join(body))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence-root", type=Path, default=Path("runs/d65"))
    ap.add_argument("--output", type=Path, default=ROOT / "docs/assets")
    a = ap.parse_args()
    out = a.output.resolve()
    (out / "diagrams").mkdir(parents=True, exist_ok=True)
    (out / "benchmark").mkdir(parents=True, exist_ok=True)

    levels = []
    for count in [16,64,128,256,512]:
        prefix=f"load{count}" + ("-actual" if count != 16 else "")
        checked=verify_lifecycle(a.evidence_root,prefix,count)
        levels.append({"count":count,"status":checked["status"],
                       "evidence":f"{prefix}-*.json"})
    verify_lifecycle(a.evidence_root,"boundary",1,True)
    ladder = {
        "schema": "l4d2-d65-ladder-v1",
        "source": "raw runs/d65 snapshots independently recomputed by check_raw_lifecycle.py",
        "ladder": levels,
    }
    boundary = {
        "schema": "l4d2-d65-boundary-v1",
        "source": "reports/n27d65/validation.json and runs/d65/boundary-*.json",
        "boundary": [
            {"index": 2047, "label": "vanilla ceiling", "result": "API round-trip"},
            {"index": 2048, "label": "first added", "result": "create/update/delete"},
            {"index": 2049, "label": "edge pair", "result": "client visible"},
            {"index": 4095, "label": "maximum", "result": "reuse + callbacks"},
        ],
    }
    (out / "benchmark/d65-ladder.json").write_text(json.dumps(ladder, indent=2) + "\n", encoding="utf-8")
    (out / "benchmark/d65-boundary.json").write_text(json.dumps(boundary, indent=2) + "\n", encoding="utf-8")
    (out / "diagrams/capacity.svg").write_text(capacity(), encoding="utf-8")
    (out / "diagrams/protocol.svg").write_text(protocol(), encoding="utf-8")
    (out / "diagrams/lifecycle.svg").write_text(lifecycle(), encoding="utf-8")
    (out / "benchmark/d65-ladder.svg").write_text(ladder_chart(ladder), encoding="utf-8")
    (out / "benchmark/d65-boundary.svg").write_text(boundary_chart(boundary), encoding="utf-8")
    print(f"wrote assets under {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
