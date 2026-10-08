"""Store cuts (state, pack, LFL/NFL) must tie to the FY27 Apr-Aug offtake total and split every store once."""
import json
from pathlib import Path

D = json.loads((Path(__file__).resolve().parents[1] / "data" / "store_cuts_aug26.json").read_text())


def test_total_ties_to_fy27_offtake():
    assert abs(D["total_ty"] - 18971.69) < 0.05


def test_chain_state_pack_all_tie_to_total():
    for k in ("by_chain", "by_state", "by_zone"):
        assert abs(sum(r["ty_total"] for r in D[k]) - D["total_ty"]) < 0.05, k
    assert abs(sum(p["nsv"] for p in D["by_pack"]) - D["total_ty"]) < 0.05


def test_reliance_retail_kept_out_of_lfl():
    r = next(x for x in D["by_chain"] if x["Chain"] == "Reliance Retail")
    assert r["lfl_stores"] == 0 and r["noly_stores"] > 0


def test_powerbi_queries_type_columns_that_exist_in_the_seed_files():
    import re
    import pandas as pd
    root = Path(__file__).resolve().parents[1] / "PowerBI"
    for pq, csv in (("58_Fact_Store_Type.pq", "store_type_aug26.csv"), ("59_Fact_Pack_Size.pq", "pack_size_monthly_fy27.csv"),
                    ("60_Fact_Sales_Cuts.pq", "sales_cuts_fy27.csv"), ("61_Fact_Inhouse_Distribution.pq", "inhouse_distribution_fy27.csv")):
        typed = re.findall(r'\{"([^"]+)", type', (root / "PowerQuery" / pq).read_text(encoding="utf-8"))
        cols = set(pd.read_csv(root / "SeedData" / "Store_Cuts" / csv, nrows=1).columns)
        assert typed and set(typed) <= cols, (pq, set(typed) - cols)


def test_dax_only_reads_columns_the_queries_build():
    import re
    dax = (Path(__file__).resolve().parents[1] / "PowerBI" / "DAX" / "20_Store_Type_Pack_Measures.dax").read_text(encoding="utf-8")
    st = {"Store Key", "Chain", "State", "Zone", "Store Type", "NFL Kind", "LY Months Sold", "Growth Basis", "NSV This Year Rs", "NSV Last Year Same Months Rs", "Period"}
    pk = {"Month", "FY Year", "Category", "Pack", "NSV Rs", "Stores Selling", "MonthStart", "Pack Sort"}
    sc = {"Month", "FY Year", "Zone", "Brand", "Category", "Sub Category", "Store Type", "NSV Rs", "Stores Selling", "MonthStart"}
    ih = {"Month", "FY Year", "Level", "Name", "Stores Selling", "SKUs Selling", "SKU Listings", "Stores In Master", "NSV Rs", "Basis", "MonthStart"}
    for tbl, cols in (("Fact Store Type", st), ("Fact Pack Size", pk), ("Fact Sales Cuts", sc), ("Fact Inhouse Distribution", ih)):
        used = set(re.findall(rf"'{tbl}'\[([^\]]+)\]", dax))
        assert used <= cols, (tbl, used - cols)


def test_html_dashboard_has_the_store_cuts_sub_view():
    root = Path(__file__).resolve().parents[1] / "dashboard"
    html = (root / "index.html").read_text(encoding="utf-8")
    assert '<script src="store_cuts.js"></script>' in html and "renderStoreCuts(content)" in html and "storecuts:'State, Pack & Store Type'" in html
    js = (root / "store_cuts.js").read_text(encoding="utf-8")
    assert js.startswith("window.STORE_CUTS=")
    assert json.loads(js[len("window.STORE_CUTS="):].rstrip().rstrip(";")) == D


def test_nfl_splits_into_new_and_restarted():
    s = D["stores"]
    assert s["New"] + s["Restarted"] == s["NFL"]
    for k in ("by_chain", "by_state"):
        assert abs(sum(r["new_ty"] + r["restart_ty"] for r in D[k]) - sum(r["nfl_ty"] for r in D[k])) < 0.05


def test_store_movers_only_use_stores_with_enough_history():
    m = D["movers"]
    assert m["min_ly_months"] == 3 and m["eligible_stores"] > 0
    for r in m["top_gainers"] + m["top_decliners"]:
        assert r["ly_months"] >= 3 and r["ly"] > 0
    assert m["eligible_stores"] + m["thin_history_stores"] == D["stores"]["LFL"]


def test_zone_brand_subcategory_sales_tie_to_the_total():
    for k in ("zone_sales", "brand_sales", "subcat_sales"):
        assert abs(sum(r["ty"] for r in D[k]) - D["total_ty"]) < 0.05, k
        for r in D[k]:     # the four store types add back to the row total
            assert abs(r["lfl_ty"] + r["new_ty"] + r["restart_ty"] + r["noly_ty"] - r["ty"]) < 0.05


def test_sales_cuts_seed_ties_to_the_total():
    import pandas as pd
    c = pd.read_csv(Path(__file__).resolve().parents[1] / "PowerBI" / "SeedData" / "Store_Cuts" / "sales_cuts_fy27.csv")
    assert abs(c["NSV Rs"].sum() / 100000 - D["total_ty"]) < 0.5
