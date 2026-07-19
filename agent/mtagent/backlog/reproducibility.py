"""Reproducibility Skill.

Compares two run snapshots on normalized business content, not raw file
bytes -- a timestamp or run-order difference is an EXPECTED technical
difference; a changed row count, total, or mapping version is an
UNEXPECTED business-data difference. Generic and testable on its own;
applying it to a real June'26 rerun requires JUN26-V3 (the actual source
files) to exist first -- see the backlog table.
"""
from __future__ import annotations

from dataclasses import dataclass, field

REPRODUCIBLE = "REPRODUCIBLE"
NON_REPRODUCIBLE = "NON_REPRODUCIBLE"

# Fields whose difference is expected and does not affect reproducibility.
_EXPECTED_TECHNICAL_FIELDS = ("run_id", "created_timestamp", "output_hash")
# Fields whose difference means the underlying business result changed.
_BUSINESS_FIELDS = ("source_hashes", "rule_version", "mapping_version", "row_count",
                     "nsv_total", "qty_total", "canonical_chain_count", "exception_count",
                     "output_schema", "reconciliation_status")


@dataclass
class RunSnapshot:
    run_id: str
    created_timestamp: str
    source_hashes: dict
    rule_version: str
    mapping_version: str
    row_count: int
    nsv_total: float
    qty_total: float
    canonical_chain_count: int
    exception_count: int
    output_schema: list
    output_hash: str
    reconciliation_status: str


@dataclass
class ReproducibilityReport:
    verdict: str
    expected_technical_differences: list
    unexpected_business_differences: list


def compare(a: RunSnapshot, b: RunSnapshot) -> ReproducibilityReport:
    expected = []
    unexpected = []
    for field_name in _EXPECTED_TECHNICAL_FIELDS:
        va, vb = getattr(a, field_name), getattr(b, field_name)
        if va != vb:
            expected.append(f"{field_name}: '{va}' vs '{vb}' (expected to differ between runs)")
    for field_name in _BUSINESS_FIELDS:
        va, vb = getattr(a, field_name), getattr(b, field_name)
        if va != vb:
            unexpected.append(f"{field_name}: '{va}' vs '{vb}'")
    verdict = NON_REPRODUCIBLE if unexpected else REPRODUCIBLE
    return ReproducibilityReport(verdict, expected, unexpected)


def format_report(report: ReproducibilityReport) -> str:
    lines = [f"Reproducibility verdict: {report.verdict}", ""]
    lines.append("Expected technical differences:")
    lines += [f"  - {d}" for d in report.expected_technical_differences] or ["  - (none)"]
    lines.append("")
    lines.append("Unexpected business-data differences:")
    lines += [f"  - {d}" for d in report.unexpected_business_differences] or ["  - (none)"]
    return "\n".join(lines)
