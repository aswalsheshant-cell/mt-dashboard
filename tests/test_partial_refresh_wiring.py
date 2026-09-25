"""
Regression test for a gap FM-17 itself flagged as unresolved (see
docs/FAILURE_MODE_REGISTER.md FM-17's closing note): --detail-only was fixed
to call refresh_derived_blocks() after updating detail_meta/primary/etc, but
--primary-only, --offtake-rebuild and --offtake-patch update the SAME
upstream inputs (primary, offtake) that refresh_derived_blocks()'s output
layer (targets/insights/mapping_health/mom/scorecard/pvm/profitability/npd/
readiness) derives from, and were never wired up -- so a real business
refresh through any of those three modes would leave that whole downstream
layer frozen at whatever the last full build (or --detail-only run)
produced, the exact "Unmapped Chain shown as a top-2 revenue driver" failure
mode FM-17 fixed for --detail-only specifically.

Real source workbooks for --primary-only/--offtake-rebuild/--offtake-patch
are not available in this environment (gitignored per this repo's
convention), so this can't be proven with a full CLI run the way
tests/test_refresh_derived_blocks.py does for --detail-only. Instead this
proves the WIRING itself is present: refresh_derived_blocks(obj, src) must
appear within each fixed branch's own source, between its own `if a.<mode>:`
line and its own `return` -- so a future edit that reorders or removes the
call is caught structurally, without needing real data to execute it.

--forecast-only and --distgap are deliberately NOT required to call it:
neither one touches primary/offtake/detail_meta/alloc (the only inputs
refresh_derived_blocks() actually reads), so calling it there would be a
no-op recompute with nothing to refresh, not a fix to a real gap -- and this
test would fail loudly if a future edit added a needless call there and
this test's own understanding of the dependency went stale.
"""
import inspect
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_dashboard_data as bdd  # noqa: E402


def _branch_source(mode_flag: str) -> str:
    """Extract the source of one `if a.<mode_flag>:` branch inside main(),
    from that line up to (and including) its own top-level `return`."""
    main_src = inspect.getsource(bdd.main)
    pattern = re.compile(rf"^    if a\.{mode_flag}:\n(.*?)^        return\n", re.MULTILINE | re.DOTALL)
    m = pattern.search(main_src)
    assert m, f"could not locate 'if a.{mode_flag}:' branch in main() -- has main() been restructured?"
    return m.group(0)


@pytest.mark.parametrize("mode_flag", ["primary_only", "offtake_rebuild", "offtake_patch"])
def test_branch_calls_refresh_derived_blocks(mode_flag):
    branch = _branch_source(mode_flag)
    assert "refresh_derived_blocks(obj, src)" in branch, (
        f"--{mode_flag.replace('_', '-')} updates primary/offtake but does not call "
        f"refresh_derived_blocks(obj, src) -- targets/mapping_health/mom/scorecard/pvm/"
        f"profitability/npd/readiness will go stale after this mode runs, the exact "
        f"pattern FM-17 fixed for --detail-only (see FM-17's own closing note)."
    )


def test_refresh_derived_blocks_called_before_write_not_after(mode_flag_list=("primary_only", "offtake_rebuild", "offtake_patch")):
    """The call must happen BEFORE _safe_write_data_js writes obj to disk --
    calling it after would compute fresh blocks into a dict that was already
    serialized and written, silently discarding the refresh."""
    for mode_flag in mode_flag_list:
        branch = _branch_source(mode_flag)
        refresh_idx = branch.index("refresh_derived_blocks(obj, src)")
        write_idx = branch.index("_safe_write_data_js(")
        assert refresh_idx < write_idx, (
            f"--{mode_flag.replace('_', '-')}: refresh_derived_blocks() is called AFTER "
            f"_safe_write_data_js(), so the refresh never reaches the written file"
        )


def test_primary_only_calls_apply_primary_channel_correction():
    """Found 2026-09-24 by actually running --primary-only against the real
    committed seed (PowerBI/SeedData/Primary/Primary_FY202426_10.csv) and
    diffing its output against the certified data.js it was refreshing:
    by_channel silently regressed from the corrected split (MT 30684.99 /
    EB2B 1965.20 / SIS 250.17) back to the pre-aggregated workbook's raw,
    lossy "every row tagged MT" export (MT 32900.36 / EB2B 0 / SIS 0) --
    apply_primary_channel_correction() exists exactly to fix this (see its
    own docstring and tests/test_primary_channel_correction.py), and both
    --detail-only and the full-rebuild path already call it, but
    --primary-only never did. Same "gap FM-17 fixed for --detail-only, never
    extended to the sibling modes" shape as the rest of this file -- added
    here as its own dedicated case since it does not fit the generic
    refresh_derived_blocks() parametrization above."""
    branch = _branch_source("primary_only")
    assert "apply_primary_channel_correction(" in branch, (
        "--primary-only computes primary_block() output but does not call "
        "apply_primary_channel_correction() -- by_channel silently reverts to "
        "the pre-aggregated workbook's uncorrected, 100%-MT split on every "
        "--primary-only-only refresh (the documented refresh_dashboard.sh Pass 1)"
    )
    correction_idx = branch.index("apply_primary_channel_correction(")
    write_idx = branch.index("_safe_write_data_js(")
    assert correction_idx < write_idx, (
        "--primary-only: apply_primary_channel_correction() is called AFTER "
        "_safe_write_data_js(), so the correction never reaches the written file"
    )


@pytest.mark.parametrize("mode_flag", ["forecast_only", "distgap"])
def test_branches_that_do_not_touch_primary_or_offtake_are_not_required_to_refresh(mode_flag):
    """Documents the deliberate exclusion: these two modes don't update
    primary/offtake/detail_meta/alloc, so refresh_derived_blocks() would be a
    needless no-op recompute there, not a fix. This isn't asserting they must
    NOT call it (that would be an arbitrary restriction) -- it's here so the
    reasoning is checked against the actual branch source, not just asserted
    in a comment that can drift from the code."""
    branch = _branch_source(mode_flag)
    # Distinguish a WRITE (obj["offtake"] = ...) from a mere READ
    # (forecast_block_ty(obj["offtake"], ...)) -- only a write actually
    # changes what refresh_derived_blocks() would recompute from.
    writes_refresh_inputs = any(
        re.search(rf'obj\["{key}"\]\s*=[^=]', branch) for key in ("primary", "offtake", "detail_meta", "alloc")
    )
    assert not writes_refresh_inputs, (
        f"--{mode_flag.replace('_', '-')} now writes to primary/offtake/detail_meta/alloc -- "
        f"re-evaluate whether it needs refresh_derived_blocks(obj, src) too"
    )
