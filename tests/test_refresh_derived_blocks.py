"""
Regression test for the 2026-09-15 fix: targets/insights/mapping_health/mom/
scorecard/pvm/profitability/npd/readiness used to be computed ONLY inline in
main()'s full-build path. Every partial-refresh CLI mode (--detail-only
chief among them) updated detail_meta/primary/offtake but left this whole
downstream layer frozen at whatever an earlier full build had produced.

Concretely this showed "Unmapped Chain" as a ~40%-contribution top-2 revenue
driver on the Executive Cockpit's "Chain -- target vs achievement" table and
the Performance & Comparison "Chain scorecard", long after the real
Unmapped-Chain bucket had been fixed down to <0.1% of Primary everywhere
else on the dashboard (same_period.by_chain, fyx_primary.by_chain, the
Channel & Chain Performance tab).

refresh_derived_blocks() is now the single place this layer is computed, and
is called from both the full build and --detail-only. These tests build on
the REAL committed dashboard/data.js (already-valid primary/offtake/pnl/
universe/promo -- insights_block alone reads 5+ distinct sub-shapes from
those, so a hand-built minimal fixture chases an ever-growing field list
without proving anything insights_block-specific isn't already testing) and
prove refresh_derived_blocks() actually overwrites a deliberately-corrupted
stale targets/scorecard block rather than leaving it untouched.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_dashboard_data as bdd  # noqa: E402

DATA_JS = REPO_ROOT / "dashboard" / "data.js"


def _load_real_data():
    txt = DATA_JS.read_text(encoding="utf-8")
    return json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])


def _corrupt_targets_and_scorecard(data):
    """Overwrite data['targets']/['scorecard'] with a fabricated stale block
    -- 'Unmapped Chain' wrongly dominant -- exactly the shape a leftover full
    build (from before the chain-mapping fixes) would leave behind."""
    stale_row = {"name": "Unmapped Chain", "target": 999999.0, "actual": 999999.0,
                 "achievement_pct": 100.0, "gap": 0.0, "contribution_pct": 99.0}
    basis = data["targets"]["basis"]
    data["targets"]["measures"][basis]["by_chain"] = [stale_row]
    if "scorecard" in data and "by_chain" in data["scorecard"]:
        data["scorecard"]["by_chain"]["rows"] = [dict(stale_row, curr=999999.0, prev=0.0)]


@pytest.mark.skipif(not DATA_JS.exists(), reason="dashboard/data.js not present in this environment")
def test_refresh_derived_blocks_overwrites_stale_unmapped_chain():
    data = _load_real_data()
    if not (data.get("targets") and data.get("detail_meta", {}).get("same_period")):
        pytest.skip("this data.js has no targets/same_period block to corrupt-and-refresh")

    real_same_period_chain = {r["name"]: r for r in data["detail_meta"]["same_period"]["by_chain"]}
    top_real_chain = max(real_same_period_chain.values(), key=lambda r: r["curr"] or 0)
    assert top_real_chain["name"] != "Unmapped Chain", (
        "test premise broken: the real same_period data itself has Unmapped Chain on top"
    )

    _corrupt_targets_and_scorecard(data)

    bdd.refresh_derived_blocks(data, REPO_ROOT)

    basis = data["targets"]["basis"]
    fresh_by_chain = {r["name"]: r for r in data["targets"]["measures"][basis]["by_chain"]}
    assert top_real_chain["name"] in fresh_by_chain, (
        f"refresh_derived_blocks() did not restore {top_real_chain['name']!r} into targets.by_chain"
    )
    unmapped = fresh_by_chain.get("Unmapped Chain")
    if unmapped is not None:
        assert unmapped["actual"] != pytest.approx(999999.0), (
            "stale fabricated 'Unmapped Chain' actual (999999.0) was not overwritten"
        )
        assert unmapped["actual"] < fresh_by_chain[top_real_chain["name"]]["actual"]

    if "scorecard" in data:
        sc_rows = {r["name"]: r for r in data["scorecard"]["by_chain"]["rows"]}
        sc_unmapped = sc_rows.get("Unmapped Chain")
        if sc_unmapped is not None:
            assert sc_unmapped.get("actual") != pytest.approx(999999.0), (
                "stale fabricated scorecard row was not overwritten"
            )


@pytest.mark.skipif(not DATA_JS.exists(), reason="dashboard/data.js not present in this environment")
def test_detail_only_cli_refreshes_targets_not_just_detail_records(tmp_path):
    """End-to-end: run the actual --detail-only CLI path against the real
    committed source (a genuine month with real EANs/chains) on top of a
    data.js whose targets/scorecard were corrupted, and confirm they come
    back correct rather than being left untouched."""
    data = _load_real_data()
    _corrupt_targets_and_scorecard(data)
    out = tmp_path / "data.js"
    out.write_text("window.DASH = " + json.dumps(data) + ";\n")

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "build_dashboard_data.py"),
         "--detail-only", "--detail-max-rows", "200000",
         "--src", str(REPO_ROOT / "PowerBI" / "RawDataFolders"), "--out", str(out)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr

    txt = out.read_text()
    obj = json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])
    basis = obj["targets"]["basis"]
    by_chain = {r["name"]: r for r in obj["targets"]["measures"][basis]["by_chain"]}
    unmapped = by_chain.get("Unmapped Chain")
    if unmapped is not None:
        assert unmapped["actual"] != pytest.approx(999999.0), (
            "--detail-only did not refresh the corrupted stale targets block"
        )
