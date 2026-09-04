#!/usr/bin/env python3
"""
Automated Agent Sentiments & Executive Insights Engine

Generates qualitative, actionable commentary across Modern Trade performance dimensions
using the Situation-Complication-Resolution (SCR) framework with severity levels.

Inputs: Extracted CSV data contracts from PowerBI/ExportData/
Outputs: JSON insights for dashboard and Power BI

Dimensions:
1. Revenue & Offtake Velocity — growth, acceleration, forecast variance
2. Channel Inventory & Pipeline Health — Primary vs Offtake gap, conversion %
3. Profitability & Trade Spend — CM2 value, margin erosion, TOT% efficiency
4. Distribution & Store Universe — coverage %, productivity per store

Exit codes:
    0 = Insights generated successfully
    1 = Missing required CSV files
    2 = Data validation failed (empty or malformed)
    3 = Computation/logic error
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def log(level: str, msg: str):
    """Print timestamped log message."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sym = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "DEBUG": "→"}[level]
    print(f"[{ts}] {sym} {msg}")


def load_csv(csv_path: Path) -> pd.DataFrame | None:
    """Load CSV safely; return None if missing."""
    if not csv_path.exists():
        log("WARN", f"Missing: {csv_path.name}")
        return None
    try:
        df = pd.read_csv(csv_path)
        log("DEBUG", f"Loaded {csv_path.name}: {len(df)} rows")
        return df
    except Exception as e:
        log("ERROR", f"Failed to load {csv_path.name}: {e}")
        return None


def load_tot_config(config_path: Path) -> dict:
    """
    Load TOT% (Terms of Trade) configuration from JSON.
    Returns dict with blended_tot_pct and by_chain rates.
    Falls back to blended 50% if config missing or invalid.
    """
    default_config = {
        "status": "FALLBACK",
        "blended_tot_pct": 50.0,
        "by_chain": {},
        "notes": "Using default blended rate; config file not found or invalid"
    }

    if not config_path.exists():
        log("WARN", f"TOT% config missing: {config_path}. Using default blended rate (50.0%).")
        return default_config

    try:
        with open(config_path) as f:
            config = json.load(f)

        if config.get("status") == "DRAFT":
            log("WARN", "TOT% config status is DRAFT — awaiting Finance approval. Using blended rate.")
            return config

        if config.get("status") != "APPROVED":
            log("WARN", f"TOT% config status is '{config.get('status')}' — not approved. Using fallback.")
            return default_config

        log("OK", f"TOT% config loaded: status=APPROVED, blended={config.get('blended_tot_pct')}%")
        return config

    except Exception as e:
        log("ERROR", f"Failed to parse TOT% config: {e}. Using default.")
        return default_config


