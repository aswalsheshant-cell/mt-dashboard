"""One store = one row in the store master; merged codes are kept as aliases and the offtake follows them."""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MASTERS = ROOT / "PowerBI" / "SeedData" / "Masters"


def _norm(x):
    return re.sub(r"[^a-z0-9]", "", str(x).lower())


def test_no_store_appears_twice_in_the_master():
    m = pd.read_csv(MASTERS / "Store_City_Master.csv", dtype=str)
    assert m["Store Key"].is_unique
    named = m[m["Store Name"].notna() & m["City Final"].notna()]
    key = named["Chain Name"] + "|" + named["Store Name"].map(_norm) + "|" + named["City Final"].str.lower()
    assert not key.duplicated().any(), named.loc[key.duplicated(keep=False), "Store Key"].head(10).tolist()


def test_aliases_point_at_a_store_in_the_master_and_keep_their_codes():
    m = pd.read_csv(MASTERS / "Store_City_Master.csv", dtype=str).set_index("Store Key")
    a = pd.read_csv(MASTERS / "Store_Key_Aliases.csv", dtype=str)
    keys = a.dropna(subset=["Alias Store Key"])                                    # a blank Alias Store Key only adds a Match Key spelling
    assert len(keys) > 100 and keys["Alias Store Key"].is_unique
    assert a["Alias Match Key"].dropna().is_unique and not set(a["Alias Match Key"].dropna()) & set(m["Match Key"].dropna())
    assert not set(keys["Alias Store Key"]) & set(m.index)            # an alias is never also a store row
    assert set(a["Store Key"]) <= set(m.index)
    coded = keys.dropna(subset=["Alias Site Code"])
    for _, r in coded.head(200).iterrows():
        assert r["Alias Site Code"] in str(m.at[r["Store Key"], "Other Site Codes"]).split("; ") or r["Store Match Key"] != r["Alias Match Key"]
        assert r["Store Match Key"] == m.at[r["Store Key"], "Match Key"]


def test_offtake_keys_follow_the_alias(monkeypatch):
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import visit_cities as vc
    a = vc.load_aliases()
    assert a and all(k != v for k, v in a.items())
    assert "Apollo|25876" in a and a["Apollo|25876"] == "Apollo|18692"


def test_state_and_zone_follow_the_offtake_data():
    """A store that sells carries the state and zone of its own offtake rows (standard spelling)."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import visit_cities as vc
    m = pd.read_csv(MASTERS / "Store_City_Master.csv", dtype=str).set_index("Store Key")
    o = vc.load_offtake(["Aug"])
    mode = lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None   # noqa: E731
    g = o.groupby("sid").agg(State=("State", mode), Zone=("Zone", mode))
    g["State"] = g["State"].map(lambda x: vc.std_state(x)[0])
    g = g[g["State"].notna() & (g["State"] != "Pan India") & g.index.isin(m.index)]
    g["Zone"] = [vc.apply_zone_rules(st, c, z) for st, c, z in zip(g["State"], o.groupby("sid")["City"].agg(mode).reindex(g.index), g["Zone"])]      # the owner's zone rules sit on top of the offtake zone
    assert len(g) > 5000
    bad = g[(g["State"] != m.loc[g.index, "State"]) | (g["Zone"] != m.loc[g.index, "Zone"])]
    assert len(bad) / len(g) < 0.02, bad.head(10).index.tolist()           # only stores whose Aug rows disagree with their own earlier months can differ


def test_zone_rules_from_the_owner():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import visit_cities as vc
    assert vc.apply_zone_rules("Andhra Pradesh", "Guntur", "South-1") == "South-2" and vc.apply_zone_rules("Odisha", "Cuttack", "North") == "East"
    assert vc.apply_zone_rules("Rajasthan", "Jaipur", "Central") == "North" and vc.apply_zone_rules("Chhattisgarh", "Raipur", "West") == "Central"
    assert [vc.apply_zone_rules("Maharashtra", c, "West") for c in ("Nagpur", "Pune", "Wakad", "Mumbai", "Nashik")] == ["Central", "West", "West", "West", "West"]
    m = pd.read_csv(MASTERS / "Store_City_Master.csv", dtype=str)
    z = m.groupby("State")["Zone"].nunique()
    assert list(z[z > 1].index) == ["Maharashtra"]                                      # the only divided state
    assert set(m.loc[m.State == "Chhattisgarh", "Zone"]) == {"Central"} and set(m.loc[m.State == "Andhra Pradesh", "Zone"]) == {"South-2"}
