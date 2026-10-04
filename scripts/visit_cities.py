"""Visit-city list, spelling aliases, near-listed cities, and the store-level offtake loader.

Shared by build_store_city_master.py and build_visit_city_plan.py so the city rules live in one place.

Status of a store's city against the corporate-visit list:
  Considered        city is on the list (spelling aliases applied)
  Near listed city  city is NOT on the list but sits next to a listed one (Navi Mumbai, Thane, Mohali,
                    Panchkula, Ernakulam, Howrah); the nearest listed city is recorded as a third option
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
           "tiruchirappalli": "Trichy", "baroda": "Vadodara", "kapra hyderabad": "Hyderabad"}
# not on the list, but next to a listed city -> the nearest listed city
NEAR = {"navi mumbai": "Mumbai", "thane": "Mumbai", "mohali": "Chandigarh", "panchkula": "Chandigarh",
        "kurali (sas nagar/mohali)": "Chandigarh", "new chandigarh (mohali)": "Chandigarh", "ernakulam": "Cochin", "howrah": "Kolkata"}
BAD = ("&", "kasmir", "kashmir")
ZONE_FIX = {"WEST": "West", "SOUTH-1": "South-1", "SOUTH-2": "South-2", "NORTH": "North", "EAST": "East", "CENTRAL": "Central",
            "SOUTH1": "South-1", "SOUTH2": "South-2"}


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


def norm_zone(z):
    z = clean(z)
    return ZONE_FIX.get(z.upper().replace(" ", "-"), z.title()) if z else None


def load_offtake(months=MONTHS):
    """Store x article offtake rows for the months given, one frame, with a store id (sid).

    sid = chain + site code where the file has a code; chain + site name, or chain + city, where it does not.
    NSV is Rs lakh as in the source. April rows carry an Excel date code in Month, so the month comes from the file name.
    """
    cols = ["Unique", "Unique Code", "Zone", "State", "City", "Chain Name", "Store Type", "Site Code", "Site Name", "EAN", "Brand",
            "Category", "Sub_category", "Sales Qty", "NSV"]
    frames = []
    for m in months:
        d = pd.read_csv(RAW / f"offtake_store_article_{m}_26.csv", low_memory=False, usecols=lambda c: c in cols)
        d = d.rename(columns={"Unique": "Unique Code"})
        d["file"] = m
        frames.append(d)
    d = pd.concat(frames, ignore_index=True)
    d["Chain"] = d["Chain Name"].map(lambda s: re.sub(r"\s+", " ", str(s)).strip().upper())
    d["bc"] = d["Store Type"].astype(str).str.strip().eq("Brand Counter")
    for c in ("City", "State", "Site Name"):
        d[c] = d[c].map(clean)
    d["Zone"] = d["Zone"].map(norm_zone)
    d["Site Code"] = d["Site Code"].map(lambda v: None if pd.isna(v) else re.sub(r"\.0$", "", str(v).strip()))
    key = d["Unique Code"].astype(str).str.strip()
    d["sid"] = key
    nocode = d["Site Code"].isna()
    d.loc[nocode & d["Site Name"].notna(), "sid"] = key + "|" + d["Site Name"]
    d.loc[nocode & d["Site Name"].isna() & d["City"].notna(), "sid"] = key + "|" + d["City"]
    d.loc[nocode & d["Site Name"].isna() & d["City"].isna(), "sid"] = key + "|NO-CITY|" + d["State"].fillna("")
    return d
