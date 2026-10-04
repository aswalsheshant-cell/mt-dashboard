"""In-house distribution view (from our offtake, not TDP): ties to the offtake total and is labelled as not TDP."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_tdp_inhouse as bt  # noqa: E402

H = json.loads((ROOT / "dashboard" / "tdp_inhouse.js").read_text(encoding="utf-8")[len("window.TDP_INHOUSE="):].rstrip().rstrip(";"))


def test_label_says_not_tdp():
    assert "not TDP" in H["label"] and H["status"] == "IN_HOUSE"


def test_every_level_ties_to_the_offtake_total_by_month():
    for m in H["months"]:
        tot = next(r for r in H["total"] if r["month"] == m)["nsv"]
        for k in ("by_chain", "by_state", "by_pack"):
            assert abs(sum(r["nsv"] for r in H[k] if r["month"] == m) - tot) < 0.1, (k, m)
    assert abs(sum(r["nsv"] for r in H["total"]) - 18971.69) < 0.05      # FY27 Apr-Aug offtake, Brand Counter left out


def test_listings_and_per_store_are_consistent():
    for r in H["total"]:
        assert r["listings"] >= r["stores"] > 0 and abs(r["skus_per_store"] - r["listings"] / r["stores"]) < 0.01


def test_reach_is_blank_where_the_source_has_no_store_codes():
    for r in H["by_chain"]:
        if not r["has_store_codes"]:
            assert r["reach_pct"] is None and r["skus_per_store"] is None


def test_powerbi_seed_matches_the_dashboard_file():
    c = pd.read_csv(ROOT / "PowerBI" / "SeedData" / "Store_Cuts" / "inhouse_distribution_fy27.csv")
    assert set(c["Level"]) == {"Total", "Chain", "State", "Pack"} and (c["Basis"] == "From our offtake, not TDP").all()
    assert abs(c[c["Level"] == "Total"]["NSV Rs"].sum() / 100000 - 18971.69) < 0.5


def test_html_shows_the_inhouse_view():
    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert '<script src="tdp_inhouse.js"></script>' in html and "renderTdpInhouse(content,H)" in html
