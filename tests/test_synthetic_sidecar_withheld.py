"""Synthetic store-audit / fill-rate data must not count as real evidence.

dashboard/compliance_metrics.json marks itself `is_synthetic: true` (its accounts
block is a byte-for-byte copy of scripts/sync_compliance_data.py's mock output;
config/data_source_registry.yml `store_audit_compliance`). Found 2026-10-01 on
main 6aa2e3c:

  * readiness_gate() read the sidecar's `total_doors_audited` (189) and reported
    "audit coverage 44.37% (189 of 426 stores)" as a measured value;
  * mom_block() described the mock as "a single Q3 FY27 snapshot over 189 of 426
    stores" -- Q3 FY27 (Oct-Dec'26) has not happened.

The browser side (tabs show "Not available", no mock number) is covered by
TC14 in tests/e2e_v1.1.0_consolidation.spec.js.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as bdd  # noqa: E402

SIDECAR = ROOT / "dashboard" / "compliance_metrics.json"
DATA_JS = ROOT / "dashboard" / "data.js"


def _gate(compliance):
    data = {"compliance": compliance, "universe": {"active_stores": 426}}
    cfg = bdd.load_analytics_config(bdd._REPO_ROOT)
    return bdd.readiness_gate(data, cfg)["gates"]["scorecard_execution"]


def test_sidecar_is_still_synthetic():
    meta = json.loads(SIDECAR.read_text(encoding="utf-8"))["compliance"]["metadata"]
    assert meta["is_synthetic"] is True          # premise of every test below


def test_synthetic_audit_is_not_counted_as_coverage():
    g = _gate({"metadata": {"is_synthetic": True, "total_doors_audited": 189}})
    assert g["status"] != "PASS"
    assert "189" not in g["measured"]
    assert "synthetic" in g["measured"].lower()


def test_real_audit_is_still_measured():
    # A non-synthetic sidecar keeps the existing coverage rule unchanged.
    g = _gate({"metadata": {"is_synthetic": False, "total_doors_audited": 300}})
    assert "300 of 426" in g["measured"]


def test_readiness_rule_text_does_not_describe_the_mock_as_an_audit():
    cfg = json.loads((ROOT / "config" / "analytics_config.json").read_text(encoding="utf-8"))
    text = json.dumps(cfg["readiness"]["scorecard_execution"])
    assert "189 doors" not in text and "Q3 FY27" not in text
    assert cfg["readiness"]["scorecard_execution"]["min_audit_coverage_pct"] == 60.0   # threshold unchanged


def test_mom_note_does_not_describe_the_mock_as_real():
    reasons = " ".join(u["reason"] for u in bdd.MOM_UNAVAILABLE)
    assert "Q3 FY27" not in reasons and "189" not in reasons


def _dash():
    t = DATA_JS.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"): t.rindex("}") + 1])


@pytest.fixture(scope="module")
def dash():
    return _dash()


def test_published_readiness_and_mom_carry_no_mock_coverage(dash):
    text = json.dumps(dash["readiness"]) + json.dumps(dash["mom"]["unavailable"])
    assert "189 of 426" not in text and "189 doors" not in text and "Q3 FY27" not in text
    assert dash["readiness"]["gates"]["scorecard_execution"]["status"] != "PASS"
