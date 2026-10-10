"""Source-side expected values for the Power BI full report (read-only).

This computes what the Power BI measures SHOULD show if the model reads the raw
folders correctly. It does not run DAX and it does not prove the Desktop model
is right. A person compares these numbers with live DAX in the same period,
filters and units, then records the result in the evidence file.

Reuses audit_csv() from audit_dashboard_units.py (same reader, same Reliance
Brand Counter rule: counter rows are split out for OFFTAKE only, never Primary).

Usage:
  python scripts/reconcile_powerbi_full.py
  python scripts/reconcile_powerbi_full.py --out PowerBI/reconciliation_expected.json
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_dashboard_units import audit_csv  # noqa: E402
from powerbi_full_sources import fy_tag, parse_period  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "PowerBI" / "RawDataFolders"
LAKH = Decimal(100000)

# Protected reference values from CLAUDE.md / config/baselines.json (Rs lakh).
# Shown next to the source result for context only. Not used to force a match.
BASELINES_LAKH = {
    "FY26 Primary (MT basis)": "30684.99",
    "FY26 Primary (all channel)": "32900.36",
    "FY26 Offtake": "31119.88",
    "FY25 Distributor Secondary": "23332.36",
}


def by_fy(month_totals):
    """month label -> total  =>  {'months': {YYYY-MM: total}, 'fy': {FYnn: total}}"""
    months, fy = defaultdict(Decimal), defaultdict(Decimal)
    unparsed = []
    for label, value in month_totals.items():
        p = parse_period(label)
        if not p:
            unparsed.append(label)
            continue
        months[p] += Decimal(value)
        fy[fy_tag(int(p[:4]), int(p[5:]))] += Decimal(value)
    return months, fy, unparsed


def lakh(rupees):
    return str((rupees / LAKH).quantize(Decimal("0.01")))


def family(folder, pattern, amount_col, mrp_col, source_is_lakh, offtake=False):
    files = sorted((RAW / folder).glob(pattern))
    gross, governed = defaultdict(Decimal), defaultdict(Decimal)
    rows, hashes = 0, {}
    for f in files:
        a = audit_csv(f, amount_col, mrp_col, sample_stride=1000, exclude_reliance_bc=offtake)
        rows += a["rows"]
        hashes[f.name] = a["sha256"]
        for m, v in a["month_totals_raw"].items():
            gross[m] += Decimal(v)
        for m, v in a["month_totals_governed_raw"].items():
            governed[m] += Decimal(v)
    scale = LAKH if source_is_lakh else Decimal(1)
    out = {"folder": "RawDataFolders/" + folder, "files": len(files), "rows": rows,
           "sha256": hashes, "source_unit": "lakh" if source_is_lakh else "rupees",
           "model_unit": "rupees"}
    for key, totals in (("gross", gross), ("governed_ex_reliance_brand_counter", governed)):
        if key != "gross" and not offtake:
            continue
        m, fy, bad = by_fy({k: v * scale for k, v in totals.items()})
        out[key] = {
            "monthly_rupees": {k: str(v) for k, v in sorted(m.items())},
            "monthly_lakh": {k: lakh(v) for k, v in sorted(m.items())},
            "fy_lakh": {k: lakh(v) for k, v in sorted(fy.items())},
            "unparsed_month_labels": bad,
        }
    return out


def primary_article_by_channel():
    """FY (derived from Month, never the source FY text) x Channel, Rs lakh. Channel case is folded."""
    tot = defaultdict(Decimal)
    for f in sorted((RAW / "Primary_Article_Monthly").glob("primary_article_*.csv")):
        with open(f, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                p = parse_period(r["Month"])
                if not p:
                    continue
                tot[(fy_tag(int(p[:4]), int(p[5:])), (r["Channel"] or "<blank>").strip().upper())] += Decimal(r["Inv. Net value(LOC)"] or 0)
    out = defaultdict(dict)
    for (fy, ch), v in sorted(tot.items()):
        out[fy][ch] = lakh(v)
    return {"fy_channel_lakh": out,
            "note": "MT is the model's MT basis. 16_Fact_PrimaryArticle.pq does not filter Channel, so an unfiltered Power BI total includes EB2B and SIS. The source FY text is inconsistent (FY'25-26, FY'26-27, FY27), so FY must come from Month."}


def secondary_chain():
    files = sorted((RAW / "SecondarySales_Monthly").glob("secondary_sales_chain_*.csv"))
    tot = defaultdict(Decimal)
    for f in files:
        with open(f, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                tot[r["Source_Month"]] += Decimal(r["NSV_Lakh"] or 0)
    fy = defaultdict(Decimal)
    for m, v in tot.items():
        fy[fy_tag(int(m[:4]), int(m[5:]))] += v
    return {"folder": "RawDataFolders/SecondarySales_Monthly", "files": [f.name for f in files],
            "source_unit": "lakh", "monthly_lakh": {k: str(v) for k, v in sorted(tot.items())},
            "fy_lakh": {k: str(v) for k, v in sorted(fy.items())},
            "note": "Chain files only. FY25 distributor secondary is not in these folders (see docs/DATA_AVAILABILITY_MATRIX.md)."}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "PowerBI" / "reconciliation_expected.json"))
    args = ap.parse_args()

    offtake = family("Offtake_Monthly", "offtake_store_article_*.csv", "NSV", "MRP Sales Value", True, offtake=True)
    primary_article = family("Primary_Article_Monthly", "primary_article_*.csv", "Inv. Net value(LOC)", "Total MRP sales", False)

    doc = {
        "generated": date.today().isoformat(),
        "basis": "SOURCE-SIDE EXPECTED VALUES. Not Desktop-verified. Compare with live DAX in the same period, filters and units.",
        "reference_baselines_lakh": BASELINES_LAKH,
        "offtake": offtake,
        "primary_article": primary_article,
        "primary_article_by_channel": primary_article_by_channel(),
        "secondary_chain": secondary_chain(),
        "primary_shipto": {
            "status": "NOT_RECONCILED",
            "reason": "Three overlapping snapshots in Primary_ShipTo_Monthly (FY24-25, FY24-26 composite, FY25-26 to May26). Summing them double counts. Needs a dedupe rule before an expected value is stated.",
        },
        "coverage_notes": [],
    }
    # Say plainly what these folders cannot prove.
    off_months = set(offtake["gross"]["monthly_lakh"])
    if not any(m < "2026-04" for m in off_months):
        doc["coverage_notes"].append(
            "Offtake_Monthly holds Apr-26 onward only. The FY26 Offtake baseline (Rs 31,119.88 L) lives in dashboard/data.js, so the Power BI model cannot reproduce it from this folder.")
    doc["coverage_notes"].append(
        "Primary_Weekly has no data files (template only), so Fact Primary Sales has no source here. Primary comparisons use the Article feed.")

    Path(args.out).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    for name in ("offtake", "primary_article"):
        print(name, "FY lakh (gross):", doc[name]["gross"]["fy_lakh"])
    print("offtake governed (ex RBC):", doc["offtake"]["governed_ex_reliance_brand_counter"]["fy_lakh"])
    print("primary article FY x channel (lakh):", dict(doc["primary_article_by_channel"]["fy_channel_lakh"]))
    print("secondary chain:", doc["secondary_chain"]["fy_lakh"])
    print("Wrote", Path(args.out))


if __name__ == "__main__":
    main()