def analyze_revenue_velocity(offtake_df: pd.DataFrame, forecast_df: pd.DataFrame | None) -> dict:
    """
    Analyze revenue growth, MoM acceleration, and YoY trend.
    Uses YoY comparison as primary basis (avoids misleading period-mismatch variance).

    Returns insight dict with severity, title, and narrative.
    """
    if offtake_df is None or len(offtake_df) == 0:
        return {"type": "revenue", "severity": "UNKNOWN", "title": "Revenue data unavailable"}

    try:
        # Latest month total offtake
        latest_offtake = offtake_df['Offtake_NSV_Lakh'].sum()

        # MoM growth (last month vs previous)
        if len(offtake_df) >= 2:
            grouped = offtake_df.groupby('Month')['Offtake_NSV_Lakh'].sum().reset_index()
            if len(grouped) >= 2:
                latest_month = grouped.iloc[-1]['Offtake_NSV_Lakh']
                prev_month = grouped.iloc[-2]['Offtake_NSV_Lakh']
                mom_growth = (latest_month / prev_month - 1) * 100 if prev_month > 0 else 0
            else:
                mom_growth = 0
        else:
            mom_growth = 0

        # YoY growth (FY27 vs FY26) — primary basis for severity
        fy27_offtake = offtake_df[offtake_df['FY'] == 'FY27']['Offtake_NSV_Lakh'].sum()
        fy26_offtake = offtake_df[offtake_df['FY'] == 'FY26']['Offtake_NSV_Lakh'].sum()
        yoy_growth = (fy27_offtake / fy26_offtake - 1) * 100 if fy26_offtake > 0 else 0

        # Determine severity based on YoY trend (not period-mismatch variance)
        if yoy_growth < -30:
            severity = "CRITICAL"
            title = "Revenue Momentum Declined — YoY Growth at -30%+"
            narrative = (
                f"YoY decline of {yoy_growth:.1f}% indicates market share loss or channel contraction. "
                f"This period's revenue ₹{fy27_offtake:.0f}Cr is down from ₹{fy26_offtake:.0f}Cr last year. "
                f"Action: (1) Diagnose channel-wise decline (DMart, Reliance, Apollo), "
                f"(2) Accelerate hero SKUs with incremental trade support, "
                f"(3) Review discounting strategy vs. offtake lift."
            )
        elif yoy_growth < -10:
            severity = "WARNING"
            title = "Revenue Deceleration — Trend Reversal Needed"
            narrative = (
                f"Revenue down {yoy_growth:.1f}% YoY to ₹{fy27_offtake:.0f}Cr. "
                f"MoM trend: {mom_growth:+.1f}%. "
                f"Risk of brand perception erosion if decline persists. "
                f"Recommend: portfolio refresh, distributor incentive program."
            )
        elif yoy_growth > 20:
            severity = "OPPORTUNITY"
            title = "Revenue Outperforming — Capture Upside"
            narrative = (
                f"YoY growth of {yoy_growth:+.1f}% indicates strong momentum. "
                f"Revenue ₹{fy27_offtake:.0f}Cr vs ₹{fy26_offtake:.0f}Cr prior year. "
                f"Capitalize on hero SKU success: increase production, expand distribution into tier-2 chains."
            )
        else:
            severity = "ON_TRACK"
            title = "Revenue Tracking Growth Baseline"
            narrative = (
                f"YoY growth {yoy_growth:+.1f}%, MoM acceleration {mom_growth:+.1f}%. "
                f"Revenue ₹{fy27_offtake:.0f}Cr vs ₹{fy26_offtake:.0f}Cr prior year. Maintain current strategy."
            )

        return {
            "type": "revenue",
            "severity": severity,
            "title": title,
            "text": narrative,
            "metrics": {
                "revenue_current_cr": round(fy27_offtake, 1),
                "revenue_prior_year_cr": round(fy26_offtake, 1),
                "mom_growth_pct": round(mom_growth, 1),
                "yoy_growth_pct": round(yoy_growth, 1),
            }
        }
    except Exception as e:
        log("ERROR", f"Revenue analysis failed: {e}")
        return {"type": "revenue", "severity": "UNKNOWN", "title": "Revenue analysis error", "text": str(e)}


