from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_distributor_claim_expense_seed.py"
SOURCE = ROOT / "PowerBI" / "RawDataFolders" / "ClaimMaster_Quarterly" / "claim_master_chain_AprJun_2026.csv"
SEED = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Distributor_Claim_Input_Q1_FY27.csv"

spec = importlib.util.spec_from_file_location("dist_claim_seed", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def _read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def test_seed_reconciles_to_source_with_rounding_only():
    source = _read(SOURCE)
    seed = _read(SEED)
    source_total = sum(float(r["Total_Claim_Lakh"]) for r in source)
    seed_total = sum(float(r["Expense Amount (INR Lakh)"]) for r in seed)

    assert len(source) == 23
    assert len(seed) == 32
    assert abs(source_total - 449.7696) < 0.0001
    assert abs(seed_total - 449.7694) < 0.0001
    assert abs(seed_total - source_total) <= mod.ROUNDING_TOLERANCE_LAKH


def test_seed_preserves_actual_q1_grain_and_never_invents_months():
    seed = _read(SEED)

    assert all(r["Period"] == "Apr-Jun 2026" for r in seed)
    assert all(r["Quarter"] == "Q1" for r in seed)
    assert all(r["FY"] == "FY26-27" for r in seed)
    assert "Month" not in seed[0]
    assert all("Do not allocate to months" in r["Remarks"] for r in seed)


def test_zero_heads_removed_and_negative_credit_rows_preserved():
    seed = _read(SEED)
    values = [float(r["Expense Amount (INR Lakh)"]) for r in seed]

    assert all(v != 0 for v in values)
    assert any(v < 0 for v in values)
    assert sum(v < 0 for v in values) == 3


def test_generator_reproduces_committed_seed():
    expected, report = mod.build_rows(SOURCE, "2026-09-27")
    committed = _read(SEED)

    assert committed == expected
    assert report["source_rows"] == 23
    assert report["output_rows"] == 32
    assert report["source_total_lakh"] == 449.7696
    assert report["written_total_lakh"] == 449.7694
    assert report["rounding_variance_lakh"] == -0.0002
    assert report["negative_rows_preserved"] == 3


def test_distributor_claim_seed_is_not_silently_mixed_into_monthly_pl_input():
    pl_input = (ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv").read_text(encoding="utf-8")
    assert mod.SOURCE_TAG not in pl_input, (
        "Quarter-level distributor claims were inserted into the monthly PL input. "
        "Use real month x chain claim evidence before loading them into CM2."
    )
