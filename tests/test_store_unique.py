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
    assert len(a) > 100 and a["Alias Store Key"].is_unique
    assert not set(a["Alias Store Key"]) & set(m.index)               # an alias is never also a store row
    assert set(a["Store Key"]) <= set(m.index)
    coded = a.dropna(subset=["Alias Site Code"])
    for _, r in coded.head(200).iterrows():
        assert r["Alias Site Code"] in str(m.at[r["Store Key"], "Other Site Codes"]).split("; ")
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
    assert len(g) > 5000
    bad = g[(g["State"] != m.loc[g.index, "State"]) | (g["Zone"] != m.loc[g.index, "Zone"])]
    assert len(bad) / len(g) < 0.02, bad.head(10).index.tolist()           # only stores whose Aug rows disagree with their own earlier months can differ
