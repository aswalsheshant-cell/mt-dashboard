"""
Claim guard — prevents unsupported accuracy and certainty claims.

Scans a textual answer for phrases that overstate confidence and either
blocks them or rewrites them into evidence-based statements.
"""
from __future__ import annotations
import re
from typing import Optional

from answer_governance.models import ConfidenceStatus

_UNSAFE_PATTERNS = [
    (re.compile(r"\b100\s*%\s*accurate\b", re.I), "classified as {status} for the available period"),
    (re.compile(r"\bfully\s+correct\b", re.I), "classified as {status} based on governed evidence"),
    (re.compile(r"\bguaranteed\b", re.I), "supported by governed reconciliation ({status})"),
    (re.compile(r"\bexact\s+(?:number|figure|value|total)\b", re.I),
     "governed value ({status}; see reconciliation and coverage)"),
    (re.compile(r"\bfinance[- ]approved\b", re.I), "{approval_note}"),
    (re.compile(r"\bperfect(?:ly)?\s+(?:accurate|correct|right)\b", re.I),
     "classified as {status} within reconciliation tolerance"),
    (re.compile(r"\bno\s+(?:error|issue|problem|limitation)s?\b", re.I),
     "governed with documented assumptions and exclusions ({status})"),
]


def guard_claim(
    text: str,
    status: ConfidenceStatus,
    approval_status: str = "",
) -> str:
    """Rewrite unsafe certainty claims into evidence-based statements.

    Preserves legitimate business terminology from source data (e.g.,
    "Finance Approved" when it genuinely appears in a source field) by
    only rewriting when the claim is about the *answer's* accuracy.
    """
    approval_note = (
        f"Finance approval status: {approval_status}"
        if approval_status
        else "Finance approval status not confirmed"
    )

    result = text
    for pattern, replacement_template in _UNSAFE_PATTERNS:
        replacement = replacement_template.format(
            status=status.value,
            approval_note=approval_note,
        )
        result = pattern.sub(replacement, result)

    return result


def is_safe_claim(text: str) -> bool:
    """Check whether a text contains any unsafe certainty claims."""
    for pattern, _ in _UNSAFE_PATTERNS:
        if pattern.search(text):
            return False
    return True


def format_status_statement(
    metric: str,
    status: ConfidenceStatus,
    reason: str,
) -> str:
    """Produce a safe, evidence-based status statement for a metric."""
    if status == ConfidenceStatus.CONFIRMED:
        return (
            f"{metric} is classified as CONFIRMED because {reason}."
        )
    if status == ConfidenceStatus.HIGH_CONFIDENCE:
        return (
            f"{metric} is classified as HIGH CONFIDENCE. {reason}."
        )
    if status == ConfidenceStatus.PROVISIONAL:
        return (
            f"{metric} is classified as PROVISIONAL because {reason}. "
            "Treat as indicative until the limitation is resolved."
        )
    return (
        f"{metric} is BLOCKED: {reason}. "
        "A governed answer cannot be produced until the blocker is resolved."
    )
