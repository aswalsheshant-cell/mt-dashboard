# -*- coding: utf-8 -*-
"""Forecast integration — connects margin changes to demand planning.

When a margin changes, estimates the downstream impact on:
  Sales lift → Demand increase → Inventory requirement →
  Primary requirement → Secondary impact

This module provides the hooks and estimation framework. Actual
elasticity coefficients and planning parameters must be supplied
by the business/demand planning team.
"""
import pandas as pd
from config import DEFAULT_CONFIG


# Default elasticity assumptions (business must review and approve)
DEFAULT_ELASTICITY = {
    "price_elasticity": -1.2,
    "margin_pass_through_to_price": 0.0,
    "promotion_lift_factor": 1.15,
    "inventory_weeks_cover": 4,
    "primary_lead_weeks": 2,
    "secondary_fill_rate": 0.95,
}


def estimate_demand_impact(margin_change_pp, current_monthly_units,
                           current_monthly_nsv, mrp, gst_pct=18,
                           elasticity=None):
    """Estimate demand planning impact from a margin change.

    margin_change_pp: change in Final Effective Margin (percentage points).
    current_monthly_units: current average monthly units.
    current_monthly_nsv: current monthly NSV (INR).
    mrp: MRP of the article.
    elasticity: dict overriding DEFAULT_ELASTICITY.

    Returns a dict with estimated impacts.
    """
    e = {**DEFAULT_ELASTICITY, **(elasticity or {})}

    base_price = mrp / (1 + gst_pct / 100) if gst_pct > 0 else mrp
    price_change_pct = margin_change_pp * e["margin_pass_through_to_price"]

    # If margin increase is passed to consumer as price reduction
    if price_change_pct != 0:
        volume_change_pct = price_change_pct * e["price_elasticity"]
    else:
        volume_change_pct = 0.0

    new_monthly_units = current_monthly_units * (1 + volume_change_pct / 100)
    units_delta = new_monthly_units - current_monthly_units

    new_nsv_per_unit = base_price * (1 - (margin_change_pp / 100))
    nsv_impact_per_unit = -base_price * margin_change_pp / 100

    new_monthly_nsv = current_monthly_nsv + (current_monthly_nsv * margin_change_pp / 100)

    inventory_units = new_monthly_units * e["inventory_weeks_cover"] / 4.33
    primary_units = new_monthly_units * (1 + e["primary_lead_weeks"] / 4.33)
    secondary_units = primary_units * e["secondary_fill_rate"]

    return {
        "Margin Change (pp)": margin_change_pp,
        "Price Change to Consumer (%)": round(price_change_pct, 2),
        "Volume Change (%)": round(volume_change_pct, 2),
        "Current Monthly Units": current_monthly_units,
        "Estimated New Monthly Units": round(new_monthly_units, 0),
        "Units Delta": round(units_delta, 0),
        "Current Monthly NSV (INR)": current_monthly_nsv,
        "Estimated New Monthly NSV (INR)": round(new_monthly_nsv, 2),
        "NSV Impact/Unit (INR)": round(nsv_impact_per_unit, 2),
        "CM2 Impact (INR/mo)": round(current_monthly_nsv * margin_change_pp / 100, 2),
        "Inventory Requirement (units)": round(inventory_units, 0),
        "Primary Requirement (units/mo)": round(primary_units, 0),
        "Secondary Dispatch (units/mo)": round(secondary_units, 0),
        "Assumptions": {
            "price_elasticity": e["price_elasticity"],
            "margin_pass_through": e["margin_pass_through_to_price"],
            "inventory_weeks_cover": e["inventory_weeks_cover"],
            "primary_lead_weeks": e["primary_lead_weeks"],
        },
    }


def build_planning_feed(repo, changelog, drivers_df, elasticity=None):
    """Build a demand planning feed from margin changes.

    repo: MarginRepository.
    changelog: DataFrame from import_frame.
    drivers_df: DataFrame with Article_Key/EAN, Monthly_Units, Monthly_NSV.
    Returns a DataFrame with planning estimates per changed article.
    """
    if changelog is None or changelog.empty:
        return pd.DataFrame()

    margin_fields = {"Final Effective Margin %", "Trade Margin %"}
    changes = changelog[changelog["Field"].isin(margin_fields)].copy()
    if changes.empty:
        return pd.DataFrame()

    driver_map = {}
    if drivers_df is not None and not drivers_df.empty:
        for _, d in drivers_df.iterrows():
            key = d.get("Article_Key") or d.get("EAN", "")
            driver_map[key] = d.to_dict()

    cur = repo.current(include_held=False)
    results = []

    for _, chg in changes.iterrows():
        ak = chg.get("Article_Key", "")
        delta = pd.to_numeric(chg.get("Difference"), errors="coerce")
        if pd.isna(delta):
            continue

        article = cur[cur["Article_Key"] == ak]
        if article.empty:
            continue
        art = article.iloc[0]

        drivers = driver_map.get(ak) or driver_map.get(str(art.get("EAN", "")))
        if not drivers:
            results.append({
                "Chain": chg.get("Chain"), "Article": chg.get("Article"),
                "EAN": chg.get("EAN"), "Field": chg.get("Field"),
                "Delta (pp)": delta,
                "Planning Impact": "requires volume/NSV drivers",
            })
            continue

        mrp = pd.to_numeric(art.get("MRP"), errors="coerce") or 0
        gst = pd.to_numeric(art.get("GST %"), errors="coerce") or 18

        impact = estimate_demand_impact(
            delta,
            float(drivers.get("Monthly_Units", 0)),
            float(drivers.get("Monthly_NSV", 0)),
            mrp, gst, elasticity)

        results.append({
            "Chain": chg.get("Chain"),
            "Brand": art.get("Brand"),
            "Article": chg.get("Article"),
            "EAN": chg.get("EAN"),
            "Field": chg.get("Field"),
            "Old Value": chg.get("Old Value"),
            "New Value": chg.get("New Value"),
            **{k: v for k, v in impact.items() if k != "Assumptions"},
        })

    return pd.DataFrame(results) if results else pd.DataFrame()


def generate_forecast_override(repo, output_path=None):
    """Generate a forecast override file from current approved margins.

    This can feed directly into the demand forecasting model as the
    margin assumption input.
    """
    cur = repo.current(include_held=False)
    if cur.empty:
        return pd.DataFrame()

    _n = lambda c: pd.to_numeric(cur.get(c), errors="coerce")

    feed = pd.DataFrame({
        "Chain": cur["Chain"],
        "Brand": cur.get("Brand", ""),
        "Category": cur.get("Category", ""),
        "Article": cur["Article"],
        "EAN": cur["EAN"],
        "Pack_Size": cur.get("Pack Size", ""),
        "MRP": _n("MRP"),
        "Trade_Margin_Pct": _n("Trade Margin %"),
        "Final_Effective_Margin_Pct": _n("Final Effective Margin %"),
        "GST_Pct": _n("GST %"),
        "Effective_From": cur.get("Effective From", ""),
        "Version": cur.get("Version Number", ""),
        "Source": "Margin_Repository_v" + DEFAULT_CONFIG.get("schema_version", "1.0"),
    })

    if output_path:
        feed.to_csv(output_path, index=False)
    return feed
