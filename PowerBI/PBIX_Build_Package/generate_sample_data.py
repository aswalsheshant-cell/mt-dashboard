#!/usr/bin/env python3
"""
Enhanced sample data generator for Power BI semantic model.

Produces CSV files aligned with operational & financial metrics:
  - Dim_Date (calendar with FY mapping)
  - Dim_Chain (MT chains with account tier)
  - Dim_Geography (zones)
  - Dim_Product (SKUs with base cost)
  - Fact_Sales (actual sales with fulfillment, trade spend, CM2)
  - Fact_Forecast (demand forecast with CM2 values)
  - Fact_Inventory (stock levels by hub & SKU)
  - Param_CM2_Logic (parameter table for CM2 toggle)

All data is repeatable (seed=42) and realistic for Modern Trade context.
"""

import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============================================================================
# Configuration
# ============================================================================

random.seed(42)
np.random.seed(42)

os.makedirs("powerbi_data", exist_ok=True)

# Date range: FY27 (Apr 2026 - Mar 2027)
START_DATE = datetime(2026, 4, 1)
END_DATE = datetime(2026, 9, 30)

# ============================================================================
# 1. Dimension Tables
# ============================================================================

def generate_dim_date():
    """Generate monthly calendar dimension."""
    dates = pd.date_range(start=START_DATE, end=END_DATE, freq="MS")
    records = []

    for d in dates:
        date_key = d.strftime("%Y%m")
        month_name = d.strftime("%B")
        fy_quarter = f"Q{(d.month - 4) // 3 + 1 if d.month >= 4 else (d.month + 8) // 3 + 1}"
        fiscal_year = "FY27" if d.month >= 4 else "FY26"

        records.append({
            "DateKey": date_key,
            "Month_Year": d.strftime("%b %Y"),
            "Month_Name": month_name,
            "FY_Quarter": fy_quarter,
            "Fiscal_Year": fiscal_year,
            "Is_Current_Month": d.strftime("%Y%m") == datetime.now().strftime("%Y%m")
        })

    return pd.DataFrame(records)

def generate_dim_chain():
    """Generate Modern Trade chain master."""
    chains = [
        ("CH01", "C001", "DMart", "Tier 1", "Active"),
        ("CH02", "C002", "Reliance Retail", "Tier 1", "Active"),
        ("CH03", "C003", "Spencer's", "Tier 2", "Active"),
        ("CH04", "C004", "Nature's Basket", "Tier 2", "Active"),
        ("CH05", "C005", "More Retail", "Tier 1", "Active"),
        ("CH06", "C006", "BigBazaar", "Tier 1", "Active"),
        ("CH07", "C007", "Aditya Birla", "Tier 1", "Active"),
        ("CH08", "C008", "Walmart India", "Tier 1", "Active"),
    ]

    return pd.DataFrame([
        {
            "Chain_ID": cid,
            "Chain_Code": code,
            "Chain_Name": name,
            "Account_Tier": tier,
            "Status": status,
            "Region": ["North", "South", "East", "West"][hash(cid) % 4],
            "Warehouse_Hub": f"WH_{cid[:2]}_01"
        }
        for cid, code, name, tier, status in chains
    ])

def generate_dim_geography():
    """Generate zone dimension."""
    zones = [
        {"Zone": "North", "Region_Name": "Northern", "Operating_Region": "North-1"},
        {"Zone": "South", "Region_Name": "Southern", "Operating_Region": "South-1"},
        {"Zone": "East", "Region_Name": "Eastern", "Operating_Region": "East-1"},
        {"Zone": "West", "Region_Name": "Western", "Operating_Region": "West-1"},
    ]
    return pd.DataFrame(zones)

