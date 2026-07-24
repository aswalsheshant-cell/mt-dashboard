#!/usr/bin/env python3
"""FY27 Provisional CM2 — COGS on GMV/MRP, logistics on NSV.

APPROVED CALCULATION BASES (Finance clarification 2026-07-24, decision D10):

    COGS Amount       = GMV/MRP Sales x COGS Rate      <- NEVER NSV
    Logistics Amount  = NSV           x Logistics Rate <- NEVER GMV/MRP
    Total Cost        = COGS Amount + Logistics Amount
    Provisional CM2   = NSV - COGS Amount - Logistics Amount
    Provisional CM2 % = Provisional CM2 / NSV

COGS and logistics are independent components, computed separately then deducted
together. The two bases are resolved from different authoritative sources and are
never substituted for one another.

AUTHORITATIVE BASES
  NSV       dashboard/data.js -> detail_meta.fyx_primary.FY27.monthly (INR Lakh)
  GMV/MRP   PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_<Mon>_<YY>.csv
            column 'Total MRP sales' (INR), excluded brands removed, /1e5 -> Lakh

The FY-total field detail_meta.fyx_primary.FY27.mrp is deliberately NOT used as a
monthly base: it covers Apr+May only (Jun-26 was patched in as NSV-only by
scripts/patch_jun26.py), so deriving a month from it would be wrong.

STAGING ONLY. Does not modify dashboard/data.js, dashboard/index.html or
build_dashboard_data.py, and is not read by the production build.

Result is PROVISIONAL: the final CM2 expense definition is pending decisions
D1 (COGS in scope) and D9 (allocation rules). Never label the output "Final CM2".
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import subprocess
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_JS = ROOT / "dashboard" / "data.js"
ARTICLE_DIR = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
OUT_CSV = ROOT / "outputs" / "cm2" / "cm2_fy27_cogs_logistics.csv"
OUT_META = ROOT / "outputs" / "cm2" / "cm2_fy27_cogs_logistics.meta.json"

CALC_VERSION = "2.0.0"
DECISION_REF = "D10 (bases approved) / D11 (components separate)"

# Excluded brands must never enter any aggregation.
EXCLUDED_BRANDS = {"pure origin", "lumineve", "staze"}

# FY27 = Apr-26 .. Mar-27 (THE ONE FY RULE: Apr-Dec Y -> FY(Y+1)).
FY27_MONTHS = ["Apr-26", "May-26", "Jun-26", "Jul-26", "Aug-26", "Sep-26",
               "Oct-26", "Nov-26", "Dec-26", "Jan-27", "Feb-27", "Mar-27"]

# Supplied rate card, percent. Business screenshot 2026-07-24.
RATE_CARD: dict[str, tuple[Decimal, Decimal]] = {
    "Apr-26": (Decimal("14.05"), Decimal("2.97")),
    "May-26": (Decimal("13.67"), Decimal("2.83")),
    "Jun-26": (Decimal("14.56"), Decimal("4.09")),
    "Jul-26": (Decimal("13.37"), Decimal("4.20")),
    "Aug-26": (Decimal("13.60"), Decimal("4.14")),
    "Sep-26": (Decimal("13.64"), Decimal("4.51")),
    "Oct-26": (Decimal("15.22"), Decimal("4.58")),
    "Nov-26": (Decimal("15.50"), Decimal("4.42")),
    "Dec-26": (Decimal("15.72"), Decimal("4.24")),
    "Jan-27": (Decimal("15.11"), Decimal("4.42")),
    "Feb-27": (Decimal("14.50"), Decimal("3.90")),
    "Mar-27": (Decimal("14.32"), Decimal("3.79")),
}

HUNDRED = Decimal("100")
RUPEES_PER_LAKH = Decimal("100000")
MAX_RATE_PCT = Decimal("100")

# Status vocabulary (Phase 4).
CALCULATED = "CALCULATED"
NSV_MISSING = "NSV_MISSING"
GMV_MRP_MISSING = "GMV_MRP_MISSING"
COGS_RATE_MISSING = "COGS_RATE_MISSING"
LOGISTICS_RATE_MISSING = "LOGISTICS_RATE_MISSING"
NO_SALES_MONTH = "NO_SALES_MONTH"
INVALID_UNIT = "INVALID_UNIT"
INVALID_RATE = "INVALID_RATE"


class UnitValidationError(ValueError):
    """Raised when an input cannot be shown to be in the expected unit."""


def q2(d: Decimal) -> Decimal:
    """Round for presentation only. Internal maths keeps full precision."""
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def pct(rate_pct: Decimal) -> Decimal:
    """14.05 (percent) -> 0.1405 (decimal rate). Never multiply by 14.05."""
    return rate_pct / HUNDRED


def validate_rate(rate_pct: Decimal | None) -> bool:
    return rate_pct is not None and Decimal(0) <= rate_pct <= MAX_RATE_PCT


def _month_to_csv_name(month: str) -> str:
    mon, yy = month.split("-")
    return f"primary_article_{mon}_{yy}.csv"


def load_nsv_monthly() -> tuple[list[Decimal | None], dict]:
    """FY27 monthly NSV in INR Lakh, straight from the published data.js block."""
    raw = DATA_JS.read_text(encoding="utf-8")
    dash = json.loads(raw[raw.index("{"):].rstrip().rstrip(";"))
    fy27 = dash["detail_meta"]["fyx_primary"]["FY27"]

    unit = str(fy27.get("unit", "")).strip()
    if unit.upper() != "INR LAKH":
        raise UnitValidationError(
            f"FY27 NSV unit is {unit!r}, expected 'INR Lakh'. Refusing to mix units.")

    monthly = fy27["monthly"]
    if len(monthly) != 12:
        raise UnitValidationError(f"expected 12 monthly NSV buckets, got {len(monthly)}")

    vals = [Decimal(str(v)) for v in monthly]
    meta = {
        "field": "detail_meta.fyx_primary.FY27.monthly",
        "unit": "INR Lakh",
        "grain": "FY month (Apr..Mar)",
        "nature": "aggregated from article-level primary; Jun-26 patched from Primary_Summary KPI row",
        "fy_total": str(fy27["nsv"]),
        "months_covered": fy27.get("months_covered"),
    }
    return vals, meta


def load_gmv_mrp_monthly() -> tuple[dict[str, Decimal], dict]:
    """FY27 monthly GMV/MRP sales in INR Lakh from the article CSVs.

    Only months with a tracked article CSV can be resolved. A month with no CSV
    is absent from the returned mapping -- it is NOT derived from the FY total
    and NOT estimated from NSV.
    """
    import pandas as pd

    out: dict[str, Decimal] = {}
    per_month = {}
    for month in FY27_MONTHS:
        path = ARTICLE_DIR / _month_to_csv_name(month)
        if not path.exists():
            continue
        df = pd.read_csv(path, encoding="latin-1", low_memory=False)
        if "Total MRP sales" not in df.columns:
            raise UnitValidationError(f"{path.name} has no 'Total MRP sales' column")

        brand = df["brand"].astype(str).str.strip().str.lower()
        kept = df[~brand.isin(EXCLUDED_BRANDS)]
        rupees = Decimal(str(kept["Total MRP sales"].sum()))
        lakh = rupees / RUPEES_PER_LAKH

        # Unit sanity: the CSV column is in rupees, so a full month must be
        # orders of magnitude above 1 lakh. A value this small means the column
        # was already converted upstream and would silently under-state COGS.
        if rupees != 0 and abs(lakh) < Decimal("1"):
            raise UnitValidationError(
                f"{path.name}: 'Total MRP sales' sums to {rupees} which is under 1 lakh "
                f"after conversion -- unit is not rupees as assumed.")

        out[month] = lakh
        per_month[month] = {
            "source_file": rel(path),
            "field": "Total MRP sales",
            "source_unit": "INR",
            "converted_unit": "INR Lakh",
            "rows_total": int(len(df)),
            "rows_after_brand_exclusion": int(len(kept)),
        }

    meta = {
        "grain": "calendar month, article-level, excluded brands removed",
        "unit": "INR Lakh",
        "nature": "raw source column summed",
        "excluded_brands": sorted(EXCLUDED_BRANDS),
        "months_resolved": sorted(per_month),
        "per_month": per_month,
    }
    return out, meta


def classify(nsv: Decimal | None, gmv: Decimal | None,
             cogs_pct: Decimal | None, log_pct: Decimal | None) -> str:
    """Controlled missing-data status. Never guesses a base."""
    if not validate_rate(cogs_pct):
        return INVALID_RATE if cogs_pct is not None else COGS_RATE_MISSING
    if not validate_rate(log_pct):
        return INVALID_RATE if log_pct is not None else LOGISTICS_RATE_MISSING
    nsv_zero = nsv is not None and nsv == 0
    gmv_zero = gmv is not None and gmv == 0
    if (nsv is None or nsv_zero) and (gmv is None or gmv_zero):
        return NO_SALES_MONTH
    if nsv is None or nsv_zero:
        return NSV_MISSING
    if gmv is None:
        return GMV_MRP_MISSING
    return CALCULATED


def compute_month(nsv: Decimal | None, gmv: Decimal | None,
                  cogs_pct: Decimal | None, log_pct: Decimal | None):
    """Returns (status, cogs, logistics, total_cost, cm2, cm2_pct).

    COGS is computed ONLY from GMV/MRP. Logistics is computed ONLY from NSV.
    Values are None when the status forbids calculating them.
    """
    status = classify(nsv, gmv, cogs_pct, log_pct)
    if status != CALCULATED:
        # Logistics may still be computable as a memo when NSV exists, but no
        # CM2 is produced -- CM2 requires both components.
        logistics = (nsv * pct(log_pct)
                     if status == GMV_MRP_MISSING and nsv is not None
                     and validate_rate(log_pct) else None)
        return status, None, logistics, None, None, None

    cogs = gmv * pct(cogs_pct)          # GMV/MRP base
    logistics = nsv * pct(log_pct)      # NSV base
    total_cost = cogs + logistics
    cm2 = nsv - total_cost
    cm2_pct = cm2 / nsv * HUNDRED
    return status, cogs, logistics, total_cost, cm2, cm2_pct


def rel(p: pathlib.Path) -> str:
    """Repo-relative path for display, falling back to the absolute path when
    the caller writes outside the repository (e.g. a temp dir in tests)."""
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def source_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def build_rows():
    nsv_monthly, nsv_meta = load_nsv_monthly()
    gmv_monthly, gmv_meta = load_gmv_mrp_monthly()

    rows, totals = [], {k: Decimal(0) for k in ("gmv", "nsv", "cogs", "log", "cost", "cm2")}
    n_calc = 0

    for i, month in enumerate(FY27_MONTHS):
        nsv = nsv_monthly[i]
        gmv = gmv_monthly.get(month)
        cogs_pct, log_pct = RATE_CARD.get(month, (None, None))
        status, cogs, log, cost, cm2, cm2_pct = compute_month(nsv, gmv, cogs_pct, log_pct)

        if status == CALCULATED:
            n_calc += 1
            totals["gmv"] += gmv
            totals["nsv"] += nsv
            totals["cogs"] += cogs
            totals["log"] += log
            totals["cost"] += cost
            totals["cm2"] += cm2

        rows.append({
            "Month": month,
            "Status": status,
            "GMV_MRP_Sales_L": q2(gmv) if gmv is not None else "",
            "NSV_L": q2(nsv) if nsv is not None else "",
            "COGS_Pct": cogs_pct if cogs_pct is not None else "",
            "Logistics_Pct": log_pct if log_pct is not None else "",
            "COGS_Basis": "GMV_MRP_SALES",
            "Logistics_Basis": "NSV",
            "COGS_L": q2(cogs) if cogs is not None else "",
            "Logistics_L": q2(log) if log is not None else "",
            "Total_Cost_L": q2(cost) if cost is not None else "",
            "Provisional_CM2_L": q2(cm2) if cm2 is not None else "",
            "Provisional_CM2_Pct": q2(cm2_pct) if cm2_pct is not None else "",
        })

    # Q1/FYTD subtotal over CALCULATED months only. CM2 % is computed from the
    # summed values -- never an average of the monthly percentages.
    subtotal = {
        "Month": f"FY27 CALCULATED TOTAL ({n_calc} months)",
        "Status": "SUBTOTAL_CALCULATED_ONLY",
        "GMV_MRP_Sales_L": q2(totals["gmv"]),
        "NSV_L": q2(totals["nsv"]),
        "COGS_Pct": q2(totals["cogs"] / totals["gmv"] * HUNDRED) if totals["gmv"] else "",
        "Logistics_Pct": q2(totals["log"] / totals["nsv"] * HUNDRED) if totals["nsv"] else "",
        "COGS_Basis": "GMV_MRP_SALES",
        "Logistics_Basis": "NSV",
        "COGS_L": q2(totals["cogs"]),
        "Logistics_L": q2(totals["log"]),
        "Total_Cost_L": q2(totals["cost"]),
        "Provisional_CM2_L": q2(totals["cm2"]),
        "Provisional_CM2_Pct": q2(totals["cm2"] / totals["nsv"] * HUNDRED) if totals["nsv"] else "",
    }

    assert totals["cogs"] + totals["log"] == totals["cost"], "component sum drift"
    assert totals["nsv"] - totals["cost"] == totals["cm2"], "CM2 identity drift"

    rows.append(subtotal)
    return rows, totals, n_calc, nsv_meta, gmv_meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_CSV))
    ap.add_argument("--meta", default=str(OUT_META))
    args = ap.parse_args()

    rows, totals, n_calc, nsv_meta, gmv_meta = build_rows()

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    meta = {
        "calculation_status": "PROVISIONAL",
        "calculation_version": CALC_VERSION,
        "label": "Provisional CM2 after COGS and logistics",
        "scenario": "CM2 scenario: COGS on GMV/MRP, logistics on NSV",
        "cogs_basis": "GMV_MRP_SALES",
        "logistics_basis": "NSV",
        "cogs_and_logistics_separate": True,
        "included_expense_layers": ["COGS", "LOGISTICS"],
        "excluded_expense_layers": [
            "TRADE EXPENSE (indirect claims, provisional, D3/D4)",
            "FIELD FORCE COST (CTC, reimbursement, incentive, D5/D6/D7)",
            "VISIBILITY AND RENTAL (no real source supplied)",
            "SHARED OR CORPORATE",
            "TAX (GST held separately, never deducted from net-of-tax NSV)",
        ],
        "pending_decisions": ["D1", "D3", "D4", "D5", "D6", "D7", "D8", "D9"],
        "approved_decisions": ["D10", "D11"],
        "decision_reference": DECISION_REF,
        "sources": {"nsv": nsv_meta, "gmv_mrp": gmv_meta,
                    "rate_card": {"origin": "business screenshot 2026-07-24",
                                  "unit": "percent", "grain": "FY month",
                                  "nature": "supplied, not derived"}},
        "source_files": [rel(DATA_JS)]
                        + [m["source_file"] for m in gmv_meta["per_month"].values()],
        "source_commit": source_commit(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "months_calculated": n_calc,
        "totals_lakh": {k: str(q2(v)) for k, v in totals.items()},
        "production_files_modified": [],
        "note": ("PROVISIONAL. Final CM2 expense definition pending D1 and D9. "
                 "Do not label this Final CM2 and do not publish into production "
                 "visuals until those decisions are approved."),
    }
    pathlib.Path(args.meta).write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    w0 = max(len(r["Month"]) for r in rows)
    print("Provisional CM2 — COGS on GMV/MRP, logistics on NSV  (PROVISIONAL)\n")
    print(f"{'Month':<{w0}} {'GMV/MRP_L':>11} {'NSV_L':>9} {'COGS%':>6} {'LOG%':>5} "
          f"{'COGS_L':>10} {'LOG_L':>8} {'COST_L':>10} {'CM2_L':>10} {'CM2%':>7}  Status")
    print("-" * (w0 + 92))
    for r in rows:
        if r["Status"] == "SUBTOTAL_CALCULATED_ONLY":
            print("-" * (w0 + 92))
        dash = lambda v: (str(v) if v != "" else "--")
        print(f"{r['Month']:<{w0}} {dash(r['GMV_MRP_Sales_L']):>11} {dash(r['NSV_L']):>9} "
              f"{dash(r['COGS_Pct']):>6} {dash(r['Logistics_Pct']):>5} "
              f"{dash(r['COGS_L']):>10} {dash(r['Logistics_L']):>8} {dash(r['Total_Cost_L']):>10} "
              f"{dash(r['Provisional_CM2_L']):>10} {dash(r['Provisional_CM2_Pct']):>7}  {r['Status']}")
    print(f"\nwrote {rel(out)}")
    print(f"wrote {rel(pathlib.Path(args.meta))}")


if __name__ == "__main__":
    main()
