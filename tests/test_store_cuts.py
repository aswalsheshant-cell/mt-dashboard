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
    for pq, csv in (("58_Fact_Store_Type.pq", "store_type_aug26.csv"), ("59_Fact_Pack_Size.pq", "pack_size_monthly_fy27.csv")):
        typed = re.findall(r'\{"([^"]+)", type', (root / "PowerQuery" / pq).read_text(encoding="utf-8"))
        cols = set(pd.read_csv(root / "SeedData" / "Store_Cuts" / csv, nrows=1).columns)
        assert typed and set(typed) <= cols, (pq, set(typed) - cols)


def test_dax_only_reads_columns_the_queries_build():
    import re
    dax = (Path(__file__).resolve().parents[1] / "PowerBI" / "DAX" / "20_Store_Type_Pack_Measures.dax").read_text(encoding="utf-8")
    st = {"Store Key", "Chain", "State", "Zone", "Store Type", "NSV This Year Rs", "NSV Last Year Same Months Rs", "Period"}
    pk = {"Month", "FY Year", "Category", "Pack", "NSV Rs", "Stores Selling", "MonthStart", "Pack Sort"}
    for tbl, cols in (("Fact Store Type", st), ("Fact Pack Size", pk)):
        used = set(re.findall(rf"'{tbl}'\[([^\]]+)\]", dax))
        assert used <= cols, (tbl, used - cols)


def test_html_dashboard_has_the_store_cuts_sub_view():
    root = Path(__file__).resolve().parents[1] / "dashboard"
    html = (root / "index.html").read_text(encoding="utf-8")
    assert '<script src="store_cuts.js"></script>' in html and "renderStoreCuts(content)" in html and "storecuts:'State, Pack & Store Type'" in html
    js = (root / "store_cuts.js").read_text(encoding="utf-8")
    assert js.startswith("window.STORE_CUTS=")
    assert json.loads(js[len("window.STORE_CUTS="):].rstrip().rstrip(";")) == D
