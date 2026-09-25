"""OFFTAKE_NSV / CHAIN_OFFTAKE_NSV -- and the KI-OFFTAKE-001 (Issue #195)
proof case: CHAIN_OFFTAKE_NSV must never return a stale/all-period value
for a chain/FY combination with no real data for that exact FY.
"""
from canonical import offtake
from canonical.policies import NotAvailable

TOLERANCE = 0.01


def test_offtake_nsv_fy27_matches_certified_total(data):
    assert abs(offtake.offtake_nsv(data, "FY27") - 19044.99) <= TOLERANCE


def test_offtake_nsv_reconciles_to_its_own_monthly_series(data):
    """Same identity docs/PR_193_PRODUCTION_CERTIFICATION.md Control 4
    proved by hand -- re-proven here as a standing regression test."""
    from canonical import facts
    monthly = facts.offtake_fy_monthly(data, "fy27")
    assert abs(sum(monthly) - offtake.offtake_nsv(data, "FY27")) <= TOLERANCE


def test_offtake_nsv_unavailable_fy_is_not_available(data):
    assert isinstance(offtake.offtake_nsv(data, "FY99"), NotAvailable)


def test_chain_offtake_nsv_real_value_when_fy_present(data):
    assert abs(offtake.chain_offtake_nsv(data, "FY27", "DMart") - 7046.26) <= TOLERANCE


def test_chain_offtake_nsv_ki_offtake_001_no_stale_fallback(data):
    """THE proof case. Vijetha has real FY26 data (15.19 L) and NO FY27
    entry. The old dashboard code's fallback chain reached
    offtake.by_chain[].value (which happens to equal the FY26 figure here)
    and silently displayed it as if it were FY27 data. The canonical
    function must return NOT_AVAILABLE, never 15.19, never any other
    non-FY27 value."""
    result = offtake.chain_offtake_nsv(data, "FY27", "Vijetha")
    assert isinstance(result, NotAvailable)
    assert result != 15.19


def test_chain_offtake_nsv_same_chain_correct_for_its_real_fy(data):
    """Vijetha's FY26 figure IS real and must still be returned correctly
    -- the fix is "no cross-FY fallback", not "never return chain data"."""
    assert abs(offtake.chain_offtake_nsv(data, "FY26", "Vijetha") - 15.19) <= TOLERANCE


def test_chain_offtake_nsv_never_reaches_the_value_field_even_when_present(data):
    """Structural proof, not just the one Vijetha example: for EVERY chain
    lacking a real FY27 entry, the canonical function must report
    NOT_AVAILABLE, regardless of what offtake.by_chain[]'s own (deliberately
    excluded) 'value'/'total' fields contain."""
    from canonical import facts
    by_chain = (data.get("offtake") or {}).get("by_chain") or []
    affected = [r["name"] for r in by_chain if "fy27" not in r and r.get("name")]
    assert affected, "expected at least one chain with no fy27 entry (test fixture assumption)"
    for chain in affected:
        result = offtake.chain_offtake_nsv(data, "FY27", chain)
        assert isinstance(result, NotAvailable), (
            f"{chain}: expected NOT_AVAILABLE for FY27, got {result!r}")


def test_chain_offtake_nsv_unknown_chain_is_not_available(data):
    result = offtake.chain_offtake_nsv(data, "FY27", "NOT_A_REAL_CHAIN")
    assert isinstance(result, NotAvailable)
