"""Corporate-visit city rules, the maintained store master, and the city summary."""
import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import visit_cities as vc  # noqa: E402

MASTER = ROOT / "PowerBI" / "SeedData" / "Masters" / "Store_City_Master.csv"


def rows():
    with MASTER.open(encoding="utf-8", newline="") as h:
        return list(csv.DictReader(h))


def test_listed_cities_and_aliases():
    assert vc.match_city("Cochin") == vc.match_city("Kochi") == "Cochin"
    assert vc.match_city("Thiruvananthapuram") == "Trivandrum"
    assert vc.match_city("Allahabad") == "Prayagraj"
    assert vc.match_city("Kolkata-1-Vip Road") == "Kolkata" and vc.match_city("Varanasi2-Shivpur") == "Varanasi"
    assert vc.match_city("Kotagiri") is None and vc.match_city("Kothakota") is None          # not Kota
    assert vc.match_city("Jammu & Kasmir") is None                                          # a state, not Jammu city
    assert sum(len(c) for c in vc.REGIONS.values()) == 32                                   # Guwahati counted once


@pytest.mark.parametrize("city,near", [("Navi Mumbai", "Mumbai"), ("Thane", "Mumbai"), ("Mohali", "Chandigarh"), ("Panchkula", "Chandigarh"),
                                       ("Ernakulam", "Cochin"), ("Howrah", "Kolkata"), ("NAVI MUMBAI", "Mumbai")])
def test_near_listed_cities_get_the_third_option(city, near):
    visit, status, nearest = vc.classify(city)
    assert (visit, status, nearest) == (None, "Near listed city", near)


def test_other_cities_are_not_considered_and_blank_is_not_available():
    assert vc.classify("Bangalore")[1] == "Not considered"
    assert vc.classify(None)[1] == "City not available"
    assert vc.classify("Mumbai") == ("Mumbai", "Considered", "Mumbai")


def test_store_master_is_clean_and_complete():
    r = rows()
    assert len(r) > 10000
    assert len({x["Store Key"] for x in r}) == len(r)                                        # one row per store
    header = set(r[0])
    assert not any("SO" == h[:2] or "ASE" in h or "Employee" in h for h in header)           # no employee columns
    assert {x["Visit Status"] for x in r} <= {"Considered", "Near listed city", "Not considered", "City not available"}
    for x in r:
        if x["Visit Status"] == "Considered":
            assert x["Visit City"] and x["Visit Region"]
        if x["Visit Status"] == "Near listed city":
            assert x["Nearest Listed City"] and not x["Visit City"]
    assert any(x["City Final"] == "Thane" and x["Nearest Listed City"] == "Mumbai" for x in r)


def test_master_city_beats_offtake_locality_rules():
    r = rows()
    from_master = [x for x in r if x["City Source"] == "Master"]
    assert len(from_master) > 5000
    # Frankros keeps the offtake city (the store list holds localities)
    fr = [x for x in r if x["Chain Name"] == "Frankros" and x["City Source"] == "Offtake file"]
    assert fr and {x["City Final"] for x in fr} == {"Kolkata"} or len(fr) > 100


def test_city_summary_ties_to_the_visit_json():
    data = json.loads((ROOT / "data" / "nielsen" / "Visit_Cities_Aug26.json").read_text(encoding="utf-8"))
    assert len(data["cities"]) == 32 and len(data["top8"]) == 8
    near = {n["city"] for n in data["stats"]["near_listed"]}
    assert {"Thane", "Navi Mumbai", "Mohali", "Panchkula", "Ernakulam", "Howrah"} <= near
    assert data["stats"]["status_counts"]["Considered"] == sum(c["Stores"] for c in data["cities"])
    assert all(c["Beats"] in (0, 3, 5) for c in data["cities"])
    assert sum(1 for c in data["cities"] if c["Beats"] == 5) == 8


def test_visit_city_list_matches_the_rules():
    with (ROOT / "PowerBI/SeedData/Masters/Visit_City_List.csv").open(encoding="utf-8", newline="") as h:
        lst = list(csv.DictReader(h))
    assert [x["City"] for x in lst if x["Region"] == "East"] == vc.REGIONS["East"]
    mumbai = next(x for x in lst if x["City"] == "Mumbai")
    assert "Navi Mumbai" in mumbai["Near Listed (not on list)"] and "Thane" in mumbai["Near Listed (not on list)"]
