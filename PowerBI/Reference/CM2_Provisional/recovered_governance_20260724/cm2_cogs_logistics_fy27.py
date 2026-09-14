#!/usr/bin/env python3
"""FY27 CM2 from supplied COGS % and Logistics cost % rates.

Deterministic, exact-decimal calculation. Reads the FY27 article-level primary
NSV straight out of dashboard/data.js (detail_meta.fyx_primary.FY27.monthly) and
applies the monthly rate card supplied by the business.

STAGING ONLY -- writes to outputs/cm2/. Does not modify dashboard/data.js and is
not read by build_dashboard_data.py.

Basis assumption: rates are % of NSV (net sales value). This matches the CM2
definition in config/cm2_formula.csv where the base component is "NSV net of tax".
Run with --basis mrp to see the same rate card applied to MRP sales value instead.
"""
import argparse, csv, json, pathlib
from decimal import Decimal, ROUND_HALF_UP

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA_JS = ROOT / "dashboard" / "data.js"
OUT_DIR = ROOT / "outputs" / "cm2"

FY27_MONTHS = ["Apr-26", "May-26", "Jun-26", "Jul-26", "Aug-26", "Sep-26",
               "Oct-26", "Nov-26", "Dec-26", "Jan-27", "Feb-27", "Mar-27"]

# Supplied rate card, indexed by FY month position (Apr..Mar). Percent values.
RATE_CARD = {
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


def q2(d):
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def load_fy27(basis):
    raw = DATA_JS.read_text(encoding="utf-8")
    dash = json.loads(raw[raw.index("{"):].rstrip().rstrip(";"))
    fy27 = dash["detail_meta"]["fyx_primary"]["FY27"]
    monthly = fy27["monthly"]
    if len(monthly) != 12:
        raise SystemExit(f"expected 12 monthly buckets, got {len(monthly)}")
    if basis == "mrp":
        total = Decimal(str(fy27["mrp"]))
        nsv_total = Decimal(str(fy27["nsv"]))
        if nsv_total == 0:
            raise SystemExit("cannot scale to MRP basis: FY27 nsv is zero")
        # data.js carries MRP only as a FY total, so scale each month by its NSV share.
        scale = total / nsv_total
        vals = [Decimal(str(v)) * scale for v in monthly]
    else:
        vals = [Decimal(str(v)) for v in monthly]
    return fy27, vals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", choices=["nsv", "mrp"], default="nsv",
                    help="what the supplied percentages are a percentage OF")
    ap.add_argument("--out", default=str(OUT_DIR / "cm2_fy27_cogs_logistics.csv"))
    args = ap.parse_args()

    fy27, base_vals = load_fy27(args.basis)
    nsv_vals = [Decimal(str(v)) for v in fy27["monthly"]]

    rows, tot = [], {k: Decimal(0) for k in ("nsv", "base", "cogs", "log", "cost", "cm2")}
    for i, month in enumerate(FY27_MONTHS):
        nsv, base = nsv_vals[i], base_vals[i]
        cogs_pct, log_pct = RATE_CARD[month]
        has_data = nsv != 0

        cogs = base * cogs_pct / HUNDRED if has_data else Decimal(0)
        log = base * log_pct / HUNDRED if has_data else Decimal(0)
        cost = cogs + log
        cm2 = nsv - cost

        for k, v in (("nsv", nsv), ("base", base), ("cogs", cogs),
                     ("log", log), ("cost", cost), ("cm2", cm2 if has_data else Decimal(0))):
            tot[k] += v

        rows.append({
            "Month": month,
            "Data_Status": "ACTUAL" if has_data else "NO_DATA_MONTH_NOT_YET_LOADED",
            "NSV_L": q2(nsv),
            "COGS_Pct": cogs_pct,
            "Logistics_Pct": log_pct,
            "COGS_L": q2(cogs),
            "Logistics_L": q2(log),
            "Total_COGS_Logistics_L": q2(cost),
            "CM2_L": q2(cm2) if has_data else Decimal("0.00"),
            "CM2_Pct_of_NSV": q2(cm2 / nsv * HUNDRED) if has_data else "",
        })

    n_act = sum(1 for r in rows if r["Data_Status"] == "ACTUAL")
    rows.append({
        "Month": f"FY27 TOTAL ({n_act} months with data)",
        "Data_Status": "SUBTOTAL_ACTUAL_ONLY",
        "NSV_L": q2(tot["nsv"]),
        "COGS_Pct": q2(tot["cogs"] / tot["base"] * HUNDRED) if tot["base"] else "",
        "Logistics_Pct": q2(tot["log"] / tot["base"] * HUNDRED) if tot["base"] else "",
        "COGS_L": q2(tot["cogs"]),
        "Logistics_L": q2(tot["log"]),
        "Total_COGS_Logistics_L": q2(tot["cost"]),
        "CM2_L": q2(tot["cm2"]),
        "CM2_Pct_of_NSV": q2(tot["cm2"] / tot["nsv"] * HUNDRED) if tot["nsv"] else "",
    })

    # Exactness assertion: components must reconstruct the total with no drift.
    assert tot["cogs"] + tot["log"] == tot["cost"], "component sum drift"
    assert tot["nsv"] - tot["cost"] == tot["cm2"], "CM2 identity drift"

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    width = max(len(r["Month"]) for r in rows)
    print(f"Basis: percentages applied to {args.basis.upper()}")
    print(f"{'Month':<{width}} {'NSV_L':>10} {'COGS%':>7} {'LOG%':>6} "
          f"{'COGS_L':>10} {'LOG_L':>9} {'COST_L':>10} {'CM2_L':>11} {'CM2%':>7}")
    print("-" * (width + 75))
    for r in rows:
        if r["Data_Status"] == "NO_DATA_MONTH_NOT_YET_LOADED":
            print(f"{r['Month']:<{width}} {'--':>10} {r['COGS_Pct']:>6}% {r['Logistics_Pct']:>5}% "
                  f"{'--':>10} {'--':>9} {'--':>10} {'--':>11} {'--':>7}   (no NSV yet)")
            continue
        if r["Data_Status"] == "SUBTOTAL_ACTUAL_ONLY":
            print("-" * (width + 75))
        print(f"{r['Month']:<{width}} {r['NSV_L']:>10} {r['COGS_Pct']:>6}% {r['Logistics_Pct']:>5}% "
              f"{r['COGS_L']:>10} {r['Logistics_L']:>9} {r['Total_COGS_Logistics_L']:>10} "
              f"{r['CM2_L']:>11} {r['CM2_Pct_of_NSV']:>6}%")
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
