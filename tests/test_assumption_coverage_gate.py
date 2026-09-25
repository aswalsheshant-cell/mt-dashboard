"""Regression tests for scripts/check_assumption_coverage.py (F21).

docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md's follow-up sweep found the
Power BI P&L DAX silently defaulted a month with no AssumptionTable.csv row
to a hardcoded 50% Gross Margin / 0% Trade Spend. This is the release-gate
half of the fix: it must fail the build the moment a real reporting month
has no matching Assumption Table row, using only real files it can find --
never a hardcoded date list, so it keeps working unattended as new months
land (mirrors THE ONE FY RULE's "derive, never hardcode" principle).
"""
import csv
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
cac = importlib.import_module("check_assumption_coverage")


def _write_assumption_table(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "Month", "Chain", "Brand", "Category", "Gross Margin %", "Trade Spend %",
            "Visibility Spend", "Scheme Spend", "Other Spend", "Contribution Margin %", "Remarks",
        ])
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _touch_monthly_files(dir_path, filenames):
    dir_path.mkdir(parents=True, exist_ok=True)
    for name in filenames:
        (dir_path / name).write_text("placeholder\n")


def _all_row(month):
    return {"Month": month, "Chain": "ALL", "Brand": "ALL", "Category": "ALL",
            "Gross Margin %": "0.52", "Trade Spend %": "0.08", "Visibility Spend": "0",
            "Scheme Spend": "0", "Other Spend": "0", "Contribution Margin %": "0.30",
            "Remarks": "test fixture"}


def test_missing_months_reported_and_blocks(tmp_path, monkeypatch):
    assumption = tmp_path / "AssumptionTable.csv"
    _write_assumption_table(assumption, [_all_row("Apr'26"), _all_row("May'26")])
    primary_dir = tmp_path / "Primary_Article_Monthly"
    _touch_monthly_files(primary_dir, [
        "primary_article_Apr_26.csv", "primary_article_May_26.csv",
        "primary_article_Jun_26.csv", "primary_article_Jul_26.csv", "primary_article_Aug_26.csv",
    ])
    monkeypatch.setattr(cac, "ASSUMPTION_TABLE", assumption)
    monkeypatch.setattr(cac, "MONTHLY_SOURCE_DIRS", [primary_dir])

    exit_code = cac.main()

    assert exit_code == 3


def test_full_coverage_passes(tmp_path, monkeypatch, capsys):
    assumption = tmp_path / "AssumptionTable.csv"
    _write_assumption_table(assumption, [_all_row("Apr'26"), _all_row("May'26"), _all_row("Jun'26")])
    primary_dir = tmp_path / "Primary_Article_Monthly"
    _touch_monthly_files(primary_dir, [
        "primary_article_Apr_26.csv", "primary_article_May_26.csv", "primary_article_Jun_26.csv",
    ])
    monkeypatch.setattr(cac, "ASSUMPTION_TABLE", assumption)
    monkeypatch.setattr(cac, "MONTHLY_SOURCE_DIRS", [primary_dir])

    exit_code = cac.main()
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "OK" in out
    assert "BLOCKED" not in out


def test_chain_specific_row_does_not_count_as_month_coverage(tmp_path, monkeypatch):
    """A row scoped to one chain (not ALL/ALL/ALL) doesn't guarantee a value
    for every query the way the ALL fallback row does -- must not be
    mistaken for real month coverage."""
    assumption = tmp_path / "AssumptionTable.csv"
    _write_assumption_table(assumption, [
        _all_row("Apr'26"),
        {"Month": "May'26", "Chain": "Reliance Retail", "Brand": "ALL", "Category": "ALL",
         "Gross Margin %": "0.50", "Trade Spend %": "0.10", "Visibility Spend": "150000",
         "Scheme Spend": "80000", "Other Spend": "0", "Contribution Margin %": "0.27",
         "Remarks": "chain-specific only, no ALL/ALL/ALL row for May"},
    ])
    primary_dir = tmp_path / "Primary_Article_Monthly"
    _touch_monthly_files(primary_dir, ["primary_article_Apr_26.csv", "primary_article_May_26.csv"])
    monkeypatch.setattr(cac, "ASSUMPTION_TABLE", assumption)
    monkeypatch.setattr(cac, "MONTHLY_SOURCE_DIRS", [primary_dir])

    exit_code = cac.main()

    assert exit_code == 3


def test_no_real_monthly_source_found_is_not_an_error(tmp_path, monkeypatch, capsys):
    """No real Primary/Offtake drop present at all (e.g. a fresh clone with
    no data staged yet) -- nothing to require, must not be a hard failure."""
    assumption = tmp_path / "AssumptionTable.csv"
    _write_assumption_table(assumption, [_all_row("Apr'26")])
    empty_dir = tmp_path / "Primary_Article_Monthly"
    empty_dir.mkdir()
    monkeypatch.setattr(cac, "ASSUMPTION_TABLE", assumption)
    monkeypatch.setattr(cac, "MONTHLY_SOURCE_DIRS", [empty_dir])

    exit_code = cac.main()
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "nothing to require" in out


def test_missing_assumption_table_file_itself_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(cac, "ASSUMPTION_TABLE", tmp_path / "does_not_exist.csv")
    monkeypatch.setattr(cac, "MONTHLY_SOURCE_DIRS", [tmp_path])

    exit_code = cac.main()

    assert exit_code == 3


def test_real_repo_state_matches_documented_gap():
    """Confirms this script's real, unmocked verdict against the actual
    committed repo state matches the documented F21 finding: Jun/Jul/Aug'26
    are missing from AssumptionTable.csv even though real monthly Primary/
    Offtake drops exist for them. If this ever passes, either Finance
    supplied the real assumptions (great -- update this test) or the
    required-months derivation broke silently."""
    required = cac.find_required_months()
    covered = cac.find_covered_months()
    required_labels = [cac.month_label(y, m) for (y, m) in required]
    missing = [lab for lab in required_labels if lab not in covered]

    assert missing == ["Jun'26", "Jul'26", "Aug'26"], (
        f"Expected the documented F21 gap (Jun/Jul/Aug'26 missing); got {missing}. "
        "If Finance has since supplied these, update this test to match."
    )
