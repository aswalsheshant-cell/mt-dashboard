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
MONTHLY = PBI / "RawDataFolders" / "Nielsen_Monthly" / "nielsen_urban_mt_aug26.csv"
PACKS = PBI / "RawDataFolders" / "Nielsen_Pack_Monthly" / "nielsen_pack_urban_mt_aug26.csv"


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
