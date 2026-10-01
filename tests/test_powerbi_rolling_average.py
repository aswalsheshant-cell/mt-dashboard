"""Power BI L3M / L6M averages must treat a missing month as missing, not zero.

Found 2026-10-01 on main 5839efc: PowerBI/DAX/01_CoreMeasures.dax computed

    L3M Average Sales = CALCULATE ( DIVIDE ( [NSV], 3 ), <3-month window> )
    L6M Average Sales = CALCULATE ( DIVIDE ( [NSV], 6 ), <6-month window> )

so a window with only two loaded months (e.g. the first months after a source
starts) was divided by 3: the month with no data counted as Rs 0 and pulled the
average down. A month that genuinely sold 0 must still count; a month with no
rows (BLANK [NSV]) must not.

There is no DAX engine in CI or this container. These tests read the measure
STRUCTURE and replay the four window cases against the two shapes the measure
can take (fixed divisor vs average over loaded months); any other shape fails.
The same cases as DAX queries for Power BI Desktop / DAX Studio are in
tests/powerbi/rolling_average_cases.dax.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DAX = ROOT / "PowerBI" / "DAX" / "01_CoreMeasures.dax"
QS_DAX = ROOT / "PowerBI" / "QuickSetup" / "AllDAX_Consolidated.txt"
CASES = ROOT / "tests" / "powerbi" / "rolling_average_cases.dax"

MEASURES = {"L3M Average Sales": 3, "L6M Average Sales": 6}


def _code(text):
    """Drop // comments so a comment can never satisfy or fail a check."""
    return "\n".join(ln.split("//", 1)[0] for ln in text.splitlines())


def _measures(text):
    """Measure name -> body, for top-level 'Name = ...' blocks in a .dax file."""
    out, name, body = {}, None, []
    for ln in _code(text).splitlines():
        m = re.match(r"^([A-Za-z][^=\n]*?)\s*=\s*(.*)$", ln)
        if m and not ln.startswith((" ", "\t", "VAR ", "RETURN")):
            if name:
                out[name] = "\n".join(body)
            name, body = m.group(1).strip(), [m.group(2)]
        elif name:
            body.append(ln)
    if name:
        out[name] = "\n".join(body)
    return out


def _flat(body):
    return re.sub(r"\s+", " ", body)


FIXED_DIVISOR = re.compile(r"DIVIDE \( \[NSV\] , (\d+) \)")
LOADED_MONTHS = re.compile(
    r"AVERAGEX \( FILTER \( VALUES \( 'Date Table'\[MonthStart\] \) , "
    r"NOT ISBLANK \( \[NSV\] \) \) , \[NSV\] \)")


def _evaluate(body, months):
    """Replay the measure on one window. months: NSV per month, None = no rows."""
    flat = _flat(body).replace(",", " , ")
    flat = re.sub(r"\s+", " ", flat)
    fixed = FIXED_DIVISOR.search(flat)
    if fixed:
        return sum(v or 0 for v in months) / int(fixed.group(1))
    if LOADED_MONTHS.search(flat):
        loaded = [v for v in months if v is not None]
        return sum(loaded) / len(loaded) if loaded else None
    pytest.fail("measure shape not recognised; update this test with the new shape")


# (window months oldest -> newest, expected average). None = month has no rows.
L3M_CASES = [
    ([None, 100.0, 200.0], 150.0),   # two loaded months average over 2
    ([90.0, 100.0, 200.0], 130.0),   # three loaded months average over 3
    ([0.0, 100.0, 200.0], 100.0),    # a genuine zero month stays in the denominator
    ([None, None, None], None),      # nothing loaded -> BLANK, not 0
]
L6M_CASES = [
    ([None, None, None, 60.0, 120.0, 180.0], 120.0),
    ([0.0, 60.0, 60.0, 60.0, 60.0, 60.0], 50.0),
    ([None] * 6, None),
]


@pytest.fixture(scope="module")
def measures():
    return _measures(DAX.read_text(encoding="utf-8"))


@pytest.mark.parametrize("months,expected", L3M_CASES)
def test_l3m_average_counts_only_loaded_months(measures, months, expected):
    assert _evaluate(measures["L3M Average Sales"], months) == expected


@pytest.mark.parametrize("months,expected", L6M_CASES)
def test_l6m_average_counts_only_loaded_months(measures, months, expected):
    assert _evaluate(measures["L6M Average Sales"], months) == expected


@pytest.mark.parametrize("name,n", MEASURES.items())
def test_no_fixed_divisor(measures, name, n):
    flat = re.sub(r"\s+", " ", _flat(measures[name]).replace(",", " , "))
    assert not FIXED_DIVISOR.search(flat), f"{name} divides by a fixed month count"


@pytest.mark.parametrize("name,n", MEASURES.items())
def test_window_unchanged(measures, name, n):
    # The fix changes the divisor only: still the n full months before the current one.
    flat = _flat(measures[name])
    assert f"DATESINPERIOD ( 'Date Table'[Date], EOMONTH ( _curMonth, -1 ), -{n}, MONTH )" in flat


@pytest.mark.parametrize("name", MEASURES)
def test_quicksetup_copy_matches(measures, name):
    qs = _measures(QS_DAX.read_text(encoding="utf-8"))
    assert _flat(qs[name]) == _flat(measures[name])


def test_desktop_cases_cover_every_scenario():
    text = CASES.read_text(encoding="utf-8")
    for case in ("CASE 1", "CASE 2", "CASE 3", "CASE 4"):
        assert case in text
    for name in MEASURES:
        assert f"[{name}]" in text
