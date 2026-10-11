"""PO received vs PO billed -> monthly Fill Rate summary (scripts/build_po_fill_rate_summary.py).

Two kinds of check:
  * the committed summary in PowerBI/SeedData/Forecast/ (scope, privacy, totals tie out);
  * the builder's rules, on small hand-made fixtures (test data only, never shipped):
    carry-over merge, blank-vs-0 invoice rule, the Dec'25 column-swap fix, the
    September cut-off and the raw-file-outside-repo guard.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_po_fill_rate_summary as po  # noqa: E402
from build_dashboard_data import fy_tag_from_ym  # noqa: E402

OUT = ROOT / "PowerBI" / "SeedData" / "Forecast"
FR = OUT / "PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv"
REASONS = OUT / "PO_Unfilled_Reasons_Monthly_Apr25_to_Aug26.csv"
TARGET = OUT / "PO_vs_Target_Monthly_FY27.csv"
QC = OUT / "PO_Fill_Rate_QC.json"
MONTHS = ["Apr-25", "May-25", "Jun-25", "Jul-25", "Aug-25", "Sep-25", "Oct-25", "Nov-25", "Dec-25",
          "Jan-26", "Feb-26", "Mar-26", "Apr-26", "May-26", "Jun-26", "Jul-26", "Aug-26"]


@pytest.fixture(scope="module")
def fr():
    return pd.read_csv(FR)


@pytest.fixture(scope="module")
def qc():
    return json.loads(QC.read_text(encoding="utf-8"))


# ---- committed summary ------------------------------------------------------

def test_months_are_apr25_to_aug26_and_no_september_26(fr, qc):
    assert sorted(set(fr["Month"]), key=MONTHS.index) == MONTHS
    assert qc["months_kept"] == MONTHS
    for f in (FR, REASONS, TARGET):
        assert "Sep-26" not in f.read_text(encoding="utf-8")
    q = dict(qc)
    q.pop("source_parts")                     # raw file names say "..._to_Sep26_part_NN"; no data
    text = json.dumps(q)
    assert "Sep-26" not in text and "Sep'26" not in text


def test_fy_tag_follows_the_one_fy_rule(fr):
    for m, fy in fr[["Month", "FY"]].drop_duplicates().itertuples(index=False):
        mon = po.MON[m[:3].lower()]
        assert fy == fy_tag_from_ym(2000 + int(m[-2:]), mon)


def test_no_customer_or_order_identifiers_committed(fr):
    banned = {"SO No.", "Customer No", "Customer Name", "PO No", "SO Date", "SO Time", "EAN No.", "Article"}
    for f in (FR, REASONS, TARGET):
        assert not banned & set(pd.read_csv(f).columns), f.name


def test_summary_ties_to_qc_totals(fr, qc):
    assert int(fr["SO_Lines"].sum()) == qc["lines_check"]["lines_kept"]
    for k, v in qc["summary_totals"].items():
        assert fr[k].sum() == pytest.approx(v, abs=0.01)


def test_fill_rate_is_billed_over_po_and_blank_without_po(fr):
    has_po = fr["PO_Qty"] > 0
    calc = (fr["Billed_Qty"] / fr["PO_Qty"] * 100).round(2)
    assert (fr.loc[has_po, "FR_Qty_Pct"] - calc[has_po]).abs().max() < 0.011
    assert fr.loc[~has_po, "FR_Qty_Pct"].isna().all()       # missing is never shown as 0
    assert (fr["Billed_Qty"] <= fr["PO_Qty"] + 1e-9).all()


def test_unresolved_distributors_are_flagged_not_guessed(fr):
    gov = po.GOVERNED_CHAINS
    assert set(fr.loc[fr["Chain_Resolved"] == "Y", "Chain"]) <= gov
    assert not set(fr.loc[fr["Chain_Resolved"] == "N", "Chain"]) & gov


def test_source_fingerprints_and_rules_recorded(qc):
    assert len(qc["source_parts"]) == 5 and all(len(p["sha256"]) == 64 for p in qc["source_parts"])
    assert qc["article_customer_swap_extracts"] == ["Dec'25"]
    assert qc["rows_dropped_after_max_month"] > 0
    assert "OTIF" in qc["not_measurable"]


def test_target_comparison_is_total_level_fy27_only():
    t = pd.read_csv(TARGET)
    assert list(t["Month"]) == ["Apr-26", "May-26", "Jun-26", "Jul-26", "Aug-26"]
    assert not {"Chain", "Zone", "Brand"} & set(t.columns)


# ---- builder rules on hand-made fixtures --------------------------------------

def _row(**kw):
    base = {"SO No.": "9001", "SO Date": "28-04-2026", "Customer No": "1100001", "Customer Name": "Test Customer",
            "Article": "10100001", "EAN No.": "890000000001", "Article Desc": "Test", "Brand": "Mamaearth",
            "Category": "Face", "Sub category": "Face Cleanser", "Item cat": "ZDM1", "MRP": "",
            "SO Qty": 10.0, "SO Net Value": 1000.0, "Invoice Qty": 0.0, "NET Value": 0.0, "PO No": "P1",
            "Reason for Rejection Desc": None, "Dist.channel Description": "Offline Sales GT/MT",
            "Customer Group Desc": "MT_Direct", "Plant": "1003", "SO Time": "10.00.00 AM", "Chain": "DC-D-Mart-Offline",
            "Zone": "West", "Chanel": "MT", "Month": "Apr'26", "State": "Maharashtra"}
    base.update(kw)
    return base


def _build(rows, max_month="2026-08"):
    return po.build(pd.DataFrame(rows), pd.Timestamp(max_month + "-01"))


def test_carry_over_line_counted_once_with_its_later_billing():
    df, qc = _build([_row(), _row(Month="May'26", **{"Invoice Qty": 10.0, "NET Value": 1000.0})])
    assert len(df) == 1 and df["Invoice Qty"].iat[0] == 10 and df["Month"].iat[0] == "Apr-26"
    assert qc["carry_over_rows_merged"] == 1


def test_billed_row_wins_over_unbilled_repeat_in_same_extract():
    billed = _row(**{"Invoice Qty": 10.0, "NET Value": 1000.0})
    df, _ = _build([billed, _row(**{"Reason for Rejection Desc": "Pricing issue"})])
    assert len(df) == 1 and df["Invoice Qty"].iat[0] == 10


def test_blank_invoice_read_as_not_billed_only_when_extract_has_no_zero():
    ok = [_row(**{"Invoice Qty": None, "NET Value": None}), _row(Article="10100002", **{"Invoice Qty": 5.0, "NET Value": 500.0})]
    df, qc = _build(ok)
    assert qc["blank_invoice_lines_read_as_not_billed"] == 1 and df["Invoice Qty"].sum() == 5
    mixed = ok + [_row(Article="10100003")]                  # explicit 0 in the same extract
    with pytest.raises(SystemExit, match="blank and 0"):
        _build(mixed)


def test_september_extract_and_orders_dropped():
    df, qc = _build([_row(), _row(Month="Sep'26", **{"SO Date": "02-09-2026"})])
    assert len(df) == 1 and qc["rows_dropped_after_max_month"] == 1


def test_swapped_article_customer_columns_fixed_only_when_cross_check_passes():
    clean = _row(**{"Invoice Qty": 10.0, "NET Value": 1000.0})
    swapped = _row(Month="Dec'25", **{"SO No.": "9002", "SO Date": "05-12-2025", "Article": "1100001", "Customer No": "10100001"})
    fixed = po.fix_swapped_columns(pd.DataFrame([clean, swapped]), {})
    assert list(fixed["Article"]) == ["10100001", "10100001"]
    bad = dict(swapped, **{"EAN No.": "890000000001", "Customer No": "10109999"})   # EAN points elsewhere
    with pytest.raises(SystemExit, match="cross-check"):
        po.fix_swapped_columns(pd.DataFrame([clean, bad]), {})


def test_free_goods_kept_out_of_fill_rate():
    df, qc = _build([_row(), _row(Article="10100009", **{"Item cat": "ZFOC"})])
    assert len(df) == 1 and qc["free_goods_lines_excluded"] == 1


def test_raw_extract_inside_repo_is_refused(tmp_path):
    inside = ROOT / "tests" / "_po_raw_part_01.csv"
    inside.write_text("x\n1\n", encoding="utf-8")
    try:
        with pytest.raises(SystemExit, match="outside the repository"):
            po.main(["--src", str(inside), "--out-dir", str(tmp_path)])
    finally:
        inside.unlink()
