"""
Deterministic, rule-based confidence classifier for MT Dashboard answers.

Every classification is derived from governed metadata already present
in dashboard/data.js — no AI inference, no probabilistic scoring.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from answer_governance.models import ConfidenceStatus


def classify_confidence(
    *,
    metric_exists: bool,
    period_complete: bool,
    reconciliation_passed: bool,
    is_representative: bool = False,
    is_capped: bool = False,
    is_forecast: bool = False,
    is_estimated: bool = False,
    has_pending_approval: bool = False,
    has_fallback_dependency: bool = False,
    has_unmapped_records: bool = False,
    allocation_coverage_pct: Optional[float] = None,
    value_coverage_pct: Optional[float] = None,
    reconciliation_variance: Optional[float] = None,
    reconciliation_tolerance: float = 1.0,
    missing_required_source: bool = False,
    unsupported_filter: bool = False,
    warnings: Optional[List[str]] = None,
) -> ConfidenceStatus:
    """Classify the confidence of a governed answer.

    Returns one of: CONFIRMED, HIGH_CONFIDENCE, PROVISIONAL, BLOCKED.

    Classification is deterministic and rule-based:

    BLOCKED — any of:
      - metric does not exist
      - required source is missing
      - reconciliation variance exceeds tolerance
      - unsupported filter for this metric's grain

    PROVISIONAL — any of:
      - forecast / estimated / fallback-dependent value
      - pending Finance approval
      - incomplete period
      - representative / capped dataset
      - material unmapped records

    HIGH_CONFIDENCE — all CONFIRMED gates pass except:
      - a documented minor limitation exists (e.g. rounding gap < tolerance,
        allocation coverage < 100% but above 50%)

    CONFIRMED — all of:
      - metric exists
      - period complete
      - reconciliation passed within tolerance
      - not representative, capped, estimated, forecast, pending approval
      - no material unmapped records
      - no fallback dependencies
    """
    if not metric_exists or missing_required_source:
        return ConfidenceStatus.BLOCKED

    if unsupported_filter:
        return ConfidenceStatus.BLOCKED

    if reconciliation_variance is not None:
        if abs(reconciliation_variance) > reconciliation_tolerance:
            return ConfidenceStatus.BLOCKED

    if is_forecast or is_estimated:
        return ConfidenceStatus.PROVISIONAL

    if has_pending_approval:
        return ConfidenceStatus.PROVISIONAL

    if not period_complete:
        return ConfidenceStatus.PROVISIONAL

    if is_representative or is_capped:
        return ConfidenceStatus.PROVISIONAL

    if has_fallback_dependency:
        return ConfidenceStatus.PROVISIONAL

    if has_unmapped_records:
        if allocation_coverage_pct is not None and allocation_coverage_pct < 50.0:
            return ConfidenceStatus.PROVISIONAL
        return ConfidenceStatus.HIGH_CONFIDENCE

    if allocation_coverage_pct is not None and allocation_coverage_pct < 100.0:
        return ConfidenceStatus.HIGH_CONFIDENCE

    if value_coverage_pct is not None and value_coverage_pct < 99.0:
        return ConfidenceStatus.HIGH_CONFIDENCE

    if reconciliation_variance is not None and abs(reconciliation_variance) > 0.01:
        return ConfidenceStatus.HIGH_CONFIDENCE

    return ConfidenceStatus.CONFIRMED
