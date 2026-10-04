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
    assert {"Thane", "Navi Mumbai", "Mohali", "Panchkula", "Ernakulam", "Howrah"} <= set(near["City (as in file)"])
    assert set(near["Nearest listed city"]) <= set(vc.CITY_REGION)
    assert book["Beat_Options"]["City"].isin(vc.CITY_REGION).all()                           # near-listed cities are not in the beats


def test_states_are_standard_in_the_store_list(book):
    assert set(book["Store_List"]["State"].dropna()) <= set(vc.STATE_STANDARD.values())
