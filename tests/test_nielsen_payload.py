"""Aug-26 Nielsen payload: ties to the committed CSVs and builds a clean dashboard."""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

def _node_with_playwright():
    """True when node and its 'playwright' package are both available (the Python-only CI job has node but not the npm packages; the Browser Regression job covers the UI there)."""
    import shutil
    import subprocess
    if shutil.which("node") is None:
        return False
    return subprocess.run(["node", "-e", "require.resolve('playwright')"], cwd=ROOT, capture_output=True).returncode == 0

sys.path.insert(0, str(ROOT / "scripts"))
import build_nielsen_dashboard as bn  # noqa: E402
import extract_nielsen_report as ex  # noqa: E402
from validate_nielsen_output import validate_nielsen_html  # noqa: E402

AUG = ROOT / "data" / "nielsen_aug26.json"


@pytest.fixture(scope="module")
def aug():
    return json.loads(AUG.read_text(encoding="utf-8"))


def test_payload_is_governed_and_valid(aug):
    assert aug["data_status"] == "GOVERNED" and aug["market"] == "IN URB MT"
    assert bn.governance_errors(aug) == []
    assert bn.validate_payload(aug) == []


def test_mamaearth_facewash_ties_to_trend_file(aug):
    with (ROOT / "data/nielsen/Mamaearth_FW_Monthly_Trend.csv").open(encoding="utf-8") as h:
        rows = list(csv.DictReader(h))
    assert len(aug["months"]) == 37 and aug["months"][-1] == "Aug 26"
    assert aug["ms"][-1] == pytest.approx(12.8, abs=0.05)
    assert aug["nsv"][-1] == pytest.approx(10.52, abs=0.01)
    assert len(rows) >= 30


def test_pack_value_total_ties_to_category(aug):
    assert aug["fw_pack_total_cr"] == pytest.approx(aug["fw_cat"]["value"], rel=0.01)
    assert sum(b["val"] for b in aug["fw_packs"]) == pytest.approx(100, abs=0.5)
    assert aug["fw_premium_mix"]["mamaearth"] > aug["fw_premium_mix"]["category"]


def test_shampoo_same_month_and_real_reach(aug):
    sh = aug["shampoo"]
    me = next(b for b in sh["brands"] if b["n"] == "Mamaearth")
    assert sh["month"] == aug["months"][-1]
    assert me["wd"] > 0 and me["stores"] > 0
    assert sh["mamaearth_sales_cr"] / sh["category_cr"] * 100 == pytest.approx(me["ms"], abs=0.05)


def test_extractor_keeps_only_needed_rows():
    hdr = ["Markets", "Facts", "Products", "Aug 26"]
    assert ex.snapshot_rows([hdr, [None, None, None, None], ["IN URB MT", "Sales", "X", 1]])[1][0] == "IN URB MT"
    with pytest.raises(ValueError):
        ex.snapshot_rows([["a", "b", "c"], ["x", "y", "z"]])
    h = ["Facts", "BRAND", "Aug 26"]
    rows = [h, ["Sales Value in Cr.", "mamaearth", 1], ["Sales Value in Cr.", "DOVE", 2], ["Other", "MAMAEARTH", 3]]
    assert [r[2] for r in ex.pack_rows(rows, brand_sheet=True)[1:]] == [1]


@pytest.mark.skipif(not _node_with_playwright(), reason="node or its playwright package not installed")
def test_aug_dashboard_builds_and_passes_browser(tmp_path):
    out = tmp_path / "aug.html"
    bn.build(ROOT / "templates/dashboard_template.html", AUG, out)
    assert validate_nielsen_html(out.read_text(encoding="utf-8")) == []
    r = subprocess.run(["node", str(ROOT / "tests/nielsen_ms_browser.js"), str(out), "", "aug"],
                       capture_output=True, text=True, cwd=ROOT, timeout=240)
    assert r.returncode == 0, r.stdout + r.stderr


# ---------------------------------------------------------------- chains and packs

