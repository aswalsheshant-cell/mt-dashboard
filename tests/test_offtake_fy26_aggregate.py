"""Last-year (Apr-25 to Mar-26) store x month offtake, built from the cleaned FY26 store x article files."""
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
AGG = ROOT / "data" / "offtake_fy26" / "Store_Month_NSV_FY26.csv"
MONTHS = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25", "Oct'25", "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26"]


@pytest.fixture(scope="module")
def agg():
    return pd.read_csv(AGG)


def test_one_row_per_store_and_month_and_twelve_months(agg):
    assert not agg.duplicated(["Store Key", "Month"]).any()
    assert set(agg["Month"]) == set(MONTHS)
    assert not agg[["Store Key", "Chain Name", "NSV"]].isna().any().any()


def test_every_chain_month_ties_to_the_published_fy26_baseline(agg):
    ly = json.loads((ROOT / "data" / "raw_drops" / "_agg" / "offtake_fy26.json").read_text(encoding="utf-8")) if (ROOT / "data" / "raw_drops" / "_agg" / "offtake_fy26.json").exists() else None
    if ly is None:
        pytest.skip("data/raw_drops/_agg/offtake_fy26.json is not in this checkout (ignored folder)")
    mon = lambda m: m.replace("'", "-")      # noqa: E731
    non_bc = agg[agg["Chain Name"] != "Reliance Brand Counter"]
    assert non_bc["NSV"].sum() == pytest.approx(31119.87, abs=0.2)                 # the FY26 baseline
    by_month = non_bc.groupby("Month")["NSV"].sum()
    base = {}
    for chain, v in ly["by_chain"].items():
        for m, x in v.items():
            base[m] = base.get(m, 0) + (x or 0)
    for m in MONTHS:
        assert by_month[m] == pytest.approx(base[mon(m)], abs=0.1), m
    bc = agg[agg["Chain Name"] == "Reliance Brand Counter"].groupby("Month")["NSV"].sum()
    for m, v in zip(MONTHS, ly["bc_monthly"]):
        assert bc[m] == pytest.approx(v, abs=0.011), m


def test_the_qc_report_has_no_error_and_names_what_it_did():
    qc = pd.read_csv(ROOT / "data" / "qc" / "offtake_fy26_QC.csv")
    assert not (qc["Severity"] == "ERROR").any()
    text = " ".join(qc["Check"])
    for need in ("one row per month x chain x store x EAN", "one Zone per store", "one Brand per EAN", "input NSV = output NSV", "ties to data/raw_drops/_agg/offtake_fy26.json", "scientific notation"):
        assert need in text, need
    assert int(qc.loc[qc["Check"].str.startswith("input NSV = output NSV"), "Count"].iloc[0]) == 0


def test_store_keys_follow_the_store_master(agg):
    m = pd.read_csv(ROOT / "PowerBI" / "SeedData" / "Masters" / "Store_City_Master.csv", dtype=str)
    coded = set(m.loc[m["Site Code"].notna(), "Store Key"])
    ly_coded = agg[agg["Chain Name"].isin(["Apollo", "D-Mart", "Health & Glow", "Lulu", "Wellness Forever"])].drop_duplicates("Store Key")
    assert ly_coded["Store Key"].isin(coded).mean() > 0.6          # last-year stores that still exist this year use the same key
