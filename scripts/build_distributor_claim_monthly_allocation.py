#!/usr/bin/env python3
"""Allocate the Q1 FY27 distributor claims to Apr/May/Jun'26 (Finance-approved basis).

Decision (Finance, DA, 2026-10-01; Finance pack A1/A2):
  A1  Distributor claims and MT Direct DN are ADDITIVE (separate costs).
  A2  Include distributor claims in monthly AND quarterly CM2.
      Quarterly: the Q1 total Rs 449.77 L is the ACTUAL / APPROVED figure, at
      the Quarter x Chain x Expense Head grain (PL_Distributor_Claim_Input_Q1_FY27.csv,
      unchanged by this script).
      Monthly: the source carries no claim month, so each Q1 Chain x Expense
      Head claim is allocated by that chain's Apr/May/Jun share of Q1
      distributor secondary (basis 3 in the pack). Rows are ALLOCATED /
      PROVISIONAL, never presented as a Finance posting.

Rules enforced here:
  * Apr + May + Jun = the exact Q1 claim, per Chain x Expense Head line, to
    0.0001 L (the rounding residual goes to the line's largest month).
  * No equal /3 split. A chain with no secondary in Q1 is NOT spread: its claim
    stays as one UNALLOCATED_TIMING row for Q1, so the monthly file still sums
    to Rs 449.77 L and the gap is visible.
  * Chain names are matched through the governed canon_chain() on main, then a
    small, explicit PROPOSED_DRIVER_ALIASES table (secondary spellings that
    canon_chain does not resolve). Those aliases are used for this driver only
    and are listed in the PR for approval; they are not added to CHAIN_ALIASES.

Usage:
    python scripts/build_distributor_claim_monthly_allocation.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_dashboard_data import canon_chain  # noqa: E402

SEED = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Distributor_Claim_Input_Q1_FY27.csv"
SECONDARY = ROOT / "PowerBI" / "RawDataFolders" / "SecondarySales_Monthly" / "secondary_sales_tot_hierarchy_Apr_Aug_2026.csv"
OUT = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Distributor_Claim_Monthly_Allocated_Q1_FY27.csv"

Q1_TOTAL_L = 449.77
MONTHS = (("Apr-2026", "Apr'26"), ("May-2026", "May'26"), ("Jun-2026", "Jun'26"))
APPROVAL = "Finance (DA), 2026-10-01, Finance pack A1 = Additive, A2 = basis 3"
BASIS = "Chain x Month distributor secondary share of Q1"

# Secondary spellings canon_chain() does not resolve, with the evidence for each.
# PROPOSED: used for this driver only, approved with the PR, not added to CHAIN_ALIASES.
PROPOSED_DRIVER_ALIASES = {
    "MORE REATIL": ("More Retail", "spelling of MORE RETAIL"),
    "MORE RETAIL LIMITED": ("More Retail", "legal name of More Retail"),
    "MRL": ("More Retail", "More Retail Limited initials"),
    "ABRL -MORE": ("More Retail", "label names More"),
    "ABRL": ("More Retail", "Aditya Birla Retail Ltd, operator of More"),
    "FRANK ROSE": ("Frankross", "spelling of FRANK ROSS"),
    "RATNADEEP SUPERMARKET": ("Ratnadeep", "full store name"),
}
# Not aliased on purpose: bare "VISHAL" (Rs 0.05 L, May). CHAIN_ALIASES records that a
# "Vishal" distributor is unrelated to Vishal Mega Mart, so the short name is ambiguous.

OUT_FIELDS = ["Month", "FY", "Quarter", "Chain", "Expense Head", "Expense Type",
              "Expense Amount (INR Lakh)", "Status", "Q1 Claim (INR Lakh)", "Driver Share",
              "Basis", "Driver Source Names", "Approval", "Source"]


def driver_key(name: str) -> str:
    """Canonical chain key for matching claim chains to secondary chains."""
    if name in PROPOSED_DRIVER_ALIASES:
        name = PROPOSED_DRIVER_ALIASES[name][0]
    return str(canon_chain(name)).strip().lower()


def load_driver(path: Path = SECONDARY) -> tuple[dict, dict]:
    """{chain_key: {month: Rs L}} and {chain_key: set(source names)} for Apr-Jun'26."""
    val, names = defaultdict(lambda: defaultdict(float)), defaultdict(set)
    wanted = {m for m, _ in MONTHS}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["Month_Label"] not in wanted:
                continue
            k = driver_key(r["Chain"].strip())
            val[k][r["Month_Label"]] += float(r["NSV_Lakh"] or 0)
            names[k].add(r["Chain"].strip())
    return val, names


def allocate(seed_rows: list[dict], driver: dict, names: dict) -> list[dict]:
    out = []
    for r in seed_rows:
        q1 = round(float(r["Expense Amount (INR Lakh)"]), 4)
        k = driver_key(r["Chain"])
        months = driver.get(k, {})
        base = {"FY": r["FY"], "Quarter": r["Quarter"], "Chain": r["Chain"],
                "Expense Head": r["Expense Head"], "Expense Type": r["Expense Type"],
                "Q1 Claim (INR Lakh)": f"{q1:.4f}", "Approval": APPROVAL, "Source": r["Source"]}
        total = sum(months.get(m, 0.0) for m, _ in MONTHS)
        if total <= 0:
            out.append({**base, "Month": "Q1 (no month)", "Expense Amount (INR Lakh)": f"{q1:.4f}",
                        "Status": "UNALLOCATED_TIMING", "Driver Share": "",
                        "Basis": "no distributor secondary for this chain in Apr-Jun'26; not spread",
                        "Driver Source Names": ""})
            continue
        shares = [months.get(m, 0.0) / total for m, _ in MONTHS]
        amts = [round(q1 * s, 4) for s in shares]
        amts[max(range(3), key=lambda i: shares[i])] += round(q1 - sum(amts), 4)   # exact to the line
        for (m, label), s, a in zip(MONTHS, shares, amts):
            out.append({**base, "Month": label, "Expense Amount (INR Lakh)": f"{a:.4f}",
                        "Status": "ALLOCATED_PROVISIONAL", "Driver Share": f"{s:.6f}", "Basis": BASIS,
                        "Driver Source Names": "; ".join(sorted(names[k]))})
    return out


def build(seed: Path = SEED, secondary: Path = SECONDARY) -> list[dict]:
    with seed.open(newline="", encoding="utf-8-sig") as fh:
        seed_rows = list(csv.DictReader(fh))
    driver, names = load_driver(secondary)
    rows = allocate(seed_rows, driver, names)
    # control: every line reconciles, and the file reconciles to the Q1 total
    per_line = defaultdict(float)
    for r in rows:
        per_line[(r["Chain"], r["Expense Head"])] += float(r["Expense Amount (INR Lakh)"])
    for s in seed_rows:
        got = per_line[(s["Chain"], s["Expense Head"])]
        assert abs(got - float(s["Expense Amount (INR Lakh)"])) < 0.00015, (s["Chain"], s["Expense Head"], got)
    tot = sum(float(r["Expense Amount (INR Lakh)"]) for r in rows)
    assert abs(tot - Q1_TOTAL_L) < 0.01, f"monthly file sums to {tot:.4f} L, not {Q1_TOTAL_L} L"
    return rows


def render(rows: list[dict]) -> str:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=OUT_FIELDS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed file is out of date")
    a = ap.parse_args(argv)
    text = render(build())
    if a.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("allocation file up to date" if ok else f"{OUT.name} is out of date: rerun this script")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
