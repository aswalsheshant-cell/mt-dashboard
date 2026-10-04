"""Power BI Nielsen drop-folder files: real data, in the shape the queries and measures expect."""
import csv
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_nielsen_powerbi_seed as seed  # noqa: E402

PBI = ROOT / "PowerBI"
MONTHLY = PBI / "SeedData" / "Nielsen" / "Nielsen_Monthly" / "nielsen_urban_mt_aug26.csv"
PACKS = PBI / "SeedData" / "Nielsen" / "Nielsen_Pack_Monthly" / "nielsen_pack_urban_mt_aug26.csv"


def rows(path):
    with path.open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def test_monthly_file_matches_the_template_headers():
    tpl = (PBI / "RawDataFolders" / "Nielsen_Monthly" / "_TEMPLATE_Nielsen_Monthly.csv").read_text(encoding="utf-8").splitlines()[0]
    assert MONTHLY.read_text(encoding="utf-8").splitlines()[0] == tpl


def test_mamaearth_facewash_aug26_ties_to_the_workbook_extract():
    r = next(x for x in rows(MONTHLY) if x["Month"] == "Aug'26" and x["Nielsen Category"] == "Facewash" and x["Brand"] == "Mamaearth")
    assert float(r["Value Market Share %"]) == pytest.approx(0.12811, abs=1e-4)
    assert float(r["Our Brand Sales"]) / float(r["Market Value Sales"]) == pytest.approx(float(r["Value Market Share %"]), abs=2e-3)
    assert r["FY Year"] == "26-27" and r["Zone"] == "IN URB MT"


def test_no_header_row_masquerading_as_a_brand_and_shares_are_decimals():
    data = rows(MONTHLY)
    assert not any(x["Brand"].upper() == "BRAND" for x in data)
    shares = [float(x["Value Market Share %"]) for x in data if x["Value Market Share %"]]
    assert max(shares) < 1 and min(shares) >= 0
    assert {x["Nielsen Category"] for x in data} == {"Facewash", "Shampoo"}


def test_fy_label_follows_the_one_fy_rule():
    assert seed.fy_label("Apr 26") == "26-27" and seed.fy_label("Mar 26") == "25-26" and seed.fy_label("Aug 25") == "25-26"


def test_pack_file_has_both_basis_and_ties_to_category_total():
    data = rows(PACKS)
    fw = [float(x["Category Value Cr"]) for x in data if x["Month"] == "Aug'26" and x["Nielsen Category"] == "Facewash"]
    sh = [float(x["Category Value Cr"]) for x in data if x["Month"] == "Aug'26" and x["Nielsen Category"] == "Shampoo"]
    assert sum(fw) == pytest.approx(82.086, rel=0.01) and sum(sh) == pytest.approx(180.303, rel=0.01)


def test_queries_and_measures_reference_existing_columns():
    pq = (PBI / "PowerQuery" / "47_Fact_Nielsen_Pack.pq").read_text(encoding="utf-8")
    for col in rows(PACKS)[0]:
        assert f'"{col}"' in pq, col
    dax = (PBI / "DAX" / "04_Nielsen_Measures.dax").read_text(encoding="utf-8")
    for m in ("Pack Presence Status", "Pack Gap Amount", "Pack Price Per Ml", "Pack Our Contribution %", "Chain Share of Growth %", "Chain Contribution To Growth pp"):
        assert re.search(rf"^{re.escape(m)}\s*=", dax, re.M), m
    assert "DIVIDE" in dax and "'Chain Master'[Channel]" not in dax.split("CHAIN CONTRIBUTION")[1]   # uses [Total MT NSV], which already excludes RBC


def test_deck_seed_is_labelled():
    r = rows(PBI / "SeedData" / "Masters" / "Nielsen_Deck_StateExposure.csv")
    assert len(r) == 9 and all("deck" in x["Source"].lower() for x in r)


BRAND_CUT = PBI / "SeedData" / "Nielsen" / "Nielsen_Brand_Cut_Monthly" / "nielsen_brand_cut_urban_mt_aug26.csv"


def test_brand_cut_seed_ties_to_the_dashboard_payload_and_the_query_columns():
    import json
    pay = json.loads((ROOT / "data" / "nielsen_aug26.json").read_text(encoding="utf-8"))
    me = next(b for b in pay["fw_all"] if b["n"] == "Mamaearth")
    r = next(x for x in rows(BRAND_CUT) if x["Month"] == "Aug'26" and x["Nielsen Category"] == "Facewash" and x["Brand"] == "Mamaearth")
    assert float(r["Value Share %"]) * 100 == pytest.approx(me["ms"], abs=0.01) and float(r["WD %"]) == pytest.approx(me["wd"], abs=0.01)
    assert float(r["ND %"]) == pytest.approx(me["nd"], abs=0.01) and float(r["SAH %"]) == pytest.approx(me["sah"], abs=0.01) and float(r["Price Per Ml"]) == pytest.approx(me["ppml"], abs=0.001)
    cat = [x for x in rows(BRAND_CUT) if x["Is Category Row"] == "Yes" and x["Month"] == "Aug'26"]
    assert {x["Nielsen Category"] for x in cat} == {"Facewash", "Shampoo"} and all(x["Brand"] == "(Category)" for x in cat)
    header = list(rows(BRAND_CUT)[0])
    typed = re.findall(r'\{"([^"]+)", type', (PBI / "PowerQuery" / "57_Fact_Nielsen_Brand_Cut.pq").read_text(encoding="utf-8"))
    assert typed and set(typed) == set(header)


def test_refresh_script_runs_the_builders_in_order_and_skips_missing_inputs():
    import argparse
    import refresh_market_share_report as rf
    a = argparse.Namespace(label="Sep26", month="Sep 26", months=["Apr", "May", "Jun", "Jul", "Aug", "Sep"], tracker_from=Path("data/nielsen_aug26.json"), facewash=None, shampoo=None,
                           store_master=None, lulu=None, more=None, wellness=None, reliance=None, city_xlsx=Path("c.xlsx"), html=Path("h.html"), standalone=True)
    steps = rf.plan(a)
    names = [n for n, _, _ in steps]
    assert names.index("Payload (first pass)") < names.index("Account view and Facewash plan") < names.index("Payload (with the account view)") < names.index("Market-share HTML")
    skipped = [n for n, argv, _ in steps if argv is None]
    assert len(skipped) == 3 and all(why for _, argv, why in steps if argv is None)
    html = next(argv for n, argv, _ in steps if n == "Market-share HTML")
    assert "--standalone" in html and html[html.index("--data") + 1] == "data/nielsen_sep26.json"
