"""Jul-Aug'26 Distributor Secondary register (2026-09-27).

Guards the register files built by scripts/build_secondary_register.py:
same schema as the Q1 register, the three views and the article grain agree,
July reconciles to the July rows already in 01_FULL_HIERARCHY, missing
registers are never written as zero, and the GST-basis flag reaches the
Notes text that 44_Fact_SecondarySales.pq reads as Is_Provisional."""
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "PowerBI/RawDataFolders/SecondarySales_Monthly"
TOT = ROOT / "PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis"
MONTHS = {"2026-07", "2026-08"}


def _csv(p, **kw):
    return pd.read_csv(p, **kw)


@pytest.fixture(scope="module")
def files():
    return {
        "dist": _csv(REG / "secondary_sales_distributor_Jul_Aug_FY27.csv"),
        "chain": _csv(REG / "secondary_sales_chain_Jul_Aug_FY27.csv"),
        "brand": _csv(REG / "secondary_sales_brand_Jul_Aug_FY27.csv"),
        "art": _csv(TOT / "05_ARTICLE_REGISTER_Jul_Aug_2026.csv", dtype={"EAN": str}),
        "exc": _csv(TOT / "06_REGISTER_EXCEPTIONS_Jul_Aug_2026.csv"),
    }


def test_schema_matches_q1_register(files):
    for kind in ("dist", "chain", "brand"):
        q1 = {"dist": "distributor", "chain": "chain", "brand": "brand"}[kind]
        want = list(_csv(REG / f"secondary_sales_{q1}_Q1_FY27.csv", nrows=1).columns)
        assert list(files[kind].columns) == want, f"{q1} register columns drifted from Q1"


def test_months_and_fy_tag(files):
    for kind in ("dist", "chain", "brand", "art"):
        assert set(files[kind]["Source_Month"]) == MONTHS
        assert set(files[kind]["FY_Year"]) == {"FY27"}   # Jul/Aug 2026 -> FY27 (THE ONE FY RULE)


def test_views_agree_per_month(files):
    art = files["art"].groupby("Source_Month")["NSV_Value"].sum() / 1e5
    for kind in ("dist", "chain", "brand"):
        tot = files[kind].groupby("Source_Month")["NSV_Lakh"].sum()
        for m in MONTHS:
            assert abs(tot[m] - art[m]) < 0.05, f"{kind} {m}: {tot[m]:.2f} vs article {art[m]:.2f}"


def test_july_reconciles_to_existing_hierarchy(files):
    """July rows already in the repo came from the same source by register month;
    the only difference allowed is the late-reported AZ invoices moved into July."""
    h = _csv(TOT / "01_FULL_HIERARCHY_Apr_Jul_2026.csv", usecols=["Source_Month", "NSV_Value"])
    old_jul = h.loc[h["Source_Month"] == "2026-07", "NSV_Value"].sum() / 1e5
    a = files["art"]
    jul_by_register = a.loc[(a["Source_Month"] == "2026-07") & (a["Register_Month"] == "2026-07"), "NSV_Value"].sum() / 1e5
    assert abs(jul_by_register - old_jul) < 0.05
    moved = a.loc[(a["Source_Month"] == "2026-07") & (a["Register_Month"] == "2026-08"), "NSV_Value"].sum() / 1e5
    late = files["exc"].query("Exception == 'LATE_REPORTED_MOVED_TO_INVOICE_MONTH'")["NSV_Lakh"].sum()
    assert abs(moved - late) < 0.05 and moved > 0


def test_missing_register_is_not_written_as_zero(files):
    d, e = files["dist"], files["exc"]
    missing = e[e["Exception"].isin(["NO_REGISTER_THIS_MONTH", "INCLUDED_IN_ANOTHER_DISTRIBUTOR"])]
    assert len(missing), "coverage gaps must be listed"
    have = set(zip(d["Source_Month"], d["Distributor"]))
    for _, r in missing.iterrows():
        assert (r["Month"], r["Distributor"]) not in have, f"{r['Distributor']} {r['Month']} has a row but no register"


def test_gst_basis_flag_reaches_power_bi_provisional_rule(files):
    d, e = files["dist"], files["exc"]
    flagged = set(zip(e.loc[e["Exception"] == "GST_BASIS_NOT_CONFIRMED", "Month"],
                      e.loc[e["Exception"] == "GST_BASIS_NOT_CONFIRMED", "Distributor"]))
    for _, r in d.iterrows():
        provisional = ("GST" in r["Notes"]) or ("provisional" in r["Notes"])   # 44_Fact_SecondarySales.pq
        assert provisional == ((r["Source_Month"], r["Distributor"]) in flagged), r["Distributor"]


def test_date_repair_only_when_whole_register_is_swapped():
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_secondary_register import parse_date
    ts, flag = parse_date("2026-02-07", 2026, 7, allow_swap=True)
    assert (str(ts.date()), flag) == ("2026-07-02", "DATE_DAY_MONTH_SWAPPED_REPAIRED")
    ts, flag = parse_date("2026-07-08", 2026, 8, allow_swap=False)   # real 8 Jul invoice in the Aug register
    assert (str(ts.date()), flag) == ("2026-07-08", "OUT_OF_PERIOD")
    ts, flag = parse_date("27-07-26", 2026, 7)
    assert (str(ts.date()), flag) == ("2026-07-27", "")
    assert parse_date(None, 2026, 7) == (None, "DATE_MISSING")


def test_registry_warns_off_contaminated_august_hierarchy():
    reg = yaml.safe_load((ROOT / "config/data_source_registry.yml").read_text())
    e = reg["datasets"]["distributor_secondary_register_fy27"]
    assert e["date_max"] == "2026-08"
    assert "secondary_sales_tot_hierarchy_Apr_Aug_2026.csv" in e["notes"] and "DO NOT USE" in e["notes"]