def generate_dim_product():
    """Generate SKU master with base cost."""
    products = [
        ("SKU-101", "Premium Tea 500g", "Brand Alpha", "Beverages", 120.00),
        ("SKU-102", "Classic Coffee 200g", "Brand Alpha", "Beverages", 180.00),
        ("SKU-103", "Instant Coffee 100g", "Brand Alpha", "Beverages", 95.00),
        ("SKU-201", "Dark Chocolate 100g", "Brand Beta", "Confectionery", 65.00),
        ("SKU-202", "Hazelnut Spread 350g", "Brand Beta", "Confectionery", 140.00),
        ("SKU-203", "Milk Chocolate 150g", "Brand Beta", "Confectionery", 85.00),
        ("SKU-301", "Organic Oats 1kg", "Brand Gamma", "Breakfast Foods", 95.00),
        ("SKU-302", "Cornflakes 500g", "Brand Gamma", "Breakfast Foods", 55.00),
        ("SKU-303", "Granola 750g", "Brand Gamma", "Breakfast Foods", 125.00),
        ("SKU-401", "Almond Butter 500g", "Brand Delta", "Nut Butters", 220.00),
        ("SKU-402", "Peanut Butter 400g", "Brand Delta", "Nut Butters", 85.00),
    ]

    return pd.DataFrame([
        {
            "SKU_Code": sku,
            "SKU_Name": name,
            "Brand": brand,
            "Category": category,
            "Base_Unit_Cost": cost,
            "Is_Seasonal": random.choice([True, False]),
            "Status": "Active"
        }
        for sku, name, brand, category, cost in products
    ])

# ============================================================================
# 2. Fact Tables
# ============================================================================

def generate_fact_sales(dim_date, dim_chain, dim_geography, dim_product):
    """Generate monthly sales with fulfillment, trade spend, and CM2 data."""
    print("  Generating Fact_Sales (monthly grain)...")

    records = []
    sale_key = 1

    for _, date_row in dim_date.iterrows():
        date_key = date_row["DateKey"]

        for _, chain in dim_chain.iterrows():
            chain_id = chain["Chain_ID"]
            hub = chain["Warehouse_Hub"]
            tier = chain["Account_Tier"]

            for _, zone in dim_geography.iterrows():
                zone_name = zone["Zone"]

                for _, product in dim_product.iterrows():
                    sku = product["SKU_Code"]
                    base_cost = product["Base_Unit_Cost"]
                    is_seasonal = product["Is_Seasonal"]

                    # Base demand
                    base_qty = np.random.poisson(250)

                    # Apply seasonality if applicable
                    if is_seasonal and int(date_key[4:]) in [4, 12]:  # Apr, Dec
                        base_qty = int(base_qty * 1.3)

                    # Pricing
                    unit_price = base_cost * np.random.uniform(1.45, 1.75)

                    # Fulfillment (Fill Rate 90-98%)
                    fill_rate = np.random.uniform(0.90, 0.98)
                    ordered_qty = base_qty
                    delivered_qty = int(base_qty * fill_rate)
                    actual_qty = delivered_qty

                    # Revenue & costs
                    actual_revenue = actual_qty * unit_price
                    base_cogs = actual_qty * base_cost

                    # Logistics cost (state/zone dependent)
                    logistics_pct = {
                        "North": 0.06,
                        "South": 0.05,
                        "East": 0.08,
                        "West": 0.05
                    }[zone_name]
                    logistics_cost = actual_revenue * logistics_pct

                    # Trade spend (scheme + promo)
                    scheme_adjustment = actual_revenue * np.random.uniform(0.02, 0.04)
                    promo_cost = actual_revenue * np.random.uniform(0.01, 0.03) if random.random() > 0.6 else 0

                    # CM2 (provisional = revenue - base_cogs)
                    cm2_provisional = actual_revenue - base_cogs

                    records.append({
                        "SalesKey": sale_key,
                        "DateKey": date_key,
                        "Chain_ID": chain_id,
                        "Zone": zone_name,
                        "SKU_Code": sku,
                        "Ordered_Qty": ordered_qty,
                        "Delivered_Qty": delivered_qty,
                        "Actual_Qty": actual_qty,
                        "Actual_Revenue": round(actual_revenue, 2),
                        "Base_COGS": round(base_cogs, 2),
                        "Logistics_Cost": round(logistics_cost, 2),
                        "Scheme_Adjustment": round(scheme_adjustment, 2),
                        "Promo_Cost": round(promo_cost, 2),
                        "CM2_Provisional": round(cm2_provisional, 2),
                        "Metric_Type": "Actual"
                    })
                    sale_key += 1

    print(f"    Generated {len(records):,} sales records")
    return pd.DataFrame(records)

