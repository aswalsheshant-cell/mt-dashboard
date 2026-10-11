"""Distributor claims in chain-wise CM2: one calculation per chain, no double counting, unresolved items listed."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as B  # noqa: E402


def _block():
    """Small synthetic cm2 block shaped like the real one."""
    def row(n, nsv, exp=0.0):
        r = {"name": n, "nsv": nsv, "expense": exp}
        B._cm2_recompute_row(r)
        return r
    return {
        "total_nsv": 1000.0, "total_expense": 10.0, "expense_pct_of_nsv": 1.0, "cm2_value": 990.0, "cm2_pct": 99.0,
        "by_chain": [row("DMart", 600.0, 10.0), row("Spencer", 50.0), row("VMM", 100.0), row("Ratnadeep", 250.0)],
        "by_chain_fy": {"FY27": [row("DMart", 600.0, 10.0), row("Spencer", 50.0), row("VMM", 100.0), row("Ratnadeep", 250.0)]},
        "by_expense_head": [{"name": "Promotion", "amount": 10.0}],
        "monthly": [{"fy": "FY27", "month": "April", "nsv": 500.0, "expense": 10.0, "cm2_value": 490.0, "cm2_pct": 98.0,
                     "mom_expense_change": None, "mom_cm2_change": None},
                    {"fy": "FY27", "month": "May", "nsv": 500.0, "expense": 0.0, "cm2_value": 500.0, "cm2_pct": 100.0,
                     "mom_expense_change": -10.0, "mom_cm2_change": 10.0}],
        "scope_fy": {"FY27": {"nsv_by_channel": {"MT": 1000.0}, "non_mt_nsv": 0.0, "mt_nsv": 1000.0, "expense": 10.0,
                              "expense_on_mt_chains": 10.0, "cm2_pct_mt": 99.0}},
        "not_loaded": [{"bucket": B.CLAIMS_BUCKET, "why": "x"}, {"bucket": "COGS and logistics", "why": "y"}],
        "has_expense_data": True, "qc": {"total_expense": 10.0},
    }


def _claims(extra=None):
    def r(chain, head, month, amt, status="ALLOCATED_PROVISIONAL"):
        return {"Chain": chain, "Expense Head": head, "Month": month, "FY": "FY26-27", "Status": status,
                "Expense Amount (INR Lakh)": str(amt), "Driver Names Pending Alias": ""}
    rows = [r("DMart", "Promo", "Apr'26", 6.0), r("DMart", "Promo", "May'26", 4.0),
            r("Spencer's", "Promo", "Apr'26", 2.0),            # governed alias -> Spencer
            r("Ratnadeep", "Promo", "Q1 (no month)", 3.0, "UNALLOCATED_TIMING"),
            r("Spar", "Promo", "Q1 (no month)", -0.5, "UNALLOCATED_TIMING")]   # no NSV -> unresolved
    rows += extra or []
    tot = round(sum(float(x["Expense Amount (INR Lakh)"]) for x in rows), 4)
    return {"rows": rows, "monthly_total": tot, "quarterly_total": tot, "aliases_pending": ["MRL"], "aliases_total": 7}


@pytest.fixture(autouse=True)
def _no_direct_dn_claims(monkeypatch):
    monkeypatch.setattr(B, "load_pl_expense_input", lambda: [])


def test_claims_land_on_their_own_chain_and_totals_follow():
    cm = _block()
    B.apply_claims_to_cm2(cm, _claims())
    dm = {r["name"]: r for r in cm["by_chain_fy"]["FY27"]}
    assert dm["DMart"]["expense"] == 20.0 and dm["Spencer"]["expense"] == 2.0 and dm["Ratnadeep"]["expense"] == 3.0
    assert dm["DMart"]["cm2_value"] == 580.0
    assert cm["total_expense"] == 25.0                     # 10 + 6+4+2+3 ; Spar not applied
    assert cm["cm2_value"] == 975.0
    assert cm["claims"]["unresolved"][0]["chain"] == "Spar"
    assert cm["claims"]["loaded"] + cm["claims"]["unresolved_total"] == cm["claims"]["source_total"]
    assert cm["claims"]["chain_names_resolved_by_alias"] == {"Spencer's": "Spencer"}
    assert all(cm["claims"]["checks"].values())


def test_no_month_rows_stay_out_of_every_month():
    cm = _block()
    B.apply_claims_to_cm2(cm, _claims())
    apr, may = cm["monthly"]
    assert apr["expense"] == 18.0 and may["expense"] == 4.0   # 10+6+2 ; 0+4
    assert cm["monthly_unallocated_expense"] == 3.0
    assert sum(m["expense"] for m in cm["monthly"]) + cm["monthly_unallocated_expense"] == cm["total_expense"]
    assert cm["claims"]["unallocated_timing"][0]["chain"] == "Ratnadeep"


def test_second_run_changes_nothing():
    cm = _block()
    B.apply_claims_to_cm2(cm, _claims())
    once = copy.deepcopy(cm)
    B.apply_claims_to_cm2(cm, _claims())
    assert cm == once


def test_claims_leave_nsv_alone():
    cm = _block()
    B.apply_claims_to_cm2(cm, _claims())
    assert cm["total_nsv"] == 1000.0 and [r["nsv"] for r in cm["by_chain"]] == [600.0, 50.0, 100.0, 250.0]


def test_claims_bucket_leaves_the_not_loaded_list():
    cm = _block()
    B.apply_claims_to_cm2(cm, _claims())
    assert [b["bucket"] for b in cm["not_loaded"]] == ["COGS and logistics"]


def test_claims_already_in_the_direct_dn_file_stop_the_build(monkeypatch):
    monkeypatch.setattr(B, "load_pl_expense_input",
                        lambda: [{"Source": "Distributor chain claim master (Q1 FY27)", "Chain": "DMart"}])
    with pytest.raises(ValueError, match="double count"):
        B.apply_claims_to_cm2(_block(), _claims())


def test_chain_rows_that_do_not_add_up_to_the_total_stop_the_build():
    cm = _block()
    cm["total_nsv"] = 900.0
    with pytest.raises(ValueError, match="chain NSV"):
        B.apply_claims_to_cm2(cm, _claims())


def test_monthly_file_must_equal_the_quarterly_seed(monkeypatch, tmp_path):
    real = B._read_csv_rows

    def fake(path):
        rows = real(path)
        if path == B.CLAIMS_QUARTERLY_CSV:
            rows = copy.deepcopy(rows)
            rows[0]["Expense Amount (INR Lakh)"] = str(float(rows[0]["Expense Amount (INR Lakh)"]) + 5)
        return rows
    monkeypatch.setattr(B, "_read_csv_rows", fake)
    with pytest.raises(ValueError, match="quarterly seed"):
        B.load_distributor_claims()


def test_real_claim_files_add_back_to_the_quarterly_seed():
    c = B.load_distributor_claims()
    assert c["monthly_total"] == pytest.approx(449.7694, abs=1e-4)
    assert c["quarterly_total"] == pytest.approx(449.7694, abs=1e-4)
    assert len(c["aliases_pending"]) == 7        # none approved by this PR


DATA = ROOT / "dashboard" / "data.js"


@pytest.mark.skipif(not DATA.exists(), reason="data.js not present")
def test_baked_cm2_block_carries_the_claims_and_keeps_fy26():
    t = DATA.read_text(encoding="utf-8")
    d = json.loads(t[t.index("{"): t.rindex("}") + 1])
    cm = d["cm2"]
    cl = cm["claims"]
    assert cl["status"] == "ALLOCATED_PROVISIONAL" and "PENDING" in cl["approval"]
    assert cl["loaded"] + cl["unresolved_total"] == pytest.approx(cl["source_total"], abs=1e-3)
    assert [u["chain"] for u in cl["unresolved"]] == ["Spar"]
    assert all(cl["checks"].values())
    assert not any(b["bucket"] == B.CLAIMS_BUCKET for b in cm["not_loaded"])
    fy26 = [m for m in cm["monthly"] if m["fy"] == "FY26"]
    assert fy26 and all(m["expense"] == 0 for m in fy26)       # FY26 untouched: no claims, no invented cost
    # month rows plus the no-month rows add back to the total (rounding only)
    assert sum(m["expense"] for m in cm["monthly"]) + cm["monthly_unallocated_expense"] == pytest.approx(cm["total_expense"], abs=0.05)
