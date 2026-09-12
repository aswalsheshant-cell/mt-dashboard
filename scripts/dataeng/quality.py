"""Skill: data_quality — Phase 5.

Value-level checks over the published data.js: NaN/Infinity, blank dimensions,
excluded-brand leakage, unexpected signs, and month-on-month movement outliers.
Movement thresholds flag for review; they never auto-correct.
"""
from __future__ import annotations

import math
from decimal import Decimal

from .core import D, EXCLUDED_BRANDS, Finding, load_dash, q2, walk_numbers

# A month-on-month swing beyond this is worth a human look, not an error.
MOM_ALERT_PCT = Decimal("40")


def _nan_inf(dash: dict, findings: list[Finding]) -> None:
    bad = []
    for path, v in walk_numbers(dash):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            bad.append(path)
        elif isinstance(v, str) and v.strip().lower() in {"nan", "inf", "-inf", "undefined"}:
            bad.append(path)
        if len(bad) >= 25:
            break
    if bad:
        findings.append(Finding(
            id="DQ-NANINF", skill="data_quality", category="null_propagation",
            severity="FAIL", summary=f"{len(bad)}+ NaN/Infinity/undefined values in data.js",
            evidence="; ".join(bad[:5]), location="dashboard/data.js",
            owner="Dashboard team", remediation="Trace the producing block and fix the source join."))


def _excluded_brand_leak(dash: dict, findings: list[Finding]) -> None:
    """Excluded brands must never appear in any aggregation."""
    checks = [
        ("primary.by_brand", dash.get("primary", {}).get("by_brand", [])),
        ("cm2.by_brand", dash.get("cm2", {}).get("by_brand", [])),
        ("detail_meta.fyx_primary.FY27.by_brand",
         dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27", {}).get("by_brand", [])),
    ]
    dims_brand = dash.get("dims", {}).get("Brand", []) or []
    checks.append(("dims.Brand", [{"name": b} for b in dims_brand]))

    for where, rows in checks:
        for r in rows or []:
            nm = str(r.get("name", "")).strip().lower()
            if nm in EXCLUDED_BRANDS:
                findings.append(Finding(
                    id=f"DQ-EXCLBRAND-{where.replace('.', '-')}-{nm}",
                    skill="data_quality", category="excluded_brand", severity="FAIL",
                    summary=f"Excluded brand '{r.get('name')}' present in {where}",
                    location=f"dashboard/data.js:{where}", owner="Dashboard team",
                    remediation="Rebuild with the exclusion applied; preserve records in PowerBI/Excluded_Data/."))


def _blank_dimensions(dash: dict, findings: list[Finding]) -> None:
    """Blank/unmapped dimension buckets must stay visible and be sized."""
    for where, rows in (("cm2.by_chain", dash.get("cm2", {}).get("by_chain", [])),
                        ("cm2.by_brand", dash.get("cm2", {}).get("by_brand", [])),
                        ("primary.by_brand", dash.get("primary", {}).get("by_brand", []))):
        for r in rows or []:
            nm = str(r.get("name", ""))
            if not nm.strip() or "unmapped" in nm.lower() or "blank" in nm.lower():
                amt = D(r.get("nsv") or r.get("value"))
                findings.append(Finding(
                    id=f"DQ-BLANKDIM-{where.replace('.', '-')}-{nm.strip() or 'EMPTY'}",
                    skill="data_quality", category="blank_dimension", severity="WARN",
                    summary=f"Unmapped/blank bucket in {where}: {nm.strip() or '(empty name)'}",
                    amount_l=str(q2(amt)), location=f"dashboard/data.js:{where}",
                    owner="Sales MIS",
                    remediation="Keep the bucket visible until mapped to zero; never filter it out."))


def _negative_and_movement(dash: dict, findings: list[Finding]) -> None:
    """Negative aggregates are legitimate (returns) but must be surfaced;
    large month-on-month swings are flagged for review."""
    fy27 = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27", {})
    series = [(lbl, D(v)) for lbl, v in
              zip(fy27.get("months_covered") or [], fy27.get("monthly") or [])]
    # months_covered may be shorter than monthly; fall back to index labels
    if not series:
        series = [(f"m{i}", D(v)) for i, v in enumerate(fy27.get("monthly") or [])]

    prev = None
    for lbl, val in series:
        if val < 0:
            findings.append(Finding(
                id=f"DQ-NEGMONTH-{lbl}", skill="data_quality", category="unexpected_negative",
                severity="WARN", summary=f"FY27 primary NSV is negative in {lbl}",
                amount_l=str(q2(val)), location="dashboard/data.js:detail_meta.fyx_primary.FY27.monthly",
                owner="Sales MIS", remediation="Confirm returns exceed dispatch for the month."))
        if prev and prev[1] and val:
            change = (val - prev[1]) / abs(prev[1]) * Decimal(100)
            if abs(change) > MOM_ALERT_PCT:
                findings.append(Finding(
                    id=f"DQ-MOM-{lbl}", skill="data_quality", category="distribution_shift",
                    severity="INFO",
                    summary=f"FY27 primary NSV moved {q2(change)}% from {prev[0]} to {lbl}",
                    evidence=f"{q2(prev[1])} -> {q2(val)} L", amount_l=str(q2(val - prev[1])),
                    owner="Sales MIS", remediation="Review for a source-coverage change."))
        if val:
            prev = (lbl, val)


def _chain_visibility(dash: dict, findings: list[Finding]) -> None:
    """Chains present in dims but absent from a rollup are being dropped."""
    dims_chain = set(dash.get("dims", {}).get("Chain", []) or [])
    cm2_chain = {r.get("name") for r in dash.get("cm2", {}).get("by_chain", []) or []}
    dropped = sorted(dims_chain - cm2_chain)
    if dropped:
        findings.append(Finding(
            id="DQ-CHAINDROP", skill="data_quality", category="coverage_gap", severity="WARN",
            summary=f"{len(dropped)} chain(s) in dims.Chain are absent from cm2.by_chain",
            evidence=", ".join(dropped[:6]),
            location="dashboard/data.js:cm2.by_chain", owner="Dashboard team",
            decision_ref="D13",
            remediation="Retain a chain whenever any source record exists, including net-negative ones."))


def run() -> list[Finding]:
    dash = load_dash()
    findings: list[Finding] = []
    _nan_inf(dash, findings)
    _excluded_brand_leak(dash, findings)
    _blank_dimensions(dash, findings)
    _negative_and_movement(dash, findings)
    _chain_visibility(dash, findings)
    if not findings:
        findings.append(Finding(id="DQ-OK", skill="data_quality", category="quality",
                                severity="PASS", summary="All data-quality checks passed"))
    return findings
