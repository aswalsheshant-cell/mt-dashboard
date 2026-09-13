"""load_pl_expense_input() must exclude the seed template's own "EXAMPLE ROW"
placeholder rows, so an unfilled PL_Expense_Input.csv correctly reports
has_expense_data = False (CM2 = NSV, "no expense data loaded" banner shown)
instead of silently treating the 3 shipped example rows as real Finance
expense. Regression for the bug fixed 2026-09-13 (see load_pl_expense_input's
own docstring in scripts/build_dashboard_data.py)."""
import csv
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
bd = importlib.import_module("build_dashboard_data")

SEED = Path(__file__).resolve().parent.parent / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"


def test_seed_template_example_rows_are_all_filtered():
    assert SEED.exists(), "seed file moved or renamed -- update this test's path"
    with open(SEED, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "seed file has no rows to test against"
    for r in rows:
        assert "EXAMPLE ROW" in (r.get("Remarks") or "").upper(), (
            "a non-example row now exists in the seed file -- if this is real "
            "Finance data, that's expected and this assertion should be updated "
            "to reflect the new example-row subset, not silently loosened")

    result = bd.load_pl_expense_input()
    assert result == [], (
        "load_pl_expense_input() returned rows from a file containing only "
        "EXAMPLE ROW placeholders -- the example-row filter regressed")


def test_filter_keeps_real_rows_and_drops_example_rows():
    rows = [
        {"Chain": "DMart", "Expense Amount (INR Lakh)": "10.0",
         "Remarks": "Real Finance-submitted row"},
        {"Chain": "Apollo", "Expense Amount (INR Lakh)": "5.0",
         "Remarks": "EXAMPLE ROW -- replace with real data"},
        {"Chain": "Reliance Retail", "Expense Amount (INR Lakh)": "3.0",
         "Remarks": None},
    ]
    kept = [r for r in rows if "EXAMPLE ROW" not in (r.get("Remarks") or "").upper()]
    assert [r["Chain"] for r in kept] == ["DMart", "Reliance Retail"]
