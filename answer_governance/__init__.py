"""
Answer Governance Layer for MT Dashboard.

An independent, optional validation and evidence layer that reads existing
governed outputs (dashboard/data.js) and classifies numerical answers by
confidence, evidence, and claim safety.  It never modifies, replaces, or
recalculates the underlying business data.
"""
from answer_governance.confidence import ConfidenceStatus, classify_confidence
from answer_governance.evidence import build_evidence, Governed
from answer_governance.claim_guard import guard_claim
from answer_governance.period_completeness import period_months, check_period
from answer_governance.govern import govern_answer

__all__ = [
    "ConfidenceStatus",
    "classify_confidence",
    "build_evidence",
    "Governed",
    "guard_claim",
    "period_months",
    "check_period",
    "govern_answer",
]
