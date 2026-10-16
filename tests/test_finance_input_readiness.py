"""finance_input_readiness: reports gaps, never fills them, and its blank request cannot pass the gate."""
import csv
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
fir = importlib.import_module("finance_input_readiness")
cac = importlib.import_module("check_assumption_coverage")


def test_fy_tag_follows_the_one_fy_rule():
    assert fir.fy_tag(2026, 9) == "FY27"
    assert fir.fy_tag(2026, 3) == "FY26"
    assert fir.fy_tag(2027, 4) == "FY28"


def test_request_sheet_is_blank_and_cannot_satisfy_the_gate(tmp_path):
    out = tmp_path / "req.csv"
    fir.write_request(out, ["Jun'26", "Sep'26"])
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["Month"] for r in rows] == ["Jun'26", "Sep'26"]
    for r in rows:
        assert all(v == "" for k, v in r.items() if k not in ("Month", "Chain", "Brand", "Category"))
        assert not cac.APPROVAL_MARKER.search(r["Remarks"])


def test_missing_primary_is_reported_not_invented(monkeypatch, tmp_path):
    off, pri = tmp_path / "off", tmp_path / "pri"
    off.mkdir(); pri.mkdir()
    (off / "offtake_store_article_Sep_26.csv").write_text("x\n")
    monkeypatch.setattr(fir, "OFFTAKE_DIR", off)
    monkeypatch.setattr(fir, "PRIMARY_DIR", pri)
    state, lines = fir.primary_status()
    assert state == "MISSING" and "primary_article_Sep_26.csv" in lines[0]


def test_primary_with_wrong_month_or_columns_is_flagged(monkeypatch, tmp_path):
    off, pri = tmp_path / "off", tmp_path / "pri"
    off.mkdir(); pri.mkdir()
    (off / "offtake_store_article_Sep_26.csv").write_text("x\n")
    cols = ["FY", "Month", "Inv. Date", "Inv. Net value(LOC)"]
    (pri / "primary_article_Aug_26.csv").write_text(",".join(cols) + "\nFY27,Aug'26,2026-08-02,100\n")
    (pri / "primary_article_Sep_26.csv").write_text(",".join(cols) + "\nFY27,Aug'26,2026-08-30,100000\n")
    monkeypatch.setattr(fir, "OFFTAKE_DIR", off)
    monkeypatch.setattr(fir, "PRIMARY_DIR", pri)
    state, lines = fir.primary_status()
    assert state == "CHECK"
    assert any("Month column" in l for l in lines) and any("Invoice dates" in l for l in lines)


def test_good_primary_is_ready(monkeypatch, tmp_path):
    off, pri = tmp_path / "off", tmp_path / "pri"
    off.mkdir(); pri.mkdir()
    (off / "offtake_store_article_Sep_26.csv").write_text("x\n")
    cols = ["FY", "Month", "Inv. Date", "Inv. Net value(LOC)"]
    (pri / "primary_article_Aug_26.csv").write_text(",".join(cols) + "\nFY27,Aug'26,2026-08-02,100\n")
    (pri / "primary_article_Sep_26.csv").write_text(",".join(cols) + "\nFY27,Sep'26,2026-09-03,100000\n")
    monkeypatch.setattr(fir, "OFFTAKE_DIR", off)
    monkeypatch.setattr(fir, "PRIMARY_DIR", pri)
    state, _ = fir.primary_status()
    assert state == "READY"
