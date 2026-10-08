"""B5 case file must use the same FY label the Date Table produces.

#294 changed 'Date Table'[FY Year] from "2026-27" to "26-27" (same text as
fnFYLabel and Targets[FY Year]). A case file still filtering on the old label
matches nothing in Desktop, so Cases 4, 6 and 9 would give BLANK/FAIL.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests/powerbi/cm2_availability_cases.dax"
DATE_TABLE = ROOT / "PowerBI/DAX/00_DateTable.dax"
RUN_SHEET = ROOT / "docs/evidence/B5_RUN_SHEET.md"


def test_date_table_uses_two_digit_fy_label():
    assert "MOD(y, 100)" in DATE_TABLE.read_text(encoding="utf-8")


def test_case_file_fy_filters_use_two_digit_labels():
    text = CASES.read_text(encoding="utf-8")
    used = re.findall(r"'Date Table'\[FY Year\]\s*=\s*\"([^\"]+)\"", text)
    assert used, "case file no longer filters on FY Year"
    for label in used:
        assert re.fullmatch(r"\d{2}-\d{2}", label), f"old-style FY label {label!r}"


def test_run_sheet_does_not_quote_old_labels():
    text = RUN_SHEET.read_text(encoding="utf-8")
    assert not re.search(r"`?\"?20\d{2}-\d{2}`?\"?\)?.{0,40}(FY Year|row)", text)
    assert '"2026-27"' not in text and "`2026-27`" not in text and "`2025-26`" not in text
