"""Owner-approved chain rules -> PrimaryAllocationOverride rows, and the override loader's brand handling."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
acp = importlib.import_module("apply_chain_mapping_policy")
bdd = importlib.import_module("build_dashboard_data")

RULES = [
    {"rule_id": "R-001", "status": "APPROVED", "distributor": "Dist A", "brand": "ALL", "chain": "DMart"},
    {"rule_id": "R-006", "status": "APPROVED", "distributor": "Az Ent", "brand": "ALL except Dr. Sheth's", "chain": "More Retail"},
    {"rule_id": "R-013", "status": "APPROVED", "distributor": "Az Ent", "brand": "Dr. Sheth's", "chain": "Health & Glow"},
    {"rule_id": "R-011", "status": "APPROVED", "distributor": "Chh", "brand": "Mamaearth", "chain": "SPLIT: DMart, Lulu"},
    {"rule_id": "R-099", "status": "PENDING", "distributor": "Dist P", "brand": "ALL", "chain": "DMart"},
]


def test_all_scope_and_exact_distributor():
    assert acp.rule_for(RULES, "dist a ", "Mamaearth")[0]["rule_id"] == "R-001"
    assert acp.rule_for(RULES, "Dist B", "Mamaearth") is None


def test_brand_scoped_rule_beats_all_except_scope():
    assert acp.rule_for(RULES, "Az Ent", "Dr. Sheth")[0]["chain"] == "Health & Glow"      # brand alias canonicalised
    assert acp.rule_for(RULES, "Az Ent", "Mamaearth")[0]["chain"] == "More Retail"


def test_split_and_unapproved_rules_are_never_applied():
    assert acp.rule_for(RULES, "Chh", "Mamaearth") is None
    assert acp.rule_for(RULES, "Dist P", "Mamaearth") is None


def test_rows_carry_approval_evidence_and_skip_existing_keys():
    keys = [("Dist A", "Mamaearth"), ("Dist A", "Mamaearth"), ("Dist B", "Mamaearth"), ("Az Ent", "Dr. Sheth's")]
    rows, skipped = acp.build_rows(RULES, keys, "2026-09", "MT Channel Analyst Lead 2026-10-17", existing={("az ent", "dr. sheth's", "2026-09")})
    assert [(r["Ship To Name"], r["Brand"], r["Chain"]) for r in rows] == [("Dist A", "Mamaearth", "DMart")]
    assert all(r["Override Cont%"] == 100 and "Approved: MT Channel Analyst Lead 2026-10-17" in r["Remarks"] for r in rows)
    assert any("no approved single-chain rule" in s for s in skipped) and any("already" in s for s in skipped)
    assert bdd.OVERRIDE_APPROVAL.search(rows[0]["Remarks"])                                # the build accepts this evidence


def test_loader_matches_overrides_on_canonical_brand(tmp_path):
    p = tmp_path / "ov.csv"
    p.write_text("Month,Ship To Name,Chain,Brand,Override Cont%,Remarks\n"
                 "2026-09,Dist A,DMart,The Derma Co.,100,Approved: owner 2026-10-17 x\n", encoding="utf-8")
    got = bdd._load_unmapped_overrides(p)
    assert ("dist a", "the derma co", "2026-09") in got and ("dist a", "the derma co.", "2026-09") in got   # either source spelling matches
    p.write_text("Month,Ship To Name,Chain,Brand,Override Cont%,Remarks\n"
                 "2026-09,Dist A,DMart,The Derma Co,100,Approved: owner 2026-10-17 x\n"
                 "2026-09,Dist A,DMart,The Derma Co.,100,Approved: owner 2026-10-17 x\n", encoding="utf-8")
    with pytest.raises(SystemExit):                                                          # same brand written twice = duplicate
        bdd._load_unmapped_overrides(p)
