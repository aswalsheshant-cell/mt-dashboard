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
