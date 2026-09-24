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

Result states: PASS, APPROVED_GOVERNED, FAIL, UNKNOWN.
  - PASS: within tolerance, no exception needed.
  - APPROVED_GOVERNED: a variance that matches a reviewed, documented
    record in governance.APPROVED_EXCEPTIONS -- named owner, evidence,
    business/financial impact, temporary/permanent, resolution phase,
    release-blocker call. Never just a reason string a caller happened
    to pass in.
  - FAIL: a real variance beyond tolerance, no matching exception.
  - UNKNOWN: a caller marked this expected_difference=True but no
    governance registry entry matches it. Treated as failing the release
    gate exactly like FAIL -- an un-registered "expected difference" is
    not a softer category, it is a reconciliation gap that has not been
    reviewed yet.
"""
from dataclasses import dataclass
from typing import Any, Optional

from . import governance
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
    result: str  # "PASS" | "APPROVED_GOVERNED" | "FAIL" | "UNKNOWN"
    exception: Optional[governance.ApprovedException] = None

    def as_dict(self):
        d = {
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
        if self.exception is not None:
            d["governance"] = self.exception.as_dict()
        return d


def _fmt(v):
    if isinstance(v, NotAvailable):
        return f"NOT_AVAILABLE ({v.reason})"
    return v


def reconcile_one(metric, scope, existing_value, canonical_value, tolerance=0.01,
                   expected_difference=False, reason=""):
    """Compare one (existing, canonical) pair. Both may be a real number or
    a NotAvailable.

    If expected_difference=True, this function looks up
    governance.find_approved_exception(metric, scope): a match produces
    APPROVED_GOVERNED (with the full registry record attached); no match
    produces UNKNOWN, regardless of how good `reason` sounds -- a caller
    cannot self-certify an exception by writing a persuasive string, only
    by having it reviewed into the registry first.
    """
    if expected_difference and not reason:
        raise ValueError("expected_difference=True requires a non-empty reason")

    ex_avail, ca_avail = is_available(existing_value), is_available(canonical_value)

    if not ex_avail and not ca_avail:
        if not expected_difference:
            # The ordinary case: nothing to compare, nothing claimed --
            # a quiet, genuine agreement that the value is missing on
            # both sides. Auto-PASS.
            return ReconciliationRow(metric, scope, existing_value, canonical_value,
                                      None, None, tolerance, False,
                                      reason or "both sources report NOT_AVAILABLE", "PASS")
        # A caller explicitly flagged this as a finding worth recording
        # (e.g. "canonical has no real source for this metric at all") --
        # route it through the same governance-required path as any other
        # non-clean case below, rather than letting it disappear into a
        # generic auto-PASS. This is what keeps RBC_OFFTAKE_NSV's honest
        # unavailability a visible, reviewed record (GOV-004) instead of a
        # silently-passing row indistinguishable from a trivial double-NA.
        variance, variance_pct, clean = None, None, False
    elif ex_avail != ca_avail:
        # One side has a real value, the other reports NOT_AVAILABLE -- this
        # is NEVER automatically clean. It must either match a registered
        # exception (KI-OFFTAKE-001's whole point: existing has a real-
        # looking number, canonical correctly says NOT_AVAILABLE) or it is
        # a genuine, unexplained availability mismatch -- FAIL/UNKNOWN below,
        # same as a numeric variance beyond tolerance.
        variance, variance_pct, clean = None, None, False
    else:
        variance = round_lakh(abs(float(existing_value) - float(canonical_value)))
        base = abs(float(existing_value)) or 1.0
        variance_pct = round_lakh(variance / base * 100, 4) if variance is not None else None
        clean = variance is not None and variance <= tolerance

    if clean:
        return ReconciliationRow(metric, scope, existing_value, canonical_value,
                                  variance, variance_pct, tolerance, False,
                                  reason or "within tolerance", "PASS")

    if not expected_difference:
        return ReconciliationRow(metric, scope, existing_value, canonical_value,
                                  variance, variance_pct, tolerance, False,
                                  reason or "UNEXPLAINED", "FAIL")

    exc = governance.find_approved_exception(metric, scope)
    if exc is None:
        return ReconciliationRow(
            metric, scope, existing_value, canonical_value, variance, variance_pct,
            tolerance, True,
            f"caller claimed expected_difference ({reason!r}) but no matching entry "
            "exists in governance.APPROVED_EXCEPTIONS -- treated as UNKNOWN, not GOVERNED",
            "UNKNOWN")

    return ReconciliationRow(metric, scope, existing_value, canonical_value,
                              variance, variance_pct, tolerance, True,
                              exc.reason_not_pass, "APPROVED_GOVERNED", exception=exc)


def summarize(rows):
    """Release-gate rule: FAIL and UNKNOWN both fail the gate. Only PASS
    and APPROVED_GOVERNED count toward a clean population."""
    fails = [r for r in rows if r.result == "FAIL"]
    unknown = [r for r in rows if r.result == "UNKNOWN"]
    governed = [r for r in rows if r.result == "APPROVED_GOVERNED"]
    passes = [r for r in rows if r.result == "PASS"]
    clean = len(passes) + len(governed)
    return {
        "total": len(rows),
        "pass": len(passes),
        "approved_governed": len(governed),
        "fail": len(fails),
        "unknown": len(unknown),
        "clean_population_pct": round_lakh(clean / len(rows) * 100, 2) if rows else None,
        "overall": "PASS" if not fails and not unknown else "FAIL",
    }
