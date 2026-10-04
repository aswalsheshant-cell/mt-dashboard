"""Visit-city list, spelling aliases, near-listed cities, and the store-level offtake loader.

Shared by build_store_city_master.py and build_visit_city_plan.py so the city rules live in one place.

Status of a store's city against the corporate-visit list:
  Considered        city is on the list (spelling aliases applied)
  Near listed city  city is NOT on the list but sits next to a listed one (Mohali, Panchkula, Ernakulam, Howrah); the nearest
                    listed city is recorded as a third option. Thane and Navi Mumbai are not near-listed: they are in the Mumbai beats.
  Not considered    any other city
  City not available  the source has no city for the store
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
MONTHS = ["Apr", "May", "Jun", "Jul", "Aug"]

REGIONS = {
    "North + Central": ["Ludhiana", "Varanasi", "Kanpur", "Prayagraj", "Jodhpur", "Agra", "Dehradun", "Amritsar", "Kota", "Jammu", "Bikaner", "Chandigarh"],
    "West": ["Mumbai", "Pune", "Ahmedabad", "Indore", "Bhopal", "Vadodara", "Nashik", "Jabalpur"],
    "South": ["Hyderabad", "Madurai", "Trivandrum", "Cochin", "Trichy"],     # Mysore / Mangalore too small to justify a visit
    "East": ["Kolkata", "Siliguri", "Guwahati", "Bhubaneswar", "Ranchi", "Jamshedpur", "Cuttack"],   # Guwahati was listed twice
}
CITY_REGION = {c: r for r, cs in REGIONS.items() for c in cs}
LISTED = {c.lower(): c for c in CITY_REGION}
ALIASES = {"allahabad": "Prayagraj", "pryagraj": "Prayagraj", "thiruvananthapuram": "Trivandrum", "kochi": "Cochin",
           "tiruchirappalli": "Trichy", "baroda": "Vadodara", "kapra hyderabad": "Hyderabad",
           "thane": "Mumbai", "navi mumbai": "Mumbai"}       # Thane and Navi Mumbai join the Mumbai beats (owner decision 2026-10-04)
# not on the list, but next to a listed city -> the nearest listed city
NEAR = {"mohali": "Chandigarh", "panchkula": "Chandigarh",
        "kurali (sas nagar/mohali)": "Chandigarh", "new chandigarh (mohali)": "Chandigarh", "ernakulam": "Cochin", "howrah": "Kolkata"}
BAD = ("&", "kasmir", "kashmir")
ZONE_FIX = {"WEST": "West", "SOUTH-1": "South-1", "SOUTH-2": "South-2", "NORTH": "North", "EAST": "East", "CENTRAL": "Central",
            "SOUTH1": "South-1", "SOUTH2": "South-2"}


def _n(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


# One standard spelling per chain (ChainMaster.csv spelling where the chain is there). Any chain not listed stops the build:
# a new spelling must be added here on purpose, never slip through as a second chain.
CHAIN_STANDARD = {
    "Apna Mart": ["apnamart"], "Apollo": ["apollo"], "Arambagh": ["arambagh"], "Azorte": ["azorte"], "B&N": ["beautynutrie", "bn"],
    "Broadway": ["broadway"], "Centro": ["centro"], "D-Mart": ["dmart"], "Nykaa FSN": ["fsn", "nykaafsn"], "Frank Ross": ["frankros", "frankross"],
    "Guardian": ["guardian"], "Health & Glow": ["hg", "healthglow"], "Lifestyle": ["lifestyle"], "Lulu": ["lulu"], "Metro CNC": ["metrocnc", "metrocc"],
    "More Retail": ["moreretail"], "National Mart": ["nationalmart"], "Ratnadeep": ["ratnadeep", "ratandeep", "ratanadeep"],
    "Reliance Retail": ["reliance", "relianceretail"], "Reliance Brand Counter": ["reliancebrandcounter"],
    "RMT-Sancus": ["sancusrmt", "rmtsancus"], "SastaSundar": ["sastasundar"], "Shoppers Stop": ["shoppersstop", "ssl"], "Spencers": ["spencer", "spencers"],
    "Sumo Save": ["sumosave"], "Trends": ["trends"], "Trent": ["trent", "trentwestside"], "Vijetha": ["vijetha"], "V-Mart": ["vmart"], "Vishal Mega Mart": ["vmm", "vishalmegamart"],
    "Walmart CNC": ["walmartcnc", "walmart"], "WH-Smith": ["whsmith"], "Wellness Forever": ["wellnessforever"],
}
CHAIN_LOOKUP = {k: std for std, keys in CHAIN_STANDARD.items() for k in keys}


def std_chain(raw):
    """Standard chain name, or None if the spelling is not known (the caller must stop, not guess)."""
    return CHAIN_LOOKUP.get(_n(raw)) if raw is not None else None


STATE_STANDARD = {
    "andhrapradesh": "Andhra Pradesh", "bihar": "Bihar", "chhattisgarh": "Chhattisgarh", "chhatisgarh": "Chhattisgarh", "delhi": "Delhi NCR",
    "delhincr": "Delhi NCR", "goa": "Goa", "gujarat": "Gujarat", "haryana": "Haryana", "hayana": "Haryana", "himachalpradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand", "jammukashmir": "Jammu & Kashmir", "jammukasmir": "Jammu & Kashmir", "jammuandkashmir": "Jammu & Kashmir",
    "karnataka": "Karnataka", "kerala": "Kerala", "madhyapradesh": "Madhya Pradesh", "mp": "Madhya Pradesh", "maharashtra": "Maharashtra",
    "mumbai": "Maharashtra", "northeast": "Northeast", "odisha": "Odisha", "orissa": "Odisha", "punjab": "Punjab", "rajasthan": "Rajasthan",
    "tamilnadu": "Tamil Nadu", "tn": "Tamil Nadu", "cg": "Chhattisgarh", "telangana": "Telangana", "up": "Uttar Pradesh", "uttarpradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand",
    "westbengal": "West Bengal", "panindia": "Pan India",
}
STATE_GROUPS = {"upuk", "punjabjkhp"}          # regional groupings in the source (not a state): the state is taken from the store's city


# a "city" that is really a state or region name (Reliance rows carry the state in the city field): not a city
STATE_AS_CITY = {k for k in STATE_STANDARD if k not in ("mumbai", "delhi", "goa", "delhincr")} | STATE_GROUPS | {"northeast"}


def is_state_name(city):
    return isinstance(city, str) and _n(city) in STATE_AS_CITY


def std_state(raw):
    """(state, is_group). A grouping such as UP/UK returns (None, True)."""
    k = _n(raw) if raw is not None else ""
    if k in STATE_GROUPS:
        return None, True
    return STATE_STANDARD.get(k), False


def norm_code(code):
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return None
    c = re.sub(r"\.0$", "", re.sub(r"\s+", " ", str(code)).strip()).upper()
    return None if c in ("", "NOT AVAILABLE", "NA", "NAN", "NONE", "0") else c


def clean(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = unicodedata.normalize("NFKC", str(s)).replace("\xa0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return None if s in ("", "0", "0.0", "nan", "None") else s


def match_city(city):
    """The listed city a file city belongs to ('Kolkata-1-Vip Road' -> Kolkata), else None."""
    if not isinstance(city, str) or not city:
        return None
    c = city.lower()
    if c in ALIASES:
        return ALIASES[c]
    if c in LISTED:
        return LISTED[c]
    if any(b in c for b in BAD):
        return None
    for key, name in list(LISTED.items()) + list(ALIASES.items()):
        if c.startswith(key) and (len(c) == len(key) or not c[len(key)].isalpha()):
            return name if key in LISTED else ALIASES[key]
    return None


def near_city(city):
    if not isinstance(city, str) or match_city(city):
        return None
    c = city.lower()
    for key, listed in NEAR.items():
        if c == key or (c.startswith(key) and not c[len(key)].isalpha()):
            return listed
    return None


def classify(city):
    """(visit_city, status, nearest_listed_city) for one file city."""
    listed = match_city(city)
    if listed:
        return listed, "Considered", listed
    near = near_city(city)
    if near:
        return None, "Near listed city", near
    return None, ("Not considered" if isinstance(city, str) and city else "City not available"), None


# Zone rules from the owner (2026-10-04): one zone per state, except Maharashtra, which is divided.
STATE_ZONE = {"Andhra Pradesh": "South-2", "Odisha": "East", "Rajasthan": "North", "Chhattisgarh": "Central"}
CENTRAL_MAHARASHTRA = {"nagpur", "amravati", "akola", "wardha", "chandrapur", "yavatmal", "gondia", "bhandara", "buldhana", "washim", "gadchiroli", "achalpur", "wani", "hinganghat",
                       "khamgaon", "ballarpur", "warora", "umred", "nagpu"}      # Vidarbha only; Pune and the rest of Maharashtra are West (owner, 2026-10-04)


def apply_zone_rules(state, city, zone):
    """The zone after the owner's rules: Andhra Pradesh South-2, Odisha East, Rajasthan North, Chhattisgarh Central; Maharashtra is Central for Vidarbha, West elsewhere (Pune included)."""
    if state in STATE_ZONE:
        return STATE_ZONE[state]
    if state == "Maharashtra":
        c = str(city or "").lower().strip()
        return "Central" if c in CENTRAL_MAHARASHTRA or any(c.startswith(k + " ") for k in CENTRAL_MAHARASHTRA) else "West"
    return zone


