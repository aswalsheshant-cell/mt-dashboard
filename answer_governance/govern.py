"""
Top-level deterministic governance entry point.

    govern_answer(metric, period, fy_tag, dash, filters=None)

Reads existing governed outputs (the parsed ``dash`` dict from data.js),
assembles evidence, classifies confidence, and returns a Governed object.
No AI inference, no data modification.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, Optional

from answer_governance.models import Governed
from answer_governance.evidence import build_evidence
from answer_governance.claim_guard import guard_claim


def govern_answer(
    metric: str,
    period: str,
    fy_tag: str = "FY27",
    dash: Optional[Dict[str, Any]] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Governed:
    """Produce a governed, evidence-backed answer for a metric.

    Parameters
    ----------
    metric : str
        One of: primary, offtake, forecast, cm2, tot.
    period : str
        Q1, Q2, Q3, Q4, H1, H2, FY, YTD-<month>, or a single month.
    fy_tag : str
        Financial year tag, e.g. "FY27".
    dash : dict, optional
        The parsed ``window.DASH`` object.  If *None*, loads from the
        default ``dashboard/data.js``.
    filters : dict, optional
        Dimension filters (not applied to values — used for traceability).

    Returns
    -------
    Governed
        A fully populated evidence object with confidence status.
    """
    if dash is None:
        dash = _load_dash()

    return build_evidence(metric, period, fy_tag, dash, filters)


def _load_dash() -> dict:
    """Load and parse dashboard/data.js from the repository root."""
    path = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*", txt)
    if not m:
        raise RuntimeError("Cannot find window.DASH in dashboard/data.js")
    raw = txt[m.end():].rstrip().rstrip(";")
    raw = re.sub(r"\bNaN\b", "null", raw)
    return json.loads(raw)
