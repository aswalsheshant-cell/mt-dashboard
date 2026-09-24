"""Phase 2A Gate 1 -- CHAIN_OFFTAKE_NSV shadow parity, at the real available
grain (Chain x FY -- see phase2_chain_offtake.py's module docstring for why
Chain x Month is not achievable with the certified data.js's source grain).

GATE 1 STATUS: PASS (58 PASS / 12 APPROVED_GOVERNED / 0 FAIL / 0 UNKNOWN,
100% clean population). This required two governance registry entries:
GOV-003 (KI-OFFTAKE-001 -- CNC/EB2B/Others/Vijetha missing FY27) and
GOV-005 (a DIFFERENT root cause found by this migration's wider Chain x FY
sweep -- 8 chains onboarded via a later --offtake-patch merge run, with no
real FY26 entry AND no 'value' fallback field at all, so the legacy
dashboard expression falls through to its final '|| 0' and silently
displays a literal 0 -- not a stale number, the ADR-007 missing-as-zero
anti-pattern via a different mechanism). GOV-005 was deliberately NOT
folded into GOV-003 (different evidence, different mechanism) and was NOT
self-approved by the agent that found it -- it required an explicit,
separately-recorded approval decision (see governance.py's GOV-005 entry
for the full record) before this test could assert a clean Gate 1."""
from canonical import phase2_chain_offtake as p2, reconcile
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


def test_newly_onboarded_chains_are_governed_via_gov_005(data):
    rows = p2.build_shadow_comparison(data)
    by_scope = {r.scope: r for r in rows}
    for chain in NEWLY_ONBOARDED_CHAINS_MISSING_FY26:
        row = by_scope[f"chain={chain}, fy=FY26"]
        assert row.result == "APPROVED_GOVERNED", f"{chain}: expected APPROVED_GOVERNED, got {row.result}"
        assert row.exception.exception_id == "GOV-005"


def test_gate1_meets_the_release_criterion(data):
    """FAIL=0, UNKNOWN=0, 100% clean population -- the actual Gate 1
    acceptance criterion, now met after GOV-005's approval. Every
    non-PASS row traces to a fully-approved registry entry (GOV-003 or
    GOV-005), never a bare reason string or a silent pass."""
    rows = p2.build_shadow_comparison(data)
    summary = reconcile.summarize(rows)
    assert summary["fail"] == 0
    assert summary["unknown"] == 0
    assert summary["clean_population_pct"] == 100.0
    assert summary["overall"] == "PASS"
    assert summary["approved_governed"] == len(KI_OFFTAKE_001_CHAINS_MISSING_FY27) + len(NEWLY_ONBOARDED_CHAINS_MISSING_FY26)


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
