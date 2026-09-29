"""B5 exit condition (owner decision 2026-09-29): FY parser + CM2 Cases 2-8 on
the current model, with durable evidence.

Guards:
  * the run sheet covers every case it names, and those cases exist in the
    governed DAX file (no case is invented or silently dropped);
  * the zero-rules the owner required are stated (Leak, BrandLeak,
    CategoryLeak, Violations, FY parser Failures);
  * the load cross-check in the run sheet matches the live expense CSV, so a
    later data change cannot leave stale expected values;
  * the evidence template carries every required field;
  * B5 cannot be marked CLEARED in the docs unless an evidence file exists and
    every required row in it is PASS.
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "docs/evidence"
SHEET = EVID / "B5_RUN_SHEET.md"
TEMPLATE = EVID / "B5_EVIDENCE_TEMPLATE.md"
PACK = ROOT / "docs/COMPLETION_BLOCKER_PACK.md"
STATE = ROOT / "docs/PROJECT_STATE.md"
DAX = ROOT / "tests/powerbi/cm2_availability_cases.dax"
PQ = ROOT / "tests/powerbi/pq39_fy_parser_cases.pq"
EXPENSE = ROOT / "PowerBI/SeedData/Masters/PL_Expense_Input.csv"


def _b5_section(text):
    """From '## B5' to the next heading: every line up to '## B6', so leftover
    text after a table separator ('|---|') cannot hide outside the check."""
    start = text.index("## B5")
    return text[start:text.index("\n## ", start + 1)]


def test_b5_section_has_no_superseded_case1_condition():
    b5 = _b5_section(PACK.read_text(encoding="utf-8"))
    for stale in ("run the CASE 1 block alone", "Both as expected",
                  "Cases 2–4 of the CM2 file wait for B3", "CM2 Case 1 as expected"):
        assert stale not in b5, f"superseded B5 wording still present: {stale!r}"
    assert b5.count("**Exit condition.**") == 1, "B5 must state exactly one exit condition"
    row = next(l for l in PACK.read_text(encoding="utf-8").splitlines() if l.startswith("| B5 |"))
    assert "Cases 2–8" in row and "BLOCKED_PENDING_DESKTOP_EVIDENCE" in row


def test_run_sheet_cases_exist_in_governed_files():
    sheet, dax = SHEET.read_text(encoding="utf-8"), DAX.read_text(encoding="utf-8")
    for n in range(2, 9):
        assert f"// CASE {n}" in dax, f"CASE {n} missing from the governed DAX file"
        assert f"CM2 Case {n}" in sheet, f"run sheet does not cover CM2 Case {n}"
    assert "Failures" in PQ.read_text(encoding="utf-8")
    assert "pq39_fy_parser_cases.pq" in sheet


def test_required_zero_rules_are_stated():
    sheet = SHEET.read_text(encoding="utf-8")
    for rule in ("`Leak = 0`", "`BrandLeak = 0`", "`CategoryLeak = 0`", "`Violations = 0`", "**0 rows**"):
        assert rule in sheet, f"run sheet must state {rule}"
    dax = DAX.read_text(encoding="utf-8")
    for measure in ('"Leak"', '"BrandLeak"', '"CategoryLeak"', '"Violations"'):
        assert measure in dax, f"{measure} not produced by the governed DAX file"


def test_run_sheet_load_crosscheck_matches_live_expense_csv():
    d = pd.read_csv(EXPENSE, dtype=str)
    d = d[~d["Remarks"].fillna("").str.upper().str.contains("EXAMPLE ROW")]
    amt = pd.to_numeric(d["Expense Amount (INR Lakh)"])
    sheet = SHEET.read_text(encoding="utf-8")
    assert f"{len(d)} real rows" in sheet
    assert f"₹{amt.sum():,.2f} L" in sheet
    for month, g in amt.groupby(d["Month"], sort=False):
        label = month[:3] + "'26"
        row = re.search(rf"\| {label} \| (\d+) \| ([\d.]+) \|", sheet)
        assert row, f"no cross-check row for {label}"
        assert int(row.group(1)) == len(g) and abs(float(row.group(2)) - g.sum()) < 0.005, label


def test_evidence_template_has_required_fields():
    t = TEMPLATE.read_text(encoding="utf-8")
    for field in ("git SHA", "Power BI Desktop version", "Model file", "Date run",
                  "| Expected |", "| Actual |", "| Result |", "Evidence reference"):
        assert field in t, f"template missing '{field}'"
    for row in ("| 1 |", "| 2 |", "| 3 |", "| 4 |", "| 5 |", "| 6 |", "| 7a |", "| 7b |", "| 8 |"):
        assert row in t, f"template missing evidence row {row}"


def test_b5_not_cleared_without_evidence():
    evidence = sorted(EVID.glob("B5_powerbi_runtime_*.md"))
    pack_b5 = _b5_section(PACK.read_text(encoding="utf-8"))
    state = STATE.read_text(encoding="utf-8")
    if not evidence:
        assert "BLOCKED_PENDING_DESKTOP_EVIDENCE" in pack_b5
        assert "BLOCKED_PENDING_DESKTOP_EVIDENCE" in state
        assert not re.search(r"B5[^\n]{0,40}\bCLEARED\b", state.replace("CLEARED only", "")), \
            "PROJECT_STATE must not mark B5 CLEARED without an evidence file"
        return
    # evidence exists: every required row must be PASS (row 3 may be NOT_EXERCISED)
    latest = evidence[-1].read_text(encoding="utf-8")
    for row in ("1", "2", "4", "5", "6", "7a", "7b", "8"):
        line = re.search(rf"^\| {row} \|.*$", latest, re.M)
        assert line and "| PASS |" in line.group(0), f"{evidence[-1].name}: row {row} is not PASS"
    line3 = re.search(r"^\| 3 \|.*$", latest, re.M)
    assert line3 and ("| PASS |" in line3.group(0) or "NOT_EXERCISED" in line3.group(0))
