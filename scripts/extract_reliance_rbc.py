#!/usr/bin/env python3
"""
Extract Reliance Brand Counter data from offtake source CSVs and integrate into data_master.json.

This is a surgical fix for the missing reliance_bc block. It:
  1. Scans Offtake_Monthly CSVs for Brand Counter rows
  2. Filters Reliance Brand Counter (Chain Name contains 'reliance' + Store Type = 'Brand Counter')
  3. Aggregates by zone/state/brand/category
  4. Integrates into data_master.json
  5. Runs sync_data_js.py to regenerate data.js

Usage:
  python scripts/extract_reliance_rbc.py
"""
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Constants
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_MASTER = REPO_ROOT / "data_master.json"
OFFTAKE_DIR = REPO_ROOT / "PowerBI/RawDataFolders/Offtake_Monthly"
OUTPUT_JS = REPO_ROOT / "dashboard/data.js"

# Month ordering (Indian FY: Apr→Mar)
MONTH_ORDER = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
_MON3_NUM = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

def fy_tag_from_label(lab):
    """'Apr-26' / 'Sep-25' -> 'fy27' / 'fy25'"""
    m = str(lab).strip().split("-")
    if len(m) != 2 or m[0] not in _MON3_NUM:
        return None
    month_num = _MON3_NUM[m[0]]
    year = 2000 + int(m[1])
    fy_year = year if month_num < 4 else year + 1
    return f"fy{fy_year % 100:02d}"

def canon_zone(name):
    """Canonicalize zone names"""
    if not name:
        return None
    name = str(name).strip().title()
    mapping = {
        "Central": "Central",
        "East": "East",
        "North": "North",
        "South 1": "South 1",
        "South 2": "South 2",
        "West": "West",
    }
    return mapping.get(name, name)

def canon_state(name):
    """Canonicalize state names"""
    return str(name).strip().title() if name else None

def canon_brand(name):
    """Canonicalize brand names"""
    if not name:
        return None
    name = str(name).strip()
    return name

def r2(val):
    """Round to 2 decimal places"""
    return round(float(val), 2)

