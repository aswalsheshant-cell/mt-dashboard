"""Runs the full existing-vs-canonical shadow reconciliation and asserts
the gate: zero unexplained FAILs. GOVERNED rows (a named, reasoned,
expected difference -- KI-OFFTAKE-001, the documented FY27-primary.by_channel
coverage gap, RBC_OFFTAKE_NSV's honest unavailability) are allowed and
asserted to exist (proving the governance mechanism itself is exercised,
not just present but unused); an unreasoned or unexpectedly-passing
governed row would itself be a test failure below.
"""
from canonical.shadow_report import build_report
from canonical import reconcile


def test_shadow_reconciliation_has_zero_unexplained_failures(data):
    rows = build_report(data)
    summary = reconcile.summarize(rows)
    fails = [r for r in rows if r.result == "FAIL"]
    assert summary["overall"] == "PASS", (
        f"{summary['fail']} unexplained variance(s): " +
        "; ".join(f"{r.metric}/{r.scope}: existing={r.existing_value} "
                  f"canonical={r.canonical_value}" for r in fails)
    )


def test_shadow_reconciliation_governed_rows_are_all_reasoned(data):
    rows = build_report(data)
    governed = [r for r in rows if r.result == "GOVERNED"]
    assert governed, "expected at least KI-OFFTAKE-001's governed rows to be present"
    for r in governed:
        assert r.expected_difference is True
        assert r.reason and len(r.reason) > 20, f"governed row with a weak/empty reason: {r}"


def test_shadow_reconciliation_includes_ki_offtake_001_proof(data):
    """The specific governed rows proving Issue #195's mechanism are present
    -- this is the test that would fail if a future data.js rebuild
    happened to give every chain full FY coverage (in which case
    KI-OFFTAKE-001 would have nothing left to prove and this test's
    assumption should be revisited, not silently left passing on stale
    reasoning)."""
    rows = build_report(data)
    ki_rows = [r for r in rows if r.metric == "CHAIN_OFFTAKE_NSV" and r.result == "GOVERNED"]
    assert ki_rows, "expected at least one CHAIN_OFFTAKE_NSV governed row (KI-OFFTAKE-001 proof)"
    assert any("KI-OFFTAKE-001" in r.reason for r in ki_rows)


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
