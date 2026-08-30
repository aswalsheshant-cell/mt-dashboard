"""
Export Power BI-ready CSVs from dashboard/data.js.

Reads the DASH JSON blocks and writes flat, grain-level CSVs that the
Power Query tables (44_Fact_SecondarySales.pq, 45_Fact_ClaimMaster.pq, etc.)
consume directly from the RawDataFolders watch folders.

Usage:
    python scripts/export_pbi_csvs.py [--datajs dashboard/data.js]
                                      [--out    PowerBI/RawDataFolders]
                                      [--blocks all|secondary|claims|primary|offtake]
                                      [--dry-run]

Output files:
    SecondarySales_Monthly/secondary_sales_Q1_FY27.csv
    ClaimMaster_Quarterly/claim_master_AprJun_2026.csv
    ClaimMaster_Quarterly/claim_brand_AprJun_2026.csv
    ClaimMaster_Quarterly/claim_distributor_AprJun_2026.csv
"""

from __future__ import annotations
import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# DASH block extractor (works without executing JS)
# ---------------------------------------------------------------------------

def extract_block(content: str, key: str) -> dict | list | None:
    """Find `"<key>": <value>` at any depth and return parsed JSON."""
    pattern = rf'"{re.escape(key)}":\s*'
    m = re.search(pattern, content)
    if not m:
        return None
    val_start = m.end()
    ch = content[val_start]
    if ch not in ('{', '['):
        return None
    opener, closer = ('{', '}') if ch == '{' else ('[', ']')
    depth = 0
    i = val_start
    while i < len(content):
        if content[i] == opener:
            depth += 1
        elif content[i] == closer:
            depth -= 1
            if depth == 0:
                return json.loads(content[val_start:i + 1])
        i += 1
    return None


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict], dry_run: bool = False) -> int:
    if not rows:
        print(f"  SKIP (0 rows): {path.name}")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        print(f"  DRY-RUN — would write {len(rows)} rows → {path}")
        return len(rows)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  ✓  {len(rows):5d} rows → {path.relative_to(path.parents[3])}")
    return len(rows)


# ---------------------------------------------------------------------------
# Secondary Sales export
# ---------------------------------------------------------------------------

MONTH_LABEL = {"2026-04": "Apr-2026", "2026-05": "May-2026", "2026-06": "Jun-2026"}


def export_secondary_sales(ss: dict, out_dir: Path, dry_run: bool) -> int:
    """Flatten D.secondary_sales → grain: Distributor × Month."""
    folder = out_dir / "SecondarySales_Monthly"
    rows: list[dict] = []

    months = ss.get("months", ["2026-04", "2026-05", "2026-06"])
    month_labels = ss.get("month_labels", [MONTH_LABEL.get(m, m) for m in months])

    for dist in ss.get("by_distributor", []):
        name = dist["name"]
        for m, lbl in zip(months, month_labels):
            key = m.replace("-", "_")  # 2026_04
            month_key = f"{m[5:7]}_lakh"  # apr_lakh / may_lakh / jun_lakh
            # Map YYYY-MM to apr/may/jun
            mm = int(m[5:7])
            short = {4: "apr", 5: "may", 6: "jun"}.get(mm, m[5:7])
            nsv = dist.get(f"{short}_lakh", 0.0)
            rows.append({
                "Source_Month": m,
                "Month_Label": lbl,
                "FY_Year": "FY27",
                "Distributor": name,
                "NSV_Lakh": nsv,
                "Data_Source": "Secondary Sales Repository",
                "Notes": ss.get("metadata", {}).get("note", ""),
            })

    # By chain
    chain_rows: list[dict] = []
    for ch in ss.get("by_chain", []):
        if not ch["name"] or ch["name"] == "Unknown":
            continue
        for mm, short, lbl in zip(months, ["apr", "may", "jun"], month_labels):
            chain_rows.append({
                "Source_Month": mm,
                "Month_Label": lbl,
                "FY_Year": "FY27",
                "Chain": ch["name"],
                "NSV_Lakh": ch.get(f"{short}_lakh", 0.0),
            })

    # By brand
    brand_rows: list[dict] = []
    for br in ss.get("by_brand", []):
        if not br["name"] or br["name"] == "Unknown/Unmapped":
            continue
        for mm, short, lbl in zip(months, ["apr", "may", "jun"], month_labels):
            brand_rows.append({
                "Source_Month": mm,
                "Month_Label": lbl,
                "FY_Year": "FY27",
                "Brand": br["name"],
                "NSV_Lakh": br.get(f"{short}_lakh", 0.0),
            })

    total = 0
    total += write_csv(folder / "secondary_sales_distributor_Q1_FY27.csv", rows, dry_run)
    total += write_csv(folder / "secondary_sales_chain_Q1_FY27.csv", chain_rows, dry_run)
    total += write_csv(folder / "secondary_sales_brand_Q1_FY27.csv", brand_rows, dry_run)
    return total


