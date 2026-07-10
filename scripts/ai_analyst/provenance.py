"""
Phase 6 — source provenance & the 'Source data required' contract.

Every key number a filled report shows must be traceable to a real source (file,
sheet, column, filter, calculation) OR be explicitly marked as not-yet-available.
Numbers are NEVER invented from memory. This module holds the small data types
that enforce that contract; the fill engine populates them from actual queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Sentinel used everywhere a number would go but no source supports it yet.
SOURCE_REQUIRED = "Source data required"


@dataclass
class Provenance:
    source_file: str
    sheet: str = "(CSV — single sheet)"
    column: str = ""
    filter: str = ""
    calc: str = ""

    def as_row(self) -> List[str]:
        return [self.source_file, self.sheet, self.column, self.filter, self.calc]

    @staticmethod
    def header() -> List[str]:
        return ["Source file", "Sheet", "Column", "Filter applied", "Calculation logic"]


@dataclass
class Metric:
    """A named figure that is either backed by a Provenance or marked required."""
    name: str
    value: object = SOURCE_REQUIRED
    provenance: Optional[Provenance] = None
    unit: str = ""

    @property
    def available(self) -> bool:
        return self.value != SOURCE_REQUIRED and self.value is not None

    def display(self) -> str:
        if not self.available:
            return SOURCE_REQUIRED
        v = self.value
        if isinstance(v, (int, float)):
            if self.unit == "%":
                return f"{v:+.1f}%"
            if self.unit == "Cr":
                return f"₹{v:,.2f} Cr"
            if abs(v - round(v)) < 1e-9:
                return f"{int(round(v)):,}"
            return f"{v:,.2f}"
        return str(v)


@dataclass
class ProvenanceLog:
    """Collects provenance rows for the report's provenance sheet."""
    entries: List[tuple] = field(default_factory=list)  # (metric_name, Provenance)

    def record(self, metric: Metric) -> None:
        if metric.provenance is not None:
            self.entries.append((metric.name, metric.provenance))

    def table(self):
        cols = ["Metric"] + Provenance.header()
        rows = [[name] + prov.as_row() for name, prov in self.entries]
        return cols, rows
