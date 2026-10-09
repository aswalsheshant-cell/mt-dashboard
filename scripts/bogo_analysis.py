#!/usr/bin/env python3
"""
BOGO vs Non-BOGO analysis using source-level margin columns.

Primary: uses `Avg Tot` column (Trade Operating Total ratio, 0-1)
Offtake:  uses `Margin` column (ratio, 0-1)
Threshold: >= 0.55 (55%) = BOGO

Usage:
    python scripts/bogo_analysis.py [--threshold 0.55] [--output reports/bogo_report.md]
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PRIMARY_DIR = REPO_ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
OFFTAKE_DIR = REPO_ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"

MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
MONTH_NUM = {m: i for i, m in enumerate(MONTH_ORDER)}

BRAND_NORMALIZE = {
    "the derma co.": "The Derma Co",
    "the derma co": "The Derma Co",
    "mamaearth": "Mamaearth",
    "aqualogica": "Aqualogica",
    "bblunt": "BBlunt",
    "dr. sheth's": "Dr. Sheth's",
}


def fy_from_month_year(month_abbr, year_int):
    """Derive FY tag from month and calendar year (THE ONE FY RULE)."""
    if month_abbr in ("Jan", "Feb", "Mar"):
        return f"FY{year_int % 100}"
    return f"FY{(year_int + 1) % 100}"


def parse_filename_month_year(filename):
    """Extract (month_abbr, year_int) from primary_article_Aug_26.csv or offtake_store_article_Aug_26.csv."""
    m = re.search(r"_([A-Za-z]{3})_(\d{2})\.csv$", filename)
    if not m:
        return None, None
    return m.group(1), 2000 + int(m.group(2))


def safe_float(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def load_primary_files(primary_dir, threshold):
    """Load all Primary article CSVs and classify BOGO by Avg Tot."""
    results = []
    files = sorted(primary_dir.glob("primary_article_*.csv"))
    if not files:
        print(f"  No Primary article CSVs found in {primary_dir}")
        return results

    for fpath in files:
        month_abbr, year_int = parse_filename_month_year(fpath.name)
        if month_abbr is None:
            continue
        fy = fy_from_month_year(month_abbr, year_int)

        with open(fpath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                avg_tot = safe_float(row.get("Avg Tot"))
                nsv = safe_float(row.get("Inv. Net value(LOC)"))
                qty = safe_float(row.get("Inv Qty"))
                mrp_sales = safe_float(row.get("Total MRP sales"))
                if avg_tot is None or nsv is None:
                    continue

                is_bogo = avg_tot >= threshold
                chain = (row.get("Chain name for Dashboard") or row.get("Chain name") or "").strip()
                raw_brand = (row.get("brand") or "").strip()
                brand = BRAND_NORMALIZE.get(raw_brand.lower(), raw_brand)
                results.append({
                    "fy": fy,
                    "month": month_abbr,
                    "year": year_int,
                    "brand": brand,
                    "category": (row.get("category") or "").strip(),
                    "sub_category": (row.get("sub_category") or "").strip(),
                    "description": (row.get("Description") or "").strip(),
                    "chain": chain,
                    "zone": (row.get("Zone") or "").strip(),
                    "ean": (row.get("EAN No.") or row.get("EAN No") or "").strip(),
                    "nsv": nsv,
                    "qty": qty or 0,
                    "mrp_sales": mrp_sales or 0,
                    "avg_tot": avg_tot,
                    "is_bogo": is_bogo,
                    "source": "primary",
                })
    return results


def load_offtake_files(offtake_dir, threshold):
    """Load all Offtake store-article CSVs and classify BOGO by Margin."""
    results = []
    files = sorted(offtake_dir.glob("offtake_store_article_*.csv"))
    if not files:
        print(f"  No Offtake store-article CSVs found in {offtake_dir}")
        return results

    for fpath in files:
        month_abbr, year_int = parse_filename_month_year(fpath.name)
        if month_abbr is None:
            continue
        fy = fy_from_month_year(month_abbr, year_int)

        with open(fpath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            # Handle duplicate columns
            seen = {}
            clean_headers = []
            for h in headers:
                if h in seen:
                    seen[h] += 1
                    clean_headers.append(f"{h}.{seen[h]}")
                else:
                    seen[h] = 0
                    clean_headers.append(h)

            for row_raw in reader:
                row = dict(zip(clean_headers, row_raw.values()))
                margin = safe_float(row.get("Margin"))
                qty = safe_float(row.get("Sales Qty"))
                mrp_val = safe_float(row.get("MRP Sales Value"))
                if margin is None or mrp_val is None:
                    continue

                # NSV column in offtake CSVs is a per-piece rate, not total.
                # Compute actual NSV from MRP Sales Value and Margin.
                nsv = mrp_val * (1 - margin)

                is_bogo = margin >= threshold
                chain = (row.get("Chain Name") or "").strip()
                raw_brand = (row.get("Brand") or row.get("brand") or "").strip()
                brand = BRAND_NORMALIZE.get(raw_brand.lower(), raw_brand)
                results.append({
                    "fy": fy,
                    "month": month_abbr,
                    "year": year_int,
                    "brand": brand,
                    "category": (row.get("Category") or row.get("category") or "").strip(),
                    "sub_category": (row.get("Sub_category") or row.get("sub_category") or "").strip(),
                    "description": (row.get("Description as per Fountain") or row.get("Description") or "").strip(),
                    "chain": chain,
                    "zone": (row.get("Zone") or "").strip(),
                    "ean": str(row.get("EAN") or row.get("EAN No.") or "").strip(),
                    "nsv": nsv,
                    "qty": qty or 0,
                    "mrp_sales": mrp_val or 0,
                    "margin": margin,
                    "is_bogo": is_bogo,
                    "source": "offtake",
                })
    return results


def aggregate(records, group_key, value_keys=("nsv", "qty")):
    """Group records by group_key and sum value_keys."""
    agg = defaultdict(lambda: {k: 0 for k in value_keys})
    counts = defaultdict(int)
    for r in records:
        key = group_key(r) if callable(group_key) else r[group_key]
        for k in value_keys:
            agg[key][k] += r.get(k, 0) or 0
        counts[key] += 1
    return agg, counts


def fmt_l(val):
    """Format as Lakhs with comma."""
    return f"{val / 100000:,.2f}"


def fmt_cr(val):
    """Format as Crores."""
    return f"{val / 10000000:,.2f}"


def fmt_qty(val):
    """Format quantity with commas."""
    return f"{int(val):,}"


def fmt_pct(val):
    return f"{val:.1f}%"


def write_report(primary_data, offtake_data, threshold, output_path):
    """Generate the BOGO analysis report."""
    lines = []
    add = lines.append

    pct_label = f"{threshold * 100:.0f}%"

    # --- PRIMARY ANALYSIS ---
    add(f"# BOGO vs Non-BOGO Analysis Report")
    add(f"")
    add(f"**Generated:** {__import__('datetime').date.today()}")
    add(f"**BOGO Threshold:** Avg Tot / Margin >= {pct_label}")
    add(f"**Primary Source:** `Avg Tot` column from Primary article CSVs")
    add(f"**Offtake Source:** `Margin` column from Offtake store-article CSVs")
    add(f"")

    # Separate TY / LY for Primary
    # Determine available FYs
    primary_fys = sorted(set(r["fy"] for r in primary_data))
    offtake_fys = sorted(set(r["fy"] for r in offtake_data))

    add(f"**Primary FYs available:** {', '.join(primary_fys)}")
    add(f"**Offtake FYs available:** {', '.join(offtake_fys) if offtake_fys else 'None'}")
    add(f"")

    # Find the two latest FYs for TY/LY comparison
    if len(primary_fys) >= 2:
        fy_ty = primary_fys[-1]
        fy_ly = primary_fys[-2]
    elif len(primary_fys) == 1:
        fy_ty = primary_fys[0]
        fy_ly = None
    else:
        add("No Primary data found.")
        with open(output_path, "w") as f:
            f.write("\n".join(lines))
        return

    # Filter to Apr-Aug for comparison (common months)
    apr_aug = {"Apr", "May", "Jun", "Jul", "Aug"}

    p_ty = [r for r in primary_data if r["fy"] == fy_ty and r["month"] in apr_aug]
    p_ly = [r for r in primary_data if r["fy"] == fy_ly and r["month"] in apr_aug] if fy_ly else []

    p_ty_bogo = [r for r in p_ty if r["is_bogo"]]
    p_ty_nonbogo = [r for r in p_ty if not r["is_bogo"]]
    p_ly_bogo = [r for r in p_ly if r["is_bogo"]]
    p_ly_nonbogo = [r for r in p_ly if not r["is_bogo"]]

    ty_bogo_nsv = sum(r["nsv"] for r in p_ty_bogo)
    ty_nb_nsv = sum(r["nsv"] for r in p_ty_nonbogo)
    ty_total = ty_bogo_nsv + ty_nb_nsv
    ly_bogo_nsv = sum(r["nsv"] for r in p_ly_bogo)
    ly_nb_nsv = sum(r["nsv"] for r in p_ly_nonbogo)
    ly_total = ly_bogo_nsv + ly_nb_nsv

    add("---")
    add("")
    add("## PRIMARY — YoY Summary (Apr-Aug)")
    add("")
    add(f"| Segment | {fy_ty} (Rs Cr) | {fy_ly} (Rs Cr) | YoY Growth | {fy_ty} Share | {fy_ly} Share |" if fy_ly else f"| Segment | {fy_ty} (Rs Cr) | {fy_ty} Share |")
    add("|---------|" + ("-----------|-----------|-----------|---------|---------|" if fy_ly else "-----------|---------|"))

    if fy_ly and ly_total > 0:
        bogo_yoy = (ty_bogo_nsv / ly_bogo_nsv - 1) * 100 if ly_bogo_nsv > 0 else 0
        nb_yoy = (ty_nb_nsv / ly_nb_nsv - 1) * 100 if ly_nb_nsv > 0 else 0
        total_yoy = (ty_total / ly_total - 1) * 100 if ly_total > 0 else 0
        add(f"| **BOGO** | {fmt_cr(ty_bogo_nsv)} | {fmt_cr(ly_bogo_nsv)} | **+{bogo_yoy:.1f}%** | {fmt_pct(ty_bogo_nsv/ty_total*100)} | {fmt_pct(ly_bogo_nsv/ly_total*100)} |")
        add(f"| **Non-BOGO** | {fmt_cr(ty_nb_nsv)} | {fmt_cr(ly_nb_nsv)} | +{nb_yoy:.1f}% | {fmt_pct(ty_nb_nsv/ty_total*100)} | {fmt_pct(ly_nb_nsv/ly_total*100)} |")
        add(f"| **Total** | {fmt_cr(ty_total)} | {fmt_cr(ly_total)} | +{total_yoy:.1f}% | 100% | 100% |")
    else:
        add(f"| **BOGO** | {fmt_cr(ty_bogo_nsv)} | {fmt_pct(ty_bogo_nsv/ty_total*100 if ty_total else 0)} |")
        add(f"| **Non-BOGO** | {fmt_cr(ty_nb_nsv)} | {fmt_pct(ty_nb_nsv/ty_total*100 if ty_total else 0)} |")
        add(f"| **Total** | {fmt_cr(ty_total)} | 100% |")

    add("")

    # Month-wise TY
    add(f"## PRIMARY — Month-wise {fy_ty} (Apr-Aug)")
    add("")
    add("| Month | BOGO NSV (L) | BOGO Qty | Non-BOGO NSV (L) | Non-BOGO Qty | BOGO % |")
    add("|-------|-------------|----------|------------------|-------------|--------|")

    for mon in ["Apr", "May", "Jun", "Jul", "Aug"]:
        b = [r for r in p_ty_bogo if r["month"] == mon]
        nb = [r for r in p_ty_nonbogo if r["month"] == mon]
        b_nsv = sum(r["nsv"] for r in b)
        nb_nsv = sum(r["nsv"] for r in nb)
        b_qty = sum(r["qty"] for r in b)
        nb_qty = sum(r["qty"] for r in nb)
        total = b_nsv + nb_nsv
        pct = b_nsv / total * 100 if total > 0 else 0
        add(f"| {mon} | {fmt_l(b_nsv)} | {fmt_qty(b_qty)} | {fmt_l(nb_nsv)} | {fmt_qty(nb_qty)} | {fmt_pct(pct)} |")

    total_b_qty = sum(r["qty"] for r in p_ty_bogo)
    total_nb_qty = sum(r["qty"] for r in p_ty_nonbogo)
    add(f"| **Total** | **{fmt_l(ty_bogo_nsv)}** | **{fmt_qty(total_b_qty)}** | **{fmt_l(ty_nb_nsv)}** | **{fmt_qty(total_nb_qty)}** | **{fmt_pct(ty_bogo_nsv/ty_total*100 if ty_total else 0)}** |")
    add("")

    # Month-wise LY
    if fy_ly and p_ly:
        add(f"## PRIMARY — Month-wise {fy_ly} (Apr-Aug)")
        add("")
        add("| Month | BOGO NSV (L) | BOGO Qty | Non-BOGO NSV (L) | Non-BOGO Qty | BOGO % |")
        add("|-------|-------------|----------|------------------|-------------|--------|")

        for mon in ["Apr", "May", "Jun", "Jul", "Aug"]:
            b = [r for r in p_ly_bogo if r["month"] == mon]
            nb = [r for r in p_ly_nonbogo if r["month"] == mon]
            b_nsv = sum(r["nsv"] for r in b)
            nb_nsv = sum(r["nsv"] for r in nb)
            b_qty = sum(r["qty"] for r in b)
            nb_qty = sum(r["qty"] for r in nb)
            total = b_nsv + nb_nsv
            pct = b_nsv / total * 100 if total > 0 else 0
            add(f"| {mon} | {fmt_l(b_nsv)} | {fmt_qty(b_qty)} | {fmt_l(nb_nsv)} | {fmt_qty(nb_qty)} | {fmt_pct(pct)} |")

        total_b_qty_ly = sum(r["qty"] for r in p_ly_bogo)
        total_nb_qty_ly = sum(r["qty"] for r in p_ly_nonbogo)
        add(f"| **Total** | **{fmt_l(ly_bogo_nsv)}** | **{fmt_qty(total_b_qty_ly)}** | **{fmt_l(ly_nb_nsv)}** | **{fmt_qty(total_nb_qty_ly)}** | **{fmt_pct(ly_bogo_nsv/ly_total*100 if ly_total else 0)}** |")
        add("")

    # MoM YoY Growth
    if fy_ly and p_ly:
        add("## PRIMARY — MoM YoY Growth")
        add("")
        add("| Month | BOGO TY (L) | BOGO LY (L) | BOGO YoY | Non-BOGO TY (L) | Non-BOGO LY (L) | NB YoY |")
        add("|-------|-------------|-------------|----------|-----------------|-----------------|--------|")
        for mon in ["Apr", "May", "Jun", "Jul", "Aug"]:
            bt = sum(r["nsv"] for r in p_ty_bogo if r["month"] == mon)
            bl = sum(r["nsv"] for r in p_ly_bogo if r["month"] == mon)
            nbt = sum(r["nsv"] for r in p_ty_nonbogo if r["month"] == mon)
            nbl = sum(r["nsv"] for r in p_ly_nonbogo if r["month"] == mon)
            b_yoy = (bt / bl - 1) * 100 if bl > 0 else 0
            nb_yoy = (nbt / nbl - 1) * 100 if nbl > 0 else 0
            add(f"| {mon} | {fmt_l(bt)} | {fmt_l(bl)} | **+{b_yoy:.1f}%** | {fmt_l(nbt)} | {fmt_l(nbl)} | +{nb_yoy:.1f}% |")
        add("")

    # By Brand
    add("## PRIMARY — BOGO by Brand (TY)")
    add("")
    add("| Brand | NSV (L) | Qty | Share of BOGO |")
    add("|-------|---------|-----|--------------|")
    brand_agg, _ = aggregate(p_ty_bogo, "brand")
    for brand, vals in sorted(brand_agg.items(), key=lambda x: -x[1]["nsv"]):
        if vals["nsv"] < 100:
            continue
        share = vals["nsv"] / ty_bogo_nsv * 100 if ty_bogo_nsv > 0 else 0
        add(f"| {brand} | {fmt_l(vals['nsv'])} | {fmt_qty(vals['qty'])} | {fmt_pct(share)} |")
    add("")

    # By Category
    add("## PRIMARY — BOGO by Category (TY)")
    add("")
    add("| Category | NSV (L) | Qty | Share of BOGO |")
    add("|----------|---------|-----|--------------|")
    cat_agg, _ = aggregate(p_ty_bogo, "category")
    for cat, vals in sorted(cat_agg.items(), key=lambda x: -x[1]["nsv"]):
        if vals["nsv"] < 100:
            continue
        share = vals["nsv"] / ty_bogo_nsv * 100 if ty_bogo_nsv > 0 else 0
        add(f"| {cat} | {fmt_l(vals['nsv'])} | {fmt_qty(vals['qty'])} | {fmt_pct(share)} |")
    add("")

    # By Chain — Top 10
    add("## PRIMARY — BOGO by Chain — Top 10 (TY)")
    add("")
    add("| Chain | NSV (L) | Qty | Share of BOGO |")
    add("|-------|---------|-----|--------------|")
    chain_agg, _ = aggregate(p_ty_bogo, "chain")
    sorted_chains = sorted(chain_agg.items(), key=lambda x: -x[1]["nsv"])
    for i, (chain, vals) in enumerate(sorted_chains[:10]):
        share = vals["nsv"] / ty_bogo_nsv * 100 if ty_bogo_nsv > 0 else 0
        add(f"| {chain or '(blank)'} | {fmt_l(vals['nsv'])} | {fmt_qty(vals['qty'])} | {fmt_pct(share)} |")
    others_nsv = sum(v["nsv"] for _, v in sorted_chains[10:])
    others_qty = sum(v["qty"] for _, v in sorted_chains[10:])
    if others_nsv > 0:
        add(f"| Others | {fmt_l(others_nsv)} | {fmt_qty(others_qty)} | {fmt_pct(others_nsv/ty_bogo_nsv*100 if ty_bogo_nsv else 0)} |")
    add("")

    # By Zone
    add("## PRIMARY — BOGO by Zone (TY)")
    add("")
    add("| Zone | NSV (L) | Qty | Share of BOGO |")
    add("|------|---------|-----|--------------|")
    zone_agg, _ = aggregate(p_ty_bogo, "zone")
    for zone, vals in sorted(zone_agg.items(), key=lambda x: -x[1]["nsv"]):
        if vals["nsv"] < 100:
            continue
        share = vals["nsv"] / ty_bogo_nsv * 100 if ty_bogo_nsv > 0 else 0
        add(f"| {zone} | {fmt_l(vals['nsv'])} | {fmt_qty(vals['qty'])} | {fmt_pct(share)} |")
    add("")

    # Top 15 articles
    add("## PRIMARY — Top 15 BOGO Articles (TY)")
    add("")
    add("| Article | Brand | NSV (L) | Qty | Avg Tot |")
    add("|---------|-------|---------|-----|---------|")
    art_agg = defaultdict(lambda: {"nsv": 0, "qty": 0, "tot_weighted": 0, "brand": ""})
    for r in p_ty_bogo:
        key = r["description"]
        art_agg[key]["nsv"] += r["nsv"]
        art_agg[key]["qty"] += r["qty"]
        art_agg[key]["tot_weighted"] += r["avg_tot"] * r["nsv"]
        art_agg[key]["brand"] = r["brand"]
    top_arts = sorted(art_agg.items(), key=lambda x: -x[1]["nsv"])[:15]
    for desc, vals in top_arts:
        avg_tot = vals["tot_weighted"] / vals["nsv"] * 100 if vals["nsv"] > 0 else 0
        brand_short = "ME" if "mama" in vals["brand"].lower() else ("TDC" if "derma" in vals["brand"].lower() else vals["brand"][:10])
        add(f"| {desc} | {brand_short} | {fmt_l(vals['nsv'])} | {fmt_qty(vals['qty'])} | {fmt_pct(avg_tot)} |")
    add("")

    # --- OFFTAKE ANALYSIS ---
    if offtake_data:
        add("---")
        add("")
        add("## OFFTAKE — Summary (TY)")
        add("")

        o_bogo = [r for r in offtake_data if r["is_bogo"]]
        o_nonbogo = [r for r in offtake_data if not r["is_bogo"]]
        o_b_nsv = sum(r["nsv"] for r in o_bogo)
        o_nb_nsv = sum(r["nsv"] for r in o_nonbogo)
        o_total = o_b_nsv + o_nb_nsv

        add("| Segment | NSV (Rs Cr) | Share |")
        add("|---------|------------|-------|")
        add(f"| **BOGO** | {fmt_cr(o_b_nsv)} | {fmt_pct(o_b_nsv/o_total*100 if o_total else 0)} |")
        add(f"| **Non-BOGO** | {fmt_cr(o_nb_nsv)} | {fmt_pct(o_nb_nsv/o_total*100 if o_total else 0)} |")
        add(f"| **Total** | {fmt_cr(o_total)} | 100% |")
        add("")

        add("## OFFTAKE — Month-wise (TY)")
        add("")
        add("| Month | BOGO NSV (L) | Non-BOGO NSV (L) | BOGO % |")
        add("|-------|-------------|------------------|--------|")
        for mon in ["Apr", "May", "Jun", "Jul", "Aug"]:
            b_nsv = sum(r["nsv"] for r in o_bogo if r["month"] == mon)
            nb_nsv = sum(r["nsv"] for r in o_nonbogo if r["month"] == mon)
            total = b_nsv + nb_nsv
            pct = b_nsv / total * 100 if total > 0 else 0
            add(f"| {mon} | {fmt_l(b_nsv)} | {fmt_l(nb_nsv)} | {fmt_pct(pct)} |")
        add(f"| **Total** | **{fmt_l(o_b_nsv)}** | **{fmt_l(o_nb_nsv)}** | **{fmt_pct(o_b_nsv/o_total*100 if o_total else 0)}** |")
        add("")

        # Cross-check table
        add("## PRIMARY vs OFFTAKE Cross-Check")
        add("")
        add("| Metric | Primary | Offtake |")
        add("|--------|---------|---------|")
        add(f"| Total NSV | Rs {fmt_cr(ty_total)} Cr | Rs {fmt_cr(o_total)} Cr |")
        add(f"| BOGO NSV | Rs {fmt_cr(ty_bogo_nsv)} Cr | Rs {fmt_cr(o_b_nsv)} Cr |")
        add(f"| BOGO Share | {fmt_pct(ty_bogo_nsv/ty_total*100 if ty_total else 0)} | {fmt_pct(o_b_nsv/o_total*100 if o_total else 0)} |")
        add("")

    # Data basis
    add("---")
    add("")
    add("## Data Basis")
    add("")
    add("| Source | Column | Threshold | Files | Period |")
    add("|--------|--------|-----------|-------|--------|")
    p_files = sorted(PRIMARY_DIR.glob("primary_article_*.csv"))
    o_files = sorted(OFFTAKE_DIR.glob("offtake_store_article_*.csv"))
    add(f"| Primary article CSVs | `Avg Tot` (ratio 0-1) | >= {threshold} ({pct_label}) | {len(p_files)} files | {', '.join(primary_fys)} |")
    if o_files:
        add(f"| Offtake store-article CSVs | `Margin` (ratio 0-1) | >= {threshold} ({pct_label}) | {len(o_files)} files | {', '.join(offtake_fys)} |")
    add("")
    add(f"Total Primary rows: {len(primary_data):,} | Total Offtake rows: {len(offtake_data):,}")
    add("")

    report = "\n".join(lines)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)
    return report


def main():
    parser = argparse.ArgumentParser(description="BOGO vs Non-BOGO analysis")
    parser.add_argument("--threshold", type=float, default=0.55, help="BOGO margin threshold (default: 0.55)")
    parser.add_argument("--output", type=str, default=None, help="Output report path (default: reports/bogo_report.md)")
    parser.add_argument("--primary-dir", type=str, default=None, help="Primary article CSV directory")
    parser.add_argument("--offtake-dir", type=str, default=None, help="Offtake store-article CSV directory")
    args = parser.parse_args()

    primary_dir = Path(args.primary_dir) if args.primary_dir else PRIMARY_DIR
    offtake_dir = Path(args.offtake_dir) if args.offtake_dir else OFFTAKE_DIR
    output_path = Path(args.output) if args.output else REPO_ROOT / "reports" / "bogo_report.md"
    threshold = args.threshold

    print(f"BOGO Analysis — threshold: {threshold * 100:.0f}%")
    print(f"Primary source: {primary_dir}")
    print(f"Offtake source: {offtake_dir}")
    print()

    print("Loading Primary article CSVs...")
    primary_data = load_primary_files(primary_dir, threshold)
    print(f"  Loaded {len(primary_data):,} rows")

    print("Loading Offtake store-article CSVs...")
    offtake_data = load_offtake_files(offtake_dir, threshold)
    print(f"  Loaded {len(offtake_data):,} rows")

    print(f"\nGenerating report -> {output_path}")
    write_report(primary_data, offtake_data, threshold, output_path)
    print(f"Report saved: {output_path}")


if __name__ == "__main__":
    main()
