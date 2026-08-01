# -*- coding: utf-8 -*-
"""Live Margin Impact Simulator.

Given a proposed margin change, computes the cascading impact across:
  Old Margin → New Margin → NSV Impact → CM2 Impact →
  Distributor Margin → Retail Margin → Consumer Price Impact

Works with or without volume/NSV drivers. When drivers are absent,
shows percentage-point deltas and marks rupee impacts as 'input required'.
"""
import pandas as pd
from config import DEFAULT_CONFIG, classify_margin_risk


def simulate_margin_change(article_row, proposed_changes, drivers=None, cfg=None):
    """Simulate impact of proposed commercial changes on a single article.

    article_row: dict or Series with current margin fields.
    proposed_changes: dict of {field: new_value} e.g. {"Trade Margin %": 32}.
    drivers: optional dict with Monthly_NSV, Monthly_Units, Annual_NSV.
    Returns a dict with full impact breakdown.
    """
    cfg = cfg or DEFAULT_CONFIG

    comps = [
        "Trade Margin %", "TOT %", "Backend %", "Frontend %",
        "Visibility %", "Listing Support %", "Rental Support %",
        "Display %", "Scheme %", "Special Commercial %",
        "Additional Discount %", "Distributor Margin %",
    ]
    deductions = ["Consumer Offer %", "Cash Discount %"]

    def _n(v):
        try:
            return float(str(v).replace("%", "").replace(",", "").strip()) if v not in (None, "", "nan") else 0.0
        except (ValueError, TypeError):
            return 0.0

    old_values = {}
    new_values = {}
    for c in comps + deductions:
        old_values[c] = _n(article_row.get(c))
        new_values[c] = _n(proposed_changes.get(c, article_row.get(c)))

    old_fem = sum(old_values[c] for c in comps) - sum(old_values[c] for c in deductions)
    new_fem = sum(new_values[c] for c in comps) - sum(new_values[c] for c in deductions)
    delta_pp = round(new_fem - old_fem, 2)

    mrp = _n(article_row.get("MRP"))
    gst = _n(article_row.get("GST %"))
    old_dist_margin = old_values.get("Distributor Margin %", 0)
    new_dist_margin = new_values.get("Distributor Margin %", 0)

    risk_tier = classify_margin_risk(delta_pp, cfg)

    result = {
        "Chain": article_row.get("Chain", ""),
        "Brand": article_row.get("Brand", ""),
        "Article": article_row.get("Article", ""),
        "EAN": article_row.get("EAN", ""),
        "MRP": mrp,
        "GST %": gst,
        "Old Final Effective Margin %": round(old_fem, 2),
        "New Final Effective Margin %": round(new_fem, 2),
        "Margin Delta (pp)": delta_pp,
        "Risk Tier": risk_tier,
        "Old Distributor Margin %": old_dist_margin,
        "New Distributor Margin %": new_dist_margin,
        "Distributor Margin Delta (pp)": round(new_dist_margin - old_dist_margin, 2),
    }

    # Component-level changes
    changed_fields = []
    for c in comps + deductions:
        if old_values[c] != new_values[c]:
            changed_fields.append({
                "Field": c,
                "Old": old_values[c],
                "New": new_values[c],
                "Delta": round(new_values[c] - old_values[c], 2),
            })
    result["Changed Fields"] = changed_fields

    # Retail margin estimate (MRP-based)
    if mrp > 0:
        base_price = mrp / (1 + gst / 100) if gst > 0 else mrp
        old_nsv_per_unit = base_price * (1 - old_fem / 100)
        new_nsv_per_unit = base_price * (1 - new_fem / 100)
        result["Old NSV/Unit (est)"] = round(old_nsv_per_unit, 2)
        result["New NSV/Unit (est)"] = round(new_nsv_per_unit, 2)
        result["NSV/Unit Delta"] = round(new_nsv_per_unit - old_nsv_per_unit, 2)
        result["Old Retail Margin/Unit (est)"] = round(mrp - base_price + base_price * old_fem / 100, 2)
        result["New Retail Margin/Unit (est)"] = round(mrp - base_price + base_price * new_fem / 100, 2)
        result["Consumer Price Impact"] = "No change (MRP unchanged)"
    else:
        result["Old NSV/Unit (est)"] = "requires MRP"
        result["New NSV/Unit (est)"] = "requires MRP"
        result["Consumer Price Impact"] = "requires MRP"

    # Volume-driven impacts (if drivers provided)
    if drivers:
        monthly_nsv = _n(drivers.get("Monthly_NSV"))
        monthly_units = _n(drivers.get("Monthly_Units"))
        annual_nsv = _n(drivers.get("Annual_NSV", monthly_nsv * 12 if monthly_nsv else 0))

        if monthly_nsv > 0:
            cm2_monthly = round(monthly_nsv * delta_pp / 100, 2)
            cm2_annual = round(annual_nsv * delta_pp / 100, 2)
            result.update({
                "Monthly NSV (input)": monthly_nsv,
                "Annual NSV (input)": annual_nsv,
                "CM2 Impact (INR/mo)": cm2_monthly,
                "CM2 Impact (INR/yr)": cm2_annual,
                "Gross Margin Impact (INR/mo)": cm2_monthly,
                "NSV Impact (INR/mo)": 0.0,
            })
        else:
            _mark_input_required(result)

        if monthly_units > 0:
            result["Monthly Units (input)"] = monthly_units
            if mrp > 0 and gst >= 0:
                base = mrp / (1 + gst / 100)
                result["Primary Value Impact (INR/mo)"] = round(
                    monthly_units * base * delta_pp / 100, 2)
        else:
            result.setdefault("Primary Value Impact (INR/mo)", "requires units input")
    else:
        _mark_input_required(result)

    # Approval requirement
    if risk_tier == "NORMAL":
        result["Approval Required"] = "Standard review"
    elif risk_tier == "WARNING":
        result["Approval Required"] = "Checker approval required"
    elif risk_tier == "HIGH_RISK":
        result["Approval Required"] = "Commercial approval required"
    else:
        result["Approval Required"] = "Finance + Commercial dual approval required"

    return result


