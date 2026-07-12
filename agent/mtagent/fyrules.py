"""THE ONE FY RULE (Indian financial year, Apr–Mar).

Pure-Python mirror of the helpers at the top of
``scripts/build_dashboard_data.py`` so the agent, its SQL templates and its
validators all derive FY from month + year — never from a fixed index/column
position. Keep the two copies behaviourally identical; the eval tests in
``agent/tests/test_fy_rules.py`` pin the shared examples.

  Apr–Dec of calendar year Y -> FY(Y+1)   e.g. Apr-26 -> FY27
  Jan–Mar of calendar year Y -> FY(Y)     e.g. Mar-26 -> FY26
"""
from __future__ import annotations

import datetime
import re

MON3_NUM = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
            "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
NUM_MON3 = {v: k for k, v in MON3_NUM.items()}

# month labels the sources use: 'Apr-24', "Apr'25", 'Apr 2025', 'April-25'
_LABEL_RE = re.compile(r"^\s*([A-Za-z]{3})[A-Za-z]*[\s\-'](?:20)?(\d{2})\s*$")
# ... and sometimes a raw Excel date serial ('46113.0' = 2026-04-01): some
# offtake extracts carry the serial in the Month column; the dashboard build
# accepts it, so the agent must too.
_SERIAL_RE = re.compile(r"^\s*\d{5}(?:\.0*)?\s*$")
_EXCEL_EPOCH = datetime.date(1899, 12, 30)


def fy_tag_from_ym(year: int, month: int) -> str:
    """Calendar (year, month) -> 'FY27' style tag. Apr-2026 -> FY27; Mar-2026 -> FY26."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"


def fy_start_year(tag: str) -> int:
    """'FY27' -> 2026 (the FY's April calendar year)."""
    return 2000 + int(str(tag).strip()[2:]) - 1


def fy_source_key(tag: str) -> str:
    """'FY26' -> 'FY_25-26' (the source workbooks' FY column convention)."""
    y = fy_start_year(tag) % 100
    return f"FY_{y:02d}-{y + 1:02d}"


def ym_from_label(lab) -> tuple[int, int] | None:
    """Month label of ANY source style -> (year, month), or None.
    Handles 'Apr-24' / "Sep'25" / 'Apr 2026' and raw Excel date serials
    ('46113' / '46113.0' -> (2026, 4))."""
    s = str(lab).strip()
    m = _LABEL_RE.match(s)
    if m:
        mn = MON3_NUM.get(m.group(1).title())
        return (2000 + int(m.group(2)), mn) if mn else None
    if _SERIAL_RE.match(s):
        d = _EXCEL_EPOCH + datetime.timedelta(days=int(float(s)))
        return (d.year, d.month)
    return None


def fy_tag_from_label(lab) -> str | None:
    """Month label (any style, incl. Excel serial) -> FY tag, or None."""
    ym = ym_from_label(lab)
    return fy_tag_from_ym(*ym) if ym else None


def norm_month_label(lab) -> str | None:
    """Any month-label style -> canonical 'Apr-26' form, or None."""
    ym = ym_from_label(lab)
    return f"{NUM_MON3[ym[1]]}-{ym[0] % 100:02d}" if ym else None


def fy_quarter(month: int) -> int:
    """Calendar month -> Indian-FY quarter (Apr..Jun=Q1 ... Jan..Mar=Q4)."""
    return (month - 4) % 12 // 3 + 1


def month_labels(start_year: int = 2024, n_months: int = 24) -> list[str]:
    """['Apr-24', 'May-24', ...] for n_months from April of start_year."""
    out, y, m = [], start_year, 4
    for _ in range(n_months):
        out.append(f"{NUM_MON3[m]}-{y % 100:02d}")
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out
