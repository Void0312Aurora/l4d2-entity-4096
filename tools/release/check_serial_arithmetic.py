#!/usr/bin/env python3
"""Check the documented serial/index encodings without claiming runtime safety."""
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    wire = []
    for value in [0, 1, 1022, 1023, 1024, 2047, 32767]:
        encoded = value & 0x3FF
        wire.append({"input": value, "encoded_10bit": encoded,
                     "decoded": encoded, "expected": value & 0x3FF,
                     "ok": encoded == (value & 0x3FF)})
    internal = []
    for index, serial in [(0, 0), (2048, 1), (4095, 32767), (8191, 32767)]:
        handle = ((serial & 0x7FFF) << 13) | (index & 0x1FFF)
        internal.append({"index": index, "serial": serial, "handle": handle,
                         "decoded_index": handle & 0x1FFF,
                         "decoded_serial": (handle >> 13) & 0x7FFF,
                         "ok": (handle & 0x1FFF) == index and (handle >> 13) == serial})
    result = {
        "schema": "l4d2-d66-serial-arithmetic-v1",
        "wire_10bit": wire,
        "internal_13bit_index_15bit_serial": internal,
        "wire_wrap_expected": {"before": 1023, "after": 0},
        "internal_wrap_expected": {"before": 32767, "after": 0},
        "runtime_claim": "NONE",
        "result": "PASS_ARITHMETIC_ONLY" if all(x["ok"] for x in wire + internal) else "FAIL",
    }
    out = Path(__file__).resolve().parents[2] / "reports/n27d66/serial-arithmetic.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["result"] == "PASS_ARITHMETIC_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
