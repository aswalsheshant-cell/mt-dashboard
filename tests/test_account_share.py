"""Account (retailer) category share: Lulu, More Retail, Wellness Forever, Reliance, and the Facewash plan built on them."""
import csv
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_account_share as bas  # noqa: E402

AS = ROOT / "data" / "account_share"


@pytest.fixture(scope="module")
def view():
    return json.loads((AS / "Account_View.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def monthly():
    return pd.read_csv(AS / "Account_Category_Monthly.csv")


def test_lulu_honasa_totals_tie_to_the_source_files(monthly):
    lulu = monthly[(monthly.Chain == "Lulu") & (monthly.Level == "Category")].groupby("Month")["Honasa Sales Rs L"].sum()
    assert lulu["Aug 26"] == pytest.approx(115.3084, abs=0.001) and lulu["Jan 26"] == pytest.approx(105.9176, abs=0.001)
    assert lulu["Jun 26"] == pytest.approx(111.2806, abs=0.001) and lulu["Jul 26"] == pytest.approx(145.8326, abs=0.001)


def test_shares_are_valid_and_one_row_per_chain_month_category(monthly):
    assert (monthly["Share %"].dropna() <= 100.0001).all()
    assert not monthly.duplicated(["Chain", "Month", "Level", "Category"]).any()
    assert set(monthly.Chain) == {"Lulu", "More Retail", "Wellness Forever", "Reliance Retail", "Reliance Brand Counter"}


def test_more_retail_scope_break_is_flagged_and_mom_uses_one_scope(monthly, view):
    more = monthly[monthly.Chain == "More Retail"]
    assert set(more.Scope) == {"Sub-categories where Honasa sells (to May 26)", "Full account category report (from Jun 26)"}
    c = view["chains"]["More Retail"]
    assert c["latest"] == "Aug 26" and c["previous"] == "Jul 26" and c["l3m"] == ["Jun 26", "Jul 26", "Aug 26"]
    assert any(not s["scope_ok"] for s in c["series"]) and all(s["scope_ok"] for s in c["series"] if s["month"] in c["l3m"])


def test_common_categories_are_sensible():
    cc = bas.common_category
    assert cc("Shower Gel&Body Wash") == "Body Wash & Soap" and cc("Baby Hair Oil") == "Baby Care" and cc("Baby Sunscreen") == "Baby Care"
    assert cc("Face Wash") == cc("FACE CLEANSERS") == cc("Skin Care / Facial Cleanser") == "Face Wash & Cleanser"
    assert cc("Hair Shampoo") == "Shampoo" and cc("Sun Care") == "Sun Care" and cc("Insect Repellents") == "Other"
    assert cc("Perfume - Women") == "Fragrance" and cc("Soaps Beauty") == "Beauty Soap" and cc("Hair Serum") == "Hair Treatment & Styling"
    assert cc("Moisturizing Lotion") == "Body Lotion & Care" and cc("Moisturizing Cream") == "Face Moisturiser & Cream"


def test_flags_follow_the_stated_rules(view):
    r = view["rules"]
    for f in view["flags"]:
        if f["flag"] == "White space":
            assert f["pct_of_chain"] >= r["white_space_min_pct_of_chain"] and f["share"] < r["white_space_share_under"]
        if f["flag"] == "Low assortment":
            assert 0 < f["articles"] <= r["low_assortment_articles"]
        if f["flag"] == "Strong":
            assert f["share"] >= f["chain_share"] * r["strong_x"]
    assert {"White space", "Strong"} <= {f["flag"] for f in view["flags"]}


def test_top5_has_chain_zone_and_state_cuts_with_account_and_ours(view):
    levels = {(t["chain"], t["level"]) for t in view["top5"]}
    assert {("Lulu", "Chain"), ("Lulu", "Zone"), ("Lulu", "State"), ("More Retail", "State"), ("Wellness Forever", "Chain")} <= levels
    assert ("Wellness Forever", "State") not in levels                         # category level only: no zone or state in the file
    for t in view["top5"]:
        assert t["account"] >= t["honasa"] - 1e-6
    assert max(sum(1 for t in view["top5"] if t["chain"] == "Lulu" and t["level"] == "Chain" for _ in [0]), 5) == 5


def test_four_plus_chains_side_by_side(view):
    names = [t["chain"] for t in view["together"]]
    assert names[:5] == ["Lulu", "More Retail", "Wellness Forever", "Reliance Retail", "Reliance Brand Counter"] and "Dmart" in names and "Reliance Retail (deck)" in names


def test_facewash_plan_levers_have_evidence_and_sizes(view):
    plan = view["facewash_plan"]
    names = [l["lever"] for l in plan["levers"]]
    assert "Distribution" in names and "Pack gaps" in names
    for l in plan["levers"]:
        assert l["evidence"] and l["action"] and l["method"] and l["owner"] and l["timeline"] and l["kpi"] and l["size_cr_month"] is not None
    assert plan["total_cr_month"] == pytest.approx(sum(l["size_cr_month"] for l in plan["levers"]), abs=0.02)
    assert "upper bound" in plan["note"].lower()


def test_lulu_store_codes_match_the_store_master_and_mismatches_are_listed(view):
    sm = {str(s["Store Code"]): s for s in view["store_map_check"]}
    assert len(sm) == 20 and sm["9260"]["City (store master)"] == "Thrissur"          # corrected from Triprayar
    assert sm["9285"]["Check"].startswith("Differs")                                  # Kottiyam vs Thiruvananthapuram: left for the account team
    avail = {a["chain"]: a for a in view["availability"]}
    assert avail["Wellness Forever"]["zone_state"] == "No" and avail["All MT"]["store_city"].startswith("No city")


def test_no_store_or_employee_names_in_the_aggregates():
    for f in ("Account_Category_Monthly.csv", "Account_Category_Geo.csv", "Account_Assortment.csv"):
        header = next(csv.reader((AS / f).open(encoding="utf-8")))
        assert not [h for h in header if "Store Name" in h or "Employee" in h or h in ("Plant Code",)], (f, header)


def test_powerbi_account_seeds_match_the_data_and_queries_exist():
    import csv
    pbi = ROOT / "PowerBI"
    for name in ("Account_Category_Monthly", "Account_Category_Geo", "Account_Assortment"):
        a = (pbi / "SeedData" / "Account" / f"{name}.csv").read_bytes()
        b = (ROOT / "data" / "account_share" / f"{name}.csv").read_bytes()
        assert a == b, name
    for q in ("53_Fact_Account_Category", "54_Fact_Account_Category_Geo", "55_Fact_Account_Assortment"):
        assert (pbi / "PowerQuery" / f"{q}.pq").exists()
    dax = (pbi / "DAX" / "17_Account_Share_Measures.dax").read_text(encoding="utf-8")
    assert "Account Share %" in dax and "White Space Flag" in dax


def test_reliance_ties_to_the_workbook_and_the_counters_stay_apart(monthly):
    cat = monthly[monthly.Level == "Category"]
    ret = cat[cat.Chain == "Reliance Retail"].groupby("Month")["Honasa Sales Rs L"].sum()
    bc = cat[cat.Chain == "Reliance Brand Counter"].groupby("Month")["Honasa Sales Rs L"].sum()
    assert ret["Aug 26"] == pytest.approx(2602.857, abs=0.01)         # workbook sheet Aug26 Check: Offtake Data
    assert bc["Aug 26"] == pytest.approx(1600.298, abs=0.01)          # workbook sheet Aug26 Check: Brand Counter Stores
    fw = cat[(cat.Chain == "Reliance Retail") & (cat.Category == "Face Wash") & (cat.Month == "Jan 26")].iloc[0]
    assert fw["Account Sales Rs L"] == pytest.approx(3018.972, abs=0.01) and fw["Honasa Sales Rs L"] == pytest.approx(618.992, abs=0.01)
    assert not any(c.strip() == "Reliance" for c in monthly.Chain.unique())            # never one combined Reliance line


def test_reliance_in_the_view_with_zone_and_state_cuts(view):
    for chain in ("Reliance Retail", "Reliance Brand Counter"):
        c = view["chains"][chain]
        assert c["latest"] == "Aug 26" and c["share_latest"] and c["fw_share_latest"] and c["account_mom_pct"] is not None
    levels = {(t["chain"], t["level"]) for t in view["top5"]}
    assert {("Reliance Retail", "Zone"), ("Reliance Retail", "State"), ("Reliance Brand Counter", "State")} <= levels
    names = [a["chain"] for a in view["availability"]]
    assert "Reliance Retail" in names and "Reliance Brand Counter" in names


def test_categories_that_do_not_matter_to_us_are_never_flagged(view):
    skip = {x["common"] for x in view["not_highlighted"]}
    assert {"Other", "Fragrance"} & skip or "Other" in skip
    for f in view["flags"]:
        assert f["common"] in view["relevant"], f
    for p in view["proven_elsewhere"]:
        assert p["common"] in view["relevant"], p
    flagged = " ".join(f["category"].lower() for f in view["flags"])
    for bad in ("soaps beauty", "hair serum", "perfume", "insect", "tooth"):
        assert bad not in flagged
    for t in view["top5"]:
        assert "relevant" in t


def test_the_staffed_counters_are_not_a_benchmark_or_a_lever(view):
    assert not [l for l in view["facewash_plan"]["levers"] if "Brand Counter" in l["lever"]]


def test_powerbi_queries_name_only_real_csv_columns():
    """A typed column that is not in the CSV breaks the refresh in Power BI Desktop."""
    import re
    pbi = ROOT / "PowerBI"
    for q, csvname in (("53_Fact_Account_Category", "Account_Category_Monthly"), ("54_Fact_Account_Category_Geo", "Account_Category_Geo"),
                       ("55_Fact_Account_Assortment", "Account_Assortment")):
        header = next(csv.reader((pbi / "SeedData" / "Account" / f"{csvname}.csv").open(encoding="utf-8")))
        typed = re.findall(r'\{"([^"]+)", type', (pbi / "PowerQuery" / f"{q}.pq").read_text(encoding="utf-8"))
        assert typed and set(typed) <= set(header), (q, sorted(set(typed) - set(header)))
        assert "Relevant For Us" in typed
