#!/usr/bin/env python3
"""Release gate: Power BI P&L Assumption Table month coverage (F21).

docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md's follow-up sweep (2026-09-25)
found `PowerBI/DAX/02_PnL_Measures.dax` silently defaulted a month with no
`AssumptionTable.csv` row to a hardcoded 50% Gross Margin / 0% Trade Spend.
The DAX side is now fixed to fail closed (BLANK(), never a fabricated
number, plus an `Assumption Status` card measure) -- this script is the
other half: it stops that gap from ever reaching a report in the first
place, by failing the build the moment a real reporting month has no
matching Assumption Table row, instead of relying on someone noticing a
suspicious 50.0% margin in Power BI.

"Required reporting months" = every month from Apr'26 (the Assumption
Table's own starting month, and the start of the FY27 window this table
covers) through the latest month with a REAL monthly Primary or Offtake
drop already landed in this repo (`PowerBI/RawDataFolders/{Primary_
Article_Monthly,Offtake_Monthly}/`) -- never a hardcoded date, so this
keeps working unattended as new months arrive (same principle as THE ONE
FY RULE in CLAUDE.md). "Covered" = the Assumption Table has an ALL/ALL/ALL
(Chain/Brand/Category) row for that month -- the row that guarantees a
value for any query, matching what `_Assumption Gross Margin %`'s ALL
fallback in the DAX actually reads.

Exit codes: 0 = READY (every required month covered), 3 = BLOCKED_FINANCE_INPUT.
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ASSUMPTION_TABLE = REPO / "PowerBI" / "SeedData" / "Masters" / "AssumptionTable.csv"
MONTHLY_SOURCE_DIRS = [
    REPO / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly",
    REPO / "PowerBI" / "RawDataFolders" / "Offtake_Monthly",
]
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ASSUMPTION_TABLE_START = (2026, 4)  # Apr'26 -- this table's own first row; see docstring


def _month_num(abbr):
    try:
        return MONTH_ABBR.index(abbr[:3].title()) + 1
    except ValueError:
        return None


def month_label(year, month):
    """(2026, 4) -> "Apr'26", matching AssumptionTable.csv's own Month column format."""
    return f"{MONTH_ABBR[month - 1]}'{year % 100:02d}"


def month_range(start, end):
    """Inclusive (year, month) tuples from start to end, chronological."""
    y, m = start
    out = []
    while (y, m) <= end:
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def find_required_months():
    """Every (year, month) from ASSUMPTION_TABLE_START through the latest
    real monthly Primary/Offtake drop actually present in this repo."""
    pattern = re.compile(r"_([A-Za-z]{3})_(\d{2})\.csv$")
    latest = ASSUMPTION_TABLE_START
    found_any = False
    for d in MONTHLY_SOURCE_DIRS:
        if not d.is_dir():
            continue
        for f in d.glob("*.csv"):
            m = pattern.search(f.name)
            if not m:
                continue
            mon_num = _month_num(m.group(1))
            if mon_num is None:
                continue
            yr = 2000 + int(m.group(2))
            candidate = (yr, mon_num)
            if candidate < ASSUMPTION_TABLE_START:
                continue  # a real FY26-or-earlier drop -- outside this table's own scope
            found_any = True
            if candidate > latest:
                latest = candidate
    if not found_any:
        return []  # no real monthly source found at all -- nothing to require yet
    return month_range(ASSUMPTION_TABLE_START, latest)


def find_covered_months():
    """Months with a real ALL/ALL/ALL row in AssumptionTable.csv."""
    covered = set()
    with ASSUMPTION_TABLE.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("Chain") == "ALL" and row.get("Brand") == "ALL" and row.get("Category") == "ALL":
                covered.add((row.get("Month") or "").strip())
    return covered


def main():
    if not ASSUMPTION_TABLE.is_file():
        print(f"BLOCKED_FINANCE_INPUT: {ASSUMPTION_TABLE} not found")
        return 3

    required = find_required_months()
    if not required:
        print("OK: no real monthly Primary/Offtake source found yet -- nothing to require")
        return 0

    covered = find_covered_months()
    required_labels = [month_label(y, m) for (y, m) in required]
    missing = [lab for lab in required_labels if lab not in covered]

    if missing:
        print(f"BLOCKED_FINANCE_INPUT: AssumptionTable missing {', '.join(missing)}")
        print(
            "Do not fabricate, interpolate, or estimate these -- Finance must supply "
            "the approved Gross Margin %/Trade Spend %/Visibility/Scheme figures for "
            "each missing month (see PowerBI/SeedData/Masters/AssumptionTable.csv)."
        )
        return 3

    print(
        f"OK: AssumptionTable covers all {len(required_labels)} required months "
        f"({required_labels[0]}..{required_labels[-1]})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
