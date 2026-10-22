#!/usr/bin/env python3
"""Check the structural health of data/network_fields.csv.

The field map predates a fixed schema: some rows quote fields that contain
commas (``WriteUBitLong(v, 11, 1)``) while most do not, so ``csv.reader``
returns a variable number of fields per row.  This is a *reporting* tool, not
a rewriter -- rewriting rows whose quoting is ambiguous would silently
reinterpret evidence.  It

  * prints the field-count distribution,
  * lists the rows that deviate, with the field that most likely absorbed the
    split (an unquoted comma inside ``encoding_rule``),
  * exits non-zero only under ``--strict``.

Usage:
    python3 tools/check_fields_csv.py
    python3 tools/check_fields_csv.py --strict   # gate: any deviation fails
"""

from __future__ import annotations

import argparse
import collections
import csv
import pathlib
import sys

CSV_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "network_fields.csv"
COLUMNS = [
    "kind", "symbol", "struct_offset", "field", "bit_width", "encoding_rule",
    "legal_range", "evidence_class", "va", "rva", "site_va", "note",
]


def load() -> tuple[list[str], list[list[str]]]:
    with CSV_PATH.open(encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise SystemExit(f"empty csv: {CSV_PATH}")
    return rows[0], rows[1:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 if any row deviates from the header width")
    args = parser.parse_args(argv)

    header, rows = load()
    width = len(header)
    dist = collections.Counter(len(row) for row in rows)
    modal = dist.most_common(1)[0][0] if dist else width
    print(f"file      : {CSV_PATH}")
    print(f"header    : {width} columns -> {', '.join(header)}")
    print(f"data rows : {len(rows)}")
    print(f"widths    : " + ", ".join(f"{n}x{k}" for k, n in sorted(dist.items())))

    if width != modal:
        print(f"schema    : header is {width} but the modal row is {modal}")
        print(f"            modal rows align with header[0:{modal - 1}] + header[{modal}:] "
              f"(omitted: '{header[modal - 1]}')")
    if width != len(COLUMNS):
        print(f"note      : header names differ from the documented {len(COLUMNS)}-column schema")
    if len(dist) == 1 and dist.get(width, 0) == len(rows):
        print("status    : OK (uniform width)")
        return 0

    off = [(i + 2, row) for i, row in enumerate(rows) if len(row) != modal]
    print(f"status    : {len(off)} row(s) deviate from the modal width {modal}")
    print("likely cause: unquoted comma inside encoding_rule, e.g. WriteUBitLong(v, 11, 1)")
    for line_no, row in off:
        label = f"{row[0]}/{row[1]}" if len(row) > 1 else row[0]
        print(f"  line {line_no:>3}  n={len(row):<2}  {label[:64]}")
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
