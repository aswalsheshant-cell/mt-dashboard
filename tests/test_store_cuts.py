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