def generate_fact_forecast(dim_date, dim_chain, dim_geography, dim_product):
    """Generate monthly demand forecast with CM2 values."""
    print("  Generating Fact_Forecast (monthly grain)...")

    records = []
    forecast_key = 1

    for _, date_row in dim_date.iterrows():
        date_key = date_row["DateKey"]

        for _, chain in dim_chain.iterrows():
            chain_id = chain["Chain_ID"]

            for _, zone in dim_geography.iterrows():
                zone_name = zone["Zone"]

                for _, product in dim_product.iterrows():
                    sku = product["SKU_Code"]
                    base_cost = product["Base_Unit_Cost"]

                    # Forecast with variance
                    forecast_qty = np.random.poisson(270)

                    unit_price = base_cost * np.random.uniform(1.45, 1.75)
                    forecast_revenue = forecast_qty * unit_price

                    # Target ±5% of forecast
                    target_revenue = forecast_revenue * np.random.uniform(0.95, 1.05)

                    # Forecast CM2 (assumed ≈32-35% of revenue)
                    forecast_cm2_value = forecast_revenue * np.random.uniform(0.32, 0.35)

                    # Confidence (higher for near-term, lower for far-out)
                    confidence_level = np.random.uniform(0.65, 0.95)

                    records.append({
                        "ForecastKey": forecast_key,
                        "DateKey": date_key,
                        "Chain_ID": chain_id,
                        "Zone": zone_name,
                        "SKU_Code": sku,
                        "Forecast_Qty": forecast_qty,
                        "Forecast_Revenue": round(forecast_revenue, 2),
                        "Target_Revenue": round(target_revenue, 2),
                        "Forecast_CM2_Value": round(forecast_cm2_value, 2),
                        "Confidence_Level": round(confidence_level, 2),
                        "Forecast_Type": "Rolling"
                    })
                    forecast_key += 1

    print(f"    Generated {len(records):,} forecast records")
    return pd.DataFrame(records)

def generate_fact_inventory(dim_date, dim_chain, dim_product):
    """Generate inventory snapshot by hub & SKU."""
    print("  Generating Fact_Inventory (weekly snapshot)...")

    records = []
    inventory_key = 1

    # Weekly snapshots
    current = START_DATE
    while current <= END_DATE:
        date_key = current.strftime("%Y%m%d")

        for _, chain in dim_chain.iterrows():
            hub = chain["Warehouse_Hub"]

            for _, product in dim_product.iterrows():
                sku = product["SKU_Code"]

                # Closing stock (days of cover: 7-45 days)
                daily_consumption = np.random.poisson(20)
                days_of_cover = np.random.uniform(7, 45)
                closing_stock = int(daily_consumption * days_of_cover)
                opening_stock = int(closing_stock * np.random.uniform(0.95, 1.05))

                records.append({
                    "InventoryKey": inventory_key,
                    "DateKey": date_key,
                    "Hub_ID": hub,
                    "SKU_Code": sku,
                    "Opening_Stock_Units": opening_stock,
                    "Closing_Stock_Units": closing_stock,
                    "Days_of_Cover": round(days_of_cover, 1),
                    "Stock_Level_Status": (
                        "CRITICAL" if days_of_cover < 7
                        else "WARNING" if days_of_cover < 14
                        else "NORMAL" if days_of_cover <= 45
                        else "OVERSTOCK"
                    )
                })
                inventory_key += 1

        current += timedelta(days=7)  # Weekly snapshots

    print(f"    Generated {len(records):,} inventory records")
    return pd.DataFrame(records)

def generate_param_cm2_logic():
    """Generate CM2 parameter table."""
    return pd.DataFrame([
        {
            "Option": "Provisional (Base COGS Only)",
            "OptionID": 1,
            "Description": "CM2 = Revenue - Base_COGS (expense data EXAMPLE only)"
        },
        {
            "Option": "Finance Baseline (COGS + Logistics + Scheme)",
            "OptionID": 2,
            "Description": "CM2 = Revenue - Base_COGS - Logistics_Cost - Scheme_Adjustment (approved by Finance D1)"
        }
    ])

