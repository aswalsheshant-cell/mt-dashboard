"""Nielsen market-share dashboard: Facewash and Shampoo in one tab, from real files.

Covers the data wiring (scripts/build_nielsen_dashboard.py) and the template
(templates/dashboard_template.html). Browser behaviour is in
tests/nielsen_ms_browser.js, run from test_browser_switch_and_no_nan below.
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_nielsen_dashboard as bn  # noqa: E402
from validate_nielsen_output import validate_nielsen_html  # noqa: E402

JUL = ROOT / "data" / "nielsen_jul26.json"
TEMPLATE = ROOT / "templates" / "dashboard_template.html"


def _governed(base):
    d = copy.deepcopy(base)
    d.pop("_comment", None)
    d.update({"data_status": "GOVERNED", "source_reference": "test fixture",
              "validation_reference": "test fixture"})
    return d


@pytest.fixture(scope="module")
def jul():
    return json.loads(JUL.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def extras():
    return bn.load_extras(ROOT)


@pytest.fixture(scope="module")
def built(tmp_path_factory, jul):
    tmp = tmp_path_factory.mktemp("nielsen")
    src = tmp / "nielsen_test.json"
    src.write_text(json.dumps(_governed(jul)), encoding="utf-8")
    out = tmp / "out.html"
    bn.build(TEMPLATE, src, out)
    return out


# ------------------------------------------------------------ real-data extras

def test_facewash_brand_file_keeps_missing_shares_missing(extras):
    brands = {b["n"]: b for b in extras["fw_all"]}
    assert len(brands) == 25
    assert brands["Mamaearth"]["ms_py"] == 8.8 and brands["Mamaearth"]["ms"] == 11.2
    assert brands["Pond's"]["ms"] == 13.0                      # apostrophe not mangled to Pond'S
    assert brands["Cerave"]["ms_py"] is None                    # blank in the file: unknown, not 0
    assert brands["Nivea Men"]["ms"] is None


def test_share_changes_of_brands_with_both_years_roughly_net_to_zero(extras):
    both = [b for b in extras["fw_all"] if b["ms_py"] is not None and b["ms"] is not None]
    net = sum(b["ms"] - b["ms_py"] for b in both)
    assert abs(net) < 3.0, net                                  # shares are zero-sum except unlisted brands


def test_category_nsv_is_keyed_by_month_label(extras):
    cat = extras["fw_cat_nsv"]
    assert cat["Jul 26"] == 82.3 and cat["Jul 25"] == 70.8


def test_shampoo_pack_buckets_come_from_the_real_file(extras):
    pack = extras["sh_pack_file"]
    by = {b["sz"]: b for b in pack["buckets"]}
    assert by[">200ml"]["val"] == pytest.approx(73.1, abs=0.1)
    assert by["180-200ml"]["val"] == pytest.approx(19.2, abs=0.1)
    assert sum(b["val"] for b in pack["buckets"]) == pytest.approx(100.0, abs=0.2)
    assert pack["period"] == "Jul 2026"


def test_shampoo_inputs_are_internally_consistent(jul):
    sh = jul["shampoo"]
    me = next(b for b in sh["brands"] if b["n"] == "Mamaearth")
    # Sales / category must reproduce the share the slide reports.
    assert sh["mamaearth_sales_cr"] / sh["category_cr"] * 100 == pytest.approx(me["ms"], abs=0.1)
    assert sh["period"] == "May 2026" and "Urban" in sh["basis"]


def test_validate_warns_when_shampoo_sales_and_share_disagree(jul):
    bad = copy.deepcopy(jul)
    bad["shampoo"]["mamaearth_sales_cr"] = 20.0          # 20 / 276 = 7.2%, but the table says 2.5%
    assert any("Shampoo share" in w for w in bn.validate_payload(bad))
    assert not any("Shampoo" in w for w in bn.validate_payload(jul))


# ------------------------------------------------------------------- payload

def test_payload_keeps_old_keys_and_adds_new_ones(jul, extras):
    p = json.loads(bn.to_js_payload(_governed(jul), extras))
    for key in ("MONTHS", "MS_", "NSV_", "WD_", "STORES_", "BRANDS", "FW_PACKS", "SH_PACKS", "GATES"):
        assert key in p
    assert len(p["FW_CAT_NSV"]) == len(p["MONTHS"])
    assert p["FW_CAT_NSV"][p["MONTHS"].index("Jul 26")] == 82.3
    assert p["SHAMPOO"]["brands"][-1]["n"] == "Mamaearth"
    assert p["GOV"]["data_status"] == "GOVERNED"


def test_payload_without_extras_is_unchanged_in_shape(jul):
    p = json.loads(bn.to_js_payload(_governed(jul)))
    assert "MONTHS" in p and "FW_ALL" not in p


# ------------------------------------------------------------------ the build

def test_build_passes_the_structural_check(built):
    html = built.read_text(encoding="utf-8")
    assert validate_nielsen_html(html) == []


def test_template_has_no_hard_coded_headline_figures():
    # These were typed into the old template and did not match the data
    # (WD +6.4pp not 10.1; stores +25.6% not 32.3; rank stayed #4; 7,279 x Rs850 = Rs0.62 Cr).
    html = TEMPLATE.read_text(encoding="utf-8")
    for stale in ("10.1pp YoY", "32.3% YoY", "11.6% YoY", "+1 vs. Jul 25", "avg ₹850/store",
                  "₹6.2 Cr", "₹3.8 Cr", "52% PDO gap", "Rank</div>\n      <div class=\"kpi-val\">#4"):
        assert stale not in html, stale


def test_template_offers_both_facewash_and_shampoo_views():
    html = TEMPLATE.read_text(encoding="utf-8")
    for needle in ('data-view="both"', 'data-view="fw"', 'data-view="sh"', "id=\"blk-fw\"", "id=\"blk-sh\""):
        assert needle in html, needle


def test_the_old_unsupported_pack_split_is_not_shown_for_shampoo():
    # data/nielsen_jul26.json sh_packs says 180-200ml = 41%; the real pack file says 19%.
    html = TEMPLATE.read_text(encoding="utf-8")
    assert "SH_PACKS" not in html


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_browser_switch_and_no_nan(built):
    result = subprocess.run(["node", str(ROOT / "tests" / "nielsen_ms_browser.js"), str(built)],
                            capture_output=True, text=True, cwd=ROOT, timeout=240)
    assert result.returncode == 0, result.stdout + result.stderr
