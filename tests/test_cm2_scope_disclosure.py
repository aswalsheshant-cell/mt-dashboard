"""CM2 says what it does not cover (PR #229, 2026-09-27).

The loaded expenses are MT Direct DN claims only, while the NSV base is all
channels (MT + EB2B + SIS). cm2.scope_fy reports MT-channel CM2 beside the
all-channel figure, and cm2.not_loaded names the cost buckets not deducted
yet, so a partial CM2 is never read as full Finance CM2."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as bd  # noqa: E402


def _cm2():
    txt = (ROOT / "dashboard" / "data.js").read_text()
    return json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])["cm2"]


def test_not_loaded_bucket_drops_once_its_head_is_loaded():
    all_four = [b["bucket"] for b in bd.cm2_not_loaded([])]
    assert len(all_four) == 4
    left = [b["bucket"] for b in bd.cm2_not_loaded(["Promotion", "Distributor Claim", "BA Cost"])]
    assert "MT Indirect / distributor claims" not in left
    assert "Field force (BA, merchandiser, supervisor)" not in left
    assert "COGS and logistics" in left and "Provisions" in left
    # DN heads loaded today match none of the missing buckets
    assert len(bd.cm2_not_loaded(["Promotion", "Visibility", "Off-Invoice", "Listing Fees", "Extra Margin"])) == 4


def test_committed_cm2_names_missing_buckets():
    c = _cm2()
    assert c["has_expense_data"] is True
    assert {b["bucket"] for b in c["not_loaded"]} == {b["bucket"] for b in bd.CM2_NOT_YET_LOADED}
    assert all(b["why"] for b in c["not_loaded"])


def test_scope_fy_reconciles_and_mt_cm2_recomputes():
    s = _cm2()["scope_fy"]["FY27"]
    ch = s["nsv_by_channel"]
    assert set(ch) >= {"MT"} and s["non_mt_nsv"] > 0
    assert abs(s["mt_nsv"] - ch["MT"]) < 0.01
    assert abs(s["non_mt_nsv"] - sum(v for k, v in ch.items() if k != "MT")) < 0.02
    assert s["expense"] == 1274.71 and s["expense_on_mt_chains"] == 1274.71
    assert s["cm2_pct_mt"] == round((s["mt_nsv"] - s["expense_on_mt_chains"]) / s["mt_nsv"] * 100, 1)
