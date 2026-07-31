# -*- coding: utf-8 -*-
"""Margin-change impact analysis.

Impact math is transparent and driver-based. Absolute rupee impacts (CM2, NSV,
Gross Margin, distributor profit) require a volume / NSV driver that the margin
repository does NOT own. When a driver is supplied (optional `drivers` frame
keyed by Article_Key with Monthly_NSV / Monthly_Units), absolute impacts are
computed; otherwise only the margin delta (in percentage points) is reported
and the rupee columns are marked 'requires NSV/volume input' - never guessed.
"""
import pandas as pd
from config import DEFAULT_CONFIG, classify_margin_risk

# margin-point delta above/below which an article is High Risk (default)
HIGH_RISK_PP = DEFAULT_CONFIG["risk_thresholds"]["warning_max_pp"]


def impact_from_changelog(changelog, drivers=None, cfg=None):
    """changelog: rows with Field/Old Value/New Value/Difference (from repo).
    drivers: optional DataFrame [Article_Key, Monthly_NSV, Monthly_Units].
    Returns an impact table (one row per margin-affecting change)."""
    if changelog is None or changelog.empty:
        return pd.DataFrame()
    margin_fields = {"Final Effective Margin %", "Trade Margin %", "TOT %"}
    cl = changelog[changelog["Field"].isin(margin_fields)].copy()
    if cl.empty:
        return pd.DataFrame()
    cl["Delta_pp"] = pd.to_numeric(cl["Difference"], errors="coerce")

    dmap = {}
    if drivers is not None and not drivers.empty:
        for _, d in drivers.iterrows():
            dmap[d["Article_Key"]] = d

    out = []
    for _, r in cl.iterrows():
        d = dmap.get(r["Article_Key"])
        delta = r["Delta_pp"]
        rec = {
            "Article_Key": r["Article_Key"], "Chain": r.get("Chain"),
            "Brand": r.get("Brand"), "Article": r.get("Article"), "EAN": r.get("EAN"),
            "Field": r["Field"], "Old %": r["Old Value"], "New %": r["New Value"],
            "Margin Delta (pp)": delta, "Effective From": r.get("Effective From"),
        }
        if d is not None and pd.notna(delta):
            nsv = pd.to_numeric(pd.Series([d.get("Monthly_NSV")]), errors="coerce").iloc[0]
            if pd.notna(nsv):
                cm2_impact = round(nsv * delta / 100.0, 2)
                rec.update({
                    "Monthly_NSV (input)": nsv,
                    "CM2 Impact (INR/mo)": cm2_impact,
                    "Gross Margin Impact (INR/mo)": cm2_impact,
                    "NSV Impact (INR/mo)": 0.0,  # margin change alone doesn't move NSV
                    "Distributor Profit Impact": "review - depends on dist margin change",
                })
            else:
                _mark_needs_input(rec)
        else:
            _mark_needs_input(rec)
        risk_tier = classify_margin_risk(delta, cfg) if pd.notna(delta) else "NORMAL"
        rec["Risk Tier"] = risk_tier
        rec["High Risk"] = "YES" if risk_tier in ("HIGH_RISK", "BLOCKED") else "NO"
        out.append(rec)
    df = pd.DataFrame(out)
    return df.sort_values("Margin Delta (pp)", key=lambda s: s.abs(), ascending=False)


def _mark_needs_input(rec):
    for k in ("CM2 Impact (INR/mo)", "Gross Margin Impact (INR/mo)",
              "NSV Impact (INR/mo)", "Distributor Profit Impact"):
        rec[k] = "requires NSV/volume input"
    rec["Monthly_NSV (input)"] = ""