def analyze_pipeline_health(offtake_df: pd.DataFrame) -> dict:
    """
    Analyze Primary vs Offtake gap, conversion %, and pipeline fill.
    Detects incomplete data and returns diagnostic alert if metrics are missing.

    Flags: Trade inventory overhang (gap > 50%), stockout risk (gap < 10%), healthy (15-25%)
    """
    if offtake_df is None or len(offtake_df) == 0:
        return {"type": "pipeline", "severity": "UNKNOWN", "title": "Pipeline data unavailable"}

    try:
        # Latest month average metrics
        latest = offtake_df.iloc[-1]
        primary = latest.get('Primary_NSV_Lakh', None)
        offtake = latest.get('Offtake_NSV_Lakh', None)
        conversion = latest.get('Conversion_Pct', None)

        # Check for missing/NaN data
        has_missing = (primary is None or pd.isna(primary) or
                       offtake is None or pd.isna(offtake) or
                       conversion is None or pd.isna(conversion))

        if has_missing:
            severity = "WARNING"
            title = "Channel Pipeline Health — Data Review Required"
            narrative = (
                "Current data lacks channel-specific primary vs. offtake gap metrics needed "
                "to identify high-conversion channels. Action: Verify Primary × Offtake "
                "data contract loading from PowerBI/ExportData/offtake.csv on Sep 1 refresh."
            )
            return {
                "type": "pipeline",
                "severity": severity,
                "title": title,
                "text": narrative,
                "metrics": {
                    "data_completeness_pct": 0,
                    "channels_analyzed": 0,
                    "status": "awaiting_sep_1_data"
                }
            }

        primary = float(primary)
        offtake = float(offtake)
        conversion = float(conversion)

        gap = primary - offtake
        gap_pct = gap / offtake if offtake > 0 else 0

        # Trend: gap widening or narrowing?
        if len(offtake_df) >= 2:
            prev_gap_pct = ((offtake_df.iloc[-2].get('Primary_NSV_Lakh', 0) -
                            offtake_df.iloc[-2].get('Offtake_NSV_Lakh', 0)) /
                           offtake_df.iloc[-2].get('Offtake_NSV_Lakh', 1))
            gap_trend = (gap_pct - prev_gap_pct) * 100  # in percentage points
        else:
            gap_trend = 0

        # Determine severity
        if gap_pct > 0.5:
            severity = "CRITICAL"
            title = "Trade Inventory Overhang Risk"
            narrative = (
                f"Primary {gap_pct*100:.0f}% above retail offtake (₹{primary:.0f}Cr vs ₹{offtake:.0f}Cr). "
                f"Pipeline gap of ₹{gap:.0f}Cr indicates distributor inventory buildup. "
                f"Risk: trade deduction creep, markdown pressure. "
                f"Action: demand-pull promo, distributor carry reduction agreement."
            )
        elif primary < offtake:
            severity = "WARNING"
            title = "Potential Retail Stockout Risk"
            narrative = (
                f"Retail offtake exceeding distributor sell-in (₹{offtake:.0f}Cr vs ₹{primary:.0f}Cr). "
                f"Negative gap suggests retail inventory drawdown or supply shortage. "
                f"Risk: lost sales, customer dissatisfaction. "
                f"Action: increase primary shipment, expedite distributor reorders."
            )
        elif gap_pct > 0.3 or (gap_pct > 0.25 and gap_trend > 5):
            severity = "WARNING"
            title = "Elevated Pipeline Fill"
            narrative = (
                f"Gap at {gap_pct*100:.0f}% of offtake (₹{gap:.0f}Cr), trending {'up' if gap_trend > 0 else 'down'} by {abs(gap_trend):.1f}pp. "
                f"Conversion at {conversion:.1f}%. Moderate overhang; monitor closely. "
                f"Action: channel incentive to accelerate pull-through."
            )
        elif 0.15 <= gap_pct <= 0.25 and conversion > 8:
            severity = "ON_TRACK"
            title = "Healthy Pipeline Dynamics"
            narrative = (
                f"Pipeline gap of {gap_pct*100:.0f}% (₹{gap:.0f}Cr), conversion {conversion:.1f}%. "
                f"Optimal fill level balances availability with inventory control. Status: healthy."
            )
        else:
            severity = "OPPORTUNITY"
            title = "High-Conversion Channel Ready for Growth"
            narrative = (
                f"Tight pipeline ({gap_pct*100:.0f}% gap), strong conversion at {conversion:.1f}%. "
                f"Channel demonstrates pull-through efficiency. "
                f"Opportunity: increase primary allocation to this channel for growth capture."
            )

        return {
            "type": "pipeline",
            "severity": severity,
            "title": title,
            "text": narrative,
            "metrics": {
                "primary_nsv_lakh": round(primary, 1),
                "offtake_nsv_lakh": round(offtake, 1),
                "gap_lakh": round(gap, 1),
                "gap_pct": round(gap_pct * 100, 1),
                "conversion_pct": round(conversion, 1),
            }
        }
    except Exception as e:
        log("ERROR", f"Pipeline analysis failed: {e}")
        return {"type": "pipeline", "severity": "UNKNOWN", "title": "Pipeline analysis error", "text": str(e)}


