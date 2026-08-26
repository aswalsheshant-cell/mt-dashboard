"""
Evidence builder — assembles a Governed evidence object from existing
dashboard/data.js metadata without modifying any source data.
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional

from answer_governance.models import (
    ConfidenceStatus,
    Coverage,
    Governed,
    Reconciliation,
)
from answer_governance.confidence import classify_confidence
from answer_governance.period_completeness import check_period


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def build_evidence(
    metric: str,
    period: str,
    fy_tag: str,
    dash: Dict[str, Any],
    filters: Optional[Dict[str, Any]] = None,
) -> Governed:
    """Build a governed evidence object for a metric from the DASH data.

    This function reads ONLY from the existing governed outputs in
    dashboard/data.js (passed as the parsed ``dash`` dict).  It never
    modifies any value.
    """
    filters = filters or {}
    g = Governed(metric=metric, period=period, filters=filters)

    router = {
        "primary": _primary_evidence,
        "offtake": _offtake_evidence,
        "forecast": _forecast_evidence,
        "cm2": _cm2_evidence,
        "tot": _tot_evidence,
    }

    handler = router.get(metric.lower().replace(" ", "_").replace("%", ""))
    if handler is None:
        g.status = ConfidenceStatus.BLOCKED
        g.reason = f"Unknown metric '{metric}'. Available: {', '.join(router.keys())}"
        return g

    return handler(g, fy_tag, dash, filters)


# ── Metric-specific evidence builders ────────────────────────────────────


def _primary_evidence(
    g: Governed,
    fy_tag: str,
    dash: Dict[str, Any],
    filters: Dict[str, Any],
) -> Governed:
    p = dash.get("primary", {})
    dm = dash.get("detail_meta", {})
    fyx = (dm.get("fyx_primary") or {}).get(fy_tag)
    alloc_qc = dash.get("chain_allocation_qc", {})

    is_preagg = fy_tag in ("FY25", "FY26")

    if is_preagg:
        nsv_key = f"nsv_{fy_tag.lower()}"
        val = _safe_float(p.get(nsv_key))
        if val is None:
            g.status = ConfidenceStatus.BLOCKED
            g.reason = f"Primary {fy_tag} value not found in pre-aggregated block"
            return g
        g.value = val
        g.source_paths = [f"primary.{nsv_key}"]
        g.source_periods = [fy_tag]
        g.formula_reference = f"Pre-aggregated Primary NSV from source workbook ({fy_tag})"
        g.coverage = Coverage(
            required_months=["April", "May", "June", "July", "Aug", "Sept",
                             "Oct", "Nov", "Dec", "Jan", "Feb", "March"],
            available_months=list(p.get("month_labels", [])),
            complete=True,
            value_coverage_pct=100.0,
        )
        g.reconciliation = Reconciliation(status="pre-aggregated source", variance=0.0, tolerance=1.0)
        g.status = classify_confidence(
            metric_exists=True,
            period_complete=True,
            reconciliation_passed=True,
            allocation_coverage_pct=_safe_float(alloc_qc.get("allocated_coverage_pct")),
        )
        g.reason = f"Pre-aggregated {fy_tag} Primary from governed source workbook"
        return g

    if fyx is None:
        g.status = ConfidenceStatus.BLOCKED
        g.reason = f"No Primary data for {fy_tag} in detail_meta.fyx_primary"
        return g

    g.value = _safe_float(fyx.get("nsv"))
    g.source_paths = [f"detail_meta.fyx_primary['{fy_tag}']"]
    g.source_periods = fyx.get("months_covered", [])
    g.formula_reference = (
        "Article-wise Primary NSV, chain-allocated (Dist. rows split by "
        "secondary cont%), computed from the FULL uncapped source."
    )

    available = fyx.get("months_covered", [])
    required, present, complete = check_period(g.period, fy_tag, available)
    g.coverage = Coverage(
        required_months=required,
        available_months=present,
        complete=complete,
        value_coverage_pct=_safe_float(dm.get("value_coverage_pct")),
    )

    chain_sum = sum(c.get("nsv", 0) or 0 for c in fyx.get("by_chain", []))
    zone_sum = sum(z.get("nsv", 0) or 0 for z in fyx.get("by_zone", []))
    total = _safe_float(fyx.get("nsv")) or 0.0
    chain_var = abs(chain_sum - total)
    zone_var = abs(zone_sum - total)
    recon_var = max(chain_var, zone_var)
    recon_tol = 2.0
    g.reconciliation = Reconciliation(
        status="passed" if recon_var <= recon_tol else "variance detected",
        variance=round(recon_var, 2),
        tolerance=recon_tol,
    )

    is_rep = bool(dm.get("representative"))
    alloc_cov = _safe_float(alloc_qc.get("allocated_coverage_pct"))

    if alloc_cov is not None and alloc_cov < 100.0:
        g.assumptions.append(
            f"Dist. allocation coverage is {alloc_cov}% — "
            f"remainder keeps its original single-chain tag"
        )

    g.status = classify_confidence(
        metric_exists=True,
        period_complete=complete,
        reconciliation_passed=(recon_var <= recon_tol),
        is_representative=is_rep,
        allocation_coverage_pct=alloc_cov,
        value_coverage_pct=_safe_float(dm.get("value_coverage_pct")),
        reconciliation_variance=recon_var,
        reconciliation_tolerance=recon_tol,
    )

    parts = []
    if complete:
        parts.append(f"all required months present ({', '.join(present)})")
    else:
        missing = [m for m in required if m not in present]
        parts.append(f"missing months: {', '.join(missing)}")
    parts.append(f"reconciliation variance {recon_var:.2f} L (tolerance {recon_tol} L)")
    if alloc_cov is not None:
        parts.append(f"allocation coverage {alloc_cov}%")
    g.reason = "; ".join(parts)
    return g


def _offtake_evidence(
    g: Governed,
    fy_tag: str,
    dash: Dict[str, Any],
    filters: Dict[str, Any],
) -> Governed:
    o = dash.get("offtake", {})
    total_key = f"total_{fy_tag.lower()}"
    months_key = f"months_{fy_tag.lower()}"
    monthly_key = f"monthly_{fy_tag.lower()}"

    val = _safe_float(o.get(total_key))
    if val is None:
        g.status = ConfidenceStatus.BLOCKED
        g.reason = f"No Offtake data for {fy_tag} (key '{total_key}' not found)"
        return g

    g.value = val
    g.source_paths = [f"offtake.{total_key}"]
    g.formula_reference = "Chain-wise sell-out from Offtake master workbook"

    months_labels = o.get(months_key, [])
    monthly_vals = o.get(monthly_key, [])
    g.source_periods = list(months_labels)

    available_norm = _offtake_months_to_names(months_labels)
    required, present, complete = check_period(g.period, fy_tag, available_norm)
    g.coverage = Coverage(
        required_months=required,
        available_months=present,
        complete=complete,
    )

    chain_sum = sum(c.get(fy_tag.lower(), 0) or 0 for c in o.get("by_chain", []))
    zone_sum = sum(z.get(fy_tag.lower(), 0) or 0 for z in o.get("by_zone", []))
    recon_var = max(abs(chain_sum - val), abs(zone_sum - val))
    recon_tol = 1.0
    g.reconciliation = Reconciliation(
        status="passed" if recon_var <= recon_tol else "variance detected",
        variance=round(recon_var, 2),
        tolerance=recon_tol,
    )

    bc = dash.get("reliance_bc", {})
    if bc.get("include_in_overall_offtake") is False:
        g.exclusions.append(
            f"Reliance Brand Counter (₹{bc.get('total', 0):.2f} L) excluded from overall offtake"
        )

    g.status = classify_confidence(
        metric_exists=True,
        period_complete=complete,
        reconciliation_passed=(recon_var <= recon_tol),
        reconciliation_variance=recon_var,
        reconciliation_tolerance=recon_tol,
    )

    parts = []
    if complete:
        parts.append(f"all required months present ({', '.join(present)})")
    else:
        missing = [m for m in required if m not in present]
        parts.append(f"missing months: {', '.join(missing)}")
    parts.append(f"reconciliation variance {recon_var:.2f} L")
    g.reason = "; ".join(parts)
    return g


def _forecast_evidence(
    g: Governed,
    fy_tag: str,
    dash: Dict[str, Any],
    filters: Dict[str, Any],
) -> Governed:
    fc = dash.get("forecast", {})
    if not fc:
        g.status = ConfidenceStatus.BLOCKED
        g.reason = "No forecast block in data"
        return g

    val = _safe_float(fc.get("fy27_forecast"))
    method = fc.get("method", "unknown")
    growth = _safe_float(fc.get("growth_assumption_pct"))

    g.value = val
    g.source_paths = ["forecast"]
    g.formula_reference = f"Forecast method: {method}"
    g.assumptions.append(f"Method: {method}")
    if growth is not None:
        g.assumptions.append(f"Growth assumption: {growth}%")

    g.status = ConfidenceStatus.PROVISIONAL
    g.reason = (
        f"Forecast is always PROVISIONAL — method='{method}', "
        "not a reconciled actual"
    )
    return g


def _cm2_evidence(
    g: Governed,
    fy_tag: str,
    dash: Dict[str, Any],
    filters: Dict[str, Any],
) -> Governed:
    cm2 = dash.get("cm2", {})
    if not cm2:
        g.status = ConfidenceStatus.BLOCKED
        g.reason = "No CM2 block in data"
        return g

    g.value = _safe_float(cm2.get("cm2_value"))
    g.source_paths = ["cm2"]
    g.formula_reference = "CM2 = NSV - P&L Expenses (from PL_Expense_Input.csv)"

    total_exp = _safe_float(cm2.get("total_expense"))
    if total_exp is None or total_exp == 0:
        g.assumptions.append("No real P&L expense data loaded — CM2 equals NSV")
        g.warnings.append("CM2 without expense data is not a final contribution margin")

    g.status = ConfidenceStatus.PROVISIONAL
    g.reason = (
        "CM2 is PROVISIONAL — depends on manually maintained expense input "
        "and tentative TOT% assumptions"
    )
    return g


def _tot_evidence(
    g: Governed,
    fy_tag: str,
    dash: Dict[str, Any],
    filters: Dict[str, Any],
) -> Governed:
    tot = dash.get("tot", {})
    if not tot:
        g.status = ConfidenceStatus.BLOCKED
        g.reason = "No TOT block in data"
        return g

    g.value = _safe_float(tot.get("blended_tot_pct"))
    g.source_paths = ["tot"]
    g.formula_reference = (
        "TOT% = SUM(Pass-on Value) / SUM(MRP), 3-tier priority: "
        "Source Avg Tot → Actual Tax Amount → GST Rate Table fallback"
    )

    qc = tot.get("qc_table", [])
    has_fallback = any(
        r.get("confidence", "").upper() in ("LOW", "MEDIUM")
        for r in qc if isinstance(r, dict)
    )
    has_pending = any(
        str(r.get("finance_approved", "")).upper() != "YES"
        for r in qc if isinstance(r, dict)
    )

    if has_fallback:
        g.assumptions.append(
            "Some categories use GST Rate Table fallback (LOW/MEDIUM confidence)"
        )
        g.approval_status = "Pending"
    if has_pending:
        g.assumptions.append("Finance approval pending for some GST rate assumptions")

    g.status = classify_confidence(
        metric_exists=True,
        period_complete=True,
        reconciliation_passed=True,
        has_fallback_dependency=has_fallback,
        has_pending_approval=has_pending,
    )
    g.reason = (
        "PROVISIONAL if GST fallback or pending Finance approval affects "
        "the blended TOT%; CONFIRMED only when 100% of rows use source "
        "Avg Tot or approved actual tax"
    )
    return g


def _offtake_months_to_names(labels: list) -> list:
    """Convert offtake month labels like 'Apr-26' to canonical names like 'April'."""
    _MAP = {
        "apr": "April", "may": "May", "jun": "June", "jul": "July",
        "aug": "Aug", "sep": "Sept", "oct": "Oct", "nov": "Nov",
        "dec": "Dec", "jan": "Jan", "feb": "Feb", "mar": "March",
    }
    out = []
    for label in labels:
        prefix = str(label).split("-")[0].lower().strip()
        norm = _MAP.get(prefix)
        if norm:
            out.append(norm)
    return out
