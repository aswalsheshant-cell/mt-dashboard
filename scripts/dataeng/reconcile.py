"""Skill: reconciliation — Phase 8.

Additivity checks across every rollup in data.js: does each dimensional
breakdown sum back to its own declared total?

The rounding discipline here is the important part. A component difference is
compared against the MAXIMUM THEORETICAL ROUNDING difference for that rollup
(row count x half-ulp at the stored precision). Anything larger is reported as
a coverage or duplication defect -- never dismissed as rounding.
"""
from __future__ import annotations

from decimal import Decimal

from .core import D, Finding, load_dash, q2

HALF_ULP = Decimal("0.005")     # values are stored at 2 dp


def max_rounding_l(n_rows: int) -> Decimal:
    """Largest difference attributable to rounding alone across n rows."""
    return Decimal(n_rows) * HALF_ULP


def check_rollup(name: str, rows: list[dict], field: str, total: Decimal,
                 owner: str, decision_ref: str = "") -> Finding:
    """One additivity check with an explicit rounding ceiling."""
    n = len(rows or [])
    got = sum((D(r.get(field)) for r in rows or []), Decimal(0))
    diff = got - total
    ceiling = max_rounding_l(n)

    if abs(diff) <= ceiling:
        sev, cat = "PASS", "additivity"
        summary = f"{name}: {field} sums to total (diff {q2(diff)} L within {q2(ceiling)} L rounding ceiling)"
        rem = ""
    else:
        sev, cat = "WARN", "coverage_gap"
        ratio = (abs(diff) / ceiling) if ceiling else Decimal("999")
        summary = (f"{name}: {field} sum differs from total by {q2(diff)} L "
                   f"-- {q2(ratio)}x the {q2(ceiling)} L rounding ceiling, so NOT rounding")
        rem = ("Classify as coverage gap, missing mapping, duplicate allocation or "
               "unallocated bucket. Do not label rounding.")
    return Finding(
        id=f"RECON-{name.upper().replace('.', '-')}-{field.upper()}",
        skill="reconciliation", category=cat, severity=sev, summary=summary,
        evidence=f"sum={q2(got)} total={q2(total)} rows={n} ceiling={q2(ceiling)}",
        amount_l=str(q2(diff)), location=f"dashboard/data.js:{name}",
        owner=owner, decision_ref=decision_ref, remediation=rem)


def run() -> list[Finding]:
    dash = load_dash()
    out: list[Finding] = []

    # ---- CM2 ----
    cm2 = dash.get("cm2", {})
    if cm2:
        out.append(check_rollup("cm2.by_chain", cm2.get("by_chain", []), "expense",
                                D(cm2.get("total_expense")), "Finance"))
        out.append(check_rollup("cm2.by_brand", cm2.get("by_brand", []), "expense",
                                D(cm2.get("total_expense")), "Finance", "CM2-BRAND-EXPENSE-001"))
        out.append(check_rollup("cm2.by_chain", cm2.get("by_chain", []), "nsv",
                                D(cm2.get("total_nsv")), "Dashboard team", "D13"))
        out.append(check_rollup("cm2.by_brand", cm2.get("by_brand", []), "nsv",
                                D(cm2.get("total_nsv")), "Dashboard team"))
        # arithmetic identity
        ident = D(cm2.get("total_nsv")) - D(cm2.get("total_expense")) - D(cm2.get("cm2_value"))
        out.append(Finding(
            id="RECON-CM2-IDENTITY", skill="reconciliation", category="identity",
            severity="PASS" if abs(ident) <= Decimal("0.01") else "FAIL",
            summary=f"CM2 identity NSV - expense = cm2_value (residual {q2(ident)} L)",
            evidence=f"{cm2.get('total_nsv')} - {cm2.get('total_expense')} vs {cm2.get('cm2_value')}",
            amount_l=str(q2(ident)), location="dashboard/data.js:cm2", owner="Finance"))

    # ---- FY27 primary ----
    fy27 = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27", {})
    if fy27:
        total = D(fy27.get("nsv"))
        monthly = sum((D(v) for v in fy27.get("monthly") or []), Decimal(0))
        out.append(Finding(
            id="RECON-FY27-MONTHLY", skill="reconciliation", category="additivity",
            severity="PASS" if abs(monthly - total) <= max_rounding_l(12) else "WARN",
            summary=f"FY27 monthly series sums to FY total (diff {q2(monthly - total)} L)",
            evidence=f"monthly={q2(monthly)} nsv={q2(total)}", amount_l=str(q2(monthly - total)),
            location="dashboard/data.js:detail_meta.fyx_primary.FY27", owner="Sales MIS"))
        for dim in ("by_brand", "by_channel", "by_zone", "by_chain"):
            if fy27.get(dim):
                out.append(check_rollup(f"fyx_primary.FY27.{dim}", fy27[dim], "nsv",
                                        total, "Sales MIS"))

    # ---- Offtake, per FY tag, derived not hardcoded ----
    off = dash.get("offtake", {})
    for tag in off.get("fy_tags", []) or []:
        total = D(off.get(f"total_{tag}"))
        monthly = sum((D(v) for v in off.get(f"monthly_{tag}") or []), Decimal(0))
        n = len(off.get(f"monthly_{tag}") or [])
        diff = monthly - total
        out.append(Finding(
            id=f"RECON-OFFTAKE-{tag.upper()}", skill="reconciliation", category="additivity",
            severity="PASS" if abs(diff) <= max_rounding_l(n) else "WARN",
            summary=f"Offtake {tag}: monthly sums to total (diff {q2(diff)} L)",
            evidence=f"monthly={q2(monthly)} total={q2(total)} months={n}",
            amount_l=str(q2(diff)), location=f"dashboard/data.js:offtake.total_{tag}",
            owner="Trade Marketing"))
        chain_sum = sum((D(c.get(tag)) for c in off.get("by_chain", []) or []), Decimal(0))
        out.append(check_rollup(f"offtake.by_chain[{tag}]", off.get("by_chain", []), tag,
                                total, "Trade Marketing"))

    # ---- Primary pre-agg FYs ----
    prim = dash.get("primary", {})
    for tag in ("fy25", "fy26"):
        total = D(prim.get(f"nsv_{tag}"))
        if not total:
            continue
        monthly = sum((D(v) for v in prim.get(f"monthly_{tag}") or []), Decimal(0))
        diff = monthly - total
        out.append(Finding(
            id=f"RECON-PRIMARY-{tag.upper()}-MONTHLY", skill="reconciliation",
            category="additivity",
            severity="PASS" if abs(diff) <= max_rounding_l(12) else "WARN",
            summary=f"Primary {tag}: monthly sums to FY total (diff {q2(diff)} L)",
            evidence=f"monthly={q2(monthly)} nsv={q2(total)} "
                     f"(known: excluded brands are removed from the monthly pre-agg)",
            amount_l=str(q2(diff)), location=f"dashboard/data.js:primary.nsv_{tag}",
            owner="Sales MIS"))

    return out
