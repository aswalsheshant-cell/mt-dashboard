"""Canonical fiscal-period logic.

Wraps scripts/build_dashboard_data.py's existing THE ONE FY RULE helpers
rather than reimplementing FY derivation a second time (ADR-002's
discipline: one canonical source per concept). scripts/ has no __init__.py
(it is not a formal package in this repo, and Phase 1 is forbidden from
touching scripts/build_dashboard_data.py per
docs/CANONICAL_METRIC_IMPLEMENTATION_PLAN.md), so the import uses the same
sys.path pattern this repo's own tests already use.
"""
import importlib
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
_bd = importlib.import_module("build_dashboard_data")

fy_tag_from_ym = _bd.fy_tag_from_ym
fy_tag_from_label = _bd.fy_tag_from_label
fy_start_year = _bd.fy_start_year


def normalize_fy(fy):
    """Any FY spelling this repo uses ('FY27', 'fy27', 'FY_26-27', 'Apr-26')
    -> canonical uppercase 'FY27' tag, or None if unrecognisable. Canonical
    metrics always accept and return this form; data.js's lowercase
    fy-suffixed keys (fy26, total_fy27, ...) are an internal storage detail
    handled by data_key(), never exposed as this module's own convention."""
    if fy is None:
        return None
    s = str(fy).strip()
    if not s:
        return None
    tag = fy_tag_from_label(s)
    if tag:
        return tag
    m = s.upper().replace(" ", "")
    if m.startswith("FY") and m[2:].isdigit() and len(m[2:]) == 2:
        return m
    return None


def data_key(fy):
    """Canonical 'FY27' -> the lowercase suffix data.js's own fields use
    ('fy27'), e.g. for offtake['total_' + data_key(fy)]. Raises ValueError
    on an unrecognisable fy rather than silently building a nonsense key --
    a malformed lookup key must fail loudly, not resolve to some other
    field by accident (the class of defect ADR-001 exists to prevent, one
    layer earlier)."""
    tag = normalize_fy(fy)
    if tag is None:
        raise ValueError(f"not a recognisable FY tag: {fy!r}")
    return tag.lower()