# ============================================================================
# Main Execution
# ============================================================================

def main():
    print("=" * 70)
    print("Generating Enhanced Power BI Sample Data (Modern Trade Dashboard)")
    print("=" * 70)

    # Generate dimensions
    print("\n[1/8] Generating Dim_Date...")
    dim_date = generate_dim_date()
    dim_date.to_csv("powerbi_data/Dim_Date.csv", index=False)
    print(f"  ✓ {len(dim_date):,} rows")

    print("\n[2/8] Generating Dim_Chain...")
    dim_chain = generate_dim_chain()
    dim_chain.to_csv("powerbi_data/Dim_Chain.csv", index=False)
    print(f"  ✓ {len(dim_chain):,} rows")

    print("\n[3/8] Generating Dim_Geography...")
    dim_geography = generate_dim_geography()
    dim_geography.to_csv("powerbi_data/Dim_Geography.csv", index=False)
    print(f"  ✓ {len(dim_geography):,} rows")

    print("\n[4/8] Generating Dim_Product...")
    dim_product = generate_dim_product()
    dim_product.to_csv("powerbi_data/Dim_Product.csv", index=False)
    print(f"  ✓ {len(dim_product):,} rows")

    # Generate facts
    print("\n[5/8] Generating Fact_Sales...")
    fact_sales = generate_fact_sales(dim_date, dim_chain, dim_geography, dim_product)
    fact_sales.to_csv("powerbi_data/Fact_Sales.csv", index=False)

    print("\n[6/8] Generating Fact_Forecast...")
    fact_forecast = generate_fact_forecast(dim_date, dim_chain, dim_geography, dim_product)
    fact_forecast.to_csv("powerbi_data/Fact_Forecast.csv", index=False)

    print("\n[7/8] Generating Fact_Inventory...")
    fact_inventory = generate_fact_inventory(dim_date, dim_chain, dim_product)
    fact_inventory.to_csv("powerbi_data/Fact_Inventory.csv", index=False)

    print("\n[8/8] Generating Param_CM2_Logic...")
    param_cm2 = generate_param_cm2_logic()
    param_cm2.to_csv("powerbi_data/Param_CM2_Logic.csv", index=False)
    print(f"  ✓ {len(param_cm2):,} rows")

    # Summary
    print("\n" + "=" * 70)
    print("✅ All sample data generated successfully!")
    print("=" * 70)
    print(f"\nFiles created in 'powerbi_data/' directory:")

    files = [
        ("Dim_Date.csv", len(dim_date)),
        ("Dim_Chain.csv", len(dim_chain)),
        ("Dim_Geography.csv", len(dim_geography)),
        ("Dim_Product.csv", len(dim_product)),
        ("Fact_Sales.csv", len(fact_sales)),
        ("Fact_Forecast.csv", len(fact_forecast)),
        ("Fact_Inventory.csv", len(fact_inventory)),
        ("Param_CM2_Logic.csv", len(param_cm2)),
    ]

    for filename, rowcount in files:
        filepath = f"powerbi_data/{filename}"
        size_kb = os.path.getsize(filepath) / 1024
        print(f"  • {filename:30s} {rowcount:>8,} rows  ({size_kb:>8.1f} KB)")

    print("\n" + "=" * 70)
    print("Next Steps:")
    print("  1. Load all 8 CSV files into Power BI Desktop")
    print("  2. Set up relationships per 02_POWER_QUERY_TRANSFORMS.md")
    print("  3. Add measures from 03_DAX_MEASURE_LIBRARY.md")
    print("  4. Add operational measures from 07_OPERATIONAL_METRICS.md")
    print("  5. Apply theme from 06_PARAMETERIZED_CM2_MODEL.md")
    print("  6. Build report pages per 04_REPORT_LAYOUT_SPECS.md")
    print("=" * 70)

if __name__ == "__main__":
    main()
