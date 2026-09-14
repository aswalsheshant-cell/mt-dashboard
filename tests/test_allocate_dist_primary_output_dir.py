"""Regression test for the allocate_dist_primary() shadow-run side-effect fix.

Before this fix, allocate_dist_primary() unconditionally wrote 3 reviewable
governance/proposal CSVs (DistCont_Patch_Proposed.csv,
DistAllocationGovernance_FlaggedRows.csv, EanAffinity_ResidualProposal.csv)
to hardcoded repo paths under PowerBI/SeedData/Mapping/, with no way to
redirect them -- so a read-only shadow/test run of the certified allocation
engine silently overwrote tracked repository files. The fix adds an optional
`output_dir` parameter (default None preserves the original repo-writing
behaviour); this test proves a shadow run passing output_dir never touches
the tracked copies. Synthetic data only.
"""
import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
bd = importlib.import_module("build_dashboard_data")

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACKED_FILES = [
    REPO_ROOT / "PowerBI" / "SeedData" / "Mapping" / "DistCont_Patch_Proposed.csv",
    REPO_ROOT / "PowerBI" / "SeedData" / "Mapping" / "DistAllocationGovernance_FlaggedRows.csv",
    REPO_ROOT / "PowerBI" / "SeedData" / "Mapping" / "EanAffinity_ResidualProposal.csv",
]


def _synthetic_primary_df():
    return pd.DataFrame({
        "PO Type": ["Dist.", "Dist.", "Direct"],
        "Ship To Name": ["Alpha Distributors", "Alpha Distributors", "Beta Corp"],
        "brand": ["Mamaearth", "Mamaearth", "Mamaearth"],
        "Month": ["2026-04-01", "2026-04-01", "2026-04-01"],
        "Chain name for Dashboard": [None, None, "Beta Chain"],
        "_CustName": ["Alpha Distributors", "Alpha Distributors", "Beta Corp"],
        "_CustCode": ["D001", "D001", "D002"],
        "_Brand": ["Mamaearth", "Mamaearth", "Mamaearth"],
        "_Zone": ["North", "North", "North"],
        "_FY": ["FY27", "FY27", "FY27"],
        "_M": ["April", "April", "April"],
        "_NSV": [70.0, 30.0, 100.0],
        "_MRP": [100.0, 40.0, 130.0],
        "_Qty": [10, 4, 13],
        "_TaxLOC": [5.0, 2.0, 7.0],
        "_AvgTot": [10.0, 10.0, 10.0],
        "_EAN No.": ["", "", ""],
    })


def _synthetic_wdf():
    w = pd.DataFrame({
        "_st": ["alpha distributors", "alpha distributors"],
        "_bl": ["mamaearth", "mamaearth"],
        "_pm": ["2026-04", "2026-04"],
        "_frac": [0.7, 0.3],
        "_AllocChainRaw": ["DMart", "Reliance Retail"],
        "_ShipToRaw": ["Alpha Distributors", "Alpha Distributors"],
        "_BrandRaw": ["Mamaearth", "Mamaearth"],
    })
    raw_sums = {("alpha distributors", "mamaearth", "2026-04"): 100.0}
    return w, raw_sums


def test_shadow_run_with_output_dir_never_touches_tracked_files(tmp_path):
    before = {p: (p.read_bytes() if p.exists() else None) for p in TRACKED_FILES}

    df = _synthetic_primary_df()
    wdf, raw_sums = _synthetic_wdf()
    shadow_dir = tmp_path / "shadow_output"

    out_df, alloc = bd.allocate_dist_primary(
        df, wdf, raw_sums, source_label="test_shadow", output_dir=shadow_dir,
    )

    assert alloc is not None
    for p in TRACKED_FILES:
        after = p.read_bytes() if p.exists() else None
        assert after == before[p], f"{p} was modified by a shadow run that passed output_dir"

    # the 3 governance/proposal files land under the given scratch dir instead
    written = list(shadow_dir.rglob("*.csv"))
    assert len(written) >= 1, "expected at least one governance/proposal CSV under output_dir"


def test_default_call_without_output_dir_keeps_writing_to_repo_paths(tmp_path, monkeypatch):
    """Confirms output_dir=None (the default) preserves the exact pre-fix
    behaviour -- production callers that don't pass it are unaffected."""
    monkeypatch.chdir(tmp_path)
    fake_repo = tmp_path / "fake_repo"
    (fake_repo / "PowerBI" / "SeedData" / "Mapping").mkdir(parents=True)
    monkeypatch.setattr(bd, "__file__", str(fake_repo / "scripts" / "build_dashboard_data.py"))

    df = _synthetic_primary_df()
    wdf, raw_sums = _synthetic_wdf()

    bd.allocate_dist_primary(df, wdf, raw_sums, source_label="test_default")

    flagged = fake_repo / "PowerBI" / "SeedData" / "Mapping" / "DistCont_Patch_Proposed.csv"
    assert flagged.exists(), "default (output_dir=None) call should still write to the repo-relative path"
