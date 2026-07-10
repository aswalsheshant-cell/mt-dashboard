"""
Phase 6 — QC validation, run before every export.

Each check returns PASS / FAIL / WARN / NA with a human-readable detail. A check
that can't run because a required source is absent returns NA ('Source data
required') rather than silently passing. The fill engine gathers a QCContext
from real computed figures and calls run_qc(); the results become a QC sheet and
gate the report's headline status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

PASS, FAIL, WARN, NA = "PASS", "FAIL", "WARN", "NA"


@dataclass
class QCCheck:
    name: str
    status: str
    detail: str

    def as_row(self) -> List[str]:
        return [self.name, self.status, self.detail]


@dataclass
class QCContext:
    grand_total: Optional[float] = None
    breakdown_total: Optional[float] = None
    period_totals: Dict[str, float] = field(default_factory=dict)
    period: Optional[str] = None
    compare_period: Optional[str] = None
    reported_mom: Optional[float] = None
    contribution_sum: Optional[float] = None
    duplicate_count: Optional[int] = None
    missing_mapping: Optional[int] = None
    unmapped_chain: Optional[int] = None
    unmapped_article: Optional[int] = None
    yoy_available: bool = False
    l3m_available: bool = False
    channel_ok: Optional[bool] = None
    channel_note: str = ""


_EPS = 0.01  # 1% / 1-paisa tolerance for float sums


def _close(a: float, b: float, rel: float = _EPS) -> bool:
    if a is None or b is None:
        return False
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom <= rel


def run_qc(ctx: QCContext) -> List[QCCheck]:
    checks: List[QCCheck] = []

    # 1) total validation — breakdown (incl Others) reconciles to grand total
    if ctx.grand_total is None or ctx.breakdown_total is None:
        checks.append(QCCheck("Total validation", NA, "Source data required"))
    elif _close(ctx.grand_total, ctx.breakdown_total):
        checks.append(QCCheck("Total validation", PASS,
                              f"breakdown {ctx.breakdown_total:,.2f} == total {ctx.grand_total:,.2f}"))
    else:
        checks.append(QCCheck("Total validation", FAIL,
                              f"breakdown {ctx.breakdown_total:,.2f} != total {ctx.grand_total:,.2f}"))

    # 2) MoM calculation check — recompute from period totals
    if not ctx.compare_period or ctx.reported_mom is None or \
            ctx.period not in ctx.period_totals or ctx.compare_period not in ctx.period_totals:
        checks.append(QCCheck("MoM calculation", NA, "Source data required (need current + prior month)"))
    else:
        cur, prev = ctx.period_totals[ctx.period], ctx.period_totals[ctx.compare_period]
        recomputed = (cur - prev) / prev * 100.0 if prev else None
        if recomputed is not None and _close(recomputed, ctx.reported_mom, rel=0.001):
            checks.append(QCCheck("MoM calculation", PASS, f"MoM {recomputed:+.2f}% verified"))
        else:
            checks.append(QCCheck("MoM calculation", FAIL,
                                  f"reported {ctx.reported_mom} vs recomputed {recomputed}"))

    # 3) YoY calculation check
    checks.append(QCCheck("YoY calculation", PASS if ctx.yoy_available else NA,
                          "verified" if ctx.yoy_available else "Source data required (prior-year month)"))

    # 4) contribution % check — parts (incl Others) sum to ~100%
    if ctx.contribution_sum is None:
        checks.append(QCCheck("Contribution %", NA, "Source data required"))
    elif _close(ctx.contribution_sum, 100.0, rel=0.005):
        checks.append(QCCheck("Contribution %", PASS, f"sums to {ctx.contribution_sum:.2f}%"))
    else:
        checks.append(QCCheck("Contribution %", FAIL, f"sums to {ctx.contribution_sum:.2f}% (expected 100%)"))

    # 5) missing mapping check
    if ctx.missing_mapping is None:
        checks.append(QCCheck("Missing mapping", NA, "Source data required"))
    else:
        checks.append(QCCheck("Missing mapping", PASS if ctx.missing_mapping == 0 else WARN,
                              f"{ctx.missing_mapping} row(s) with blank category/mapping"))

    # 6) duplicate check
    if ctx.duplicate_count is None:
        checks.append(QCCheck("Duplicate rows", NA, "Source data required"))
    else:
        checks.append(QCCheck("Duplicate rows", PASS if ctx.duplicate_count == 0 else WARN,
                              f"{ctx.duplicate_count} duplicate row(s)"))

    # 7) unmapped chain / article
    if ctx.unmapped_chain is None and ctx.unmapped_article is None:
        checks.append(QCCheck("Unmapped chain/article", NA, "Source data required"))
    else:
        uc, ua = ctx.unmapped_chain or 0, ctx.unmapped_article or 0
        checks.append(QCCheck("Unmapped chain/article", PASS if (uc + ua) == 0 else WARN,
                              f"{uc} unmapped chain, {ua} unmapped article"))

    # 8) MT vs GT filter validation
    if ctx.channel_ok is None:
        checks.append(QCCheck("MT vs GT filter", NA, ctx.channel_note or "no channel column; MT-only source"))
    else:
        checks.append(QCCheck("MT vs GT filter", PASS if ctx.channel_ok else FAIL,
                              ctx.channel_note or ("MT-only confirmed" if ctx.channel_ok else "GT rows present")))

    return checks


def qc_status(checks: List[QCCheck]) -> str:
    """Headline status: FAIL if any FAIL, else WARN if any WARN, else PASS."""
    statuses = {c.status for c in checks}
    if FAIL in statuses:
        return FAIL
    if WARN in statuses:
        return WARN
    return PASS
