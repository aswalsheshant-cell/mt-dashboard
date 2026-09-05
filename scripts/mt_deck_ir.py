"""
Modern Trade Deck Intermediate Representation (IR) Builder
Decouples slide data extraction and analytics from rendering platforms.
Produces a structured dictionary that can be serialized to PPTX or Google Slides API.
"""

from typing import Dict, Any, List
from datetime import datetime
from mt_analytics_engine import (
    calculate_waterfall_bridge,
    calculate_scenario_roi,
    calculate_matrix_coordinates
)


def build_deck_ir(month: str, year: int, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds a complete intermediate representation of the 18-slide MT deck.
    Each slide contains pre-computed analytics and layout specifications,
    ready for export to PowerPoint or Google Slides.

    Args:
        month: Month name (e.g., "September")
        year: Fiscal year (e.g., 2026)
        config: Configuration dict with zones, diagnostic_chain, scenario_params, etc.

    Returns:
        Dict with deck metadata and array of 18 slide definitions
    """

    # Waterfall calculations (Slide 5c)
    chain_data = config.get("diagnostic_chain", {})
    waterfall = calculate_waterfall_bridge(
        chain_data.get("primary", 2.40),
        chain_data.get("offtake", 1.25)
    )

    # Scenario ROI calculations (Slide 12)
    scenario_cfg = config.get("scenario_params", {})
    scenario_roi = calculate_scenario_roi(
        current_offtake_weekly=scenario_cfg.get("current_offtake_weekly", 7.0),
        current_conv=scenario_cfg.get("current_conv", 45.3),
        target_conv=scenario_cfg.get("target_conv", 70.0),
        promo_spend=scenario_cfg.get("promo_spend", 30.0),
        promo_days=scenario_cfg.get("promo_days", 21),
        gross_margin_pct=scenario_cfg.get("gross_margin_pct", 0.45) / 100.0,
        discount_pct=scenario_cfg.get("discount_pct", 10.0)
    )

    # Matrix coordinates (Slide 7)
    zones_detail = config.get("zones_detail", [])
    matrix_coords = calculate_matrix_coordinates(
        zones_detail,
        1.5,  # box_left in inches
        1.8,  # box_top in inches
        7.0,  # box_width in inches
        4.0,  # box_height in inches
        target_conv=75.0
    )

    # Build IR payload
    deck_ir = {
        "deck_id": f"mt_deck_{month.lower()}_{year}",
        "month": month,
        "year": year,
        "generated_at": datetime.now().isoformat(),
        "dimensions": {
            "width_inches": 10.0,
            "height_inches": 7.5
        },
        "slides": [
            # Slide 1: Title
            {
                "slide_id": "slide_01_title",
                "slide_number": 1,
                "title": f"Modern Trade Leadership Review",
                "subtitle": f"{month} {year}",
                "layout_type": "title_slide",
                "elements": {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "period": config.get("period", "Q1-Sep"),
                }
            },

            # Slide 2: Table of Contents
            {
                "slide_id": "slide_02_toc",
                "slide_number": 2,
                "title": "Table of Contents",
                "layout_type": "toc",
                "elements": {
                    "items": [
                        "1. Title", "2. TOC", "3. Exec Summary", "4. Market Context",
                        "5. Primary Trend", "5b. Offtake Trend", "5c. Waterfall Diagnostic",
                        "6. Zone Primary", "7. Risk Matrix", "8. Zone Conversion",
                        "9. Chain Concentration", "9b. Strategy Pillars", "10. Category Mix",
                        "11. Comparison Table", "12. Scenario Analysis", "13. Execution Roadmap",
                        "14. Action Register", "15. Closing"
                    ]
                }
            },

            # Slide 3: Exec Summary
            {
                "slide_id": "slide_03_exec_summary",
                "slide_number": 3,
                "title": "Executive Summary",
                "layout_type": "kpi_grid",
                "elements": {
                    "kpi_cards": [
                        {"label": "Q1 Offtake", "value": config.get("q1_offtake", "₹114.39 Cr"), "status": "ON_TRACK"},
                        {"label": "4-Month Total", "value": config.get("4m_offtake", "₹185.81 Cr"), "status": "ON_TRACK"},
                        {"label": "Month Offtake", "value": config.get("month_offtake", "₹71.42 Cr"), "status": "ON_TRACK"},
                        {"label": "YoY Growth", "value": config.get("q1_growth_yoy", "+64%"), "status": "STRONG"},
                    ],
                    "bullets": [
                        "East zone conversion at 45.3% — critical recovery priority",
                        "Reliance & North channels show primary loading but conversion lag",
                        "Mamaearth +33% YoY; TDC +365% (emerging momentum)"
                    ]
                }
            },

            # Slide 4: Market Context
            {
                "slide_id": "slide_04_market_context",
                "slide_number": 4,
                "title": "Market Context: Competitive Positioning",
                "layout_type": "market_positioning",
                "elements": {
                    "market_size": "₹4,200L NSV (Personal Care Modern Trade)",
                    "growth_rate": "+11% YoY",
                    "competitors": [
                        {"name": "HUL", "share": "28%", "nsv": "₹1,176L"},
                        {"name": "P&G", "share": "15%", "nsv": "₹630L"},
                        {"name": "ITC", "share": "9%", "nsv": "₹378L"},
                        {"name": "Mamaearth", "share": "6.4%", "nsv": "₹270L"},
                    ],
                    "trend": "Value tier (<₹400) gaining +18% YoY share; premium tier pressure",
                    "implication": "Price realization risk if we don't own value tier"
                }
            },

            # Slide 5: Primary Trend
            {
                "slide_id": "slide_05_primary_trend",
                "slide_number": 5,
                "title": "3-Month Primary Revenue Trend",
                "layout_type": "trend_line",
                "elements": {
                    "data": [
                        {"month": "July", "value": 62.5, "growth": None},
                        {"month": "August", "value": 68.2, "growth": "+9.1%"},
                        {"month": "September", "value": 71.4, "growth": "+4.7%"},
                    ]
                }
            },

            # Slide 5b: Offtake Trend
            {
                "slide_id": "slide_05b_offtake_trend",
                "slide_number": 5,
                "title": "Offtake Inventory Trend & Conversion Gap",
                "layout_type": "dual_metric",
                "elements": {
                    "data": [
                        {"month": "July", "offtake": 52.68, "conversion": 73.8},
                        {"month": "August", "offtake": 54.12, "conversion": 74.2},
                        {"month": "September", "offtake": 55.18, "conversion": 75.3},
                    ],
                    "insight": "Conversion improving 150bp over 3 months; gap narrowing"
                }
            },

            # Slide 5c: Waterfall Diagnostic
            {
                "slide_id": "slide_05c_waterfall",
                "slide_number": 5,
                "title": f"Multi-Step Waterfall: {chain_data.get('chain_name', 'Reliance')} Case Study",
                "layout_type": "waterfall_bridge",
                "elements": {
                    "chain_name": chain_data.get("chain_name", "Reliance"),
                    "bridge": waterfall,
                    "action_mandate": "Freeze non-hero NPI | Reallocate shelf space | Monitor price elasticity"
                }
            },

            # Slide 6: Zone Primary
            {
                "slide_id": "slide_06_zone_primary",
                "slide_number": 6,
                "title": "Zone-Wise Primary: NSV & Growth Ranking",
                "layout_type": "zone_ranking",
                "elements": {
                    "zones": config.get("zones", {}),
                }
            },

            # Slide 7: Risk Matrix
            {
                "slide_id": "slide_07_risk_matrix",
                "slide_number": 7,
                "title": "Territory Prioritization: Risk vs. Opportunity Matrix",
                "layout_type": "scatter_matrix",
                "elements": {
                    "zones": matrix_coords,
                    "quadrants": {
                        "urgent": "High gap + Large scale",
                        "watch": "Medium gap + Large scale",
                        "monitor": "High gap + Small scale",
                        "healthy": "Low gap + Small scale"
                    }
                }
            },

            # Slide 8: Zone Conversion
            {
                "slide_id": "slide_08_zone_conversion",
                "slide_number": 8,
                "title": "Zone Conversion %: Current Status vs. 75% Target",
                "layout_type": "bar_chart",
                "elements": {
                    "target": 75.0,
                    "zones": config.get("zones", {})
                }
            },

            # Slide 9: Chain Concentration
            {
                "slide_id": "slide_09_chain_concentration",
                "slide_number": 9,
                "title": "Chain-Wise Breakdown: Concentration Risk",
                "layout_type": "chain_breakdown",
                "elements": {
                    "chains": config.get("chains", [])
                }
            },

            # Slide 9b: Strategy Pillars
            {
                "slide_id": "slide_09b_strategy_pillars",
                "slide_number": 9,
                "title": "4-Pillar Strategic Framework",
                "layout_type": "pillar_grid",
                "elements": {
                    "pillars": [
                        {"title": "Hero SKU Focus", "desc": "Concentrate 60% trade spend on top 15 SKUs", "color": "TEAL"},
                        {"title": "Price Elasticity", "desc": "Sub-₹500 bundle positioning", "color": "GREEN"},
                        {"title": "Shelf Excellence", "desc": "Category planogram enforcement & POSM", "color": "ORANGE"},
                        {"title": "Velocity Pulse", "desc": "Weekly sell-out dashboard by zone", "color": "PURPLE"},
                    ]
                }
            },

            # Slide 10: Category Mix
            {
                "slide_id": "slide_10_category_mix",
                "slide_number": 10,
                "title": "Brand Performance Ranking",
                "layout_type": "brand_ranking",
                "elements": {
                    "brands": config.get("brands", [])
                }
            },

            # Slide 11: Comparison Table
            {
                "slide_id": "slide_11_comparison_table",
                "slide_number": 11,
                "title": "Multi-Period Performance Comparison",
                "layout_type": "comparison_table",
                "elements": {
                    "periods": ["July", "August", "September"],
                    "metrics": ["Primary (₹Cr)", "Offtake (₹Cr)", "Conversion %", "Gap (₹Cr)"]
                }
            },

            # Slide 12: Scenario Analysis
            {
                "slide_id": "slide_12_scenario_analysis",
                "slide_number": 12,
                "title": "Scenario Analysis: Promotional Uplift & ROI Forecast",
                "layout_type": "scenario_comparison",
                "elements": {
                    "zone": config.get("scenario", {}).get("zone", "East"),
                    "roi": scenario_roi,
                    "scenarios": [
                        {
                            "title": "CURRENT STATE",
                            "conv": f"{scenario_roi['current_conv']:.1f}%",
                            "weekly": f"₹{scenario_roi['current_weekly']:.1f}L",
                            "status": "🔴 URGENT"
                        },
                        {
                            "title": "WITH PROMO",
                            "conv": f"{scenario_roi['mid_conv']:.1f}%",
                            "weekly": f"₹{scenario_roi['promo_weekly']:.1f}L",
                            "status": "🟡 IMPROVING"
                        },
                        {
                            "title": "TARGET STATE",
                            "conv": f"{scenario_roi['target_conv']:.0f}%+",
                            "weekly": f"₹{scenario_roi['target_weekly']:.1f}L+",
                            "status": "🟢 RECOVERED"
                        }
                    ]
                }
            },

            # Slide 13: Execution Roadmap
            {
                "slide_id": "slide_13_execution_roadmap",
                "slide_number": 13,
                "title": "Execution Roadmap: 4-Week Phased Plan",
                "layout_type": "roadmap_timeline",
                "elements": {
                    "weeks": [
                        {"week": "Week 1", "phase": "DISCOVERY", "owner": "Trade Ops", "actions": ["Retail audit", "Competitor intel"]},
                        {"week": "Week 2", "phase": "PREPARATION", "owner": "Category Head", "actions": ["Trade plan draft", "Promo SKU selection"]},
                        {"week": "Week 3", "phase": "EXECUTION", "owner": "Zone Manager", "actions": ["Promo launch", "Field sales activation"]},
                        {"week": "Week 4", "phase": "CONSOLIDATION", "owner": "NKAM", "actions": ["Results review", "Momentum hold"]},
                    ]
                }
            },

            # Slide 14: Action Register
            {
                "slide_id": "slide_14_action_register",
                "slide_number": 14,
                "title": "Live Accountability: Action Register",
                "layout_type": "action_register",
                "elements": {
                    "actions": [
                        {"priority": "P0", "owner": "VP MT", "action": "East zone recovery plan", "target": "Sep 10", "metric": "Conv ≥60%", "status": "IN PROGRESS"},
                        {"priority": "P0", "owner": "Trade Head", "action": "Reliance shelf reset", "target": "Sep 8", "metric": "Space secured", "status": "SCHEDULED"},
                        {"priority": "P1", "owner": "Category", "action": "Hero SKU bundle", "target": "Sep 12", "metric": "Launch live", "status": "IN PROGRESS"},
                        {"priority": "P1", "owner": "Zone Mgr North", "action": "Price elasticity test", "target": "Sep 15", "metric": "Data collect", "status": "PENDING"},
                    ],
                    "governance": "Weekly Monday 2:00 PM | Any P0 slip flags to VP Modern Trade"
                }
            },

            # Slide 15: Closing
            {
                "slide_id": "slide_15_closing",
                "slide_number": 15,
                "title": "Next Steps: October Leadership Review",
                "layout_type": "closing_timeline",
                "elements": {
                    "timeline": [
                        {"date": "Oct 5", "item": "Conversion update (target: East ≥60%, North ≥65%)"},
                        {"date": "Oct 10", "item": "Promo ROI assessment + Oct loading approval"},
                        {"date": "Oct 15", "item": "Full zone review (6 zones) + brand performance refresh"},
                        {"date": "Oct 25", "item": "Q2 planning + FY28 outlook"},
                    ],
                    "distribution": ["VP Modern Trade", "Category Heads", "Zone Managers", "NKAM Leadership"]
                }
            }
        ]
    }

    return deck_ir