def _mark_input_required(rec):
    for k in ("CM2 Impact (INR/mo)", "CM2 Impact (INR/yr)",
              "Gross Margin Impact (INR/mo)", "NSV Impact (INR/mo)",
              "Primary Value Impact (INR/mo)"):
        rec.setdefault(k, "requires NSV/volume input")
    rec.setdefault("Monthly NSV (input)", "")
    rec.setdefault("Annual NSV (input)", "")


def simulate_batch(current_df, proposed_changes_df, drivers_df=None, cfg=None):
    """Simulate impacts for multiple articles.

    current_df: current repository view (from repo.current()).
    proposed_changes_df: DataFrame with Article_Key + changed fields.
    drivers_df: optional DataFrame with Article_Key, Monthly_NSV, Monthly_Units.
    Returns DataFrame of simulation results.
    """
    cfg = cfg or DEFAULT_CONFIG
    driver_map = {}
    if drivers_df is not None and not drivers_df.empty:
        for _, d in drivers_df.iterrows():
            key = d.get("Article_Key") or d.get("EAN") or ""
            driver_map[key] = d.to_dict()

    results = []
    for _, proposed in proposed_changes_df.iterrows():
        ak = proposed.get("Article_Key", "")
        match = current_df[current_df["Article_Key"] == ak]
        if match.empty:
            ean = proposed.get("EAN", "")
            if ean:
                match = current_df[current_df["EAN"].astype(str) == str(ean)]
        if match.empty:
            continue
        article = match.iloc[0].to_dict()
        changes = {k: v for k, v in proposed.items()
                   if k in ("Trade Margin %", "TOT %", "Backend %", "Frontend %",
                            "Visibility %", "Listing Support %", "Rental Support %",
                            "Display %", "Scheme %", "Special Commercial %",
                            "Additional Discount %", "Distributor Margin %",
                            "Consumer Offer %", "Cash Discount %", "GST %")
                   and pd.notna(v) and str(v).strip() != ""}
        drivers = driver_map.get(ak) or driver_map.get(article.get("EAN", ""))
        results.append(simulate_margin_change(article, changes, drivers, cfg))

    return pd.DataFrame(results) if results else pd.DataFrame()


def scenario_compare(article_row, scenarios, drivers=None, cfg=None):
    """Compare multiple what-if scenarios side by side.

    scenarios: list of (name, {field: value}) tuples.
    Returns a list of (name, result_dict) for comparison.
    """
    comparisons = []
    for name, changes in scenarios:
        result = simulate_margin_change(article_row, changes, drivers, cfg)
        result["Scenario"] = name
        comparisons.append(result)
    return comparisons
