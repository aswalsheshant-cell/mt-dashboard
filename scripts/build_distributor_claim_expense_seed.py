#!/usr/bin/env python3
"""Build a governed Q1 FY27 distributor/indirect-claim expense seed.

The tracked source is already a real CSV:
PowerBI/RawDataFolders/ClaimMaster_Quarterly/claim_master_chain_AprJun_2026.csv

Its grain is Q1 x Chain, with one column per expense head. The production
PL_Expense_Input.csv is Month x Chain/Customer x Expense Head. This script
therefore DOES NOT spread Q1 values across Apr/May/Jun. It preserves the source
at its real Q1 grain so it can be reviewed and used once real month x chain
evidence is supplied (or Finance explicitly approves a period-grain treatment).

No allocation by distributor monthly ratios is permitted here: that would
create derived monthly financial truth, not actual claims.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / "PowerBI" / "RawDataFolders" / "ClaimMaster_Quarterly" / "claim_master_chain_AprJun_2026.csv"
DEFAULT_OUT = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Distributor_Claim_Input_Q1_FY27.csv"

EXPECTED_SCOPE = ("Apr-Jun 2026", "FY27", "Q1")
OUTPUT_FY = "FY26-27"
SOURCE_TAG = "Distributor chain claim master (Q1 FY27)"
ROUNDING_TOLERANCE_LAKH = 0.01

EXPENSE_COLUMNS = {
    "Chain_Promo_Lakh": ("Chain Promo (On Invoice)", "Variable"),
    "Rate_Diff_Lakh": ("Extra Margin / Rate Difference", "Variable"),
    "Freight_Lakh": ("Freight / Transportation", "Variable"),
    "Incentive_Lakh": ("Incentive", "Variable"),
    "Off_Invoice_Lakh": ("Off Invoice / Debit Note Promo", "Variable"),
    "Visibility_Lakh": ("Visibility", "Fixed"),
}

OUT_FIELDS = [
    "Period", "FY", "Quarter", "Chain", "Source Chain", "Expense Head",
    "Expense Type", "Expense Amount (INR Lakh)", "Remarks", "Source",
    "Updated By", "Updated Date",
]


def _money(value: str) -> float:
    try:
        return float(value or 0)
    except ValueError as exc:
        raise SystemExit(f"ERROR: invalid claim amount {value!r}") from exc


def build_rows(src: Path, updated_date: str) -> tuple[list[dict], dict]:
    with src.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        source_rows = list(reader)
        fields = set(reader.fieldnames or [])

    required = {
        "Period", "FY_Year", "Quarter", "Chain", "Source_Chain",
        "Total_Claim_Lakh", *EXPENSE_COLUMNS.keys(),
    }
    missing = sorted(required - fields)
    if missing:
        raise SystemExit(f"ERROR: missing required source columns: {missing}")
    if not source_rows:
        raise SystemExit("ERROR: distributor claim source is empty")

    scopes = {(r["Period"].strip(), r["FY_Year"].strip(), r["Quarter"].strip()) for r in source_rows}
    if scopes != {EXPECTED_SCOPE}:
        raise SystemExit(
            f"ERROR: expected only scope {EXPECTED_SCOPE}, found {sorted(scopes)}. "
            "Do not mix periods in one governed seed."
        )

    source_total = sum(_money(r["Total_Claim_Lakh"]) for r in source_rows)
    output_rows: list[dict] = []

    for row in source_rows:
        chain = row["Chain"].strip()
        source_chain = row["Source_Chain"].strip()
        for source_col, (expense_head, expense_type) in EXPENSE_COLUMNS.items():
            amount = _money(row[source_col])
            if amount == 0:
                continue
            output_rows.append({
                "Period": EXPECTED_SCOPE[0],
                "FY": OUTPUT_FY,
                "Quarter": EXPECTED_SCOPE[2],
                "Chain": chain,
                "Source Chain": source_chain,
                "Expense Head": expense_head,
                "Expense Type": expense_type,
                "Expense Amount (INR Lakh)": f"{amount:.4f}",
                "Remarks": (
                    "Actual distributor/indirect claim; Q1 aggregate only. "
                    "Do not allocate to months without transaction evidence."
                ),
                "Source": SOURCE_TAG,
                "Updated By": "MT Analytics",
                "Updated Date": updated_date,
            })

    written_total = sum(float(r["Expense Amount (INR Lakh)"]) for r in output_rows)
    variance = written_total - source_total
    if abs(variance) > ROUNDING_TOLERANCE_LAKH:
        raise SystemExit(
            f"ERROR: category-detail total {written_total:.4f} L does not reconcile "
            f"to source total {source_total:.4f} L (variance {variance:.4f} L)"
        )

    return output_rows, {
        "source_rows": len(source_rows),
        "output_rows": len(output_rows),
        "source_total_lakh": round(source_total, 4),
        "written_total_lakh": round(written_total, 4),
        "rounding_variance_lakh": round(variance, 4),
        "negative_rows_preserved": sum(
            float(r["Expense Amount (INR Lakh)"]) < 0 for r in output_rows
        ),
    }


def write_seed(rows: list[dict], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=DEFAULT_SRC)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--updated-date", default="2026-09-27")
    parser.add_argument("--check", action="store_true",
                        help="Validate/rebuild in memory only; do not write the seed.")
    args = parser.parse_args()

    rows, report = build_rows(args.src, args.updated_date)
    for key, value in report.items():
        print(f"{key}: {value}")

    if args.check:
        print("CHECK ONLY -- nothing written")
        return 0

    write_seed(rows, args.out)
    print(f"wrote: {args.out.relative_to(ROOT) if args.out.is_relative_to(ROOT) else args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
