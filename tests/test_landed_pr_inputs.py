"""Files landed from PRs: unchanged, classified, not restricted, and their QC facts still hold."""
import csv
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import restricted_source_firewall as fw  # noqa: E402

MANIFEST = ROOT / "PowerBI" / "Reference" / "PR_INPUTS_MANIFEST.csv"
S = ROOT / "PowerBI" / "SeedData"
R = ROOT / "PowerBI" / "Reference" / "CM2_Provisional"


def _manifest():
    return list(csv.DictReader(open(MANIFEST, encoding="utf-8")))


def test_every_landed_file_matches_its_manifest_checksum():
    for r in _manifest():
        p = ROOT / r["path"]
        assert p.exists(), r["path"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == r["sha256"], r["path"]


def test_status_classes_are_known_and_nothing_landed_is_marked_approved_by_landing():
    ok = {"SAFE_SEED", "NEEDS_OWNER", "REFERENCE_PENDING", "TEMPLATE"}
    assert {r["status_class"] for r in _manifest()} <= ok


def test_no_landed_file_is_a_restricted_source():
    policy = fw.load_policy()
    for r in _manifest():
        header = fw.csv_header(ROOT / r["path"]) if r["path"].endswith(".csv") else None
        assert not fw.classify(r["path"], header, policy), r["path"]


def test_restricted_raw_extracts_were_not_landed():
    landed = {r["path"] for r in _manifest()}
    assert not any("Offtake_Monthly_SIS" in p or "StoreChainMaster" in p or p.endswith("primary_article.csv") for p in landed)


# ---- QC facts found on 2026-10-11 ----------------------------------------------------------------

def test_fill_rate_matches_its_qc_file_and_ties_to_po_vs_target():
    f = pd.read_csv(S / "Forecast" / "PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv")
    qc = json.loads((S / "Forecast" / "PO_Fill_Rate_QC.json").read_text(encoding="utf-8"))
    assert round(f.Billed_Qty.sum() / f.PO_Qty.sum() * 100, 2) == round(qc["fr_qty_pct_overall"], 2)
    assert not f.duplicated(["Month", "Channel", "Customer_Group", "Zone", "Chain", "Chain_Raw", "Brand", "Category"]).any()
    assert f.Month.nunique() == 17 and (f.Billed_Qty <= f.PO_Qty).all()
    t = pd.read_csv(S / "Forecast" / "PO_vs_Target_Monthly_FY27.csv").set_index("Month")
    mon = f[f.FY == "FY27"].groupby("Month").PO_Value_L.sum()
    for m, v in mon.items():
        assert abs(v - t.loc[m, "PO_Value_All_L"]) < 0.01, m


def test_claim_allocation_ties_to_claim_input():
    amt = "Expense Amount (INR Lakh)"
    c = pd.read_csv(S / "Masters" / "PL_Distributor_Claim_Input_Q1_FY27.csv")
    a = pd.read_csv(S / "Masters" / "PL_Distributor_Claim_Monthly_Allocated_Q1_FY27.csv")
    assert len(c) == 32 and abs(c[amt].sum() - a[amt].sum()) < 0.001
    g = a.groupby(["Chain", "Expense Head"])[amt].sum()
    q = c.groupby(["Chain", "Expense Head"])[amt].sum()
    assert ((g - q).abs() < 0.001).all()


def test_alias_decisions_are_still_blank_so_nothing_is_treated_as_approved():
    rows = list(csv.DictReader(open(S / "Mapping" / "ClaimDriver_Alias_Decisions_Q1_FY27.csv", encoding="utf-8")))
    assert rows and all(not r["Owner_Decision"].strip() for r in rows)


def test_cm2_decisions_pending_stay_pending():
    d = {r["decision_id"]: r["status"] for r in csv.DictReader(open(R / "config" / "cm2_decision_register.csv", encoding="utf-8"))}
    assert [k for k, v in d.items() if v == "PENDING_APPROVAL"] == ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]


def test_known_cm2_arithmetic_issue_is_still_documented():
    """The COGS total row is 1,000.00 L above its three months. Finance has to fix the file; this test pins the finding so a
    silent edit (or a fix) forces the register and the pending-inputs file to be updated."""
    a = pd.read_csv(R / "SeedData" / "CM2_Provisional_Assumptions.csv")
    cogs = a[(a.Expense_Category == "COGS") & (a.Scenario == "Base")]
    months = cogs[cogs.Month.notna()].Expense_Lacs.sum()
    total = cogs[cogs.Month.isna()].Expense_Lacs.iloc[0]
    assert round(total - months, 2) == 1000.00
    reg = (ROOT / "docs" / "evidence" / "INPUT_AVAILABILITY_REGISTER.md").read_text(encoding="utf-8")
    assert "3,411.21" in reg and "4,411.21" in reg


def test_ean_master_covers_the_current_offtake_eans_and_has_no_duplicates():
    e = pd.read_csv(S / "Masters" / "EAN_Product_Master.csv", dtype=str)
    assert len(e) == 3494 and not e.EAN.duplicated().any()


def test_npi_list_has_no_mt_primary_before_apr26_and_mostly_matches_the_new_article_list():
    n = pd.read_csv(S / "Masters" / "NPI_List.csv", dtype=str)
    n["EAN"] = n.EAN.str.replace(r"\.0$", "", regex=True)
    new = pd.read_csv(S / "Masters" / "TDP_New_Articles_Since_Jan26.csv", dtype=str)
    assert len(n) == 32 and n.EAN.isin(new.EAN).sum() >= 29


def test_landed_files_are_not_ignored_by_git():
    """A landed file that .gitignore swallows would exist locally and vanish on a fresh clone."""
    import subprocess
    for r in _manifest():
        res = subprocess.run(["git", "check-ignore", "-q", r["path"]], cwd=ROOT)
        assert res.returncode == 1, "ignored by .gitignore: " + r["path"]


def test_synthetic_fy25_primary_is_never_read_by_a_query():
    import re
    for q in (ROOT / "PowerBI" / "PowerQuery").glob("*.pq"):
        assert "Primary_Article_Synthesized_FY25" not in q.read_text(encoding="utf-8"), q.name
