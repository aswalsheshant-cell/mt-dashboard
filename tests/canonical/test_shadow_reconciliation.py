"""Runs the full existing-vs-canonical shadow reconciliation and asserts
the Phase 1 certification acceptance criterion:

    FAIL = 0
    UNKNOWN = 0
    PASS + APPROVED_GOVERNED = 100% of the reconciliation population

APPROVED_GOVERNED rows (a variance matched to a reviewed record in
governance.APPROVED_EXCEPTIONS -- KI-OFFTAKE-001, the documented FY27/
primary.by_channel coverage gap, RBC_OFFTAKE_NSV's honest unavailability)
are allowed and asserted to exist, proving the governance mechanism is
exercised, not just present but unused. UNKNOWN would mean some caller
claimed an exception the registry never reviewed -- that fails the gate
exactly like an unexplained numeric variance.
"""
from canonical.shadow_report import build_report
from canonical import reconcile


def test_shadow_reconciliation_meets_phase1_acceptance_criterion(data):
    rows = build_report(data)
    summary = reconcile.summarize(rows)
    fails = [r for r in rows if r.result == "FAIL"]
    unknowns = [r for r in rows if r.result == "UNKNOWN"]
    assert summary["fail"] == 0, (
        "unexplained variance(s): " +
        "; ".join(f"{r.metric}/{r.scope}: existing={r.existing_value} "
                  f"canonical={r.canonical_value}" for r in fails))
    assert summary["unknown"] == 0, (
        "unregistered exception claim(s) -- must be reviewed into "
        "governance.APPROVED_EXCEPTIONS or fixed: " +
        "; ".join(f"{r.metric}/{r.scope}: {r.reason}" for r in unknowns))
    assert summary["clean_population_pct"] == 100.0
    assert summary["overall"] == "PASS"


def test_shadow_reconciliation_governed_rows_all_carry_a_full_governance_record(data):
    rows = build_report(data)
    governed = [r for r in rows if r.result == "APPROVED_GOVERNED"]
    assert governed, "expected at least KI-OFFTAKE-001's governed rows to be present"
    for r in governed:
        assert r.exception is not None
        assert r.exception.status == "APPROVED_GOVERNED"
        assert r.exception.owner
        assert r.exception.resolution_phase


def test_shadow_reconciliation_includes_ki_offtake_001_proof(data):
    """The specific governed rows proving Issue #195's mechanism are present
    -- this is the test that would fail if a future data.js rebuild
    happened to give every chain full FY coverage (in which case
    KI-OFFTAKE-001 would have nothing left to prove and this test's
    assumption should be revisited, not silently left passing on stale
    reasoning)."""
    rows = build_report(data)
    ki_rows = [r for r in rows if r.metric == "CHAIN_OFFTAKE_NSV" and r.result == "APPROVED_GOVERNED"]
    assert ki_rows, "expected at least one CHAIN_OFFTAKE_NSV governed row (KI-OFFTAKE-001 proof)"
    assert all(r.exception.exception_id == "GOV-003" for r in ki_rows)


def test_shadow_reconciliation_passes_include_primary_and_offtake_totals(data):
    """Sanity check that the reconciliation isn't passing merely because
    everything ended up governed -- the core, already-certified totals
    must show as clean PASSes with zero variance."""
    rows = build_report(data)
    passes = {(r.metric, r.scope): r for r in rows if r.result == "PASS"}
    assert ("PRIMARY_NSV", "fy=FY26") in passes
    assert ("OFFTAKE_NSV", "fy=FY27") in passes
    assert passes[("PRIMARY_NSV", "fy=FY26")].variance == 0.0
    assert passes[("OFFTAKE_NSV", "fy=FY27")].variance == 0.0


def test_shadow_reconciliation_rbc_offtake_not_available_is_governed_not_hidden(data):
    """RBC_OFFTAKE_NSV's honest unavailability must appear as a visible,
    reviewed governance record (GOV-004), never silently dropped from the
    report or shown as a clean PASS."""
    rows = build_report(data)
    rbc_rows = [r for r in rows if r.metric == "RBC_OFFTAKE_NSV"]
    assert rbc_rows
    assert all(r.result == "APPROVED_GOVERNED" and r.exception.exception_id == "GOV-004"
               for r in rbc_rows)
