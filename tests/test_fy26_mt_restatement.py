"""FY26 Primary restated on the MT basis (CB-01 Decision 3, approved by the repo owner 2026-10-08): scripts/restate_fy26_mt.py.

The published primary block carries MT only; the all-channel numbers stay as the reference; everything ties; the script is repeatable."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import restate_fy26_mt as r  # noqa: E402


@pytest.fixture(scope="module")
def primary():
    t = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
    d = json.loads(t[t.index("{"):t.rindex("}") + 1])
    return d["primary"], d["detail_meta"]


def test_headline_is_mt_and_ties_to_the_certified_channel_total(primary):
    p, dm = primary
    assert p["nsv_fy26"] == 30684.99
    assert p["nsv_fy26"] == dm["channel_totals"]["FY26"]["MT"]


def test_all_channel_reference_is_kept_and_by_channel_is_unchanged(primary):
    p, _ = primary
    assert p["fy26_all_channel"]["nsv_fy26"] == 32900.36
    assert abs(sum(c["fy26"] for c in p["by_channel"]) - 32900.36) < 0.05           # MT + EB2B + SIS
    assert abs(p["restatement"]["non_mt_nsv_fy26"] - (32900.36 - 30684.99)) < 0.02


def test_every_dimension_ties_to_the_mt_total(primary):
    p, _ = primary
    for key in ("by_zone", "by_brand", "by_chain"):
        assert abs(sum((x["fy26"] or 0) for x in p[key]) - p["nsv_fy26"]) < 0.1, key
    assert abs(sum(p["monthly_fy26"]) - p["nsv_fy26"]) < 0.1


def test_the_eight_non_mt_chains_left_the_mt_list(primary):
    p, _ = primary
    names = {c["name"] for c in p["by_chain"]}
    gone = {c["name"] for c in p["non_mt_fy26"]["by_chain"]}
    assert gone == {"Nykaa (FSN)", "Shoppers Stop", "Azorte", "Eremedium", "Lifestyle", "Ascent Wellness", "Broadway", "Today's Basket"}
    assert not (names & gone) and p["n_chains"] == len(p["by_chain"]) == 37


def test_restating_twice_changes_nothing():
    assert r.main(["--check"]) == 0


def test_the_script_refuses_when_the_article_files_do_not_tie(tmp_path):
    t = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
    i = t.index("{")
    d = json.loads(t[i:t.rindex("}") + 1])
    d["detail_meta"]["channel_totals"]["FY26"]["MT"] = 1.0           # break the certified total
    with pytest.raises(ValueError, match="does not tie"):
        r.restate(d, r.article_level())


def test_mrp_is_labelled_not_restated(primary):
    p, _ = primary
    assert "NOT restated" in p["mrp_fy26_basis"] and p["mrp_fy26"] == p["fy26_all_channel"]["mrp_fy26"]


def test_zones_follow_customer_code_mapping(primary):
    """Chhattisgarh and Vidarbha sit in Central, not West; the Gujarat-tagged UP customer sits in North."""
    z = {x["name"]: x["fy26"] for x in primary[0]["by_zone"]}
    assert z["Central"] == 1877.87 and z["West"] == 7876.25 and z["North"] == 6043.97