def test_pack_gap_flags_absent_packs_and_ties_to_category(aug):
    g = aug["fw_pack_gap"]
    assert g["basis"] == "value" and g["rows"]
    assert sum(r["cat_share"] for r in g["rows"]) == pytest.approx(100, abs=0.5)
    by = {r["size"]: r for r in g["rows"]}
    assert by["150"]["status"] == "Present" and by["125"]["status"] == "Not present"
    assert by["200"]["me_share_in_pack"] > 20 and 1.0 < by["150"]["price_ml"] < 1.5
    assert all(r["opp_cr"] == 0 for r in g["rows"] if r["status"] == "Present")
    assert sum(r["cat_amount"] for r in g["rows"]) == pytest.approx(aug["fw_pack_total_cr"], rel=0.01)
    s = aug["sh_pack_gap"]
    assert s["basis"] == "value"
    assert sum(r["cat_amount"] for r in s["rows"]) == pytest.approx(aug["shampoo"]["category_cr"], rel=0.01)   # shampoo packs carry value
    big = {r["size"]: r for r in s["rows"]}
    assert big["1000"]["status"] == "Not present" and big["400"]["status"] == "Present"
    assert big["400"]["me_mix"] > 50 and big["650"]["price_ml"] == pytest.approx(0.671, abs=0.01)


def test_chain_contribution_sums_and_excludes_nothing_from_primary(aug):
    rows = aug["chains"]["contribution"]
    assert rows[0]["Chain"] == "DMART"
    assert sum(r["share_ty_pct"] for r in rows) == pytest.approx(100, abs=0.1)
    assert sum(r["share_of_growth_pct"] for r in rows) == pytest.approx(100, abs=0.1)


def test_deck_block_is_labelled_as_transcribed(aug):
    d = aug["deck"]
    assert d["status"] == "TRANSCRIBED_FROM_DECK" and len(d["state_exposure"]) == 9 and len(d["plays"]) == 7


def test_chain_view_state_names_are_unified():
    import build_nielsen_chain_view as cv
    assert cv.norm_state("Delhi/ NCR") == cv.norm_state("DELHI NCR") == "Delhi NCR"
    assert cv.norm_state("UP") == cv.norm_state("Uttar Pradesh") and cv.norm_state("TELANGANA") == "Telangana"
    assert cv.norm_chain("Ratandeep") == "RATNADEEP"


# ----------------------------------------------------------- price and volume

def test_price_volume_effects_add_up_to_the_value_change(aug):
    pv = aug["price_volume"]
    for cat in ("facewash", "shampoo"):
        for r in pv["nielsen"][cat]:
            assert r["vol_effect_cr"] + r["price_effect_cr"] == pytest.approx(r["value_change_cr"], abs=0.01), (cat, r["name"])
    me = next(r for r in pv["nielsen"]["facewash"] if r["name"] == "Mamaearth")
    assert me["value_yoy"] == pytest.approx(40.7, abs=0.1)
    i = pv["internal"]
    assert i["months"] == ["Apr", "May", "Jun", "Jul", "Aug"]
    assert i["span"]["volume_cr"] + i["span"]["price_cr"] == pytest.approx(i["span"]["value_change_cr"], abs=0.02)
    assert sum(z["nsv_cr"] for z in i["zones_latest"]) == pytest.approx(i["monthly"][-1]["nsv_cr"], abs=0.02)
    assert all(not b["name"].replace(".", "").isdigit() for b in i["brands"])


def test_competitor_master_is_append_only_and_covers_the_seed():
    import csv as _csv
    master = list(_csv.DictReader((ROOT / "PowerBI/SeedData/Masters/NielsenCompetitorMaster.csv").open(encoding="utf-8")))
    have = {(r["Nielsen Category"], r["Brand"]) for r in master}
    assert ("Facewash", "Himalaya") in have and ("Facewash", "Mamaearth") in have       # original rows kept
    seed = list(_csv.DictReader((ROOT / "PowerBI/SeedData/Nielsen/Nielsen_Monthly/nielsen_urban_mt_aug26.csv").open(encoding="utf-8")))
    latest = {(r["Nielsen Category"], r["Brand"]) for r in seed if r["Month"] == "Aug'26" and r["Value Market Share %"]}
    assert latest <= have


def test_pack_brand_shows_who_sells_each_pack(aug):
    fw, sh = aug["fw_pack_brand"], aug["sh_pack_brand"]
    p = {x["size"]: x for x in fw["packs"]}
    assert p["200"]["brands_selling"] <= 8 and p["200"]["leader"] == "Himalaya"
    assert next(b for b in p["240"]["brands"] if b["n"] == "Mamaearth")["value"] == 0
    assert 85 <= fw["coverage_pct"] <= 100 and 85 <= sh["coverage_pct"] <= 100
    q = {x["size"]: x for x in sh["packs"]}
    assert q["400"]["leader"] == "Mamaearth" and q["1000"]["brands_selling"] >= 5
    for pack in fw["packs"]:
        assert sum(b["share_in_pack"] for b in pack["brands"]) <= 100.5
