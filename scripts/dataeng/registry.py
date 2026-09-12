"""Skill: metric_registry — Phases 2, 3 and 7.

One authoritative registry of business metrics with full lineage
(source -> transformation -> aggregation -> data.js -> dashboard tab).

The metric DEFINITIONS are declarative; their VALUES are resolved live from
data.js on every run. So the registry can never drift into describing a field
that no longer exists -- an unresolvable path becomes a FAIL finding.
"""
from __future__ import annotations

from .core import Finding, load_dash

# name, dashboard path, unit, grain, definition, source, transformation, tabs,
# owner, basis, limitations
METRICS: list[dict] = [
    dict(name="Primary NSV FY25", path="primary.nsv_fy25", unit="INR Lakh", grain="FY",
         definition="Net sales value dispatched to MT chains, FY25, net of TOT%/on-invoice margin and tax.",
         source="Pre-aggregated Primary workbook (ends Mar-26)",
         transformation="build_dashboard_data.py primary_block()",
         tabs="Overview, Primary", owner="Sales MIS", basis="NSV",
         limits="Pre-agg window only; excluded brands already removed."),
    dict(name="Primary NSV FY26", path="primary.nsv_fy26", unit="INR Lakh", grain="FY",
         definition="As FY25, for FY26.", source="Pre-aggregated Primary workbook",
         transformation="build_dashboard_data.py primary_block()",
         tabs="Overview, Primary", owner="Sales MIS", basis="NSV",
         limits="Monthly series excludes excluded brands; FY total may differ slightly."),
    dict(name="Primary NSV FY27", path="detail_meta.fyx_primary.FY27.nsv", unit="INR Lakh",
         grain="FY", definition="Article-level primary NSV for FY27 (Apr-26 onward).",
         source="primary_article_<Mon>_<YY>.csv; Jun-26 via patch_jun26.py",
         transformation="detail_records_real() -> fyx_primary",
         tabs="Overview, Primary", owner="Sales MIS", basis="NSV",
         limits="Only months with a loaded source contribute."),
    dict(name="Primary MRP FY27", path="detail_meta.fyx_primary.FY27.mrp", unit="INR Lakh",
         grain="FY", definition="Gross MRP/GMV sales value for FY27.",
         source="primary_article CSV (Apr/May) + governed seed FY27_Monthly_GMV_MRP.csv (Jun-26)",
         transformation="fix_d13_mrp.py; build_dashboard_data.py _fx_included['_MRP'].sum()",
         tabs="(not surfaced — used in CM2 COGS calculation)", owner="Sales MIS", basis="GMV_MRP",
         limits="D13 RESOLVED: brand exclusion applied; Jun-26 from AUTHORITATIVE seed (9300.91L). "
                "Correct total 31336.79L (Apr 11760.60 + May 10275.28 + Jun 9300.91)."),
    dict(name="Offtake NSV FY27", path="offtake.total_fy27", unit="INR Lakh", grain="FY",
         definition="Retail offtake (sell-out) across MT chains for FY27.",
         source="Monthly store x article offtake extracts",
         transformation="offtake_block() + patch_offtake_new_months()",
         tabs="Offtake, Overview", owner="Trade Marketing", basis="NSV",
         limits="Chain coverage varies by month; a partial source silently reduces a FY."),
    dict(name="CM2 value", path="cm2.cm2_value", unit="INR Lakh", grain="FY26+FY27",
         definition="NSV less P&L expenses. PROVISIONAL - formula unapproved.",
         source="PL_Expense_Input.csv", transformation="cm2_block()",
         tabs="P&L", owner="Finance", basis="NSV",
         limits="PL_Expense_Input.csv holds 3 EXAMPLE rows only; expense ratio 0.1% is not real."),
    dict(name="CM2 total expense", path="cm2.total_expense", unit="INR Lakh", grain="FY26+FY27",
         definition="Total expense entering CM2.", source="PL_Expense_Input.csv",
         transformation="cm2_block()", tabs="P&L", owner="Finance", basis="Absolute",
         limits="Example data. Real Q1 FY27 evidence is ~30x this."),
    dict(name="P&L blended discount %", path="pnl.blended_discount_pct", unit="percent",
         grain="FY", definition="(MRP - NSV) / MRP across chains.",
         source="Pre-aggregated P&L workbook", transformation="pnl_block()",
         tabs="P&L", owner="Finance", basis="MRP",
         limits="Pre-agg window ends Mar-26."),
    dict(name="TOT %", path="tot.blended_tot_pct", unit="percent", grain="FY",
         definition="Trade-on-total / on-invoice margin passed to the chain.",
         source="Article-level primary", transformation="tot_block()",
         tabs="P&L, Primary", owner="Finance", basis="NSV",
         limits="Already netted out of NSV -- must never be deducted again in CM2."),
    dict(name="Distribution gap (annualised)", path="dist_gap.total_addon_ann", unit="INR Lakh",
         grain="FY", definition="Annualised opportunity from closing distribution gaps.",
         source="TDP / store universe", transformation="dist_gap_block()",
         tabs="Distribution", owner="Trade Marketing", basis="NSV",
         limits="Modelled opportunity, not booked sales."),
]


