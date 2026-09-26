"""PQ 39 (PL Expense Input) must derive FY and MonthStart by THE ONE FY RULE, for any year.

Found 2026-09-26 on main c8ba4aa (follow-up to #233 / FM-33):
PowerBI/PowerQuery/39_PL_Expense_Input.pq mapped FY text to a tag with a fixed
if/else list (FY24..FY27 and 23-24..26-27) and the tag to a start year with a
second fixed list. An FY28 expense row ("FY28" or "FY27-28") got FY = null and
MonthStart = null, so it could never relate to 'Date Table' and silently dropped
out of CM2 once FY28 arrived. CLAUDE.md: FY is derived by arithmetic, never a
list, so FY27, FY28, ... work without a code change.

The fix mirrors scripts/build_dashboard_data.py's _fylabel() + fy_start_year()
step for step. There is no M engine in CI, so:
  * tests/powerbi/fy_parser_cases.csv is the shared case table; this file checks
    every expected value against the canonical Python rule;
  * the M step is checked structurally (no FY literal list, arithmetic start year);
  * tests/powerbi/pq39_fy_parser_cases.pq runs the same table through the SAME
    function text in Power BI Desktop; this file checks that text is identical to
    the step in query 39, so the Desktop run tests the real code.
"""
import csv
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PQ = ROOT / "PowerBI" / "PowerQuery" / "39_PL_Expense_Input.pq"
QS_PQ = ROOT / "PowerBI" / "QuickSetup" / "AllPowerQuery_Consolidated.txt"
CASES = ROOT / "tests" / "powerbi" / "fy_parser_cases.csv"
DESKTOP_CASES = ROOT / "tests" / "powerbi" / "pq39_fy_parser_cases.pq"

sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as bdd  # noqa: E402

# Same month spellings as the AddMonthNum record in query 39 (Text.Proper(Text.Trim(...))).
PQ_MONTHS = {"Apr": 4, "April": 4, "May": 5, "Jun": 6, "June": 6, "Jul": 7, "July": 7,
             "Aug": 8, "August": 8, "Sep": 9, "Sept": 9, "September": 9,
             "Oct": 10, "October": 10, "Nov": 11, "November": 11, "Dec": 12, "December": 12,
             "Jan": 1, "January": 1, "Feb": 2, "February": 2, "Mar": 3, "March": 3}


def _code(text):
    return "\n".join(ln.split("//", 1)[0] for ln in text.splitlines())


def _cases():
    with CASES.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _canonical(fy_text, month_text):
    """THE ONE FY RULE, from the pipeline's own helpers."""
    tag = bdd._fylabel(fy_text) if fy_text.strip() else None
    mn = PQ_MONTHS.get(month_text.strip().title())
    if tag is None or mn is None:
        return tag, None
    start = bdd.fy_start_year(tag)
    return tag, dt.date(start if mn >= 4 else start + 1, mn, 1).isoformat()


def test_case_table_matches_the_one_fy_rule():
    rows = _cases()
    bad = []
    for r in rows:
        tag, ms = _canonical(r["FY"], r["Month"])
        if (tag or "") != r["Expected FY Tag"] or (ms or "") != r["Expected MonthStart"]:
            bad.append((r["FY"], r["Month"], tag, ms, r["Expected FY Tag"], r["Expected MonthStart"]))
    assert bad == [], bad


def test_case_table_covers_fy24_to_fy30_rollover_and_invalid_input():
    rows = _cases()
    tags = {r["Expected FY Tag"] for r in rows}
    assert {f"FY{n}" for n in range(24, 31)} <= tags
    assert any(r["Month"].title() in ("Jan", "January", "Feb", "Mar") and r["Expected MonthStart"] for r in rows)
    assert any(r["FY"].strip() == "" for r in rows), "missing FY case"
    assert sum(1 for r in rows if r["FY"].strip() and not r["Expected FY Tag"]) >= 3, "invalid FY cases"
    # both conventions for the same FY (repo's FY27 and the FY26-27 span form)
    assert {r["FY"] for r in rows} >= {"FY27", "FY26-27", "FY28", "FY27-28"}


def test_query_39_has_no_fy_literal_list():
    code = _code(PQ.read_text(encoding="utf-8"))
    literals = re.findall(r'"(?:FY)?\d{2}-\d{2}"|"FY\d{2}"', code)
    assert literals == [], f"query 39 still lists FY values: {literals}"
    assert not re.search(r"\b20[2-3]\d\b", code), "query 39 hardcodes a calendar year"


def test_query_39_derives_the_start_year_by_arithmetic():
    code = re.sub(r"\s+", " ", _code(PQ.read_text(encoding="utf-8")))
    assert "fnFyTag" in code and "AddFyTag" in code
    assert re.search(r"2000 \+ Number\.FromText\( ?Text\.Middle\( ?\[_FyTag\], ?2 ?\) ?\) - 1", code), \
        "_FyStartYear must be fy_start_year(): 2000 + nn - 1"
    assert re.search(r"Number\.Mod\( ?_a \+ 1, ?100 ?\)", code), \
        "span form must require consecutive years, as _fylabel() does"


def _fn_text(text):
    m = re.search(r"^( {4}fnFyTag = .*?^ {8}in\n {12}.*?,)\n", text, re.S | re.M)
    assert m, "fnFyTag step not found"
    return m.group(1)


def test_desktop_case_query_uses_the_same_function_text():
    real = _fn_text(PQ.read_text(encoding="utf-8"))
    copy = _fn_text(DESKTOP_CASES.read_text(encoding="utf-8"))
    assert copy == real, "tests/powerbi/pq39_fy_parser_cases.pq drifted from query 39's fnFyTag"
    assert "fy_parser_cases.csv" in DESKTOP_CASES.read_text(encoding="utf-8")


def test_quicksetup_copy_of_query_39_is_in_sync():
    t = QS_PQ.read_text(encoding="utf-8")
    parts = re.split(r"\n#{20,}\n# STEP \d+/\d+\s+--\s+SOURCE FILE: (\S+)\n(?:#.*\n)*#{20,}\n", t)
    sec = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    assert sec[PQ.name].strip() == PQ.read_text(encoding="utf-8").strip()
