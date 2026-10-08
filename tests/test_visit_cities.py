"""Corporate-visit city rules, the maintained store master, and the city summary."""
import csv
import json
import re
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


def test_thane_and_navi_mumbai_are_in_the_mumbai_beats():
    for c in ("Thane", "Navi Mumbai", "NAVI MUMBAI", "Thane West"):
        assert vc.classify(c) == ("Mumbai", "Considered", "Mumbai"), c


@pytest.mark.parametrize("city,near", [("Mohali", "Chandigarh"), ("Panchkula", "Chandigarh"), ("Ernakulam", "Cochin"), ("Howrah", "Kolkata")])
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
    assert any(x["City Final"] == "Thane" and x["Visit City"] == "Mumbai" and x["Visit Status"] == "Considered" for x in r)


def test_every_chain_has_one_standard_spelling():
    r = rows()
    names = {x["Chain Name"] for x in r}
    assert names <= set(vc.CHAIN_STANDARD), sorted(names - set(vc.CHAIN_STANDARD))
    norm = {}
    for n in names:
        norm.setdefault(vc._n(n), set()).add(n)
    assert all(len(v) == 1 for v in norm.values())
    assert not [n for n in names if re.search(r"rswb|hinop|eb$| fl$|tb$|san$", n.lower())]    # the glued-code names of the first version
    assert vc.std_chain("Ratandeep") == vc.std_chain("Ratanadeep") == vc.std_chain("RATNADEEP") == "Ratnadeep"
    assert vc.std_chain("Sasta SundarRSWB") is None                                         # a glued code is an unknown chain, not a new chain


def test_one_row_per_chain_and_store_code():
    seen = set()
    for x in rows():
        if x["Site Code"]:
            k = (x["Chain Name"], x["Site Code"])
            assert k not in seen, f"{k} appears on two rows"
            seen.add(k)


def test_states_cities_and_text_are_standard():
    r = rows()
    states = {x["State"] for x in r if x["State"]}
    assert states <= set(vc.STATE_STANDARD.values()), sorted(states - set(vc.STATE_STANDARD.values()))
    assert not {"UP", "Up", "UP/UK", "MP", "KARNATAKA", "Delhi/ Ncr", "Punjab/J&K/Hp"} & states
    for col in ("Chain Name", "Store Name", "City Final", "State", "Zone"):
        for x in r:
            v = x[col]
            assert v == v.strip() and "  " not in v, (col, v)
    cities = [x["City Final"] for x in r if x["City Final"]]
    low = {}
    for c in cities:
        low.setdefault(c.lower(), set()).add(c)
    assert all(len(v) == 1 for v in low.values())
    assert not [c for c in cities if vc.is_state_name(c)]                                    # a state name is not a city


def test_store_master_qc_report_has_no_errors():
    qc = list(csv.DictReader((ROOT / "PowerBI/SeedData/Masters/Store_City_Master_QC.csv").open(encoding="utf-8")))
    assert not [q for q in qc if q["Severity"] == "ERROR"]


def test_unknown_chain_and_bad_values_are_caught_by_the_gate():
    import build_store_city_master as bm
    import pandas as pd
    df = pd.DataFrame([{"Store Key": "A|1", "Chain Name": "Sasta SundarRSWB", "Site Code": "1", "Store Name": "x", "City Final": "Pune", "State": "Maharashtra", "Zone": "West", "State Note": None},
                       {"Store Key": "A|1", "Chain Name": "Apollo", "Site Code": "1", "Store Name": "x ", "City Final": "pune", "State": "UP", "Zone": "West", "State Note": None}])
    errors = [f[1] for f in bm.qc(df) if f[0] == "ERROR"]
    assert "Store Key is not unique" in errors and "chain name not a standard chain" in errors
    assert "state is not a standard state" in errors and any("spaces" in e for e in errors)


def test_city_summary_ties_to_the_visit_json():
    data = json.loads((ROOT / "data" / "nielsen" / "Visit_Cities_Aug26.json").read_text(encoding="utf-8"))
    assert len(data["cities"]) == 32 and len(data["top8"]) == 8
    near = {n["city"] for n in data["stats"]["near_listed"]}
    assert {"Mohali", "Panchkula", "Ernakulam", "Howrah"} <= near and not {"Thane", "Navi Mumbai"} & near
    assert data["stats"]["status_counts"]["Considered"] == sum(c["Stores"] for c in data["cities"])
    assert all(c["Beats"] in (0, 3, 5) for c in data["cities"])
    assert sum(1 for c in data["cities"] if c["Beats"] == 5) == 8


def test_visit_city_list_matches_the_rules():
    with (ROOT / "PowerBI/SeedData/Masters/Visit_City_List.csv").open(encoding="utf-8", newline="") as h:
        lst = list(csv.DictReader(h))
    assert [x["City"] for x in lst if x["Region"] == "East"] == vc.REGIONS["East"]
    mumbai = next(x for x in lst if x["City"] == "Mumbai")
    assert "Navi Mumbai" in mumbai["Aliases"] and "Thane" in mumbai["Aliases"]            # they are in the Mumbai beats
