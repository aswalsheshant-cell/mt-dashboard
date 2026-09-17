"""
Regression test for the 2026-09-14 fix: primary_article_Jul_26.csv arrives
with sub_category/range/net_content (and PPT Category) entirely blank for
all 31,355 rows, while category and EAN No. are intact -- an upstream export
gap for that one month, not missing data. detail_records_real() now backfills
those three fields from another month's real value for the same EAN (a
physical SKU's taxonomy does not change month to month). An EAN with no real
value anywhere in the loaded months is left blank -- never fabricated.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_dashboard_data as bdd  # noqa: E402


def _row(ean, sub_category, range_, net_content, category="Face", month="Apr'26", po_type="Direct"):
    return {
        "FY": "FY27", "Month": month, "Channel": "MT", "Inv. Date": "2026-04-01",
        "Cust-SAP Code": "1", "Ship To Name": "Test Chain", "EAN No.": ean,
        "net_content": net_content, "brand": "Mamaearth", "PPT Category": sub_category,
        "category": category, "sub_category": sub_category, "range": range_,
        "Description": "Test Article", "MRP": 100.0, "Inv Qty": 10,
        "Inv. Net value(LOC)": 50000.0, "Inv. Tax Amount(LOC)": 5000.0,
        "Total MRP sales": 100000.0, "Avg Tot": 0.5, "MTD-Sale type": "Sales",
        "PO Type": po_type, "Chain name for Dashboard": "Test Chain", "Zone": "West",
        "State": "Maharashtra",
    }


def _dist_row(ean, sub_category, range_, net_content, category="Face", month="Apr'26"):
    """A minimal Dist. row alongside the Direct rows -- allocate_dist_primary()
    (an existing, unrelated function that always runs before detail_records
    are built) has a latent edge case with an all-Direct fixture (empty
    Dist. subset); giving it a non-empty Dist. subset keeps these unit tests
    focused on the backfill fix rather than tripping an unrelated pipeline
    branch. Not part of the fix under test -- confirmed by the end-to-end
    real-file test below, which needs no such workaround."""
    r = _row(ean, sub_category, range_, net_content, category, month, po_type="Dist.")
    r["Ship To Name"] = "Some Distributor"
    return r


def test_ean_backfill_fills_from_another_month(tmp_path, monkeypatch):
    """A row with blank sub_category/range/net_content is backfilled from a
    different month's real row for the same EAN."""
    rows = [
        _row("1234567890123", "Face Cleanser", "Vitamin C", "100.0", month="Apr'26"),
        _row("1234567890123", float("nan"), float("nan"), float("nan"), month="Jul'26"),
        _dist_row("7777777777777", "Shampoo", "Onion", "250.0", month="Apr'26"),
    ]
    df = pd.DataFrame(rows)
    src = tmp_path / "Primary_Article_Monthly"
    src.mkdir()
    df.to_csv(src / "primary_article_test.csv", index=False)

    # detail_records_real() calls allocate_dist_primary() without output_dir,
    # which defaults to writing 3 governance/proposal CSVs under the real repo's
    # PowerBI/SeedData/Mapping/ (Path(__file__).resolve().parent.parent). Redirect
    # bdd's own __file__ to an isolated fake repo so this synthetic-data run never
    # touches the tracked files.
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "PowerBI" / "SeedData" / "Mapping").mkdir(parents=True)
    monkeypatch.setattr(bdd, "__file__", str(fake_repo / "scripts" / "build_dashboard_data.py"))

    result = bdd.detail_records_real(tmp_path, max_rows=1000)
    assert result is not None
    recs = result[0]
    jul_rec = next(r for r in recs if r["Month"] == "July")
    assert jul_rec["SubCategory"] == "Face Cleanser"
    assert jul_rec["Range"] == "Vitamin C"
    assert jul_rec["PackSize"] == "100.0"


def test_ean_with_no_real_value_anywhere_stays_blank_not_fabricated(tmp_path, monkeypatch):
    """An EAN that never has a real sub_category in any loaded month must be
    left null -- never invented."""
    rows = [
        _row("9999999999999", float("nan"), float("nan"), float("nan"), month="Jul'26"),
        _dist_row("7777777777777", "Shampoo", "Onion", "250.0", month="Apr'26"),
    ]
    df = pd.DataFrame(rows)
    src = tmp_path / "Primary_Article_Monthly"
    src.mkdir()
    df.to_csv(src / "primary_article_test.csv", index=False)

    # See the isolation comment in test_ean_backfill_fills_from_another_month above.
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "PowerBI" / "SeedData" / "Mapping").mkdir(parents=True)
    monkeypatch.setattr(bdd, "__file__", str(fake_repo / "scripts" / "build_dashboard_data.py"))

    result = bdd.detail_records_real(tmp_path, max_rows=1000)
    assert result is not None
    recs = result[0]
    rec = next(r for r in recs if r["EAN"] == "9999999999999")
    assert rec["SubCategory"] is None


def test_real_jul26_file_backfills_to_near_full_coverage(tmp_path, monkeypatch):
    """End-to-end against the real committed source: Jul'26 arrives with
    sub_category blank for all rows; after backfill against the other real
    months, coverage should be ~99.99% (matches the independently-verified
    EAN-match check: 397/420 EANs, 99.99% of Jul'26 NSV)."""
    src_dir = REPO_ROOT / "PowerBI" / "RawDataFolders"
    jul_file = src_dir / "Primary_Article_Monthly" / "primary_article_Jul_26.csv"
    if not jul_file.exists():
        pytest.skip("primary_article_Jul_26.csv not present in this environment")

    # See the isolation comment in test_ean_backfill_fills_from_another_month above.
    # This test reads the real source tree but must not let allocate_dist_primary()
    # write its governance CSVs into the real repo's tracked Mapping/ folder.
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "PowerBI" / "SeedData" / "Mapping").mkdir(parents=True)
    monkeypatch.setattr(bdd, "__file__", str(fake_repo / "scripts" / "build_dashboard_data.py"))

    result = bdd.detail_records_real(src_dir, max_rows=200000)
    assert result is not None
    recs = result[0]
    jul27 = [r for r in recs if r["Month"] == "July" and r["FY"] == "FY27"]
    assert jul27, "expected FY27 July rows in detail_records"
    n_blank = sum(1 for r in jul27 if not r.get("SubCategory"))
    assert n_blank / len(jul27) < 0.01, (
        f"{n_blank}/{len(jul27)} July FY27 rows still blank after backfill -- "
        "expected under 1% (unmatched EANs with no real value anywhere)"
    )
