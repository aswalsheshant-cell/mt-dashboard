"""Compare governed source Offtake with the same months in dashboard/data.js."""

import argparse
import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path


MONTHS = {name: number for number, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1
)}
FILE_NAME = re.compile(r"offtake_store_article_([A-Za-z]{3})_(\d{2})\.csv$")


def load_html(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8-sig").strip()
    prefix = "window.DASH = "
    if not text.startswith(prefix):
        raise ValueError("data.js lacks the window.DASH JSON wrapper")
    return json.loads(text[len(prefix):].rstrip("; \t\r\n"))


def reconcile(audit: dict, html: dict) -> dict:
    offtake = html.get("offtake") or {}
    rows = []
    files = [item for item in audit.get("files", []) if item.get("source_family") == "Offtake_Monthly"]
    month_counts = Counter(FILE_NAME.search(item["path"]).groups() for item in files if FILE_NAME.search(item["path"]))
    for item in files:
        match = FILE_NAME.search(item["path"])
        if not match or match.group(1).title() not in MONTHS:
            raise ValueError(f"unrecognized Offtake source file: {item['path']}")
        mon, yy = match.group(1).title(), int(match.group(2))
        month = f"{mon}-{yy:02d}"
        fy = yy + (1 if MONTHS[mon] >= 4 else 0)
        key = f"fy{fy:02d}"
        labels = offtake.get(f"months_{key}") or []
        values = offtake.get(f"monthly_{key}") or []
        if len(labels) != len(values):
            raise ValueError(f"HTML {key} month and value lengths differ")
        html_values = dict(zip(labels, values))
        source = Decimal(item["governed_raw_sum"])
        if month_counts[(match.group(1), match.group(2))] > 1:
            status, value, difference = "DUPLICATE_SOURCE", None, None
        elif month not in html_values or html_values[month] is None:
            status, value, difference = "NOT_COMPARABLE", None, None
        else:
            value = Decimal(str(html_values[month]))
            difference = source - value
            status = "MATCH" if abs(difference) <= Decimal("0.01") else "MISMATCH"
        rows.append({
            "metric": "governed_offtake_nsv",
            "source_file": item["path"],
            "fy": key.upper(),
            "month": month,
            "unit": "INR_lakh",
            "source_lakh": str(source),
            "html_lakh": str(value) if value is not None else None,
            "difference_lakh": str(difference) if difference is not None else None,
            "status": status,
        })
    return {"comparison": "same_metric_month_channel_unit", "months": rows,
            "all_match": bool(rows) and all(row["status"] == "MATCH" for row in rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-json", required=True, type=Path)
    parser.add_argument("--html-data-js", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    audit = json.loads(args.audit_json.read_text(encoding="utf-8"))
    result = reconcile(audit, load_html(args.html_data_js))
    out = args.out.resolve()
    if out.is_relative_to(args.html_data_js.resolve().parent):
        raise ValueError("refusing to write a reconciliation file into the published dashboard")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, indent=2))
    return 0 if result["all_match"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

