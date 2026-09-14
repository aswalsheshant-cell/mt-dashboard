"""Synthetic regression tests for the FM-16B loader fix
(scripts/build_dashboard_data.py:load_dist_cont_weights()).

Before this fix, PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv (the
~27-row approved-patch CSV) was read EXCLUSIVELY whenever it existed, and the
real business workbook (Dist_primary_cont_based_on_secondary_MOM.xlsx) was
never even checked. These tests prove the corrected behaviour using synthetic
data only -- no real business/commercial data is used or required, per the
instruction to certify the fix before any real workbook is supplied.
"""
import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
bd = importlib.import_module("build_dashboard_data")


def _write_base_xlsx(path, rows):
    """rows: list of dicts with Ship To Name, Chain Name, Brand, Month,
    Secondary contribution %. Written with a blank title row above the header
    to match the real workbook's header=1 read convention."""
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        # header=1 means row index 1 (0-based) is the header -> one blank row first
        pd.DataFrame([[]]).to_excel(xw, sheet_name="Dist Primary Conv to Chain Art",
                                     index=False, header=False, startrow=0)
        df.to_excel(xw, sheet_name="Dist Primary Conv to Chain Art",
                     index=False, startrow=1)


class TestBaseOnly:
    """CASE 1: base workbook only, no patch -- base allocation loads unchanged."""

    def test_base_workbook_loads_when_no_patch_present(self, tmp_path, monkeypatch):
        base_rows = [
            {"Ship To Name": "Alpha Distributors", "Chain Name": "DMart",
             "Brand": "Mamaearth", "Month": "2026-04-01", "Secondary contribution %": 70.0},
            {"Ship To Name": "Alpha Distributors", "Chain Name": "Reliance Retail",
             "Brand": "Mamaearth", "Month": "2026-04-01", "Secondary contribution %": 30.0},
        ]
        xlsx = tmp_path / "Dist_primary_cont_based_on_secondary_MOM.xlsx"
        _write_base_xlsx(xlsx, base_rows)

        monkeypatch.setattr(bd, "_load_dist_cont_patch_rows", lambda: None)

        wdf, raw_sums, src_label = bd.load_dist_cont_weights(tmp_path)
        assert src_label == "xlsx"
        assert wdf is not None
        names = set(wdf["_AllocChainRaw"])
        assert names == {"DMart", "Reliance Retail"}
        assert len(wdf) == 2


class TestBaseAndPatch:
    """CASE 3: base workbook + patch -- base rows for OTHER keys survive;
    matching patch keys are fully replaced, not partially merged."""

    def test_patch_overrides_only_its_own_key_leaves_rest_of_base_untouched(self, tmp_path, monkeypatch):
        base_rows = [
            # This (ShipTo, Brand, Month) key will be overridden by the patch.
            {"Ship To Name": "Alpha Distributors", "Chain Name": "DMart",
             "Brand": "Mamaearth", "Month": "2026-04-01", "Secondary contribution %": 99.0},
            # This key is NOT covered by the patch -- must survive unchanged.
            {"Ship To Name": "Beta Distributors", "Chain Name": "Apollo",
             "Brand": "TDC", "Month": "2026-04-01", "Secondary contribution %": 100.0},
        ]
        xlsx = tmp_path / "Dist_primary_cont_based_on_secondary_MOM.xlsx"
        _write_base_xlsx(xlsx, base_rows)

        patch = pd.DataFrame([
            {"Ship To Name": "Alpha Distributors", "Chain Name": "DMart",
             "Brand": "Mamaearth", "Month": "2026-04-01", "Secondary contribution %": 60.0},
            {"Ship To Name": "Alpha Distributors", "Chain Name": "Reliance Retail",
             "Brand": "Mamaearth", "Month": "2026-04-01", "Secondary contribution %": 40.0},
        ])
        monkeypatch.setattr(bd, "_load_dist_cont_patch_rows", lambda: patch)

        wdf, raw_sums, src_label = bd.load_dist_cont_weights(tmp_path)
        assert src_label == "xlsx+patch"

        # The untouched key survives exactly as the base workbook had it.
        beta = wdf[wdf["_st"] == "beta distributors"]
        assert len(beta) == 1
        assert beta.iloc[0]["_AllocChainRaw"] == "Apollo"

        # The overridden key now has the PATCH's two rows, not the base's one.
        alpha = wdf[wdf["_st"] == "alpha distributors"]
        assert len(alpha) == 2
        assert set(alpha["_AllocChainRaw"]) == {"DMart", "Reliance Retail"}
        # Confirms the base's stale 99.0%-to-DMart row is gone, replaced by the
        # patch's approved 60/40 split -- not merged or added to.
        dmart_frac = alpha[alpha["_AllocChainRaw"] == "DMart"]["_frac"].iloc[0]
        assert abs(dmart_frac - 0.6) < 1e-6


class TestPatchAloneNeverMasqueradesAsComplete:
    """CASE 7: base workbook missing, patch exists -- the tiny patch file must
    never be treated as if it were the complete allocation universe. The
    pre-fix bug did exactly this (patch existing suppressed the workbook
    entirely); the fixed loader instead falls through to the same Priority-1
    ShipTo-primary fallback used when both DIST files are absent."""

    def test_missing_workbook_does_not_use_patch_as_sole_source(self, tmp_path, monkeypatch):
        patch = pd.DataFrame([
            {"Ship To Name": "Alpha Distributors", "Chain Name": "DMart",
             "Brand": "Mamaearth", "Month": "2026-04-01", "Secondary contribution %": 100.0},
        ])
        monkeypatch.setattr(bd, "_load_dist_cont_patch_rows", lambda: patch)
        sentinel = object()
        monkeypatch.setattr(bd, "load_shipto_primary_weights", lambda: (sentinel, {"marker": True}))

        wdf, raw_sums, src_label = bd.load_dist_cont_weights(tmp_path)  # no xlsx in tmp_path
        # Must have taken the Priority-1 fallback path, NOT built a weights
        # frame out of the patch's single row.
        assert wdf is sentinel
        assert raw_sums == {"marker": True}


class TestPatchSchemaValidation:
    """CASE 8 (patch variant): an invalid/renamed patch CSV must fail loudly,
    never silently be ignored or partially applied."""

    def test_patch_missing_required_column_raises(self, tmp_path, monkeypatch):
        bad_patch_path = tmp_path / "DistPrimaryContWeightsArticle.csv"
        pd.DataFrame([{"Ship_To_Name": "X", "Chain_Name": "Y", "Brand": "Z"}]).to_csv(
            bad_patch_path, index=False)  # missing Month, Cont_Pct

        monkeypatch.setattr(bd, "Path",
                             lambda p: bad_patch_path if "DistPrimaryContWeightsArticle" in str(p) else Path(p))
        with pytest.raises(SystemExit, match="FM-16B"):
            bd._load_dist_cont_patch_rows()
