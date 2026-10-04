"""Aug-26 Nielsen payload: ties to the committed CSVs and builds a clean dashboard."""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
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


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_aug_dashboard_builds_and_passes_browser(tmp_path):
    out = tmp_path / "aug.html"
    bn.build(ROOT / "templates/dashboard_template.html", AUG, out)
    assert validate_nielsen_html(out.read_text(encoding="utf-8")) == []
    r = subprocess.run(["node", str(ROOT / "tests/nielsen_ms_browser.js"), str(out), "", "aug"],
                       capture_output=True, text=True, cwd=ROOT, timeout=240)
    assert r.returncode == 0, r.stdout + r.stderr