def analyze_distribution_health(universe_df: pd.DataFrame, offtake_df: pd.DataFrame | None) -> dict:
    """
    Analyze store universe, active store %, and sales productivity per store.
    Segments productivity by chain/format when data available.

    Severity: CRITICAL (<₹0.5L/store/month or <400 active stores)
    """
    if universe_df is None or len(universe_df) == 0:
        return {"type": "distribution", "severity": "UNKNOWN", "title": "Distribution data unavailable"}

    try:
        total_row = universe_df[universe_df['Grain'] == 'Total']
        if len(total_row) == 0:
            return {"type": "distribution", "severity": "UNKNOWN", "title": "Total universe row missing"}

        total_stores = int(total_row.iloc[0]['Store_Count'])
        active_stores = int(total_row.iloc[0].get('Active_Stores', total_stores))
        active_pct = (active_stores / total_stores * 100) if total_stores > 0 else 0

        # Productivity per store (blended)
        if offtake_df is not None and len(offtake_df) > 0:
            total_offtake = offtake_df['Offtake_NSV_Lakh'].sum()
            months_count = offtake_df['Month'].nunique()
            avg_monthly_offtake = total_offtake / months_count if months_count > 0 else total_offtake
            productivity_per_store = avg_monthly_offtake / active_stores if active_stores > 0 else 0
        else:
            productivity_per_store = 0

        # Check if chain-level breakdown is available
        chain_data = {}
        if 'Grain' in universe_df.columns and 'Chain' in universe_df.columns:
            by_chain = universe_df[universe_df['Grain'] == 'By_Chain'].copy()
            if len(by_chain) > 0 and offtake_df is not None:
                for _, chain_row in by_chain.iterrows():
                    chain_name = chain_row.get('Chain', 'Unknown')
                    chain_stores = chain_row.get('Store_Count', 0)
                    if chain_name and chain_name != 'Unknown':
                        chain_offtake = offtake_df[offtake_df.get('Chain') == chain_name]['Offtake_NSV_Lakh'].sum()
                        if chain_stores > 0 and chain_offtake > 0:
                            chain_productivity = chain_offtake / months_count / chain_stores if months_count > 0 else 0
                            chain_data[chain_name] = round(chain_productivity, 2)

        # Determine severity based on blended metric
        if productivity_per_store < 0.5 or active_stores < 350:
            severity = "CRITICAL"
            if chain_data:
                chain_breakdown = "\n".join([f"  • {k}: ₹{v}L/store" for k, v in sorted(chain_data.items(), key=lambda x: x[1], reverse=True)])
                narrative = (
                    f"Blended productivity ₹{productivity_per_store:.2f}L/store/month masks channel variation.\n"
                    f"Breakdown by chain:\n{chain_breakdown}\n"
                    f"Action: (1) Audit underperforming chains, (2) Rationalize stores with <₹50K/month, "
                    f"(3) Increase assortment/planogram compliance in high-potential zones."
                )
            else:
                narrative = (
                    f"Active stores: {active_stores}/{total_stores} ({active_pct:.0f}%). "
                    f"Productivity: ₹{productivity_per_store:.2f}L per store/month. "
                    f"Critically low productivity suggests stale/low-velocity store base. "
                    f"Action: rationalize bottom 20% stores, accelerate new-store ramp in high-potential zones."
                )
            title = "Low Store Productivity — Distribution Audit Required"
        elif active_pct < 90 or active_stores < 400:
            severity = "WARNING"
            title = "Distribution Expansion Lagging Growth Target"
            narrative = (
                f"Active stores: {active_stores}/{total_stores} ({active_pct:.0f}%). "
                f"Productivity: ₹{productivity_per_store:.2f}L/store/month. "
                f"Growth target implies 450+ stores; current gap of {450 - active_stores} stores. "
                f"Action: accelerate new-store recruitment in under-penetrated zones."
            )
        else:
            severity = "ON_TRACK"
            title = "Store Universe Expanding on Plan"
            narrative = (
                f"Active stores: {active_stores}/{total_stores} ({active_pct:.0f}%). "
                f"Productivity: ₹{productivity_per_store:.2f}L/store/month. "
                f"Universe healthy and growing. Maintain recruitment pace."
            )

        return {
            "type": "distribution",
            "severity": severity,
            "title": title,
            "text": narrative,
            "metrics": {
                "total_stores": total_stores,
                "active_stores": active_stores,
                "active_pct": round(active_pct, 1),
                "productivity_per_store_lakh": round(productivity_per_store, 2),
            }
        }
    except Exception as e:
        log("ERROR", f"Distribution analysis failed: {e}")
        return {"type": "distribution", "severity": "UNKNOWN", "title": "Distribution analysis error", "text": str(e)}


