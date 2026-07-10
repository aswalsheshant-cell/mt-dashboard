"""
Phase 6 — template registry.

Declarative specs for each leadership report format. A spec says *what* a report
needs (which datasets, which measures, which breakdowns, which comparisons) and
*how* it should be framed (classification, whether to hide 'Others', MT-only).
It contains structure/business-logic only — NEVER any numbers. The fill engine
supplies every value from the sources the user provides.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MeasureSpec:
    key: str            # sanitized source column, e.g. "mrp_sales_value"
    label: str          # display, e.g. "MRP Sales Value"
    unit: str = ""      # "Cr" -> value/1e7 for display; "" -> raw
    calc: str = "sum"   # only 'sum' today


@dataclass
class BreakdownSpec:
    key: str            # source column to group by, e.g. "category"
    label: str          # display, e.g. "Category"


@dataclass
class TemplateSpec:
    key: str
    name: str
    classification: str
    required_datasets: List[str]          # e.g. ["offtake"]
    measures: List[MeasureSpec]
    breakdowns: List[BreakdownSpec]
    comparisons: List[str] = field(default_factory=lambda: ["MoM", "L3M", "YoY"])
    mt_only: bool = True                  # exclude GT; MT channel only
    hide_others: bool = True              # hide 'Others' from visible tables, keep in totals
    channel_column: Optional[str] = None  # column that carries MT/GT, if any
    notes: str = ""


# --- the registry ---------------------------------------------------------
# Only MRP Sales Value is unit-verified against the known dashboard scale (₹ Cr).
# NSV and other measures are intentionally omitted until their source unit is
# confirmed — we do not apply an unverified conversion (see the no-assumption rule).
_OFFTAKE_MEASURES = [
    MeasureSpec("mrp_sales_value", "MRP Sales Value", unit="Cr"),
]
_OFFTAKE_BREAKDOWNS = [
    BreakdownSpec("category", "Category"),
    BreakdownSpec("chain_name", "Chain"),
    BreakdownSpec("zone", "Zone"),
]

TEMPLATE_REGISTRY: Dict[str, TemplateSpec] = {
    "mt_monthly_offtake": TemplateSpec(
        key="mt_monthly_offtake",
        name="MT Monthly Offtake Report",
        classification="Confidential - MT Internal",
        required_datasets=["offtake"],
        measures=_OFFTAKE_MEASURES,
        breakdowns=_OFFTAKE_BREAKDOWNS,
        comparisons=["MoM", "L3M", "YoY"],
        channel_column=None,  # offtake source is MT-only by construction
        notes="Store x article MT offtake. GT excluded (not present in MT offtake source).",
    ),
    "qbr_leadership_review": TemplateSpec(
        key="qbr_leadership_review",
        name="QBR Leadership Review",
        classification="Confidential - MT Internal",
        required_datasets=["primary", "offtake"],
        measures=[
            MeasureSpec("sale_in_lac", "Primary NSV", unit="Cr"),
            MeasureSpec("mrp_sales_value", "Offtake MRP Value", unit="Cr"),
        ],
        breakdowns=[BreakdownSpec("category", "Category"), BreakdownSpec("zone", "Zone")],
        comparisons=["MoM", "QoQ", "YoY"],
        channel_column="channel",  # primary has a Channel column (MT/GT)
        notes="Primary vs offtake leadership view. MT channel only.",
    ),
    "nielsen_market_share": TemplateSpec(
        key="nielsen_market_share",
        name="Nielsen Market Share Deep Dive",
        classification="Confidential - MT Internal",
        required_datasets=["nielsen"],
        measures=[MeasureSpec("value_share", "Value Share", unit="%")],
        breakdowns=[BreakdownSpec("nielsen_category", "Nielsen Category")],
        comparisons=["MoM", "YoY"],
        channel_column=None,
        notes="Nielsen value/volume share. Requires a Nielsen source file.",
    ),
    # declared for completeness; fill engine degrades gracefully to 'Source data required'
    "chain_deep_dive": TemplateSpec(
        key="chain_deep_dive", name="Chain Deep Dive",
        classification="Confidential - MT Internal",
        required_datasets=["offtake"], measures=_OFFTAKE_MEASURES,
        breakdowns=[BreakdownSpec("chain_name", "Chain"), BreakdownSpec("category", "Category")],
        notes="Deep dive by chain.",
    ),
    "forecast_tracker": TemplateSpec(
        key="forecast_tracker", name="Forecast Tracker",
        classification="Confidential - MT Internal",
        required_datasets=["primary", "forecast"],
        measures=[MeasureSpec("sale_in_lac", "Primary NSV", unit="Cr")],
        breakdowns=[BreakdownSpec("category", "Category")],
        comparisons=["MoM", "vs Target"],
        channel_column="channel",
        notes="Actual vs forecast/target.",
    ),
    "exception_report": TemplateSpec(
        key="exception_report", name="Exception Report",
        classification="Confidential - MT Internal",
        required_datasets=["offtake"], measures=_OFFTAKE_MEASURES,
        breakdowns=[BreakdownSpec("category", "Category")],
        comparisons=["MoM"],
        notes="Highlights anomalies / exceptions only.",
    ),
}


def get_template(key: str) -> TemplateSpec:
    k = (key or "").strip().lower().replace(" ", "_").replace("-", "_")
    # friendly aliases
    aliases = {
        "mt_monthly_offtake_report": "mt_monthly_offtake",
        "qbr": "qbr_leadership_review",
        "nielsen": "nielsen_market_share",
        "nielsen_market_share_deep_dive": "nielsen_market_share",
    }
    k = aliases.get(k, k)
    if k not in TEMPLATE_REGISTRY:
        raise KeyError(f"Unknown template {key!r}. Available: {', '.join(TEMPLATE_REGISTRY)}")
    return TEMPLATE_REGISTRY[k]


def list_templates() -> List[dict]:
    return [{"key": t.key, "name": t.name, "datasets": t.required_datasets}
            for t in TEMPLATE_REGISTRY.values()]