def build() -> tuple[list[dict], list[Finding]]:
    dash = load_dash()
    findings: list[Finding] = []
    rows: list[dict] = []

    for m in METRICS:
        node, resolved, missing = dash, True, None
        for part in m["path"].split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                resolved, missing = False, part
                break

        value = node if resolved and not isinstance(node, (dict, list)) else (
            f"<{type(node).__name__}>" if resolved else "")

        rows.append({
            "Metric": m["name"], "Dashboard_Path": m["path"],
            "Current_Value": value, "Unit": m["unit"], "Grain": m["grain"],
            "Calculation_Basis": m["basis"], "Definition": m["definition"],
            "Source": m["source"], "Transformation": m["transformation"],
            "Consumers_Tabs": m["tabs"], "Business_Owner": m["owner"],
            "Resolved": "YES" if resolved else "NO",
            "Known_Limitations": m["limits"],
        })

        if not resolved:
            findings.append(Finding(
                id=f"REG-UNRESOLVED-{m['name'].replace(' ', '-').upper()}",
                skill="metric_registry", category="lineage", severity="FAIL",
                summary=f"Registry metric '{m['name']}' no longer resolves in data.js",
                evidence=f"path {m['path']} broke at segment {missing!r}",
                location=f"dashboard/data.js:{m['path']}", owner=m["owner"],
                remediation="A block was renamed or removed. Fix the path or retire the metric."))

    # Basis hygiene: an MRP-based metric must not silently be documented as NSV.
    for r in rows:
        if "mrp" in r["Dashboard_Path"].lower() and r["Calculation_Basis"] == "NSV":
            findings.append(Finding(
                id=f"REG-BASIS-{r['Metric'].replace(' ', '-').upper()}",
                skill="metric_registry", category="unit_basis", severity="WARN",
                summary=f"'{r['Metric']}' reads an MRP field but declares an NSV basis",
                location=r["Dashboard_Path"], owner=r["Business_Owner"],
                remediation="Confirm the intended basis; MRP/NSV confusion changes results ~2.3x."))

    resolved_n = sum(1 for r in rows if r["Resolved"] == "YES")
    findings.append(Finding(
        id="REG-SUMMARY", skill="metric_registry", category="lineage",
        severity="PASS" if resolved_n == len(rows) else "FAIL",
        summary=f"{resolved_n}/{len(rows)} registered metrics resolve against data.js"))
    return rows, findings


def lineage_rows() -> list[dict]:
    """Flat lineage edges for the Data Lineage Map output."""
    out = []
    for m in METRICS:
        for stage, node in (("1_source", m["source"]),
                            ("2_transformation", m["transformation"]),
                            ("3_output", f"data.js:{m['path']}"),
                            ("4_consumer", m["tabs"])):
            out.append({"Metric": m["name"], "Stage": stage, "Node": node,
                        "Unit": m["unit"], "Basis": m["basis"]})
    return out
