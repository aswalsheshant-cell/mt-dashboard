"""Shared data models for the answer-governance layer."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConfidenceStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    PROVISIONAL = "PROVISIONAL"
    BLOCKED = "BLOCKED"


@dataclass
class Reconciliation:
    status: str = ""
    variance: Optional[float] = None
    tolerance: Optional[float] = None


@dataclass
class Coverage:
    required_months: List[str] = field(default_factory=list)
    available_months: List[str] = field(default_factory=list)
    complete: bool = False
    value_coverage_pct: Optional[float] = None


@dataclass
class Governed:
    metric: str = ""
    period: str = ""
    filters: Dict[str, Any] = field(default_factory=dict)
    value: Optional[float] = None
    unit: str = "INR Lakh"
    status: ConfidenceStatus = ConfidenceStatus.BLOCKED
    source_paths: List[str] = field(default_factory=list)
    source_periods: List[str] = field(default_factory=list)
    reconciliation: Reconciliation = field(default_factory=Reconciliation)
    coverage: Coverage = field(default_factory=Coverage)
    assumptions: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    formula_reference: str = ""
    approval_status: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "period": self.period,
            "filters": self.filters,
            "value": self.value,
            "unit": self.unit,
            "status": self.status.value,
            "source_paths": self.source_paths,
            "source_periods": self.source_periods,
            "reconciliation": {
                "status": self.reconciliation.status,
                "variance": self.reconciliation.variance,
                "tolerance": self.reconciliation.tolerance,
            },
            "coverage": {
                "required_months": self.coverage.required_months,
                "available_months": self.coverage.available_months,
                "complete": self.coverage.complete,
                "value_coverage_pct": self.coverage.value_coverage_pct,
            },
            "assumptions": self.assumptions,
            "exclusions": self.exclusions,
            "warnings": self.warnings,
            "formula_reference": self.formula_reference,
            "approval_status": self.approval_status,
            "reason": self.reason,
        }
