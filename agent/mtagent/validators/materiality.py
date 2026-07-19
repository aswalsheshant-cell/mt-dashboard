"""Materiality filter (AI_LEVERAGE_AND_JUDGMENT.md, enforcement §E).

Not every movement belongs in a leadership summary. This module ranks and
filters movements down to the ones actually worth a human's attention --
largest growth driver, largest decline, material exception -- instead of
a long list of every small change. Thresholds are configurable per call,
not hardcoded into the caller.
"""
from __future__ import annotations

DEFAULT_PCT_THRESHOLD = 0.10       # ±10%
DEFAULT_ABS_THRESHOLD = 1_000_000  # ₹10L


def is_material(pct_change: float | None = None, abs_impact: float | None = None,
                 pct_threshold: float = DEFAULT_PCT_THRESHOLD,
                 abs_threshold: float = DEFAULT_ABS_THRESHOLD) -> bool:
    if pct_change is not None and abs(pct_change) >= pct_threshold:
        return True
    if abs_impact is not None and abs(abs_impact) >= abs_threshold:
        return True
    return False


def rank_movements(movements: list, pct_threshold: float = DEFAULT_PCT_THRESHOLD,
                    abs_threshold: float = DEFAULT_ABS_THRESHOLD, top_n: int = 10) -> list:
    """`movements`: [{"name": str, "pct_change": float|None, "abs_impact": float|None}, ...].
    Returns only materially significant movements, largest absolute impact
    first, capped at `top_n`.
    """
    material = [
        m for m in movements
        if is_material(m.get("pct_change"), m.get("abs_impact"), pct_threshold, abs_threshold)
    ]
    material.sort(key=lambda m: abs(m.get("abs_impact") or 0), reverse=True)
    return material[:top_n]
