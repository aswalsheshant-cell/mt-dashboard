"""Reconciliation framework: compares "current production" (what
dashboard/index.html actually computes and displays today, replicated
here read-only) against "canonical" (this package's metric functions),
and produces a structured report -- never silently passing an unexplained
difference.

This intentionally does NOT import dashboard/index.html or execute any
JS. It replicates the specific JS expressions being reconciled, in Python,
directly from the same certified data.js both "sides" read -- mirroring
the same technique tests/test_pr193_reconciliation.py already used and
that this repo's certification reports already trust.
"""
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .policies import NotAvailable, is_available
from .units import round_lakh


@dataclass
class ReconciliationRow:
    metric: str
    scope: str
    existing_value: Any
    canonical_value: Any
    variance: Optional[float]
    variance_pct: Optional[float]
    tolerance: float
    expected_difference: bool
    reason: str
    result: str  # "PASS" | "FAIL" | "GOVERNED"

    def as_dict(self):
        return {
            "metric": self.metric,
            "scope": self.scope,
            "existing_value": _fmt(self.existing_value),
            "canonical_value": _fmt(self.canonical_value),
            "variance": self.variance,
            "variance_pct": self.variance_pct,
            "tolerance": self.tolerance,
            "expected_difference": self.expected_difference,
            "reason": self.reason,
            "result": self.result,
        }


def _fmt(v):
    if isinstance(v, NotAvailable):
        return f"NOT_AVAILABLE ({v.reason})"
    return v


def reconcile_one(metric, scope, existing_value, canonical_value, tolerance=0.01,
                   expected_difference=False, reason=""):
    """Compare one (existing, canonical) pair. Both may be a real number or
    a NotAvailable. Rules:
      - both NotAvailable -> PASS (they agree that it's missing)
      - existing real, canonical NotAvailable (or vice versa) -> FAIL,
        UNLESS expected_difference=True with a reason given (e.g. this is
        exactly KI-OFFTAKE-001's governed case: existing had a real-looking
        but WRONG number; canonical correctly reports NOT_AVAILABLE)
      - both real -> variance = |existing - canonical|; PASS if within
        tolerance, else FAIL unless expected_difference=True with a reason
    Never silently marks an unexplained variance as PASS: expected_difference
    without a non-empty reason raises, on the principle that a governed
    exception must be named, not merely flagged.
    """
    if expected_difference and not reason:
        raise ValueError("expected_difference=True requires a non-empty reason")

    ex_avail, ca_avail = is_available(existing_value), is_available(canonical_value)

    if not ex_avail and not ca_avail:
        return ReconciliationRow(metric, scope, existing_value, canonical_value,
                                  None, None, tolerance, False,
                                  reason or "both sources report NOT_AVAILABLE", "PASS")

    if ex_avail != ca_avail:
        result = "GOVERNED" if expected_difference else "FAIL"
        return ReconciliationRow(metric, scope, existing_value, canonical_value,
                                  None, None, tolerance, expected_difference,
                                  reason or "availability mismatch, unexplained", result)

    variance = round_lakh(abs(float(existing_value) - float(canonical_value)))
    base = abs(float(existing_value)) or 1.0
    variance_pct = round_lakh(variance / base * 100, 4) if variance is not None else None
    within_tolerance = variance is not None and variance <= tolerance
    if within_tolerance:
        result = "PASS"
    elif expected_difference:
        result = "GOVERNED"
    else:
        result = "FAIL"
    return ReconciliationRow(metric, scope, existing_value, canonical_value,
                              variance, variance_pct, tolerance, expected_difference,
                              reason or ("within tolerance" if within_tolerance else "UNEXPLAINED"),
                              result)


def summarize(rows):
    """Overall pass/fail: FAIL if any row is FAIL. GOVERNED rows do not
    fail the gate (they are explicitly named, reasoned exceptions), but are
    reported separately from clean PASSes so they stay visible."""
    fails = [r for r in rows if r.result == "FAIL"]
    governed = [r for r in rows if r.result == "GOVERNED"]
    passes = [r for r in rows if r.result == "PASS"]
    return {
        "total": len(rows),
        "pass": len(passes),
        "governed": len(governed),
        "fail": len(fails),
        "overall": "FAIL" if fails else "PASS",
    }
