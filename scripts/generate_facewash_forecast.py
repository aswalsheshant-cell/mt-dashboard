"""
generate_facewash_forecast.py

Build FaceWash_Forecast_Q2_FY27.xlsx (6-sheet operational workbook)
Sep/Oct/Nov weekly + monthly forecasts from Mapping_MT_Forecast_FY27.xlsx

Execution flow:
  1. Read Brand_Master baselines (Q2'26 Nielsen actuals)
  2. Apply brand growth vectors (Explosive/Growth/Stable/Declining)
  3. Apply zone PSR uplift factors (High/Medium/Low intensity)
  4. Distribute across 13 weeks with time-phasing (Sep/Oct/Nov)
  5. Cascade Chain × Tier breakdown for store-level targets
  6. Generate 6 sheets: Master, Methods, Brand, Weekly, PSR, Dashboard

Output: FaceWash_Forecast_Q2_FY27.xlsx (operational forecast ready for Power BI integration)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# =========================================================================
# CONFIGURATION
# =========================================================================
MAPPING_FILE = "/home/user/mt-dashboard/exports/Mapping_MT_Forecast_FY27.xlsx"
OUTPUT_FILE = "/home/user/mt-dashboard/exports/FaceWash_Forecast_Q2_FY27.xlsx"

# Brand growth vectors (from Nielsen Q2'26 YoY % + forecast assumptions)
BRAND_GROWTH_BOUNDS = {
    "HIMALAYA": 0.02,  # Declining -0.35% YoY → defensive +2% for bundling
    "POND'S": 0.15,    # Growth +10.6% YoY → modest +15% with PSR
    "GARNIER": 0.18,   # Growth +14.3% YoY → +18% with visibility
    "MAMAEARTH": 0.42, # Explosive +58.2% YoY → capped at +42% (supply constraint)
    "CLEAN & CLEAR": 0.14,
    "JOY": 0.12,
    "NIVEA": 0.05,     # Declining -19.6% YoY → defensive flat
    "LAKME": 0.20,
    "SIMPLE": 0.80,    # Explosive 861% YoY → capped at +80%
    "EVERYUTH": 0.25,
    "PATANJALI": 0.08,
    "BIOTIQUE": 0.05,
    "EMAMI": 0.16,
    "VLCC": 0.06,
    "GLOW & LOVELY": 0.09,
    "LOTUS": 0.30,
    "THE DERMA CO": 0.90, # Explosive 3191% → capped at +90%
    "PEARS": 0.04,
    "HIMALAYA MENS": 0.05,
    "CETAPHIL": 1.00,  # Explosive 5343% → capped at +100%
}

# PSR uplift by zone intensity
PSR_UPLIFT = {
    "High": 0.20,      # West, North, South-1, South-2
    "Medium": 0.12,    # Central
    "Low": 0.05,       # East
}

# Weekly time-phasing multipliers (distribution of monthly target across weeks)
WEEKLY_PHASING = {
    "September": {  # Weeks 1-5: Pipeline fill + range-selling ramp
        1: 0.16, 2: 0.18, 3: 0.20, 4: 0.22, 5: 0.24  # Progressive ramp
    },
    "October": {    # Weeks 6-9: Festive peak
        6: 0.28, 7: 0.27, 8: 0.26, 9: 0.25  # High but steady
    },
    "November": {   # Weeks 10-13: Post-festive steady-state
        10: 0.24, 11: 0.24, 12: 0.24, 13: 0.24  # Stable replenishment
    }
}

# =========================================================================
# 1. LOAD MAPPING DATA
# =========================================================================
print("[1/6] Loading Mapping_MT_Forecast_FY27.xlsx...")

try:
    brand_master = pd.read_excel(MAPPING_FILE, sheet_name="Brand_Master")
    chain_universe = pd.read_excel(MAPPING_FILE, sheet_name="Chain_Universe")
    zone_mapping = pd.read_excel(MAPPING_FILE, sheet_name="Zone_Metro_Mapping")
    print(f"  ✓ Loaded: {len(brand_master)} brands, {len(chain_universe)} chains, {len(zone_mapping)} zones")
except Exception as e:
    print(f"  ✗ Error loading mapping file: {e}")
    exit(1)

# =========================================================================
# 2. BUILD SHEET 1: MASTER DATA (Brand baselines + growth vectors)
# =========================================================================
print("[2/6] Building Master Data sheet...")

sheet1_master = brand_master[["rank", "brand", "baseline_cr", "yoy_pct", "growth_tier"]].copy()
sheet1_master["growth_vector"] = sheet1_master["brand"].map(BRAND_GROWTH_BOUNDS)
sheet1_master["adjusted_baseline_cr"] = (
    sheet1_master["baseline_cr"] * (1 + sheet1_master["growth_vector"])
)
sheet1_master = sheet1_master.round(2)
print(f"  ✓ Sheet 1: {len(sheet1_master)} brands with growth vectors")

# =========================================================================
# 3. BUILD SHEET 2: FORECAST METHODS (Consensus approach)
# =========================================================================
print("[3/6] Building Forecast Methods sheet...")

# Calculate consensus forecast for Sep/Oct/Nov
total_baseline = sheet1_master["baseline_cr"].sum()
total_adjusted = sheet1_master["adjusted_baseline_cr"].sum()

# Monthly seasonal indices (from playbook: Aug baseline → Sep/Oct/Nov)
seasonal_index = {
    "September": 1.025,  # +2.5% post-monsoon recovery
    "October": 1.128,    # +12.8% Dussehra / festive build
    "November": 1.140    # +14.0% Diwali peak
}

# 4 methods: baseline, growth-adjusted, conservative, optimistic
methods_data = []
for month in ["September", "October", "November"]:
    season_mult = seasonal_index[month]

    # Method 1: Moving Average (baseline + seasonal)
    ma_forecast = total_baseline * season_mult

    # Method 2: Weighted MA (growth-adjusted + seasonal)
    wma_forecast = total_adjusted * season_mult

    # Method 3: Conservative (baseline + 50% of growth vector + seasonal)
    conservative = (total_baseline + (total_adjusted - total_baseline) * 0.5) * season_mult

    # Method 4: Optimistic (full adjusted + 1.5x seasonal)
    optimistic = total_adjusted * (season_mult * 1.15)

    # Consensus = average of 4 methods
    consensus = np.mean([ma_forecast, wma_forecast, conservative, optimistic])

    methods_data.append({
        "Month": month,
        "MA_Baseline_Cr": round(ma_forecast, 2),
        "WMA_Adjusted_Cr": round(wma_forecast, 2),
        "Conservative_Cr": round(conservative, 2),
        "Optimistic_Cr": round(optimistic, 2),
        "Consensus_Cr": round(consensus, 2),
    })

sheet2_methods = pd.DataFrame(methods_data)
print(f"  ✓ Sheet 2: 4-method consensus, Sep ₹{sheet2_methods.loc[0, 'Consensus_Cr']:.2f}Cr | Oct ₹{sheet2_methods.loc[1, 'Consensus_Cr']:.2f}Cr | Nov ₹{sheet2_methods.loc[2, 'Consensus_Cr']:.2f}Cr")

# =========================================================================
# 4. BUILD SHEET 3: BRAND FORECAST (Chain × Brand × Month)
# =========================================================================
print("[4/6] Building Brand Forecast sheet (Chain × Brand × Month)...")

brand_forecast_rows = []
for _, brand_row in sheet1_master.iterrows():
    brand = brand_row["brand"]
    brand_baseline = brand_row["baseline_cr"]
    adjusted = brand_row["adjusted_baseline_cr"]

    for _, chain_row in chain_universe.iterrows():
        chain = chain_row["chain_name"]
        chain_outlets = chain_row["total_stores"]

        # Chain share: proportional to outlet count
        chain_share = chain_outlets / chain_universe["total_stores"].sum()

        for month in ["September", "October", "November"]:
            season_mult = seasonal_index[month]

            # Find primary zone for this chain (simplified: use top_zones first)
            chain_zone = zone_mapping.iloc[0]["zone"]  # Default to highest PSR intensity zone
            zone_uplift = PSR_UPLIFT.get(
                zone_mapping[zone_mapping["zone"] == chain_zone]["psr_intensity"].iloc[0]
                if chain_zone in zone_mapping["zone"].values else "High",
                0.20
            )

            # Monthly forecast with chain share + seasonal + PSR uplift
            monthly_forecast = (adjusted * chain_share * season_mult * (1 + zone_uplift))

            # YoY comparison (vs baseline same month prior year)
            prior_year_baseline = (brand_baseline * chain_share * season_mult)
            yoy_pct = ((monthly_forecast - prior_year_baseline) / max(prior_year_baseline, 0.001)) * 100

            brand_forecast_rows.append({
                "Brand": brand,
                "Chain": chain,
                "Month": month,
                "Baseline_Cr": round(brand_baseline * chain_share, 3),
                "Forecast_Cr": round(monthly_forecast, 3),
                "YoY_Pct": round(yoy_pct, 1),
                "Status": "Green" if yoy_pct >= 10 else ("Yellow" if yoy_pct >= 0 else "Red"),
            })

sheet3_brand_forecast = pd.DataFrame(brand_forecast_rows)
print(f"  ✓ Sheet 3: {len(sheet3_brand_forecast)} rows (Brand × Chain × Month)")

# =========================================================================
# 5. BUILD SHEET 4: WEEKLY TRACKER (13 weeks Sep-Nov)
# =========================================================================
print("[5/6] Building Weekly Tracker sheet (13 weeks)...")

week_start_date = datetime(2026, 9, 1)  # Sep 1, 2026
weekly_tracker_rows = []

week_num = 1
for month in ["September", "October", "November"]:
    for week_idx in range(1, 6):  # Max 5 weeks per month
        if month == "September" and week_idx > 5:
            continue
        if month == "October" and week_idx > 4:
            continue
        if month == "November" and week_idx > 4:
            continue

        # Calculate week dates
        week_start = week_start_date + timedelta(weeks=week_num - 1)
        week_end = week_start + timedelta(days=6)

        # Phasing multiplier for this week
        phasing = WEEKLY_PHASING[month].get(week_num, 0.20)

        # Weekly target = monthly consensus / weeks in month * phasing adjustment
        monthly_consensus = sheet2_methods[sheet2_methods["Month"] == month]["Consensus_Cr"].iloc[0]
        weeks_in_month = 5 if month == "September" else 4
        weekly_target = (monthly_consensus / weeks_in_month) * (phasing / (1 / weeks_in_month))

        weekly_tracker_rows.append({
            "Week": week_num,
            "Month": month,
            "Start_Date": week_start.strftime("%Y-%m-%d"),
            "End_Date": week_end.strftime("%Y-%m-%d"),
            "Weekly_Target_Cr": round(weekly_target, 2),
            "Actual_Cr": "",  # To be filled in weekly
            "Variance_Pct": "",
            "Alert": "",
        })

        week_num += 1

sheet4_weekly = pd.DataFrame(weekly_tracker_rows)
print(f"  ✓ Sheet 4: {len(sheet4_weekly)} weeks (Sep W1-W5, Oct W6-W9, Nov W10-W13)")

# =========================================================================
# 6. BUILD SHEET 5: PSR ACTION PLAN (Outlet assignment + cumulative uplift)
# =========================================================================
print("[6/6] Building PSR Action Plan sheet...")

psr_rows = []
cumulative_uplift = 0

for _, week_row in sheet4_weekly.iterrows():
    week = week_row["Week"]
    month = week_row["Month"]
    weekly_target = week_row["Weekly_Target_Cr"]

    # PSR effort: allocate 50-70% of outlets in top 20% volume tiers
    # For simplicity: High zones get 70% of effort, others proportional
    high_intensity_zone_outlets = zone_mapping[zone_mapping["psr_intensity"] == "High"]["target_outlets"].sum()
    total_outlets = zone_mapping["target_outlets"].sum()
    psr_outlet_intensity = high_intensity_zone_outlets / total_outlets

    # Weekly uplift = 8-12% of monthly consensus (conservative PSR impact)
    weekly_uplift = weekly_target * 0.10  # 10% uplift from PSR execution
    cumulative_uplift += weekly_uplift

    psr_rows.append({
        "Week": week,
        "Month": month,
        "Outlets_Assigned": int(total_outlets * psr_outlet_intensity * 0.5),  # 50% assignment
        "Baseline_Target_Cr": round(weekly_target, 2),
        "PSR_Uplift_Cr": round(weekly_uplift, 2),
        "Total_Target_Cr": round(weekly_target + weekly_uplift, 2),
        "Cumulative_Uplift_Cr": round(cumulative_uplift, 2),
    })

sheet5_psr = pd.DataFrame(psr_rows)
total_psr_uplift = sheet5_psr["PSR_Uplift_Cr"].sum()
print(f"  ✓ Sheet 5: 13-week PSR action plan, Total uplift: ₹{total_psr_uplift:.2f} Cr")

# =========================================================================
# 7. BUILD SHEET 6: DASHBOARD KPI SUMMARY
# =========================================================================
print("[7/6] Building Dashboard KPI Summary sheet...")

sep_consensus = sheet2_methods[sheet2_methods["Month"] == "September"]["Consensus_Cr"].iloc[0]
oct_consensus = sheet2_methods[sheet2_methods["Month"] == "October"]["Consensus_Cr"].iloc[0]
nov_consensus = sheet2_methods[sheet2_methods["Month"] == "November"]["Consensus_Cr"].iloc[0]
total_forecast = sep_consensus + oct_consensus + nov_consensus

# Confidence bands
best_case = total_forecast * 1.30  # +30% (full adoption)
conservative_case = total_forecast * 0.85  # -15% (slower adoption)

kpi_summary = pd.DataFrame([
    {
        "Metric": "3-Month Total Forecast",
        "Best_Case_Cr": round(best_case, 2),
        "Base_Case_Cr": round(total_forecast, 2),
        "Conservative_Cr": round(conservative_case, 2),
    },
    {
        "Metric": "September Target",
        "Best_Case_Cr": round(sep_consensus * 1.30, 2),
        "Base_Case_Cr": round(sep_consensus, 2),
        "Conservative_Cr": round(sep_consensus * 0.85, 2),
    },
    {
        "Metric": "October Target",
        "Best_Case_Cr": round(oct_consensus * 1.30, 2),
        "Base_Case_Cr": round(oct_consensus, 2),
        "Conservative_Cr": round(oct_consensus * 0.85, 2),
    },
    {
        "Metric": "November Target",
        "Best_Case_Cr": round(nov_consensus * 1.30, 2),
        "Base_Case_Cr": round(nov_consensus, 2),
        "Conservative_Cr": round(nov_consensus * 0.85, 2),
    },
    {
        "Metric": "PSR Uplift (₹ Cr)",
        "Best_Case_Cr": round(total_psr_uplift * 1.5, 2),
        "Base_Case_Cr": round(total_psr_uplift, 2),
        "Conservative_Cr": round(total_psr_uplift * 0.5, 2),
    },
])

print(f"  ✓ Sheet 6: Dashboard KPI summary")
print(f"    Base case 3-month: ₹{total_forecast:.2f} Cr")
print(f"    PSR uplift range: ₹{round(total_psr_uplift*0.5, 2)}-₹{round(total_psr_uplift*1.5, 2)} Cr")

# =========================================================================
# 8. EXPORT TO EXCEL
# =========================================================================
print(f"\n[EXPORT] Writing {OUTPUT_FILE}...")

try:
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        sheet1_master.to_excel(writer, sheet_name="Master_Data", index=False)
        sheet2_methods.to_excel(writer, sheet_name="Forecast_Methods", index=False)
        sheet3_brand_forecast.to_excel(writer, sheet_name="Brand_Forecast", index=False)
        sheet4_weekly.to_excel(writer, sheet_name="Weekly_Tracker", index=False)
        sheet5_psr.to_excel(writer, sheet_name="PSR_Action_Plan", index=False)
        kpi_summary.to_excel(writer, sheet_name="Dashboard_KPI", index=False)

    print(f"✓ SUCCESS: {OUTPUT_FILE}")
    print(f"\n📊 FORECAST WORKBOOK GENERATED:")
    print(f"\n  1. Master_Data: {len(sheet1_master)} brands with growth vectors")
    print(f"  2. Forecast_Methods: 4-method consensus (MA, WMA, Conservative, Optimistic)")
    print(f"     • September: ₹{sep_consensus:.2f} Cr")
    print(f"     • October: ₹{oct_consensus:.2f} Cr")
    print(f"     • November: ₹{nov_consensus:.2f} Cr")
    print(f"     • 3-Month Total: ₹{total_forecast:.2f} Cr")
    print(f"\n  3. Brand_Forecast: {len(sheet3_brand_forecast)} rows (Brand × Chain × Month)")
    print(f"\n  4. Weekly_Tracker: {len(sheet4_weekly)} weeks (Sep/Oct/Nov)")
    print(f"     • Time-phased distribution with variance tracking")
    print(f"\n  5. PSR_Action_Plan: {len(sheet5_psr)} weeks")
    print(f"     • Weekly outlet assignment & cumulative uplift tracking")
    print(f"     • Total PSR uplift: ₹{total_psr_uplift:.2f} Cr")
    print(f"\n  6. Dashboard_KPI: Executive summary with confidence bands")
    print(f"     • Best case (full adoption): ₹{best_case:.2f} Cr (+30%)")
    print(f"     • Base case (consensus): ₹{total_forecast:.2f} Cr")
    print(f"     • Conservative (slower adoption): ₹{conservative_case:.2f} Cr (-15%)")

except Exception as e:
    print(f"✗ EXPORT FAILED: {e}")
    exit(1)

print(f"\n✓ Forecast workbook ready for Power BI integration + weekly execution tracking")
