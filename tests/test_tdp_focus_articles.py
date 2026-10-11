"""The TDP focus article list follows the agreed rule and stays an aggregate (no store rows)."""
from pathlib import Path

import pandas as pd

M = Path(__file__).resolve().parent.parent / "PowerBI" / "SeedData" / "Masters"


def _focus():
    return pd.read_csv(M / "TDP_Focus_Articles.csv", dtype={"EAN": str})


def test_every_chain_brand_reaches_95_percent():
    f = _focus()
    top = f[f.Selection.str.contains("TOP95")]
    reach = top.groupby(["Chain", "Brand"])["Cum Share %"].max()
    assert (reach >= 95 - 0.01).all(), reach[reach < 95]


def test_keys_are_unique_and_filled():
    f = _focus()
    assert not f.duplicated(["Chain", "Brand", "EAN"]).any()
    assert f.EAN.str.len().eq(13).all()
    assert f["Article Description"].notna().all()


def test_new_articles_start_in_2026_or_later():
    n = pd.read_csv(M / "TDP_New_Articles_Since_Jan26.csv", dtype={"EAN": str})
    assert n.EAN.is_unique
    jan = n[n.Type.str.contains("NEW_SINCE_JAN26")]
    assert jan["First Sale"].ge("2026-01").all()
    # an article that is only new to a chain (offtake NPI) may be older overall but must be new to at least one chain
    npi = n[n.Type.eq("NPI_NEW_TO_CHAIN")]
    assert (npi["Chains New To"] >= 1).all()


def test_npi_rows_are_absent_from_the_april_baseline_of_their_chain():
    f = _focus()
    npi = f[f.Selection.str.contains("NPI_NEW_TO_CHAIN")]
    assert len(npi) > 0
    assert npi["First Month in Chain"].gt("2026-04").all()


def test_trends_is_its_own_chain_not_reliance_retail():
    f = _focus()
    assert "Reliance Trends" in set(f.Chain)
    q = (Path(__file__).resolve().parent.parent / "PowerBI" / "PowerQuery" / "11_Fact_OfftakeSales.pq").read_text(encoding="utf-8")
    assert '{"trends", "Reliance Trends"}' in q and 'if [Chain] = "Reliance Trends"' in q


def test_no_store_level_columns():
    cols = set(_focus().columns)
    assert not cols & {"Site Code", "Site Name", "Store Code", "SO/ASE Emp Code", "SO/ASE Name"}
