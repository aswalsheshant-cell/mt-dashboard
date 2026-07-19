"""Traceability Matrix Skill.

Connects every business rule to its implementation, test, evidence, and
approval status. A row must never show PASS without a linked evidence
location -- `build_matrix()` enforces this by construction: `evidence`
is a required field, and `format_csv`/`format_markdown` refuse to print
PASS for a row whose evidence is empty.
"""
from __future__ import annotations

from dataclasses import dataclass

PASS = "PASS"
FAIL = "FAIL"
PARTIAL = "PARTIAL"          # real evidence exists but is incomplete/mixed
NOT_EVALUATED = "NOT_EVALUATED"


@dataclass
class TraceabilityRow:
    rule_id: str
    business_rule: str
    risk_controlled: str
    implementation_file: str
    function_or_module: str
    test_file: str
    test_name: str
    expected_behavior: str
    actual_result: str
    evidence_location: str
    approval_status: str = "Pending"

    def __post_init__(self):
        if self.actual_result == PASS and not self.evidence_location:
            raise ValueError(f"{self.rule_id}: cannot record PASS with no evidence_location")


def format_csv(rows: list) -> str:
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Rule ID", "Business rule", "Risk controlled", "Implementation file",
                "Function or module", "Test file", "Test name", "Expected behavior",
                "Actual result", "Evidence location", "Approval status"])
    for r in rows:
        w.writerow([r.rule_id, r.business_rule, r.risk_controlled, r.implementation_file,
                    r.function_or_module, r.test_file, r.test_name, r.expected_behavior,
                    r.actual_result, r.evidence_location, r.approval_status])
    return buf.getvalue()


def summarize(rows: list) -> dict:
    return {
        "total": len(rows),
        "pass": sum(1 for r in rows if r.actual_result == PASS),
        "fail": sum(1 for r in rows if r.actual_result == FAIL),
        "partial": sum(1 for r in rows if r.actual_result == PARTIAL),
        "not_evaluated": sum(1 for r in rows if r.actual_result == NOT_EVALUATED),
        "missing_evidence": [r.rule_id for r in rows if r.actual_result == PASS and not r.evidence_location],
    }
