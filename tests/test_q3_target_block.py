"""Q3 FY27 chain target (Primary basis): seed ingest + dashboard block."""
import importlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
bd = importlib.import_module("build_dashboard_data")
ing = importlib.import_module("ingest_rkam_q3_targets")


def test_chain_totals_sum_across_rkams_and_skip_total_rows():
    rows = [("Q3", "A", "N1", "Dmart", 10, 12), ("Q3", "B", "N2", "Dmart", 5, 6),
            ("Q3", "A", "N1", "Trent", 1, 2), ("Q3 Total", None, None, None, 16, 20),
            ("Q3", "A Total", None, None, 99, 99)]
    agg = ing.chain_totals(rows, lambda c: {"Dmart": "DMart"}.get(c, c))
    assert dict(agg) == {"DMart": [15.0, 18.0], "Trent": [1.0, 2.0]}


def test_seed_has_no_employee_names_and_primary_basis():
    seed = pd.read_csv(ing.OUT)
    assert set(seed["Basis"]) == {"Primary"}
    assert not {"RKAM", "NKAM"} & set(seed.columns)
    assert abs(seed["Q3_New_Target_L"].sum() - 12499.43) < 0.1


def test_block_step_up_uses_matched_chains_and_flags_unmatched(tmp_path):
    seed = pd.DataFrame([
        ["FY27", "Q3", "DMart", "Primary", 90, 110, "INR Lakh", "s", "me", "2026-10-17"],
        ["FY27", "Q3", "V Mart", "Primary", 1, 2, "INR Lakh", "s", "me", "2026-10-17"],
        ["FY27", "Q3", "Rmt", "Primary", 5, 8, "INR Lakh", "s", "me", "2026-10-17"]],
        columns=ing.HEADER)
    f = tmp_path / "seed.csv"; seed.to_csv(f, index=False)
    fyx = {"months_canon": ["Jul-26", "Aug-26", "Sep-26"],
           "by_chain_month": {"DMart": [30.0, 30.0, 40.0], "V-Mart": [0.5, 0.5, 0.5]}}
    q = bd.q3_target_block(fyx, f)
    assert q["basis"] == "primary"
    assert [u["name"] for u in q["unmatched"]] == ["Rmt"]
    d = {r["name"]: r for r in q["rows"]}
    assert d["DMart"]["prev_q_primary"] == 100.0 and d["DMart"]["step_up_pct"] == 10.0
    assert d["V Mart"]["prev_q_primary"] == 1.5          # name variant matched
    assert q["prev_q_target_matched"] == 112.0           # excludes unmatched Rmt
    assert q["total_new"] == 120.0


def test_block_absent_when_primary_months_missing(tmp_path):
    assert bd.q3_target_block(None) is None
