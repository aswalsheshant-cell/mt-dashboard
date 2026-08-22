#!/usr/bin/env python3
"""Report taxonomy completeness in dashboard detail records.

Taxonomy gaps are advisory: their presence never changes the process exit code.
Unreadable or invalid input remains an execution error.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
DEFAULT_DATA = REPO / "dashboard" / "data.js"
TAXONOMY_FIELDS = ("SubCategory", "Range", "PackSize")
BREAKDOWN_FIELDS = ("FY", "Month", "Brand", "Chain")


def _reject_non_finite(value: str):
    raise ValueError(f"non-finite JSON number: {value}")


def load_data_js(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    marker = "window.DASH"
    marker_pos = text.find(marker)
    equals_pos = text.find("=", marker_pos + len(marker)) if marker_pos >= 0 else -1
    if marker_pos < 0 or equals_pos < 0:
        raise ValueError("window.DASH assignment not found in data.js")
    payload = text[equals_pos + 1:].rstrip().rstrip(";")
    return json.loads(payload, parse_constant=_reject_non_finite)


def _is_missing(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _sorted_counts(records: list[dict], field: str) -> dict[str, int]:
    counts = Counter(str(row.get(field) or "(Missing)").strip() or "(Missing)" for row in records)
    return dict(sorted(counts.items(), key=lambda item: item[0]))


def profile_records(records: list[dict]) -> dict:
    row_count = len(records)
    fields = {}
    for field in TAXONOMY_FIELDS:
        null_count = sum(_is_missing(row.get(field)) for row in records)
        complete_count = row_count - null_count
        fields[field] = {
            "null_count": null_count,
            "null_pct": round(null_count / row_count * 100, 2) if row_count else 0.0,
            "complete_count": complete_count,
            "complete_pct": round(complete_count / row_count * 100, 2) if row_count else 0.0,
        }

    affected = [
        row for row in records
        if any(_is_missing(row.get(field)) for field in TAXONOMY_FIELDS)
    ]
    return {
        "status": "ADVISORY",
        "row_count": row_count,
        "affected_row_count": len(affected),
        "affected_row_pct": round(len(affected) / row_count * 100, 2) if row_count else 0.0,
        "fields": fields,
        "breakdowns": {field: _sorted_counts(affected, field) for field in BREAKDOWN_FIELDS},
    }


def print_report(report: dict) -> None:
    print("TAXONOMY QUALITY REPORT (ADVISORY)")
    print(f"Rows processed: {report['row_count']:,}")
    print(f"Rows with any taxonomy gap: {report['affected_row_count']:,} "
          f"({report['affected_row_pct']:.2f}%)")
    print("\nField completeness")
    print(f"{'Field':<16} {'Nulls':>10} {'Null %':>10} {'Complete %':>12}")
    for field in TAXONOMY_FIELDS:
        metrics = report["fields"][field]
        print(f"{field:<16} {metrics['null_count']:>10,} "
              f"{metrics['null_pct']:>9.2f}% {metrics['complete_pct']:>11.2f}%")

    for dimension in BREAKDOWN_FIELDS:
        print(f"\nAffected rows by {dimension}")
        for value, count in report["breakdowns"][dimension].items():
            print(f"  {value:<30} {count:>8,}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA,
                        help="dashboard data.js to profile")
    parser.add_argument("--json-out", type=Path,
                        help="optional path for the advisory JSON report")
    args = parser.parse_args(argv)

    dashboard = load_data_js(args.data)
    records = dashboard.get("detail_records", [])
    if not isinstance(records, list):
        raise ValueError("detail_records must be a list")
    report = profile_records(records)
    print_report(report)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nJSON report: {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
