"""
Generate the Historical Primary Chain Backfill final-report figures
PROGRAMMATICALLY from Monthly_Reconciliation_Summary.csv -- never hand-copy
these numbers into a report or PR description again.

Root cause this exists for: an earlier write-up of this backfill quoted
Rs9,455.51L for the provisional bucket and swapped the Actual/DistChainSingle
figures -- a transcription error made while typing the numbers by hand from
a printed table. The run itself was correct; the report was not. This
script removes the hand-copy step entirely and asserts the one invariant
that would have caught the error immediately: the five level totals must
sum to the reported grand total, within a small rounding tolerance.

Usage:
    python scripts/historical_primary_chain_backfill_report.py \
        --summary historical_primary_chain_backfill_output/Monthly_Reconciliation_Summary.csv
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

LEVEL_COLS = ["Actual_L", "DistChainTen_Single_L", "Provisional_L",
              "Secondary_Derived_L", "Unallocated_L"]
LEVEL_LABELS = {
    "Actual_L": "ACTUAL_CHAIN_PRIMARY",
    "DistChainTen_Single_L": "DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY",
    "Provisional_L": "PROVISIONAL_BUSINESS_MAPPED_PRIMARY",
    "Secondary_Derived_L": "SECONDARY_DERIVED_PRIMARY",
    "Unallocated_L": "UNALLOCATED_PRIMARY",
}
DEFAULT_TOLERANCE_L = 0.01


def build_report(summary: pd.DataFrame, tolerance_l: float = DEFAULT_TOLERANCE_L) -> dict:
    """Return the aggregate ₹L / % table plus a PASS/FAIL reconciliation
    check. Raises AssertionError if the levels don't sum to the total within
    tolerance -- this is the control that would have caught the original
    transcription error before it reached a PR description."""
    missing = [c for c in ["Raw_Primary_L", *LEVEL_COLS] if c not in summary.columns]
    if missing:
        raise KeyError(f"Monthly_Reconciliation_Summary.csv missing expected columns: {missing}")

    total = round(float(summary["Raw_Primary_L"].sum()), 4)
    levels = {LEVEL_LABELS[c]: round(float(summary[c].sum()), 4) for c in LEVEL_COLS}
    levels_sum = round(sum(levels.values()), 4)
    diff = round(levels_sum - total, 4)

    assert abs(diff) <= tolerance_l, (
        f"Level totals (sum={levels_sum}) do not reconcile to the reported total "
        f"({total}) within tolerance (+/-{tolerance_l}L) -- diff={diff}L. "
        f"Do not publish this report until this is resolved."
    )

    n_fail = int((summary.get("Status", pd.Series(dtype=str)) != "PASS").sum()) if "Status" in summary.columns else None

    return {
        "total_primary_l": total,
        "levels_l": levels,
        "levels_pct": {k: round(v / total * 100, 2) if total else 0.0 for k, v in levels.items()},
        "reconciliation_diff_l": diff,
        "months_not_reconciled": n_fail,
        "months_covered": int(len(summary)),
    }


def print_report(report: dict) -> None:
    print(f"Total Primary: Rs{report['total_primary_l']:,.2f}L "
          f"across {report['months_covered']} months\n")
    print(f"{'Level':<42}{'Rs L':>12}{'%':>10}")
    for label, value in report["levels_l"].items():
        pct = report["levels_pct"][label]
        print(f"{label:<42}{value:>12,.2f}{pct:>9.2f}%")
    print(f"\nReconciliation diff (levels sum vs. total): Rs{report['reconciliation_diff_l']:.4f}L")
    if report["months_not_reconciled"]:
        print(f"WARNING: {report['months_not_reconciled']} month(s) not PASS in the source summary.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", type=Path,
                     default=Path(__file__).resolve().parent.parent /
                     "historical_primary_chain_backfill_output/Monthly_Reconciliation_Summary.csv")
    ap.add_argument("--tolerance-l", type=float, default=DEFAULT_TOLERANCE_L)
    args = ap.parse_args()

    if not args.summary.exists():
        print(f"Not found: {args.summary}\nRun scripts/historical_primary_chain_backfill.py first.", file=sys.stderr)
        return 1

    summary = pd.read_csv(args.summary)
    report = build_report(summary, args.tolerance_l)
    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
