"""
Reconcile the owner's decisions on the PROVISIONAL_BUSINESS_MAPPED_PRIMARY
approval register (PowerBI/docs/HistoricalPrimaryBackfill/ -- register sent
to the business owner as ProvisionalMapping_OwnerApproval_Apr25_Jul26.xlsx,
sheet "Approval Summary") back to the frozen Rs9,455.20L bucket.

Rules enforced:
  - Every one of the 266 Distributor x Brand x Chain lines must carry an
    Owner_Decision of Approve, Reject, or Amend. A blank/missing decision is
    tracked as PENDING -- silence is never counted as approval.
  - Approve  -> counted at the line's original Value_L.
  - Amend    -> requires Owner_Correction to name the intended governed
    chain (and, optionally, a corrected Rs value); an Amend with no
    Owner_Correction is a data-entry error and is rejected by this script
    rather than silently defaulting to the original split.
  - Reject   -> counted as Rejected_L; these rupees fall back to
    UNALLOCATED_PRIMARY on the next governance rerun, they are not dropped.
  - Approved_L + Amended_L + Rejected_L + Pending_L must equal the frozen
    bucket total (Rs9,455.1997L in the underlying detail, Rs9,455.20L
    rounded) within tolerance -- this is the same reconciliation discipline
    as the backfill itself, applied to the approval process.

Usage:
    python scripts/provisional_mapping_disposition.py --register <returned xlsx/csv>
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

EXPECTED_BUCKET_TOTAL_L = 9455.1997
DEFAULT_TOLERANCE_L = 0.05
VALID_DECISIONS = {"Approve", "Reject", "Amend"}


def load_register(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name="Approval Summary")
    else:
        df = pd.read_csv(path)
    required = {"Distributor", "Brand", "Chain", "Value_L", "Owner_Decision", "Owner_Correction"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Register missing expected columns: {sorted(missing)}")
    return df


def build_disposition(df: pd.DataFrame, tolerance_l: float = DEFAULT_TOLERANCE_L) -> dict:
    df = df.copy()
    df["Owner_Decision"] = df["Owner_Decision"].astype(str).str.strip()
    df.loc[~df["Owner_Decision"].isin(VALID_DECISIONS), "Owner_Decision"] = "PENDING"

    amend_no_correction = df[(df["Owner_Decision"] == "Amend") &
                              (df["Owner_Correction"].isna() | (df["Owner_Correction"].astype(str).str.strip() == ""))]
    if len(amend_no_correction):
        raise ValueError(
            f"{len(amend_no_correction)} row(s) marked Amend with no Owner_Correction -- "
            "the intended governed chain must be provided by the owner, not inferred. "
            "Affected rows:\n" + amend_no_correction[["Distributor", "Brand", "Chain", "Value_L"]].to_string(index=False)
        )

    by_decision = df.groupby("Owner_Decision")["Value_L"].sum()
    approved_l = round(float(by_decision.get("Approve", 0.0)), 4)
    amended_l = round(float(by_decision.get("Amend", 0.0)), 4)
    rejected_l = round(float(by_decision.get("Reject", 0.0)), 4)
    pending_l = round(float(by_decision.get("PENDING", 0.0)), 4)
    total_l = round(approved_l + amended_l + rejected_l + pending_l, 4)

    diff = round(total_l - EXPECTED_BUCKET_TOTAL_L, 4)
    assert abs(diff) <= tolerance_l, (
        f"Disposition total (Rs{total_l}L) does not reconcile to the frozen provisional "
        f"bucket (Rs{EXPECTED_BUCKET_TOTAL_L}L) within tolerance (+/-{tolerance_l}L) -- "
        f"diff=Rs{diff}L. A line was likely added, removed, or double-counted in the "
        f"returned register -- do not report a disposition summary until this is Rs0."
    )

    return {
        "approved_l": approved_l,
        "amended_l": amended_l,
        "rejected_l": rejected_l,
        "pending_l": pending_l,
        "total_l": total_l,
        "n_lines": int(len(df)),
        "n_pending": int((df["Owner_Decision"] == "PENDING").sum()),
        "reconciliation_diff_l": diff,
    }


def print_disposition(d: dict) -> None:
    pct = lambda v: (v / d["total_l"] * 100) if d["total_l"] else 0.0
    print(f"Provisional bucket disposition -- {d['n_lines']} lines "
          f"({d['n_pending']} still PENDING)\n")
    print(f"  Approved:  Rs{d['approved_l']:>10,.2f}L  ({pct(d['approved_l']):.2f}%)")
    print(f"  Amended:   Rs{d['amended_l']:>10,.2f}L  ({pct(d['amended_l']):.2f}%)")
    print(f"  Rejected:  Rs{d['rejected_l']:>10,.2f}L  ({pct(d['rejected_l']):.2f}%)")
    print(f"  Pending:   Rs{d['pending_l']:>10,.2f}L  ({pct(d['pending_l']):.2f}%)")
    print(f"  ---------------------------------")
    print(f"  Total:     Rs{d['total_l']:>10,.2f}L  (vs frozen bucket Rs{EXPECTED_BUCKET_TOTAL_L}L, "
          f"diff Rs{d['reconciliation_diff_l']}L)")
    if d["n_pending"]:
        print(f"\n{d['n_pending']} line(s) still pending -- NOT counted as approved.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--register", type=Path, required=True,
                     help="Returned owner register (.xlsx with an 'Approval Summary' sheet, or .csv)")
    ap.add_argument("--tolerance-l", type=float, default=DEFAULT_TOLERANCE_L)
    args = ap.parse_args()

    df = load_register(args.register)
    disposition = build_disposition(df, args.tolerance_l)
    print_disposition(disposition)
    return 0


if __name__ == "__main__":
    sys.exit(main())