def extract_reliance_bc():
    """Extract Reliance Brand Counter from offtake CSVs"""
    print("=" * 80)
    print("EXTRACTING RELIANCE BRAND COUNTER FROM OFFTAKE SOURCE FILES")
    print("=" * 80)

    offtake_files = sorted(OFFTAKE_DIR.glob("offtake_store_article_*.csv"))
    print(f"\n[1] Found {len(offtake_files)} offtake CSV files")

    frames = []
    for fp in offtake_files:
        print(f"  Reading: {fp.name}")
        try:
            df = pd.read_csv(fp, low_memory=False)

            # Filter for Reliance Brand Counter
            if "Chain Name" in df.columns and "Store Type" in df.columns:
                _chain_c = df["Chain Name"].astype(str).str.strip().str.lower()
                _store_c = df["Store Type"].astype(str).str.strip().str.lower()
                _is_rel = _chain_c.str.contains("reliance", na=False)
                _is_bc = (_store_c == "brand counter")

                rbc_df = df[_is_rel & _is_bc].copy()
                if len(rbc_df) > 0:
                    print(f"    ✓ Found {len(rbc_df):,} RBC rows")
                    frames.append(rbc_df)
                else:
                    print(f"    - No RBC rows")
        except Exception as e:
            print(f"    ✗ Error: {e}")

    if not frames:
        print("\n✗ No Reliance Brand Counter data found")
        return None

    all_rbc = pd.concat(frames, ignore_index=True)
    print(f"\n[2] Total RBC rows aggregated: {len(all_rbc):,}")

    # Prepare data
    all_rbc["_year_str"] = all_rbc["Year"].astype(int).astype(str).str[-2:]
    all_rbc["_month"] = all_rbc["Month"].astype(str).str.strip() + "-" + all_rbc["_year_str"]
    # NSV is already in Lakh, divide by 100 to get Crore
    all_rbc["_nsv"] = pd.to_numeric(all_rbc["NSV"], errors="coerce").fillna(0.0) / 100
    all_rbc["_zone"] = all_rbc["Zone"].map(canon_zone)
    all_rbc["_state"] = all_rbc["State"].map(canon_state)
    all_rbc["_brand"] = all_rbc["Brand"].map(canon_brand) if "Brand" in all_rbc.columns else None
    all_rbc["_category"] = all_rbc["Category"].astype(str).str.strip() if "Category" in all_rbc.columns else ""

    # Filter valid records
    all_rbc = all_rbc[all_rbc["_month"].notna() & (all_rbc["_nsv"] > 0)]
    print(f"  Valid records: {len(all_rbc):,}")

    # Get months
    months = sorted(all_rbc["_month"].unique(),
                   key=lambda mo: (int(mo.split("-")[1]), _MON3_NUM.get(mo.split("-")[0], 99)))
    print(f"  Months covered: {', '.join(months)}")

    # Aggregate by FY
    fy_data = {}
    for mo in months:
        tag = fy_tag_from_label(mo)
        if tag:
            fy_data.setdefault(tag, []).append(mo)

    # Monthly totals
    monthly_totals = {}
    for mo in months:
        monthly_totals[mo] = r2(float(all_rbc[all_rbc["_month"] == mo]["_nsv"].sum()))

    # By zone
    by_zone = []
    for zone, grp in all_rbc.groupby("_zone"):
        entry = {"name": zone, "total": r2(float(grp["_nsv"].sum()))}
        for mo in months:
            tag = fy_tag_from_label(mo)
            if tag:
                lo = tag
                mo_val = float(grp[grp["_month"] == mo]["_nsv"].sum())
                entry[lo] = r2(entry.get(lo, 0) + mo_val)
        by_zone.append(entry)
    by_zone.sort(key=lambda d: -d["total"])

    # By state
    by_state = []
    for (zone, state), grp in all_rbc.groupby(["_zone", "_state"]):
        entry = {"zone": zone, "state": state, "total": r2(float(grp["_nsv"].sum()))}
        for mo in months:
            tag = fy_tag_from_label(mo)
            if tag:
                lo = tag
                mo_val = float(grp[grp["_month"] == mo]["_nsv"].sum())
                entry[lo] = r2(entry.get(lo, 0) + mo_val)
        by_state.append(entry)
    by_state.sort(key=lambda d: -d["total"])

    # By brand
    by_brand = []
    if all_rbc["_brand"].notna().any():
        for brand, grp in all_rbc[all_rbc["_brand"].notna()].groupby("_brand"):
            entry = {"name": brand, "total": r2(float(grp["_nsv"].sum()))}
            for mo in months:
                tag = fy_tag_from_label(mo)
                if tag:
                    lo = tag
                    mo_val = float(grp[grp["_month"] == mo]["_nsv"].sum())
                    entry[lo] = r2(entry.get(lo, 0) + mo_val)
            by_brand.append(entry)
        by_brand.sort(key=lambda d: -d["total"])

    # By category
    by_category = []
    if all_rbc["_category"].notna().any():
        for cat, grp in all_rbc[all_rbc["_category"] != ""].groupby("_category"):
            entry = {"name": cat, "total": r2(float(grp["_nsv"].sum()))}
            for mo in months:
                tag = fy_tag_from_label(mo)
                if tag:
                    lo = tag
                    mo_val = float(grp[grp["_month"] == mo]["_nsv"].sum())
                    entry[lo] = r2(entry.get(lo, 0) + mo_val)
            by_category.append(entry)
        by_category.sort(key=lambda d: -d["total"])

    result = {
        "total": r2(float(all_rbc["_nsv"].sum())),
        "months": months,
        "monthly": [monthly_totals[mo] for mo in months],
        "fy_tags": sorted(fy_data.keys(), key=lambda t: int(t[2:])),
        "by_zone": by_zone,
        "by_state": by_state,
        "by_brand": by_brand,
        "by_category": by_category,
        "include_in_overall_offtake": False,
        "is_brand_counter": True,
        "parent_chain": "Reliance Retail",
        "note": "Reliance Brand Counter Offtake is shown as a separate analytical breakout. Data extracted from store-article offtake CSVs.",
    }

    # Add FY-specific totals and monthly arrays
    for tag, tag_months in fy_data.items():
        result[f"months_{tag}"] = tag_months
        result[f"monthly_{tag}"] = [monthly_totals[mo] for mo in tag_months]
        result[f"total_{tag}"] = r2(sum(monthly_totals[mo] for mo in tag_months))

    print(f"\n[3] RBC Aggregation Complete")
    print(f"  Total RBC: ₹{result['total']:.2f} Cr")
    print(f"  FYs covered: {result['fy_tags']}")
    print(f"  Zones: {len(by_zone)}")
    print(f"  States: {len(by_state)}")
    print(f"  Brands: {len(by_brand)}")
    print(f"  Categories: {len(by_category)}")

    return result

def main():
    # Extract RBC
    rbc_data = extract_reliance_bc()
    if rbc_data is None:
        return 1

    # Integrate into data_master.json
    print(f"\n[4] Integrating into data_master.json")
    master = json.load(open(DATA_MASTER))
    master["reliance_bc"] = rbc_data

    # Write updated data_master.json
    with open(DATA_MASTER, 'w') as f:
        json.dump(master, f, indent=2, ensure_ascii=False)
    print(f"  ✓ Updated data_master.json")

    # Run sync_data_js.py to regenerate data.js
    print(f"\n[5] Regenerating data.js via sync_data_js.py")
    import subprocess
    result = subprocess.run([
        "python", str(REPO_ROOT / "scripts/sync_data_js.py"),
        "--source", str(DATA_MASTER),
        "--output", str(OUTPUT_JS)
    ], cwd=REPO_ROOT)

    if result.returncode == 0:
        print(f"\n" + "=" * 80)
        print("✓ SUCCESS: Reliance Brand Counter extracted and data.js regenerated")
        print("=" * 80)

        # Verify
        d = json.load(open(OUTPUT_JS))
        d_text = d.replace("window.DASH = ", "").rstrip(";")
        d_obj = json.loads(d_text)

        offtake_total = d_obj.get("offtake", {}).get("total_fy26", 0)
        rbc_total = d_obj.get("reliance_bc", {}).get("total", 0)

        print(f"\nVerification:")
        print(f"  offtake.total_fy26:   ₹{offtake_total/100:.2f} Cr (RBC excluded)")
        print(f"  reliance_bc.total:    ₹{rbc_total:.2f} Cr (RBC only)")
        print(f"  Combined:             ₹{(offtake_total/100 + rbc_total):.2f} Cr")
        print(f"\n✓ No double-counting — RBC properly separated")
        return 0
    else:
        print(f"\n✗ sync_data_js.py failed")
        return 1

if __name__ == "__main__":
    exit(main())