def norm_zone(z):
    z = clean(z)
    return ZONE_FIX.get(z.upper().replace(" ", "-"), z.title()) if z else None


ALIASES_CSV = ROOT / "PowerBI" / "SeedData" / "Masters" / "Store_Key_Aliases.csv"


def load_aliases():
    """{alias Store Key: Store Key}: store keys that are the same store (same chain + store name + city) and were merged into one by build_store_city_master.py."""
    if not ALIASES_CSV.exists():
        return {}
    a = pd.read_csv(ALIASES_CSV, dtype=str).dropna(subset=["Alias Store Key"])      # rows with a blank Alias Store Key only add a Match Key spelling
    return dict(zip(a["Alias Store Key"], a["Store Key"]))


def load_offtake(months=MONTHS, aliases=True, year="26"):
    """Store x article offtake rows for the months given, one frame, with a store id (sid).

    sid = chain + site code where the file has a code; chain + site name, or chain + city, where it does not.
    NSV is Rs lakh as in the source. April rows carry an Excel date code in Month, so the month comes from the file name.
    """
    cols = ["Unique", "Unique Code", "Zone", "State", "City", "Chain Name", "Store Type", "Site Code", "Site Name", "EAN", "Brand",
            "Category", "Sub_category", "Sales Qty", "NSV", "Net Weight"]
    frames = []
    for m in months:
        d = pd.read_csv(RAW / f"offtake_store_article_{m}_{year}.csv", low_memory=False, usecols=lambda c: c in cols)
        d = d.rename(columns={"Unique": "Unique Code"})
        d["file"] = m
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["Chain Raw"] = d["Chain Name"].map(lambda s: re.sub(r"\s+", " ", str(s)).strip())
    d["Chain"] = d["Chain Raw"].map(std_chain)
    unknown = sorted(d.loc[d["Chain"].isna(), "Chain Raw"].unique())
    if unknown:
        raise ValueError(f"chain spelling(s) not in CHAIN_STANDARD: {unknown} (add them on purpose in scripts/visit_cities.py)")
    d["bc"] = d["Store Type"].astype(str).str.strip().eq("Brand Counter")
    # a staffed Brand Counter store is one store: Apr-Jun files label its rows "Reliance", Jul-Aug files "Reliance Brand Counter"
    d.loc[d["bc"] & (d["Chain"] == "Reliance Retail"), "Chain"] = "Reliance Brand Counter"
    for c in ("City", "State", "Site Name"):
        d[c] = d[c].map(clean)
    d["Zone"] = d["Zone"].map(norm_zone)
    d["code"] = d["Site Code"].map(norm_code)
    d["Offtake Key"] = d["Unique Code"].astype(str).str.strip()
    # one identity per store: standard chain + site code; chain + name or chain + city where the file has no code
    d["sid"] = d["Chain"] + "|" + d["code"].fillna("")
    nocode = d["code"].isna()
    d.loc[nocode & d["Site Name"].notna(), "sid"] = d["Chain"] + "|" + d["Site Name"]
    d.loc[nocode & d["Site Name"].isna() & d["City"].notna(), "sid"] = d["Chain"] + "|" + d["City"]
    d.loc[nocode & d["Site Name"].isna() & d["City"].isna(), "sid"] = d["Chain"] + "|NO-CITY|" + d["State"].fillna("")
    if aliases:     # two keys for one store (same chain + name + city) count once
        a = load_aliases()
        d["sid"] = d["sid"].map(lambda k: a.get(k, k))
    return d
