"""Publish the committed MT PO billing summary as a small dashboard sidecar.

This is billed-versus-ordered fill rate. The source has no delivery dates or
stock-on-hand balance, so it cannot produce OTIF or days of inventory.
"""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "PowerBI/SeedData/Forecast/PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv"
OUTPUT = ROOT / "dashboard/po_fill_rate.js"
AMOUNTS = ("PO_Qty", "Billed_Qty", "PO_Value_L", "Billed_Value_L")


def _percentage(numerator, denominator):
    if denominator <= 0:
        return None
    return float((numerator / denominator * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def build_payload(source):
    source = Path(source)
    try:
        source_label = source.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        source_label = source.name
    totals = defaultdict(lambda: {name: Decimal(0) for name in AMOUNTS})
    months = defaultdict(set)
    with source.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        required = {"Month", "FY", "Channel", *AMOUNTS}
        if not required <= set(reader.fieldnames or []):
            raise ValueError(f"PO fill-rate source is missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for row in reader:
            if row["Channel"] != "MT":
                continue
            month = datetime.strptime(row["Month"], "%b-%y")
            fy = f"fy{(month.year + (month.month >= 4)) % 100:02d}"
            if row["FY"].lower() != fy:
                raise ValueError(f"FY does not match month {row['Month']}: {row['FY']}")
            months[fy].add(row["Month"])
            for name in AMOUNTS:
                totals[fy][name] += Decimal(row[name])

    by_fy = {}
    for fy, t in sorted(totals.items()):
        by_fy[fy] = {
            "months": sorted(months[fy], key=lambda m: datetime.strptime(m, "%b-%y")),
            "po_qty": float(t["PO_Qty"]),
            "billed_qty": float(t["Billed_Qty"]),
            "po_value_l": float(t["PO_Value_L"]),
            "billed_value_l": float(t["Billed_Value_L"]),
            "qty_pct": _percentage(t["Billed_Qty"], t["PO_Qty"]),
            "value_pct": _percentage(t["Billed_Value_L"], t["PO_Value_L"]),
        }
    return {
        "measure": "PO billing fill rate (billed / ordered)",
        "channel": "MT",
        "source": source_label,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "by_fy": by_fy,
    }


def render_js(payload):
    return "window.PO_FILL_RATE = " + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + ";\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true", help="fail if the committed sidecar differs from its source")
    args = parser.parse_args()
    content = render_js(build_payload(args.source))
    if args.check:
        if not args.out.exists() or args.out.read_text(encoding="utf-8") != content:
            parser.error(f"stale dashboard sidecar: {args.out}")
    else:
        args.out.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
