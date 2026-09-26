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


def _example_rows(rows):
    return [r for r in rows if "EXAMPLE ROW" in (r.get("Remarks") or "").upper()]


def test_seed_template_example_rows_are_all_filtered():
    """The committed seed file: its 3 template rows are still there, the loader
    drops every one of them, and returns exactly the real (non-template) rows.
    Updated 2026-09-26 when real MT Direct DN claims were loaded (owner request),
    as this test's own earlier message asked: the example-row subset is now
    asserted explicitly instead of "every row is an example row"."""
    assert SEED.exists(), "seed file moved or renamed -- update this test's path"
    with open(SEED, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    examples = _example_rows(rows)
    assert len(examples) == 3, "the 3 shipped template rows must stay in the seed file (schema example for Finance)"

    result = bd.load_pl_expense_input()
    assert _example_rows(result) == [], "an EXAMPLE ROW reached the loader output -- the filter regressed"
    assert result == [r for r in rows if r not in examples], "loader must return exactly the non-template rows"


def test_file_with_only_template_rows_loads_as_empty(tmp_path, monkeypatch):
    """The original FM-01 guarantee, run through the real loader: a seed file that
    holds only the template rows yields [] (CM2 = NSV + "no expense data" banner),
    never the template's Rs47.65L of placeholder values."""
    with open(SEED, newline="", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    header, body = lines[0], lines[1:]
    template_lines = [ln for ln in body if "EXAMPLE ROW" in ln.upper()]
    assert len(template_lines) == 3
    fake = tmp_path / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"
    fake.parent.mkdir(parents=True)
    fake.write_text("\n".join([header] + template_lines) + "\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    monkeypatch.setattr(bd, "__file__", str(tmp_path / "scripts" / "build_dashboard_data.py"))
    assert bd.load_pl_expense_input() == [], (
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
