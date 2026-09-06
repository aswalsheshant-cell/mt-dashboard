"""
Fiscal-period completeness checker using the repository's April-to-March FY rule.

Indian Financial Year:
  Apr-Dec of calendar year Y  →  FY(Y+1)
  Jan-Mar of calendar year Y  →  FY(Y)
"""
from __future__ import annotations
from typing import List, Tuple

MONTH_NAMES = [
    "April", "May", "June", "July", "Aug", "Sept",
    "Oct", "Nov", "Dec", "Jan", "Feb", "March",
]

MONTH_SHORT = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
]

Q1 = MONTH_NAMES[:3]     # April, May, June
Q2 = MONTH_NAMES[3:6]    # July, Aug, Sept
Q3 = MONTH_NAMES[6:9]    # Oct, Nov, Dec
Q4 = MONTH_NAMES[9:12]   # Jan, Feb, March
H1 = Q1 + Q2
H2 = Q3 + Q4


def fy_start_year(tag: str) -> int:
    """FY27 → 2026 (the calendar year April falls in)."""
    return 2000 + int(tag[2:]) - 1


def period_months(period: str, fy_tag: str) -> List[str]:
    """Return the list of month names required for a named period within an FY.

    Supported periods: Q1, Q2, Q3, Q4, H1, H2, FY (full year),
    YTD-<month> (e.g. YTD-June), or a single month name (e.g. April).
    """
    period_upper = period.upper().strip()

    if period_upper == "Q1":
        return list(Q1)
    if period_upper == "Q2":
        return list(Q2)
    if period_upper == "Q3":
        return list(Q3)
    if period_upper == "Q4":
        return list(Q4)
    if period_upper == "H1":
        return list(H1)
    if period_upper == "H2":
        return list(H2)
    if period_upper in ("FY", "FULL", "FULL YEAR"):
        return list(MONTH_NAMES)

    if period_upper.startswith("YTD-") or period_upper.startswith("YTD "):
        target = period[4:].strip()
        return _months_through(target)

    single = _normalise_month(period)
    if single:
        return [single]

    return []


def _normalise_month(name: str) -> str | None:
    """Map various month spellings to the canonical MONTH_NAMES entry."""
    s = name.strip()
    for full, short in zip(MONTH_NAMES, MONTH_SHORT):
        if s.lower() in (full.lower(), short.lower()):
            return full
    return None


def _months_through(target_month: str) -> List[str]:
    """Return April through target_month inclusive."""
    norm = _normalise_month(target_month)
    if norm is None:
        return []
    idx = MONTH_NAMES.index(norm)
    return MONTH_NAMES[: idx + 1]


def check_period(
    period: str,
    fy_tag: str,
    available_months: List[str],
) -> Tuple[List[str], List[str], bool]:
    """Check whether a fiscal period is complete given available months.

    Returns (required, available_intersection, is_complete).
    """
    required = period_months(period, fy_tag)
    if not required:
        return [], [], False

    avail_norm = []
    for m in available_months:
        n = _normalise_month(m)
        if n:
            avail_norm.append(n)

    present = [m for m in required if m in avail_norm]
    return required, present, len(present) == len(required)
