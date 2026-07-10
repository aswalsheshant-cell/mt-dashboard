"""
Phase 3 (part A) — EDA profiling & data-cleaning suggestions.

Profiles any table already loaded into the DataLayer, using the engine itself
(so it works offline on stdlib sqlite3 and, unchanged, on DuckDB). For each
column it reports null counts, distinct counts, an inferred kind
(numeric / categorical / empty), numeric summary stats, and the most frequent
categorical values — then derives concrete cleaning suggestions.

Everything here is deterministic and local; no model and no network involved.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ai_analyst.data_layer import DataLayer


def _is_number(s) -> bool:
    if s is None:
        return False
    try:
        float(s)
        return True
    except (TypeError, ValueError):
        return False


@dataclass
class ColumnProfile:
    name: str
    non_null: int
    nulls: int
    distinct: int
    kind: str  # 'numeric' | 'categorical' | 'empty'
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    mean: Optional[float] = None
    total: Optional[float] = None
    top_values: List[Tuple[str, int]] = field(default_factory=list)

    @property
    def null_pct(self) -> float:
        n = self.non_null + self.nulls
        return (self.nulls / n * 100.0) if n else 0.0


@dataclass
class TableProfile:
    table: str
    rows_total: int
    rows_profiled: int
    truncated: bool
    rows_distinct: int
    duplicates: int
    columns: List[ColumnProfile]


def profile_table(data: DataLayer, table: str, sample: int = 5000, top_n: int = 5) -> TableProfile:
    """Compute an EDA profile for a loaded table (samples up to `sample` rows)."""
    t = data.table(table)
    if t is None:
        raise ValueError(f"Unknown table: {table!r}. Loaded: {', '.join(data.tables()) or '(none)'}")

    cols = t.columns
    _, rows = data.run_sql(f'SELECT * FROM "{table}" LIMIT {sample}')
    rows_profiled = len(rows)
    truncated = t.nrows > rows_profiled

    # whole-table duplicate detection (cheap single query, not sampled)
    try:
        _, dr = data.run_sql(f'SELECT COUNT(*) FROM (SELECT DISTINCT * FROM "{table}")')
        rows_distinct = dr[0][0]
    except Exception:
        rows_distinct = t.nrows
    duplicates = max(0, t.nrows - rows_distinct)

    col_profiles: List[ColumnProfile] = []
    for ci, name in enumerate(cols):
        values = [r[ci] for r in rows]
        non_null = [v for v in values if v is not None and v != ""]
        nulls = rows_profiled - len(non_null)
        distinct = len(set(non_null))

        if not non_null:
            col_profiles.append(ColumnProfile(name, 0, nulls, 0, "empty"))
            continue

        numeric_frac = sum(1 for v in non_null if _is_number(v)) / len(non_null)
        if numeric_frac >= 0.9:
            nums = [float(v) for v in non_null if _is_number(v)]
            col_profiles.append(ColumnProfile(
                name, len(non_null), nulls, distinct, "numeric",
                minimum=min(nums), maximum=max(nums),
                mean=statistics.fmean(nums), total=sum(nums),
            ))
        else:
            counts: dict = {}
            for v in non_null:
                counts[v] = counts.get(v, 0) + 1
            top = sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))[:top_n]
            col_profiles.append(ColumnProfile(
                name, len(non_null), nulls, distinct, "categorical", top_values=top,
            ))

    return TableProfile(table, t.nrows, rows_profiled, truncated, rows_distinct, duplicates, col_profiles)


def suggest_cleaning(profile: TableProfile) -> List[dict]:
    """Derive concrete, prioritised cleaning suggestions from a TableProfile."""
    suggestions: List[dict] = []

    if profile.duplicates > 0:
        suggestions.append({
            "priority": "high",
            "column": None,
            "issue": f"{profile.duplicates} duplicate row(s)",
            "suggestion": "Drop exact-duplicate rows (SELECT DISTINCT *) before analysis.",
        })

    for c in profile.columns:
        if c.kind == "empty":
            suggestions.append({
                "priority": "medium", "column": c.name,
                "issue": "column is entirely empty",
                "suggestion": "Consider dropping this column — it carries no data.",
            })
            continue
        if c.null_pct >= 50.0:
            suggestions.append({
                "priority": "high", "column": c.name,
                "issue": f"{c.null_pct:.0f}% missing",
                "suggestion": "High missingness — drop the column or impute deliberately.",
            })
        elif c.nulls > 0:
            suggestions.append({
                "priority": "low", "column": c.name,
                "issue": f"{c.nulls} missing value(s) ({c.null_pct:.0f}%)",
                "suggestion": "Fill (mean/median/mode) or drop the affected rows.",
            })
        if c.distinct == 1:
            suggestions.append({
                "priority": "low", "column": c.name,
                "issue": "constant column (single distinct value)",
                "suggestion": "Constant columns add no signal — consider dropping.",
            })
    return suggestions


def profile_report(profile: TableProfile, suggestions: Optional[List[dict]] = None) -> str:
    """Render a plain-text EDA report."""
    out: List[str] = []
    head = f"Table '{profile.table}': {profile.rows_total} rows × {len(profile.columns)} columns"
    if profile.truncated:
        head += f" (profiled first {profile.rows_profiled})"
    out.append(head)
    if profile.duplicates:
        out.append(f"  duplicates: {profile.duplicates}")
    out.append("")
    out.append(f"{'column':28} {'kind':11} {'nulls':>7} {'distinct':>9}  summary")
    out.append("-" * 78)
    for c in profile.columns:
        if c.kind == "numeric":
            summary = f"min={_fmt(c.minimum)} max={_fmt(c.maximum)} mean={_fmt(c.mean)}"
        elif c.kind == "categorical":
            summary = "top: " + ", ".join(f"{v}({n})" for v, n in c.top_values[:3])
        else:
            summary = "(empty)"
        nulls = f"{c.nulls}({c.null_pct:.0f}%)"
        out.append(f"{c.name[:28]:28} {c.kind:11} {nulls:>7} {c.distinct:>9}  {summary}")

    sug = suggestions if suggestions is not None else suggest_cleaning(profile)
    if sug:
        out.append("")
        out.append("Cleaning suggestions:")
        for s in sug:
            where = f" [{s['column']}]" if s.get("column") else ""
            out.append(f"  - ({s['priority']}){where} {s['issue']} -> {s['suggestion']}")
    return "\n".join(out)


def _fmt(x: Optional[float]) -> str:
    if x is None:
        return "-"
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.2f}"
