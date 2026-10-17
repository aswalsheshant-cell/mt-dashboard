"""ingest_primary_month_xlsx: month/FY tagging, date guard, row and NSV preserved, unknown EAN left blank."""
import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
ing = importlib.import_module("ingest_primary_month_xlsx")
REF = ing.REFERENCE

pytestmark = pytest.mark.skipif(not REF.exists(), reason="Aug'26 Primary reference file is not on this machine")


def _book(path, rows):
    cols = list(ing.COLUMN_MAP) + ["Division Desc."]
    df = pd.DataFrame(rows, columns=cols)
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="MTD-Primary-Sept'26.", index=False)


def _row(date, ean, nsv):
    r = {c: "x" for c in list(ing.COLUMN_MAP) + ["Division Desc."]}
    r.update({"Inv. Date": pd.Timestamp(date), "EAN No.": ean, "Inv. Net value(LOC)": nsv, "Chanel": "MT",
              "Division Desc.": "Mamaearth", "zone": "North", "state": "Punjab", "Customer master 2": "D-Mart", "Category": "Face"})
    return r


def test_fy_tag_and_month_parse():
    assert ing.fy_tag(2026, 9) == "FY27" and ing.fy_tag(2027, 2) == "FY27" and ing.fy_tag(2026, 3) == "FY26"
    assert ing.parse_month("Sep_26") == (2026, 9)


def test_maps_rows_keeps_value_and_leaves_new_ean_blank(tmp_path):
    known = int(pd.read_csv(REF, usecols=["EAN No."], nrows=1)["EAN No."].iloc[0])
    src = tmp_path / "w.xlsx"
    _book(src, [_row("2026-09-02", known, 100.0), _row("2026-09-03", 8900000000001, -40.0)])
    args = ["--src", str(src), "--month", "Sep_26", "--out-dir", str(tmp_path), "--control-total", "60"]
    assert ing.main(args) == 0
    out = pd.read_csv(tmp_path / "primary_article_Sep_26.csv")
    assert len(out) == 2 and set(out["Month"]) == {"Sep'26"} and set(out["FY"]) == {"FY27"}
    assert round(out["Inv. Net value(LOC)"].sum(), 2) == 60.0           # signed value kept, nothing filtered
    assert list(out.columns) == list(pd.read_csv(REF, nrows=0).columns)
    new = out[out["EAN No."] == 8900000000001].iloc[0]
    assert pd.isna(new["sub_category"]) and pd.isna(new["range"])        # never guessed


def test_rerun_keeps_the_new_ean_list_stable(tmp_path, capsys, monkeypatch):
    import shutil
    shutil.copy(REF, tmp_path / "primary_article_Aug_26.csv")
    monkeypatch.setattr(ing, "PRIMARY_DIR", tmp_path)                 # output folder == lookup folder, as in production
    monkeypatch.setattr(ing, "REFERENCE", tmp_path / "primary_article_Aug_26.csv")
    known = int(pd.read_csv(REF, usecols=["EAN No."], nrows=1)["EAN No."].iloc[0])
    src = tmp_path / "w.xlsx"
    _book(src, [_row("2026-09-02", known, 100.0), _row("2026-09-03", 8900000000001, -40.0)])
    args = ["--src", str(src), "--month", "Sep_26", "--out-dir", str(tmp_path), "--control-total", "60"]
    ing.main(args); first = capsys.readouterr().out
    ing.main(args); second = capsys.readouterr().out                 # second run must not read its own output
    assert "NEW EANs" in first and "NEW EANs" in second and "8900000000001" in second


def test_valued_row_without_invoice_date_is_rejected_not_dropped(tmp_path):
    src = tmp_path / "w.xlsx"
    rows = [_row("2026-09-02", 8900000000001, 100.0), _row("2026-09-03", 8900000000002, 500.0)]
    rows[1]["Inv. Date"] = None
    _book(src, rows)
    assert ing.main(["--src", str(src), "--month", "Sep_26", "--out-dir", str(tmp_path), "--control-total", "600"]) == 1
    assert not (tmp_path / "primary_article_Sep_26.csv").exists()


def test_control_total_mismatch_or_missing_writes_nothing(tmp_path):
    src = tmp_path / "w.xlsx"
    _book(src, [_row("2026-09-02", 8900000000001, 100.0)])
    base = ["--src", str(src), "--month", "Sep_26", "--out-dir", str(tmp_path)]
    assert ing.main(base) == 1                                       # no pivot and no control total
    assert ing.main(base + ["--control-total", "999"]) == 1          # control disagrees
    assert not (tmp_path / "primary_article_Sep_26.csv").exists()
    assert ing.main(base + ["--control-total", "100"]) == 0


def test_date_outside_month_fails(tmp_path):
    src = tmp_path / "w.xlsx"
    _book(src, [_row("2026-08-30", 8900000000001, 10.0)])
    assert ing.main(["--src", str(src), "--month", "Sep_26", "--out-dir", str(tmp_path), "--control-total", "10"]) == 1
    assert not (tmp_path / "primary_article_Sep_26.csv").exists()