# ---------------------------------------------------------------------------
# Claims export
# ---------------------------------------------------------------------------

def export_claims(cl: dict, out_dir: Path, dry_run: bool) -> int:
    folder = out_dir / "ClaimMaster_Quarterly"
    rows: list[dict] = []

    for chain, cv in cl.get("by_chain", {}).items():
        by_cat = cv.get("by_category", {})
        rows.append({
            "Period": "Apr-Jun 2026",
            "FY_Year": "FY27",
            "Quarter": "Q1",
            "Chain": chain,
            "Source_Chain": cv.get("source_chain", chain),
            "Chain_Promo_Lakh": by_cat.get("Chain Promo (On Invoice)", 0.0),
            "Rate_Diff_Lakh": by_cat.get("Extra Margin / Rate Difference", 0.0),
            "Freight_Lakh": by_cat.get("Freight / Transportation", 0.0),
            "Incentive_Lakh": by_cat.get("Incentive", 0.0),
            "Off_Invoice_Lakh": by_cat.get("Off Invoice / Debit Note Promo", 0.0),
            "Visibility_Lakh": by_cat.get("Visibility", 0.0),
            "Total_Claim_Lakh": cv.get("total_claim_lakh", 0.0),
        })

    brand_rows: list[dict] = []
    for brand, bv in cl.get("by_brand", {}).items():
        brand_rows.append({
            "Period": "Apr-Jun 2026",
            "FY_Year": "FY27",
            "Quarter": "Q1",
            "Brand": brand,
            "Apr_Lakh": bv.get("apr_lakh", 0.0),
            "May_Lakh": bv.get("may_lakh", 0.0),
            "Jun_Lakh": bv.get("jun_lakh", 0.0),
            "Total_Lakh": bv.get("total_lakh", 0.0),
        })

    dist_rows: list[dict] = []
    for dist, dv in cl.get("by_distributor", {}).items():
        dist_rows.append({
            "Period": "Apr-Jun 2026",
            "FY_Year": "FY27",
            "Quarter": "Q1",
            "Distributor": dist,
            "Source_Name": dv.get("source_name", dist),
            "Apr_Lakh": dv.get("apr_lakh", 0.0),
            "May_Lakh": dv.get("may_lakh", 0.0),
            "Jun_Lakh": dv.get("jun_lakh", 0.0),
            "Total_Claim_Lakh": dv.get("total_claim_lakh", 0.0),
        })

    total = 0
    total += write_csv(folder / "claim_master_chain_AprJun_2026.csv", rows, dry_run)
    total += write_csv(folder / "claim_master_brand_AprJun_2026.csv", brand_rows, dry_run)
    total += write_csv(folder / "claim_master_distributor_AprJun_2026.csv", dist_rows, dry_run)
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datajs", default="dashboard/data.js")
    ap.add_argument("--out", default="PowerBI/RawDataFolders")
    ap.add_argument("--blocks", default="all",
                    help="Comma-separated: all|secondary|claims")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    blocks = {b.strip() for b in args.blocks.split(",")}
    run_all = "all" in blocks

    print(f"Reading {args.datajs} …")
    content = Path(args.datajs).read_text(encoding="utf-8")
    out_dir = Path(args.out)
    total_rows = 0
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Export run: {ts}\n")

    if run_all or "secondary" in blocks:
        ss = extract_block(content, "secondary_sales")
        if ss:
            print("→ Exporting secondary_sales …")
            total_rows += export_secondary_sales(ss, out_dir, args.dry_run)
        else:
            print("  WARN: D.secondary_sales not found in data.js")

    if run_all or "claims" in blocks:
        cl = extract_block(content, "claims")
        if cl:
            print("→ Exporting claims …")
            total_rows += export_claims(cl, out_dir, args.dry_run)
        else:
            print("  WARN: D.claims not found in data.js")

    print(f"\nDone — {total_rows} rows exported{' (dry-run)' if args.dry_run else ''}.")


if __name__ == "__main__":
    main()
