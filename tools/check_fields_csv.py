#!/usr/bin/env python3
"""Strict structural gate for the CSV evidence tables in ``data/``.

Every checked file must have a header row and every following record must have
exactly as many fields as the header.  Rows are parsed with the standard
``csv`` module, so a comma inside a properly quoted field does *not* count as a
delimiter; only a real structural mismatch (missing/extra column, unquoted
comma in a field, unbalanced quote) is reported.

The default mode is the gate: any mismatch prints ``file:line: expected N
columns, got M`` and exits 1.  ``--report`` prints the same findings but always
exits 0 (pure reporting, for local diagnosis).

There is deliberately no "heuristic re-split" mode: guessing where an unquoted
comma belongs would silently reassign evidence text to another column.

Usage:
    python3 tools/check_fields_csv.py            # strict gate, exit 1 on any defect
    python3 tools/check_fields_csv.py --report   # report only, always exit 0
    python3 tools/check_fields_csv.py --strict   # legacy alias for the default
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys
from dataclasses import dataclass, field

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_FILES = (
    REPO_ROOT / "data" / "network_fields.csv",
    REPO_ROOT / "data" / "member_offsets.csv",
    REPO_ROOT / "data" / "network_boundary.csv",
    REPO_ROOT / "data" / "unresolved_references.csv",
    REPO_ROOT / "data" / "handle_ops.csv",
)


@dataclass(frozen=True)
class StructuralError:
    """One row whose field count differs from its file's header width."""

    path: pathlib.Path
    line: int
    expected: int
    actual: int
    detail: str = ""


@dataclass
class FileReport:
    path: pathlib.Path
    expected: int = 0
    rows: int = 0
    errors: list[StructuralError] = field(default_factory=list)


def display_path(path: pathlib.Path) -> str:
    """Repository-relative path when possible, absolute path otherwise."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def format_error(error: StructuralError) -> str:
    name = display_path(error.path)
    if error.actual < 0:
        return "%s:%d: CSV parse error (expected %d columns): %s" % (
            name, error.line, error.expected, error.detail)
    text = "%s:%d: expected %d columns, got %d" % (
        name, error.line, error.expected, error.actual)
    if error.detail:
        text += " (%s)" % error.detail
    return text


def scan_file(path: pathlib.Path) -> FileReport:
    """Parse one CSV and compare every record width with the header width."""
    report = FileReport(path=path)
    reader: csv.reader | None = None
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            try:
                header = next(reader)
            except StopIteration:
                report.errors.append(
                    StructuralError(path, 0, 0, 0, "empty file (no header row)"))
                return report
            report.expected = len(header)
            for row in reader:
                report.rows += 1
                if len(row) != report.expected:
                    report.errors.append(StructuralError(
                        path, reader.line_num, report.expected, len(row)))
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        line = reader.line_num if reader is not None else 0
        report.errors.append(StructuralError(
            path, line, report.expected, -1,
            "%s: %s" % (type(exc).__name__, exc)))
    return report


def scan_all(paths: tuple[pathlib.Path, ...] | None = None) -> list[FileReport]:
    """Run the structural check over ``paths`` (all five data CSVs by default)."""
    if paths is None:
        paths = DEFAULT_FILES
    return [scan_file(path) for path in paths]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Strict CSV structure gate for data/*.csv")
    parser.add_argument(
        "--report", action="store_true",
        help="print findings only; always exit 0")
    parser.add_argument(
        "--strict", action="store_true",
        help="legacy alias: strict is already the default")
    args = parser.parse_args(argv)

    reports = scan_all()
    total_errors = 0
    bad_files = 0
    for report in reports:
        name = display_path(report.path)
        if report.errors:
            bad_files += 1
            total_errors += len(report.errors)
            print("FAIL %s: %d data rows, header %d columns, %d bad row(s)" % (
                name, report.rows, report.expected, len(report.errors)))
            for error in report.errors:
                print("  " + format_error(error))
        else:
            print("OK   %s: %d data rows, header %d columns" % (
                name, report.rows, report.expected))

    if total_errors:
        print("status: FAILED (%d structural error(s) in %d file(s))" % (
            total_errors, bad_files))
    else:
        print("status: OK (%d files, %d rows; every row matches its header width)" % (
            len(reports), sum(report.rows for report in reports)))

    if args.report:
        return 0
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
