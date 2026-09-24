"""Proves the governance registry actually gates APPROVED_GOVERNED --
an expected_difference claim with no matching registry entry must become
UNKNOWN, never a silent PASS or an unregistered GOVERNED."""
from canonical import governance, reconcile


def test_unregistered_exception_becomes_unknown_not_governed():
    row = reconcile.reconcile_one(
        "SOME_METRIC_NOT_IN_REGISTRY", "scope=whatever", 100.0, 50.0,
        expected_difference=True, reason="a caller's own claim, unreviewed")
    assert row.result == "UNKNOWN"
    assert row.exception is None


def test_registered_exception_becomes_approved_governed():
    row = reconcile.reconcile_one(
        "CHANNEL_PRIMARY_NSV", "channel=MT, fy=FY27", None, 1000.0,
        expected_difference=True, reason="doesn't matter, registry decides")
    assert row.result == "APPROVED_GOVERNED"
    assert row.exception is not None
    assert row.exception.exception_id == "GOV-001"


def test_every_registry_entry_has_all_required_fields():
    required = ["exception_id", "metric", "scope", "reason_not_pass", "evidence",
                "business_impact", "financial_impact", "owner",
                "temporary_or_permanent", "resolution_phase", "release_blocker", "status"]
    for exc in governance.APPROVED_EXCEPTIONS:
        d = exc.as_dict()
        for field in required:
            assert d.get(field), f"{exc.exception_id} missing/empty field: {field}"
        assert d["temporary_or_permanent"] in ("TEMPORARY", "PERMANENT")
        assert d["release_blocker"] in ("YES", "NO")
        assert d["status"] == "APPROVED_GOVERNED"


def test_registry_exception_ids_are_unique():
    ids = [e.exception_id for e in governance.APPROVED_EXCEPTIONS]
    assert len(ids) == len(set(ids))


def test_find_approved_exception_returns_none_for_no_match():
    assert governance.find_approved_exception("NOT_A_REAL_METRIC", "anything") is None


def test_unexplained_variance_beyond_tolerance_without_claim_is_fail_not_unknown():
    """A caller that does NOT claim expected_difference gets FAIL, not UNKNOWN
    -- UNKNOWN is specifically reserved for an unregistered claim, so the two
    failure modes stay distinguishable in the report."""
    row = reconcile.reconcile_one("X", "scope", 100.0, 50.0)
    assert row.result == "FAIL"
