"""
generate_mock_w01_actuals.py

Generate realistic mock Point-of-Sale (POS) actuals for Week 01 (Sep 1-7)
to test end-to-end Power BI ingestion, alert logic, and variance tracking.

Output Format:
  • POS_Actuals_W01_Sep_AllChains.xlsx (consolidated multi-chain feed)
  • POS_Actuals_W01_Sep_Subset.csv (subset simulation)

Variance Distribution (tests all 3 alert states):
  • Red Alert (>±10%): High-growth brands (Mamaearth +15%) + supply-constrained legacy (Himalaya -14%)
  • Yellow Alert (±5-10%): Core brands (Pond's, Dove, Garnier ±6-8%)
  • Green Alert (±0-4%): Baseline brands (Head & Shoulders, Lakme ±2%)
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path

# =========================================================================
# 1. PATH CONFIGURATION
# =========================================================================
# Try Windows path first; fallback to local exports directory
DROP_FOLDER = None
if os.name == 'nt':  # Windows
    try:
        DROP_FOLDER = r"C:\MT_Forecasting\actuals_drops"
        os.makedirs(DROP_FOLDER, exist_ok=True)
        print(f"✓ Using Windows drop folder: {DROP_FOLDER}")
    except:
        DROP_FOLDER = None

# Fallback to local directory
if DROP_FOLDER is None:
    DROP_FOLDER = "/home/user/mt-dashboard/exports/actuals_drops"
    os.makedirs(DROP_FOLDER, exist_ok=True)
    print(f"✓ Using fallback drop folder: {DROP_FOLDER}")

# Source files
COMBINED_FILE = "/home/user/mt-dashboard/exports/Combined_MT_Forecast_Q2_FY27.xlsx"

print(f"=" * 80)
print(f"GENERATING MOCK W01 POS ACTUALS")
print(f"=" * 80)

# =========================================================================
# 2. LOAD FORECAST BENCHMARKS
# =========================================================================
print(f"\n[1] Loading forecast benchmarks from {COMBINED_FILE}...")

try:
    df_fw_methods = pd.read_excel(COMBINED_FILE, sheet_name="FaceWash_Methods")
    df_shampoo_methods = pd.read_excel(COMBINED_FILE, sheet_name="Shampoo_Methods")
except Exception as e:
    print(f"✗ Error loading forecast file: {e}")
    print(f"  Creating synthetic benchmarks instead...")
    # Synthetic if file not found
    df_fw_methods = pd.DataFrame({
        "Month": ["September"],
        "Consensus_Cr": [268.58]
    })
    df_shampoo_methods = pd.DataFrame({
        "Month": ["September"],
        "Consensus_Cr": [39.02]
    })

sep_fw_target = df_fw_methods[df_fw_methods["Month"] == "September"]["Consensus_Cr"].iloc[0]
sep_shampoo_target = df_shampoo_methods[df_shampoo_methods["Month"] == "September"]["Consensus_Cr"].iloc[0]

print(f"  ✓ Face Wash Sep target: ₹{sep_fw_target:.2f} Cr")
print(f"  ✓ Shampoo Sep target: ₹{sep_shampoo_target:.2f} Cr")

# =========================================================================
# 3. DEFINE PORTFOLIO & VARIANCE SCENARIOS
# =========================================================================
print(f"\n[2] Building brand × chain matrix with variance scenarios...")

# Face Wash brands with alert-specific variance patterns
FACEWASH_BRANDS_VARIANCE = {
    "MAMAEARTH": (0.15, "RED"),          # Over-performing +15% (supply success)
    "THE DERMA CO": (0.18, "RED"),       # Explosive growth +18%
    "CETAPHIL": (0.22, "RED"),           # Premium derma breakout +22%
    "HIMALAYA": (-0.14, "RED"),          # Declining, supply OOS -14%
    "NIVEA": (-0.11, "RED"),             # Legacy brand struggle -11%
    "POND'S": (0.067, "YELLOW"),         # Stable +6.7%
    "GARNIER": (0.058, "YELLOW"),        # Growth +5.8%
    "DOVE": (0.08, "YELLOW"),            # Premium +8%
    "HEAD & SHOULDERS": (0.02, "GREEN"), # Baseline +2%
    "CLEAN & CLEAR": (0.015, "GREEN"),   # Baseline +1.5%
    "JOY": (-0.01, "GREEN"),             # Flat -1%
    "EVERYUTH": (0.025, "GREEN"),        # Stable +2.5%
    "SIMPLE": (0.03, "GREEN"),           # New entrant, stable +3%
    "LOTUS": (0.02, "GREEN"),            # Baseline +2%
    "LAKME": (0.018, "GREEN"),           # Baseline +1.8%
    "PATANJALI": (0.008, "GREEN"),       # Ayurvedic, stable +0.8%
    "EMAMI": (0.012, "GREEN"),           # Stable +1.2%
    "PEARS": (-0.025, "GREEN"),          # Slight decline -2.5%
    "BIOTIQUE": (-0.018, "GREEN"),       # Slight decline -1.8%
    "GLOW & LOVELY": (0.009, "GREEN"),   # Stable +0.9%
}

# Shampoo brands with variance patterns
SHAMPOO_BRANDS_VARIANCE = {
    "MAMAEARTH": (0.12, "RED"),          # High growth +12%
    "KÉRASTASE": (0.16, "RED"),          # Luxury growth +16%
    "HEAD & SHOULDERS": (-0.10, "RED"),  # Mature, supply issue -10%
    "PANTENE": (0.065, "YELLOW"),        # Growth +6.5%
    "GARNIER": (0.055, "YELLOW"),        # Growth +5.5%
    "DOVE": (0.075, "YELLOW"),           # Premium +7.5%
    "CLINIC ALL CLEAR": (0.025, "GREEN"),# Baseline +2.5%
    "SUNSILK": (-0.015, "GREEN"),        # Decline -1.5%
    "GILLETTE": (0.01, "GREEN"),         # Flat +1%
    "PATANJALI": (0.005, "GREEN"),       # Ayurvedic +0.5%
    "GODREJ": (0.018, "GREEN"),          # Color care +1.8%
    "LOreal Professionnel": (0.022, "GREEN"),  # Salon +2.2%
    "TRESEMMÉ": (0.02, "GREEN"),         # Aspirational +2%
    "JOHNSON'S": (0.008, "GREEN"),       # Baby care +0.8%
    "BIOTIQUE": (-0.02, "GREEN"),        # Natural, declining -2%
    "HIMALAYA": (0.003, "GREEN"),        # Ayurvedic, flat +0.3%
    "WELLA": (-0.018, "GREEN"),          # Legacy -1.8%
    "KHUS & KHUS": (0.028, "GREEN"),     # Premium natural +2.8%
    "SESA": (0.016, "GREEN"),            # Regional +1.6%
    "HERBAL ESSENTIALS": (0.024, "GREEN"),# Herbal +2.4%
}

# Chains for distribution
CHAINS = ["APOLLO", "RELIANCE", "DMART", "FRANKROS", "GUARDIAN", "H&G", "LULU", "METRO CNC"]

# =========================================================================
# 4. SYNTHESIZE REALISTIC POS ACTUALS
# =========================================================================
print(f"  ✓ Generating {len(FACEWASH_BRANDS_VARIANCE)} Face Wash brands × {len(CHAINS)} chains")
print(f"  ✓ Generating {len(SHAMPOO_BRANDS_VARIANCE)} Shampoo brands × {len(CHAINS)} chains")

records = []
chain_dist = np.array([0.35, 0.18, 0.12, 0.10, 0.08, 0.08, 0.04, 0.05])  # Apollo dominates

# Week 1 of September = 19.05% of monthly target (from weekly phasing)
W01_SHARE = 0.1905

# Face Wash actuals
fw_target_per_brand = (sep_fw_target * W01_SHARE) / len(FACEWASH_BRANDS_VARIANCE)
np.random.seed(42)  # Reproducible randomness

for idx, (brand, (var_pct, alert)) in enumerate(FACEWASH_BRANDS_VARIANCE.items()):
    for chain_idx, chain in enumerate(CHAINS):
        # Distribute target across chains
        target_cr = fw_target_per_brand * chain_dist[chain_idx]

        # Add controlled variance
        var_noise = np.random.uniform(-0.01, 0.01)  # ±1% noise around nominal variance
        actual_variance = var_pct + var_noise
        actual_cr = max(0.0001, target_cr * (1.0 + actual_variance))

        # Convert to INR Rupees for Power Query test
        actual_inr = round(actual_cr * 10000000, 2)

        records.append({
            "CATEGORY": "FACE WASH",
            "CHAIN_ACCOUNT": chain,
            "BRAND_NAME": brand,
            "WEEK_CODE": "W01_Sep",
            "SALES_VALUE_INR": actual_inr,
            "UNITS_SOLD": max(1, int(actual_inr / np.random.uniform(280, 450))),
            "ALERT_EXPECTED": alert,
        })

# Shampoo actuals
shampoo_target_per_brand = (sep_shampoo_target * W01_SHARE) / len(SHAMPOO_BRANDS_VARIANCE)

for idx, (brand, (var_pct, alert)) in enumerate(SHAMPOO_BRANDS_VARIANCE.items()):
    for chain_idx, chain in enumerate(CHAINS):
        target_cr = shampoo_target_per_brand * chain_dist[chain_idx]

        var_noise = np.random.uniform(-0.01, 0.01)
        actual_variance = var_pct + var_noise
        actual_cr = max(0.0001, target_cr * (1.0 + actual_variance))
        actual_inr = round(actual_cr * 10000000, 2)

        records.append({
            "CATEGORY": "SHAMPOO",
            "CHAIN_ACCOUNT": chain,
            "BRAND_NAME": brand,
            "WEEK_CODE": "W01_Sep",
            "SALES_VALUE_INR": actual_inr,
            "UNITS_SOLD": max(1, int(actual_inr / np.random.uniform(200, 350))),
            "ALERT_EXPECTED": alert,
        })

df_actuals = pd.DataFrame(records)
total_actual_cr = (df_actuals["SALES_VALUE_INR"].sum() / 10000000)

print(f"  ✓ Generated {len(df_actuals)} POS records")
print(f"    Total W01 actual: ₹{total_actual_cr:.2f} Cr")
print(f"    Alert distribution: {df_actuals['ALERT_EXPECTED'].value_counts().to_dict()}")

# =========================================================================
# 5. EXPORT POS DROPS
# =========================================================================
print(f"\n[3] Exporting POS drops to {DROP_FOLDER}...")

# Export 1: Excel (Apollo/Central EDI drop)
excel_file = os.path.join(DROP_FOLDER, "POS_Actuals_W01_Sep_AllChains.xlsx")
df_actuals.to_excel(excel_file, sheet_name="Sheet1", index=False)
print(f"  ✓ Excel: {os.path.basename(excel_file)} ({len(df_actuals)} rows)")

# Export 2: CSV (Reliance/DMart quick-drop)
csv_file = os.path.join(DROP_FOLDER, "POS_Actuals_W01_Sep_Subset.csv")
df_subset = df_actuals[df_actuals["CHAIN_ACCOUNT"].isin(["RELIANCE", "DMART", "APOLLO"])]
df_subset.to_csv(csv_file, index=False)
print(f"  ✓ CSV: {os.path.basename(csv_file)} ({len(df_subset)} rows)")

# Export 3: JSON metadata for reference
import json
metadata = {
    "generation_date": pd.Timestamp.now().isoformat(),
    "week_code": "W01_Sep",
    "total_actual_cr": round(total_actual_cr, 2),
    "target_sep_fw_cr": round(sep_fw_target, 2),
    "target_sep_shampoo_cr": round(sep_shampoo_target, 2),
    "alert_distribution": df_actuals['ALERT_EXPECTED'].value_counts().to_dict(),
    "file_locations": {
        "excel": os.path.basename(excel_file),
        "csv": os.path.basename(csv_file),
    }
}

json_file = os.path.join(DROP_FOLDER, "W01_Metadata.json")
with open(json_file, "w") as f:
    json.dump(metadata, f, indent=2)
print(f"  ✓ Metadata: {os.path.basename(json_file)}")

# =========================================================================
# 6. SUMMARY & NEXT STEPS
# =========================================================================
print(f"\n{'=' * 80}")
print(f"✓ MOCK W01 POS ACTUALS READY FOR POWER BI TESTING")
print(f"{'=' * 80}")
print(f"\nFILES CREATED:")
print(f"  {excel_file}")
print(f"  {csv_file}")
print(f"  {json_file}")
print(f"\nNEXT STEPS (Power BI Desktop):")
print(f"  1. Open Power BI Desktop")
print(f"  2. Get Data → Excel → Import 'Combined_MT_Forecast_Q2_FY27.xlsx'")
print(f"  3. Transform Data → Paste M-code for Fact_Weekly_Actuals")
print(f"  4. Set ActualsFolderPath parameter to: {DROP_FOLDER}")
print(f"  5. Refresh → Verify Fact_Weekly_Actuals reads both .xlsx and .csv files")
print(f"  6. Check Fact_Weekly_SOP_Enriched alerts:")
print(f"     • RED (Mamaearth +15%, Himalaya -14%)")
print(f"     • YELLOW (Pond's ±6.7%, Dove +8%)")
print(f"     • GREEN (Head & Shoulders +2%, Lakme +1.8%)")