def analyze_profitability(cm2_value: float, cm2_pct: float, tot_pct: float,
                          primary_nsv: float, expense_pct: float, is_placeholder: bool = False) -> dict:
    """
    Analyze CM2, margin trends, and TOT% efficiency.

    Severity: CRITICAL (CM2% <20%), WARNING (margin erosion >5pp), ON_TRACK, OPPORTUNITY
    When is_placeholder=True, returns DRAFT status acknowledging real data loads Sep 1.
    """
    try:
        if is_placeholder:
            severity = "DRAFT"
            title = "Profitability Analysis — Production Data Loading Sep 1"
            narrative = (
                f"CM2 and expense analysis currently use placeholder data. On Sep 1 refresh, "
                "this insight will load real CM2 from data.js, PnL expenses from Power BI, "
                "and Finance-approved TOT% rates from config. Metric framework is validated; "
                "awaiting production data."
            )
            return {
                "type": "profitability",
                "severity": severity,
                "title": title,
                "text": narrative,
                "metrics": {
                    "cm2_pct_of_nsv": round(cm2_pct * 100, 1),
                    "expense_pct_of_nsv": round(expense_pct * 100, 1),
                    "tot_pct": round(tot_pct, 1),
                    "status": "awaiting_sep_1_production_data"
                }
            }

        if cm2_pct < 0.20:
            severity = "CRITICAL"
            title = "Margin Pressure: CM2 Below 20% of NSV"
            narrative = (
                f"CM2: ₹{cm2_value:.0f}Cr ({cm2_pct*100:.1f}% of NSV). "
                f"Critical margin compression. Expense load: {expense_pct*100:.1f}% of NSV. "
                f"TOT%: {tot_pct:.1f}%. "
                f"Action: evaluate trade spend ROI, reduce high-discount SKUs, renegotiate terms with underperforming chains."
            )
        elif cm2_pct < 0.25 or expense_pct > 0.25:
            severity = "WARNING"
            title = "Margin Erosion Detected"
            narrative = (
                f"CM2: ₹{cm2_value:.0f}Cr ({cm2_pct*100:.1f}% of NSV). "
                f"Margin below baseline. Expense: {expense_pct*100:.1f}% of NSV. "
                f"TOT%: {tot_pct:.1f}%. "
                f"Action: optimize SKU mix toward margin leaders, reduce trade spend on low-ROI programs."
            )
        else:
            severity = "ON_TRACK"
            title = "Profitability Stable"
            narrative = (
                f"CM2: ₹{cm2_value:.0f}Cr ({cm2_pct*100:.1f}% of NSV). "
                f"Expense: {expense_pct*100:.1f}% of NSV, TOT%: {tot_pct:.1f}%. "
                f"Profitability on track. Maintain current strategy."
            )

        return {
            "type": "profitability",
            "severity": severity,
            "title": title,
            "text": narrative,
            "metrics": {
                "cm2_value_cr": round(cm2_value, 1),
                "cm2_pct_of_nsv": round(cm2_pct * 100, 1),
                "expense_pct_of_nsv": round(expense_pct * 100, 1),
                "tot_pct": round(tot_pct, 1),
            }
        }
    except Exception as e:
        log("ERROR", f"Profitability analysis failed: {e}")
        return {"type": "profitability", "severity": "UNKNOWN", "title": "Profitability analysis error", "text": str(e)}


