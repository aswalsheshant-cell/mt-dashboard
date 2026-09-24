"""ADR-003: RBC_PRIMARY_NSV / RBC_OFFTAKE_NSV stay strictly separate --
never substituted for each other."""
from canonical import offtake, primary
from canonical.policies import NotAvailable

TOLERANCE = 0.01


def test_rbc_primary_nsv_is_real(data):
    assert not isinstance(primary.rbc_primary_nsv(data, "FY26"), NotAvailable)


def test_rbc_offtake_nsv_honestly_not_available_in_certified_baseline(data):
    """The certified baseline's reliance_brand_counters block is the empty
    stub ('data not available in current extracts') -- confirmed by
    reading data.js directly, not assumed. RBC_OFFTAKE_NSV must report
    NOT_AVAILABLE here, not silently substitute RBC_PRIMARY_NSV's value
    (ADR-003 rule 2) or a zero (ADR-007)."""
    result = offtake.rbc_offtake_nsv(data, "FY27")
    assert isinstance(result, NotAvailable)
    primary_value = primary.rbc_primary_nsv(data, "FY27")
    assert result != primary_value  # never silently substituted


def test_rbc_gap_requires_both_operands_never_computed_from_one():
    """ADR-003 rule 5: Gap may only be calculated when both measures are
    available. Phase 1 does not implement RBC_GAP_NSV as a public function
    (RBC_OFFTAKE_NSV is not available in this data, so there is nothing to
    subtract) -- this test documents that non-implementation is correct,
    not an oversight: this repo's canonical package intentionally exposes
    no rbc_gap_nsv() function yet, so there is no way to call one against
    only a Primary value by mistake."""
    from canonical import primary as primary_mod
    assert not hasattr(primary_mod, "rbc_gap_nsv")
    import canonical.offtake as offtake_mod
    assert not hasattr(offtake_mod, "rbc_gap_nsv")
