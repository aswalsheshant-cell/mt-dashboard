"""Canonical financial-unit handling (ADR-006).

Canonical storage unit is INR Lakh -- this repo's existing absolute-INR
convention (1 Lakh = INR 100,000, an absolute quantity, not a display
scaling). Every canonical metric function in this package returns a value
in Lakh. Lakh/Crore conversion happens ONLY at presentation time, via
to_crore()/to_lakh_display() below -- never inside a metric calculation or
a reconciliation comparison. This is the rule PR #193's bug #2 (a
dashboard display site dividing by 100 before crc()'s own conversion)
violated; this module exists so the canonical engine cannot repeat it.
"""
import math


def round_lakh(x, nd=2):
    """Canonical rounding for a Lakh value -- mirrors
    scripts/build_dashboard_data.py's r2() exactly (NaN/Infinity -> None,
    never a numeric placeholder)."""
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return None
    if math.isnan(xf) or math.isinf(xf):
        return None
    return round(xf, nd)


def to_crore(lakh_value):
    """Lakh -> Crore, presentation only. None in, None out -- never 0."""
    if lakh_value is None:
        return None
    return round_lakh(lakh_value / 100.0, 2)


def format_inr(lakh_value):
    """Mirrors dashboard/index.html's crc(): input already in Lakh, self-
    selects 'L' or 'Cr' display based on magnitude. Presentation-layer only
    -- never called from inside a metric or reconciliation function, only
    from a report/human-readable rendering path."""
    if lakh_value is None:
        return "–"  # en dash, matches the dashboard's own convention for missing values
    av = abs(lakh_value)
    if av < 100:
        return f"₹{lakh_value:,.1f} L"
    return f"₹{lakh_value / 100.0:,.2f} Cr"
