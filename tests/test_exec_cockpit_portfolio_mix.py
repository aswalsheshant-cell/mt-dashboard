"""Executive Cockpit portfolio-mix and Way Forward figures come from data.

Defect (2026-09-29 dashboard QC): the "Portfolio mix" insight read the current
FY from the pre-aggregated primary.by_brand, which only carries FY26, and so
told leadership "Mamaearth is 0% of FY26-FY27 MT primary". The Way Forward
list next to it had "~83%" (an FY26-only share) and "12,000+ active stores"
(no source in the repo; the MT universe is 426) typed into the HTML.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def _builder():
    spec = importlib.util.spec_from_file_location("bdd_pm", ROOT / "scripts/build_dashboard_data.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["bdd_pm"] = m
    spec.loader.exec_module(m)
    return m


def _dash():
    t = (ROOT / "dashboard/data.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):].rstrip().rstrip(";"))


def test_live_portfolio_mix_matches_same_period_brand_share():
    d = _dash()
    sp = d["detail_meta"]["same_period"]
    lead = max(sp["by_brand"], key=lambda r: r["curr"])
    card = next(i for i in d["insights"] if i["title"] == "Portfolio mix")
    share = round(lead["curr"] / sp["curr"] * 100)
    assert f"{lead['name']} is {share}% of {sp['curr_fy']} MT primary" in card["text"]
    assert not re.search(r"\b0% of", card["text"])


def test_insights_block_rebases_brand_on_same_period():
    b = _builder()
    d = _dash()
    ins = b.insights_block(d["primary"], d["offtake"], d.get("pnl"), d.get("universe"),
                           d.get("promo"), d["detail_meta"]["same_period"])
    card = next(i for i in ins if i["title"] == "Portfolio mix")
    assert not re.search(r"\b0% of", card["text"])


def test_no_brand_value_means_no_card_not_zero():
    b = _builder()
    d = _dash()
    sp = dict(d["detail_meta"]["same_period"])
    sp.pop("by_brand")                       # current FY has no brand split
    ins = b.insights_block(d["primary"], d["offtake"], d.get("pnl"), d.get("universe"),
                           d.get("promo"), sp)
    assert not any(i["title"] == "Portfolio mix" for i in ins)


def test_way_forward_has_no_typed_in_figures():
    html = (ROOT / "dashboard/index.html").read_text(encoding="utf-8")
    assert "~83% of MT primary" not in html
    assert "12,000+ active stores" not in html
    assert "D.universe.active_stores" in html
    assert "same_period.by_brand" in html
