"""Phase 2A Gate 1 -- CHAIN_OFFTAKE_NSV shadow parity, at the real available
grain (Chain x FY -- see phase2_chain_offtake.py's module docstring for why
Chain x Month is not achievable with the certified data.js's source grain).

This currently pins a REAL, GENUINE, NOT-YET-APPROVED finding: 8 chains
(newly onboarded via an --offtake-patch merge run, not present in the
original full-rebuild dataset) have no real FY26 entry AND no 'value'
fallback field, so the legacy dashboard expression falls all the way
through to its final '|| 0' and silently displays 0 -- not a stale
number, but a literal, wrong zero -- for a chain that simply didn't exist
yet in FY26, exactly the ADR-007 missing-as-zero anti-pattern this whole
canonical architecture exists to prevent. This is a DIFFERENT root cause
than KI-OFFTAKE-001/GOV-003 (which is about a '.value' all-months
fallback, not a bare '|| 0' with no value field at all) and is therefore
correctly NOT covered by GOV-003's registry entry -- it needs its own,
separately reviewed and approved registry entry before Gate 1 can pass.

Until that approval exists, Gate 1 is BLOCKED, and this test file makes
that a first-class, visible, tested fact rather than a silent finding
that could be lost between sessions."""
from canonical import facts, phase2_chain_offtake as p2, reconcile
from canonical.policies import NotAvailable

NEWLY_ONBOARDED_CHAINS_MISSING_FY26 = frozenset({
    "Apna Mart", "Azorte", "Broadway", "Centro", "Lifestyle",
    "National Mart", "Shoppers Stop", "Trent/Westside",
})

KI_OFFTAKE_001_CHAINS_MISSING_FY27 = frozenset({"CNC", "EB2B", "Others", "Vijetha"})


def test_shadow_comparison_grain_is_chain_by_fy_only(data):
    """Regression guard for the documented grain limitation -- if a future
    data.js rebuild ever adds a real Chain x Month grain to offtake.by_chain,
    this test (and the module docstring it guards) should be revisited, not
    silently left describing a limitation that no longer exists."""
    by_chain = data["offtake"]["by_chain"]
    month_like_keys = {"month", "months", "monthly"}
    for row in by_chain:
        assert not (set(row.keys()) & month_like_keys), (
            f"{row.get('name')!r} row unexpectedly carries a month-like key -- "
            "the Chain x FY-only grain assumption in phase2_chain_offtake.py may be stale")


def test_ki_offtake_001_chains_are_governed_via_gov_003(data):
    rows = p2.build_shadow_comparison(data)
    by_scope = {r.scope: r for r in rows}
    for chain in KI_OFFTAKE_001_CHAINS_MISSING_FY27:
        row = by_scope[f"chain={chain}, fy=FY27"]
        assert row.result == "APPROVED_GOVERNED", f"{chain}: expected APPROVED_GOVERNED, got {row.result}"
        assert row.exception.exception_id == "GOV-003"


def test_gate1_is_currently_blocked_by_a_real_unapproved_finding(data):
    """Pins today's honest state: Gate 1 does NOT yet meet the release
    criterion (FAIL=0, UNKNOWN=0). The 8 UNKNOWN rows are exactly the 8
    newly-onboarded chains missing FY26 -- a real, distinct root cause from
    GOV-003, correctly NOT auto-approved by it. When a business-reviewed
    registry entry for this finding is added (with real approver/
    approval_reference/approved_at, per the self-approval guard), this test
    must be updated to assert UNKNOWN == 0 instead -- it is intentionally
    written to fail loudly if that governance work is skipped and someone
    tries to proceed to Gate 2/3 anyway."""
    rows = p2.build_shadow_comparison(data)
    summary = reconcile.summarize(rows)
    unknown_chains = {r.scope.split(",")[0].removeprefix("chain=")
                       for r in rows if r.result == "UNKNOWN"}
    assert unknown_chains == NEWLY_ONBOARDED_CHAINS_MISSING_FY26, (
        f"expected exactly the 8 known newly-onboarded chains to be UNKNOWN, got: {unknown_chains}")
    assert summary["fail"] == 0, "no NEW unexplained variance beyond the known, tracked UNKNOWN set"
    assert summary["overall"] == "FAIL"  # UNKNOWN > 0 fails the gate, by design


def test_newly_onboarded_chains_existing_shows_zero_not_a_stale_number(data):
    """Confirms the precise mechanism: for these 8 chains, legacy's FY26
    value is a literal 0 (not a stale non-zero figure like GOV-003's
    chains) -- because these rows never had a 'value' field populated at
    all (the --offtake-patch merge path creates {'name','raw','total':0.0}
    rows for brand-new chains, build_dashboard_data.py:1499-1504, with no
    all-months 'value' aggregate ever computed for them)."""
    from canonical import existing
    for chain in NEWLY_ONBOARDED_CHAINS_MISSING_FY26:
        assert existing.chain_offtake_nsv(data, "FY26", chain) == 0
        canonical_value = p2.offtake.chain_offtake_nsv(data, "FY26", chain)
        assert isinstance(canonical_value, NotAvailable)


def test_conservation_check_within_documented_tolerance(data):
    for fy in ("FY26", "FY27"):
        result = p2.conservation_check(data, fy)
        assert result["within_tolerance"], (
            f"{fy}: variance {result['variance']} exceeds tolerance {result['tolerance']} -- "
            "this is no longer the documented small rounding residual, investigate before proceeding")
        assert result["variance"] is not None and result["variance"] > 0, (
            "expected the known small rounding residual to still be present and non-zero; if this "
            "is now exactly 0.0, the 'not expected to be exact' framing in conservation_check()'s "
            "docstring should be revisited")


def test_edge_case_report_matches_known_findings(data):
    report = p2.edge_case_report(data)
    assert report["unmapped_chain"]["found"] is False
    assert report["duplicate_mapping"]["found"] is False
    assert report["blank_chain"]["found"] is False
    assert report["negative_nsv"]["found"] is False
    assert report["partial_fy_chains"]["found"] is True
    partial_chains = {c["chain"] for c in report["partial_fy_chains"]["chains"]}
    assert partial_chains == (NEWLY_ONBOARDED_CHAINS_MISSING_FY26 | KI_OFFTAKE_001_CHAINS_MISSING_FY27)


def test_no_chain_offtake_row_is_available_with_a_bare_none_or_silently_zero(data):
    """Every row in the shadow comparison is either a real number or an
    explicit NotAvailable with a reason -- never a bare None standing in
    for 'missing' (ADR-007, re-verified for this migration's own output)."""
    rows = p2.build_shadow_comparison(data)
    for r in rows:
        assert r.canonical_value is not None
        if isinstance(r.canonical_value, NotAvailable):
            assert r.canonical_value.reason
