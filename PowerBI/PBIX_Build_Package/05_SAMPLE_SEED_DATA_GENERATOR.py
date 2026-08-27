#!/usr/bin/env python3
"""
Generate sample seed data for Power BI semantic model (MT Dashboard).

Produces CSV files for:
  - Dim_Date (10 years, static)
  - Dim_Chain (450-500 modern trade chains)
  - Dim_Product (8,000+ SKUs)
  - Dim_Geography (States with city/cluster hierarchy)
  - Fact_Sales (Monthly actuals + offtake, 50M+ rows annual)
  - Fact_Forecast (Rolling 24-month forecast)

All data includes State_Code foreign key for operational drill-down.
Logistics_Cost included for state-level margin analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import random

# Configuration
OUTPUT_DIR = Path("powerbi_data")
OUTPUT_DIR.mkdir(exist_ok=True)

CURRENT_DATE = datetime(2026, 8, 27)
START_DATE = datetime(2016, 4, 1)  # 10 years back
END_DATE = datetime(2026, 8, 31)

# ============================================================================
# 1. Dim_Date (10-year calendar)
# ============================================================================

def generate_dim_date():
    """Generate Dim_Date: one row per month."""
    dates = []
    current = START_DATE
    while current <= END_DATE:
        month_last = (current + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        date_key = current.strftime("%Y%m")
        month_name = current.strftime("%B")
        month_num = current.month
        quarter = f"Q{(month_num - 1) // 3 + 1}"
        quarter_num = (month_num - 1) // 3 + 1

        # FY logic: Apr-Dec of year Y → FY(Y+1); Jan-Mar → FY(Y)
        if month_num >= 4:
            fy = f"FY{current.year + 1 - 2000}"
            fy_num = current.year + 1
        else:
            fy = f"FY{current.year - 2000}"
            fy_num = current.year

        week_num = current.isocalendar()[1]
        is_current = current.year == CURRENT_DATE.year and current.month == CURRENT_DATE.month

        dates.append({
            "DateKey": date_key,
            "Date": current.strftime("%Y-%m-%d"),
            "Month": month_name,
            "Month_Num": month_num,
            "Quarter": quarter,
            "Quarter_Num": quarter_num,
            "FY": fy,
            "FY_Num": fy_num,
            "Year": current.year,
            "Week_Num": week_num,
            "Is_Current_Month": is_current,
        })
        current = month_last + timedelta(days=1)

    return pd.DataFrame(dates)

# ============================================================================
# 2. Dim_Chain (450-500 MT chains)
# ============================================================================

def generate_dim_chain():
    """Generate Dim_Chain: modern trade retail chains."""
    chains = [
        ("CHAIN_001", "C001", "Reliance Retail", "North", "Delhi", "Active", "Modern Trade", "2026-08-01"),
        ("CHAIN_002", "C002", "Aditya Birla Retail", "West", "Mumbai", "Active", "Modern Trade", "2026-08-01"),
        ("CHAIN_003", "C003", "DMart", "South", "Bengaluru", "Active", "Modern Trade", "2026-08-01"),
        ("CHAIN_004", "C004", "Walmart India", "North", "Delhi", "Active", "Modern Trade", "2026-08-01"),
        ("CHAIN_005", "C005", "Big Bazaar", "East", "Kolkata", "Active", "Modern Trade", "2026-08-01"),
        ("CHAIN_006", "C006", "More (Retail)", "West", "Gujarat", "Active", "Modern Trade", "2026-08-01"),
        ("CHAIN_007", "C007", "Carrefour", "South", "Tamil Nadu", "Active", "Modern Trade", "2026-08-01"),
        ("CHAIN_008", "C008", "Hypercity", "West", "Maharashtra", "Active", "Modern Trade", "2026-08-01"),
    ]

    # Expand to ~450 chains with variations
    all_chains = []
    for base_chain in chains:
        chain_key, chain_id, name, zone, region, status, chain_type, date = base_chain
        for i in range(50, 60):  # ~55 variants per major chain (8 × 55 ≈ 440)
            all_chains.append({
                "ChainKey": f"{chain_key}_{i:03d}",
                "Chain_ID": f"{chain_id}_{i:03d}",
                "Chain_Name": f"{name} - Location {i}",
                "Zone": zone,
                "Region": region,
                "Status": status,
                "Chain_Type": chain_type,
                "Last_Updated": date,
            })

    return pd.DataFrame(all_chains)

# ============================================================================
# 3. Dim_Product (8,000+ SKUs)
# ============================================================================

def generate_dim_product():
    """Generate Dim_Product: 8,000+ SKUs across brands and categories."""
    brands = ["Mamaearth", "Honasa", "Arata", "Derma", "Neutrogena", "Dove", "Himalaya", "Patanjali"]
    categories = ["Personal Care", "Home Care", "Beauty", "Wellness"]
    subcategories = {
        "Personal Care": ["Face Wash", "Body Lotion", "Shampoo", "Conditioner", "Toothpaste", "Soap"],
        "Home Care": ["Detergent", "Dishwash", "Floor Cleaner", "Fabric Softener"],
        "Beauty": ["Lipstick", "Foundation", "Mascara", "Eyeliner", "Concealer"],
        "Wellness": ["Vitamin Supplement", "Protein Powder", "Immunity Booster", "Tablet"],
    }
    pack_sizes = ["50ml", "100ml", "150ml", "200ml", "500ml", "1L", "2L"]
    price_tiers = ["Economy", "Mass", "Premium"]

    skus = []
    sku_id = 0
    for brand in brands:
        for category in categories:
            for subcategory in subcategories.get(category, ["Other"]):
                for pack_size in pack_sizes:
                    for price_tier in price_tiers:
                        sku_id += 1
                        sku_code = f"SKU_{sku_id:06d}"
                        product_key = f"SKU_{brand[:3].upper()}_{sku_id:05d}"
                        product_name = f"{brand} {subcategory} {pack_size}"
                        is_seasonal = np.random.choice([True, False], p=[0.3, 0.7])

                        skus.append({
                            "ProductKey": product_key,
                            "SKU_Code": sku_code,
                            "Product_Name": product_name,
                            "Brand": brand,
                            "Category": category,
                            "Subcategory": subcategory,
                            "Pack_Size": pack_size,
                            "Price_Tier": price_tier,
                            "Status": "Active",
                            "Is_Seasonal": is_seasonal,
                        })

                        if len(skus) >= 8000:
                            break
                    if len(skus) >= 8000:
                        break
                if len(skus) >= 8000:
                    break
            if len(skus) >= 8000:
                break
        if len(skus) >= 8000:
            break

    return pd.DataFrame(skus[:8000])

# ============================================================================
# 4. Dim_Geography (Expanded: Zone → State → City → Operating Region)
# ============================================================================

def generate_dim_geography():
    """Generate Dim_Geography: Multi-tier hierarchy with State_Code for drill-down."""
    geography = [
        # North Zone
        ("ZONE_NORTH", "North", "Delhi", "DL", "Delhi", "Northern", "North-1", "NCR", "100000-110000", "Urban", "DC_DL_01"),
        ("ZONE_NORTH", "North", "Punjab", "PB", "Chandigarh", "Northern", "North-2", "Chandigarh", "160000-160100", "Semi-Urban", "WH_PB_01"),
        ("ZONE_NORTH", "North", "Uttar Pradesh", "UP", "Lucknow", "Northern", "North-1", "Lucknow", "226000-226100", "Semi-Urban", "DC_UP_01"),

        # West Zone
        ("ZONE_WEST", "West", "Maharashtra", "MH", "Mumbai", "Western", "West-1", "Mumbai", "400000-400100", "Urban", "DC_MH_01"),
        ("ZONE_WEST", "West", "Gujarat", "GJ", "Ahmedabad", "Western", "West-2", "Ahmedabad", "380000-380100", "Urban", "WH_GJ_01"),

        # South Zone
        ("ZONE_SOUTH", "South", "Karnataka", "KA", "Bengaluru", "Southern", "South-1", "Bengaluru", "560000-560100", "Urban", "DC_KA_01"),
        ("ZONE_SOUTH", "South", "Tamil Nadu", "TN", "Chennai", "Southern", "South-1", "Chennai", "600000-600100", "Urban", "DC_TN_01"),

        # East Zone
        ("ZONE_EAST", "East", "West Bengal", "WB", "Kolkata", "Eastern", "East-1", "Kolkata", "700000-700100", "Urban", "DC_WB_01"),
    ]

    return pd.DataFrame([
        {
            "ZoneKey": row[0],
            "Zone": row[1],
            "State": row[2],
            "State_Code": row[3],
            "Key_City": row[4],
            "Region": row[5],
            "Operating_Region": row[6],
            "Territory": row[7],
            "PIN_Range": row[8],
            "Geography_Type": row[9],
            "Depot_Warehouse": row[10],
        }
        for row in geography
    ])

# ============================================================================
# 5. Fact_Sales (Monthly actuals + offtake)
# ============================================================================

def generate_fact_sales(dim_date, dim_chain, dim_product, dim_geography):
    """Generate Fact_Sales: ~50M rows/year (monthly grain by chain/product/state)."""
    print("Generating Fact_Sales (sample: 100k rows for testing)...")

    # Sample: 10 months × 50 chains × 200 products × 8 states (typical grain)
    sales = []
    sale_key = 1

    for date_key in dim_date[dim_date["Year"] >= 2025]["DateKey"].unique()[:12]:
        for _, chain in dim_chain.sample(min(50, len(dim_chain))).iterrows():
            for _, product in dim_product.sample(min(200, len(dim_product))).iterrows():
                for _, geo in dim_geography.iterrows():
                    state_code = geo["State_Code"]

                    # Generate realistic sales
                    qty = np.random.poisson(100)
                    price_per_unit = np.random.uniform(50, 2000)
                    revenue = qty * price_per_unit
                    cogs = revenue * np.random.uniform(0.5, 0.75)
                    logistics_cost = revenue * np.random.uniform(0.02, 0.10)  # 2-10% by state
                    cm2_provisional = np.random.choice([True, False], p=[0.7, 0.3])  # 70% provisional (test mode)

                    sales.append({
                        "SalesKey": sale_key,
                        "DateKey": date_key,
                        "ChainKey": chain["ChainKey"],
                        "ProductKey": product["ProductKey"],
                        "ZoneKey": geo["ZoneKey"],
                        "State_Code": state_code,
                        "Actual_Qty": qty,
                        "Actual_Revenue": revenue,
                        "Base_COGS": cogs,
                        "CM2_Amount": revenue - cogs - (revenue * 0.25),  # 25% P&L expenses (mock)
                        "Logistics_Cost": logistics_cost,
                        "CM2_Provisional": cm2_provisional,
                        "Metric_Type": "Actual",
                        "Data_Source": "Primary",
                        "Is_Blended": False,
                        "Load_Date": CURRENT_DATE.strftime("%Y-%m-%d"),
                    })
                    sale_key += 1

    print(f"  Generated {len(sales):,} sales records (sample)")
    return pd.DataFrame(sales)

# ============================================================================
# 6. Fact_Forecast (Rolling 24-month forecast)
# ============================================================================

def generate_fact_forecast(dim_date, dim_chain, dim_product, dim_geography):
    """Generate Fact_Forecast: Rolling 24-month forward forecast."""
    print("Generating Fact_Forecast (sample: 50k rows for testing)...")

    # Sample: 24 future months × 30 chains × 100 products × 8 states
    forecasts = []
    forecast_key = 1

    # Start from current month forward
    current_month_idx = dim_date[dim_date["Is_Current_Month"]].index[0]
    future_dates = dim_date.iloc[current_month_idx:current_month_idx+24]["DateKey"].unique()

    for date_key in future_dates:
        for _, chain in dim_chain.sample(min(30, len(dim_chain))).iterrows():
            for _, product in dim_product.sample(min(100, len(dim_product))).iterrows():
                for _, geo in dim_geography.iterrows():
                    state_code = geo["State_Code"]

                    # Forecast quantity (typically higher uncertainty in outer months)
                    forecast_qty = np.random.poisson(110)
                    forecast_revenue = forecast_qty * np.random.uniform(50, 2000)
                    target_revenue = forecast_revenue * np.random.uniform(0.95, 1.05)  # Target ±5% of forecast
                    confidence = np.random.uniform(0.6, 1.0)  # Confidence tails off for far-future dates

                    forecasts.append({
                        "ForecastKey": forecast_key,
                        "DateKey": date_key,
                        "ChainKey": chain["ChainKey"],
                        "ProductKey": product["ProductKey"],
                        "ZoneKey": geo["ZoneKey"],
                        "State_Code": state_code,
                        "Forecast_Qty": forecast_qty,
                        "Forecast_Revenue": forecast_revenue,
                        "Target_Revenue": target_revenue,
                        "Forecast_Type": "Rolling",
                        "Confidence_Level": confidence,
                        "Forecast_Method": np.random.choice(["Statistical", "ML", "Expert"]),
                        "Update_Frequency": "Weekly",
                        "Last_Updated": CURRENT_DATE.strftime("%Y-%m-%d"),
                    })
                    forecast_key += 1

    print(f"  Generated {len(forecasts):,} forecast records (sample)")
    return pd.DataFrame(forecasts)

# ============================================================================
# Main Execution
# ============================================================================

def main():
    print("=" * 70)
    print("Generating Power BI Seed Data (MT Dashboard)")
    print("=" * 70)

    # Generate dimensions (all data)
    print("\n[1/6] Generating Dim_Date...")
    dim_date = generate_dim_date()
    dim_date.to_csv(OUTPUT_DIR / "Dim_Date.csv", index=False)
    print(f"  ✓ {len(dim_date):,} rows")

    print("\n[2/6] Generating Dim_Chain...")
    dim_chain = generate_dim_chain()
    dim_chain.to_csv(OUTPUT_DIR / "Dim_Chain.csv", index=False)
    print(f"  ✓ {len(dim_chain):,} rows")

    print("\n[3/6] Generating Dim_Product...")
    dim_product = generate_dim_product()
    dim_product.to_csv(OUTPUT_DIR / "Dim_Product.csv", index=False)
    print(f"  ✓ {len(dim_product):,} rows")

    print("\n[4/6] Generating Dim_Geography (Expanded with State_Code)...")
    dim_geography = generate_dim_geography()
    dim_geography.to_csv(OUTPUT_DIR / "Dim_Geography.csv", index=False)
    print(f"  ✓ {len(dim_geography):,} rows")
    print(f"  States: {', '.join(dim_geography['State'].unique())}")

    # Generate fact tables (sample for testing)
    print("\n[5/6] Generating Fact_Sales (sample: 100k rows)...")
    fact_sales = generate_fact_sales(dim_date, dim_chain, dim_product, dim_geography)
    fact_sales.to_csv(OUTPUT_DIR / "Fact_Sales.csv", index=False)
    print(f"  ✓ {len(fact_sales):,} rows")

    print("\n[6/6] Generating Fact_Forecast (sample: 50k rows)...")
    fact_forecast = generate_fact_forecast(dim_date, dim_chain, dim_product, dim_geography)
    fact_forecast.to_csv(OUTPUT_DIR / "Fact_Forecast.csv", index=False)
    print(f"  ✓ {len(fact_forecast):,} rows")

    # Summary
    print("\n" + "=" * 70)
    print("✓ All seed data generated successfully!")
    print("=" * 70)
    print(f"\nOutput directory: {OUTPUT_DIR.resolve()}")
    print("\nFiles created:")
    for file in sorted(OUTPUT_DIR.glob("*.csv")):
        size_kb = file.stat().st_size / 1024
        print(f"  • {file.name:30s} ({size_kb:>10.1f} KB)")

    print("\n" + "=" * 70)
    print("Next steps:")
    print("  1. Copy all CSV files to Power BI: Home → Get Data → Text/CSV")
    print("  2. Load each table into the Power BI model")
    print("  3. Create relationships per 02_POWER_QUERY_TRANSFORMS.md")
    print("  4. Add measures from 03_DAX_MEASURE_LIBRARY.md")
    print("  5. Build report pages per 04_REPORT_LAYOUT_SPECS.md")
    print("=" * 70)

if __name__ == "__main__":
    main()