def main():
    ap = argparse.ArgumentParser(
        description="Generate automated Agent Sentiments & Executive Insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate insights from extracted CSV data contracts
  python scripts/generate_agent_sentiments.py --data PowerBI/ExportData/ --out insights_output.json

  # Dry-run mode (validate CSVs only, no analysis)
  python scripts/generate_agent_sentiments.py --data PowerBI/ExportData/ --dry-run
        """
    )
    ap.add_argument("--data", type=Path, default=Path("PowerBI/ExportData"),
                    help="CSV data directory (default: PowerBI/ExportData)")
    ap.add_argument("--out", type=Path, default=Path("insights_output.json"),
                    help="Output JSON path (default: insights_output.json)")
    ap.add_argument("--tot-config", type=Path,
                    default=Path("PowerBI/Reference/CM2_Provisional/config/tot_rates.json"),
                    help="TOT% config path (default: PowerBI/Reference/CM2_Provisional/config/tot_rates.json)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Validate CSVs only, don't analyze")

    args = ap.parse_args()

    log("INFO", "═" * 70)
    log("INFO", "Agent Sentiments & Executive Insights Engine")
    log("INFO", "═" * 70)
    log("INFO", f"Data: {args.data}")
    log("INFO", f"Output: {args.out}")
    log("INFO", f"TOT% config: {args.tot_config}")

    # Load data contracts
    log("INFO", "")
    log("INFO", "Step 1: Load CSV data contracts")
    offtake_df = load_csv(args.data / "offtake.csv")
    primary_df = load_csv(args.data / "primary.csv")
    universe_df = load_csv(args.data / "universe.csv")
    forecast_df = load_csv(args.data / "forecast_targets.csv")
    tot_df = load_csv(args.data / "tot_mapping.csv")
    pnl_df = load_csv(args.data / "pnl_expenses.csv")

    if offtake_df is None or universe_df is None:
        log("ERROR", "Missing required CSVs: offtake.csv and/or universe.csv")
        sys.exit(1)

    log("OK", "All available CSVs loaded")

    if args.dry_run:
        log("INFO", "")
        log("INFO", "[DRY RUN] Skipping analysis")
        sys.exit(0)

    # Load TOT% configuration
    log("INFO", "")
    log("INFO", "Step 2: Load configuration")
    tot_config = load_tot_config(args.tot_config)
    tot_pct = tot_config.get("blended_tot_pct", 50.0)
    log("OK", f"TOT% config: {tot_config.get('status')} (blended={tot_pct}%)")

    # Analyze insights
    log("INFO", "")
    log("INFO", "Step 3: Analyze dimensions")
    insights = []

    # 1. Revenue velocity
    revenue_insight = analyze_revenue_velocity(offtake_df, forecast_df)
    insights.append(revenue_insight)
    log("OK", f"Revenue: {revenue_insight['severity']}")

    # 2. Pipeline health
    pipeline_insight = analyze_pipeline_health(offtake_df)
    insights.append(pipeline_insight)
    log("OK", f"Pipeline: {pipeline_insight['severity']}")

    # 3. Distribution health
    distrib_insight = analyze_distribution_health(universe_df, offtake_df)
    insights.append(distrib_insight)
    log("OK", f"Distribution: {distrib_insight['severity']}")

    # 4. Profitability (if we had CM2/PnL data in CSVs, would load from there)
    # For now: placeholder with mock data (would come from data.js in production)
    profitability_insight = analyze_profitability(
        cm2_value=10000,  # Placeholder
        cm2_pct=0.25,
        tot_pct=tot_pct,  # From config file
        primary_nsv=18000,
        expense_pct=0.15,
        is_placeholder=True  # Flag that this uses placeholder data
    )
    insights.append(profitability_insight)
    log("OK", f"Profitability: {profitability_insight['severity']}")

    # Write output
    log("INFO", "")
    log("INFO", "Step 4: Write insights JSON")
    output = {
        "generated_at": datetime.now().isoformat(),
        "version": "Phase 3 - Agent Sentiments Engine v1",
        "insights": insights,
        "summary": {
            "total_insights": len(insights),
            "critical_count": sum(1 for i in insights if i['severity'] == 'CRITICAL'),
            "warning_count": sum(1 for i in insights if i['severity'] == 'WARNING'),
            "on_track_count": sum(1 for i in insights if i['severity'] == 'ON_TRACK'),
            "opportunity_count": sum(1 for i in insights if i['severity'] == 'OPPORTUNITY'),
        }
    }

    with open(args.out, 'w') as f:
        json.dump(output, f, indent=2)

    log("OK", f"Insights written to {args.out.name}")

    # Report summary
    log("INFO", "")
    log("INFO", "Insights Summary:")
    for insight in insights:
        severity_emoji = {"CRITICAL": "🔴", "WARNING": "🟠", "ON_TRACK": "🟢", "OPPORTUNITY": "💡"}.get(insight['severity'], "⚪")
        log("INFO", f"  {severity_emoji} {insight['type'].capitalize()}: {insight['title']}")

    log("INFO", "")
    log("INFO", "═" * 70)
    log("OK", "Agent Sentiments generation complete!")
    log("INFO", "═" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
