#!/usr/bin/env python3
"""Read-only readiness report for the two inputs the dashboard is waiting on.

1. Finance AssumptionTable: which months are MISSING or UNAPPROVED, plus an
   optional BLANK request sheet for Finance to fill (--write-request).
   Nothing is estimated, copied forward or filled in.
2. Monthly Primary file for the latest Offtake month (for example
   primary_article_Sep_26.csv): is it present, does it carry the same 24
   columns as the last loaded month, and do its month, FY, dates and totals
   look right. Nothing is loaded or changed here.

Usage:
    python scripts/finance_input_readiness.py
    python scripts/finance_input_readiness.py --write-request exports/Finance_Assumption_Request.csv

Exit code: 0 = both ready, 3 = at least one input still missing.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_assumption_coverage as cac  # noqa: E402

REPO = cac.REPO
PRIMARY_DIR = REPO / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
OFFTAKE_DIR = REPO / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
REQUEST_COLUMNS = [
    "Month", "Chain", "Brand", "Category", "Gross Margin %", "Trade Spend %", "Visibility Spend",
    "Scheme Spend", "Other Spend", "Contribution Margin %", "Remarks",
]
_FILE = re.compile(r"_([A-Za-z]{3})_(\d{2})\.csv$")


def fy_tag(year, month):
    """THE ONE FY RULE: Apr-Dec of Y is FY(Y+1); Jan-Mar of Y is FY(Y)."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"


def latest_file(folder):
    best = None
    for f in folder.glob("*.csv"):
        m = _FILE.search(f.name)
        mon = cac._month_num(m.group(1)) if m else None
        if mon:
            key = (2000 + int(m.group(2)), mon)
            if best is None or key > best[0]:
                best = (key, f)
    return best


def finance_status():
    required = [cac.month_label(y, m) for y, m in cac.find_required_months()]
    status = cac.find_month_status()
    missing = [x for x in required if x not in status]
    unapproved = [x for x in required if status.get(x) == "UNAPPROVED"]
    return required, missing, unapproved


def write_request(path, months):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(REQUEST_COLUMNS)
        for m in months:
            # Every value AND Remarks stay blank on purpose. A pre-filled "Approved: ..." text would pass the
            # coverage gate (it only looks for the words), so Finance must type the real reference themselves.
            w.writerow([m, "ALL", "ALL", "ALL"] + [""] * 7)


def primary_status():
    """Check the Primary file for the latest Offtake month. Returns (state, lines)."""
    off = latest_file(OFFTAKE_DIR)
    if off is None:
        return "NO_OFFTAKE", ["No monthly Offtake file found."]
    (y, mon), _ = off
    name = f"primary_article_{cac.MONTH_ABBR[mon - 1]}_{y % 100:02d}.csv"
    label = cac.month_label(y, mon)
    target = PRIMARY_DIR / name
    if not target.is_file():
        return "MISSING", [f"{label} Primary not loaded: {name} not in PowerBI/RawDataFolders/Primary_Article_Monthly/."]
    prev = None
    for f in sorted(PRIMARY_DIR.glob("primary_article_*_26.csv")):
        if f != target:
            prev = f
    out, state = [f"Found {name}."], "READY"
    with target.open(newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        rows = list(rd)
    if prev is not None:
        with prev.open(newline="", encoding="utf-8-sig") as fh:
            ref = next(csv.reader(fh))
        if cols != ref:
            state = "CHECK"
            out.append(f"Columns differ from {prev.name}: missing {sorted(set(ref) - set(cols))}, extra {sorted(set(cols) - set(ref))}.")
    months = {r.get("Month") for r in rows}
    fys = {r.get("FY") for r in rows}
    if months != {label}:
        state = "CHECK"
        out.append(f"Month column is {sorted(months)}, expected only {label}.")
    if fys != {fy_tag(y, mon)}:
        state = "CHECK"
        out.append(f"FY column is {sorted(fys)}, expected only {fy_tag(y, mon)}.")
    try:
        nsv = sum(float(r["Inv. Net value(LOC)"] or 0) for r in rows) / 1e5
    except (KeyError, ValueError):
        nsv, state = None, "CHECK"
        out.append("Inv. Net value(LOC) missing or not numeric.")
    dates = sorted(r["Inv. Date"] for r in rows if r.get("Inv. Date"))
    if dates and not (dates[0].startswith(f"{y}-{mon:02d}") and dates[-1].startswith(f"{y}-{mon:02d}")):
        state = "CHECK"
        out.append(f"Invoice dates run {dates[0]} to {dates[-1]}, outside {label}.")
    out.append(f"{len(rows)} rows" + (f", NSV {nsv:,.2f} L." if nsv is not None else "."))
    return state, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write-request", type=Path, help="write a BLANK Finance request sheet for the missing months")
    a = ap.parse_args(argv)

    blocked = False
    required, missing, unapproved = finance_status()
    print("== Finance AssumptionTable ==")
    print(f"Required months: {', '.join(required) or 'none'}")
    print(f"Missing:    {', '.join(missing) or 'none'}")
    print(f"Unapproved: {', '.join(unapproved) or 'none'}")
    if missing or unapproved:
        blocked = True
        print("BLOCKED_FINANCE_INPUT: needs Finance figures with an 'Approved: <reference>' in Remarks. Nothing estimated.")
    if a.write_request and missing:
        write_request(a.write_request, missing)
        print(f"Blank request sheet written: {a.write_request}")

    print("\n== Primary file for the latest Offtake month ==")
    state, lines = primary_status()
    print("\n".join(lines))
    print(f"Primary status: {state}")
    if state != "READY":
        blocked = True
    return 3 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
