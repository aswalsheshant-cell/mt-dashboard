"""The city workbook is checked after it is built: one row per store, one spelling per chain, sales tie to the offtake files."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_visit_city_plan as bp  # noqa: E402
import visit_cities as vc  # noqa: E402


@pytest.fixture(scope="module")
def book(tmp_path_factory):
    out = tmp_path_factory.mktemp("plan") / "plan.xlsx"
    bp.build(vc.MONTHS, "Aug26", out, ROOT / "data" / "nielsen_aug26.json")
    return pd.read_excel(out, sheet_name=None)


def test_qc_sheet_is_all_pass(book):
    qc = book["QC"].dropna(subset=["Expected"])
    assert len(qc) >= 10 and set(qc["Result"]) == {"PASS"}


def test_one_row_per_store_and_standard_chains_everywhere(book):
    sl = book["Store_List"]
    coded = sl[sl["Store code"].notna()]
    assert not coded.duplicated(["Chain", "Store code"]).any()
    assert not (sl["Store code"].isna() & sl["Store name"].isna()).any()                    # no chain-city total posing as a store
    names = set(sl["Chain"].dropna())
    for sheet in ("Beat_Options", "Chain_City_Totals", "Chain_NoCity"):
        names |= set(book[sheet]["Chain"].dropna())
    names |= {c for c in book["Chain_LastYear"]["Chain"].dropna() if c != "TOTAL" and not c.startswith("Chain level")}
    assert names <= set(vc.CHAIN_STANDARD), sorted(names - set(vc.CHAIN_STANDARD))


def test_three_consider_values_and_near_listed_sheet(book):
    sl = book["Store_List"]
    assert set(sl["Consider city?"]) == {"Considered", "Near listed city", "Not considered"}
    near = book["Near_Listed"]
    assert {"Mohali", "Panchkula", "Ernakulam", "Howrah"} <= set(near["City (as in file)"]) and not {"Thane", "Navi Mumbai"} & set(near["City (as in file)"])
    assert set(near["Nearest listed city"]) <= set(vc.CITY_REGION)
    bo = book["Beat_Options"].dropna(subset=["Region"])                                      # the two count cells under the table have no region
    assert bo["City"].isin(vc.CITY_REGION).all()                                             # near-listed cities are not in the beats
    assert len(bo) == bo.drop_duplicates(["Chain", "Store code", "Store name"]).shape[0]       # no store twice (the Store count column is a formula, read blank here)


def test_states_are_standard_in_the_store_list(book):
    assert set(book["Store_List"]["State"].dropna()) <= set(vc.STATE_STANDARD.values())


def test_last_year_store_sales_load_only_from_real_files(tmp_path, monkeypatch):
    """LY store sales come from offtake_store_article_<Mon>_25.csv files; with none present nothing is filled or estimated."""
    import build_visit_city_plan as bvp
    import visit_cities as vc
    monkeypatch.setattr(vc, "RAW", tmp_path)
    monkeypatch.setattr(bvp, "LY_AGG", tmp_path / "none.csv")
    assert bvp.load_ly_store() == (None, [])
    hdr = "Unique Code,Zone,State,City,Chain Name,Store Type,Site Code,Site Name,EAN,Brand,Category,Sub_category,Sales Qty,NSV"
    row = "x,West,Maharashtra,Pune,Dmart,Non Brand Counter,D1,Dmart Pune,1,Mamaearth,Face,Face Wash,2,1.5"
    (tmp_path / "offtake_store_article_Apr_25.csv").write_text(f"{hdr}\n{row}\n{row}\n", encoding="utf-8")
    t, have = bvp.load_ly_store()
    assert have == ["Apr-25"] and float(t.loc["D-Mart|D1", "Apr-25"]) == 3.0


def test_reliance_state_sheet_and_like_for_like_city_yoy(book):
    assert "Reliance_State_YoY" in book
    rs = book["Reliance_State_YoY"].dropna(subset=["State"])
    assert len(rs) >= 15 and "Andhra Pradesh" in set(rs["State"])
    cs = book["City_Summary"]
    assert any(c.startswith("NSV this year, stores with last-year sales") for c in cs.columns)
