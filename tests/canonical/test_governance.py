"""Proves the governance registry actually gates APPROVED_GOVERNED --
an expected_difference claim with no matching registry entry must become
UNKNOWN, never a silent PASS or an unregistered GOVERNED."""
import dataclasses

from canonical import governance, reconcile


def _mutate(exc, **overrides):
    """Build a copy of a real registry entry with specific fields
    overridden -- used to prove the self-approval guard rejects an entry
    that matches by metric/scope but fails the approval check, without
    needing a second hand-written ApprovedException with all 16 fields."""
    return dataclasses.replace(exc, **overrides)


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
                "approver", "approval_reference", "approved_at", "approval_status",
                "temporary_or_permanent", "resolution_phase", "release_blocker", "status"]
    for exc in governance.APPROVED_EXCEPTIONS:
        d = exc.as_dict()
        for field in required:
            assert d.get(field), f"{exc.exception_id} missing/empty field: {field}"
        assert d["temporary_or_permanent"] in ("TEMPORARY", "PERMANENT")
        assert d["release_blocker"] in ("YES", "NO")
        assert d["status"] == "APPROVED_GOVERNED"
        assert d["approval_status"] == "APPROVED"


def test_every_registry_entry_is_fully_approved():
    """Every entry actually shipped in the registry must pass the
    self-approval guard -- a real regression test, not just a unit test of
    the guard's logic on synthetic data."""
    for exc in governance.APPROVED_EXCEPTIONS:
        assert exc.is_fully_approved(), f"{exc.exception_id} is in the registry but not fully approved"


def test_self_approval_guard_rejects_missing_approver():
    unapproved = _mutate(governance.APPROVED_EXCEPTIONS[0], approver="")
    assert not unapproved.is_fully_approved()


def test_self_approval_guard_rejects_blank_approval_reference():
    unapproved = _mutate(governance.APPROVED_EXCEPTIONS[0], approval_reference="   ")
    assert not unapproved.is_fully_approved()


def test_self_approval_guard_rejects_missing_approved_at():
    unapproved = _mutate(governance.APPROVED_EXCEPTIONS[0], approved_at="")
    assert not unapproved.is_fully_approved()


def test_self_approval_guard_rejects_non_approved_status():
    """A status of PENDING or WITHDRAWN -- not just a blank field -- must
    also fail the guard. A developer flipping approval_status to something
    other than the literal string 'APPROVED' (e.g. while drafting an entry
    before real sign-off) must not accidentally pass."""
    for bad_status in ("PENDING", "WITHDRAWN", "approved", "Approved", ""):
        mutated = _mutate(governance.APPROVED_EXCEPTIONS[0], approval_status=bad_status)
        assert not mutated.is_fully_approved(), f"status {bad_status!r} incorrectly passed the guard"


def test_a_new_entry_with_blank_approval_fields_cannot_manufacture_a_pass(monkeypatch):
    """The core self-approval scenario: a developer adds a brand-new
    ApprovedException entry for a metric/scope that would otherwise FAIL,
    but never populates the approval fields (e.g. drafts it, intending to
    get sign-off later, but it ships anyway). find_approved_exception()
    must not return it -- the caller sees None and reconcile_one() produces
    UNKNOWN, never APPROVED_GOVERNED."""
    fake_unapproved_entry = governance.ApprovedException(
        exception_id="GOV-999",
        metric="SOME_NEW_METRIC",
        scope_matches=lambda scope: True,
        scope_description="anything",
        reason_not_pass="a developer's own claim",
        evidence="none reviewed yet",
        business_impact="unknown",
        financial_impact="unknown",
        owner="Engineering",
        approver="",              # never actually signed off
        approval_reference="",    # nothing to check
        approved_at="",           # no date
        approval_status="APPROVED",  # even claiming APPROVED status doesn't save it
    temporary_or_permanent="TEMPORARY",
        resolution_phase="unscheduled",
        release_blocker=False,
    )
    monkeypatch.setattr(governance, "APPROVED_EXCEPTIONS",
                         governance.APPROVED_EXCEPTIONS + [fake_unapproved_entry])
    assert governance.find_approved_exception("SOME_NEW_METRIC", "anything") is None

    row = reconcile.reconcile_one(
        "SOME_NEW_METRIC", "anything", 100.0, 50.0,
        expected_difference=True, reason="a developer's own claim")
    assert row.result == "UNKNOWN"
    assert row.exception is None


def test_a_new_entry_with_approval_status_not_approved_cannot_manufacture_a_pass(monkeypatch):
    """Same scenario, but the entry claims every field is populated except
    approval_status itself is left as PENDING -- still must not fire."""
    fake_pending_entry = governance.ApprovedException(
        exception_id="GOV-998",
        metric="ANOTHER_NEW_METRIC",
        scope_matches=lambda scope: True,
        scope_description="anything",
        reason_not_pass="a developer's own claim",
        evidence="a real-looking reference",
        business_impact="unknown",
        financial_impact="unknown",
        owner="Engineering",
        approver="Someone",
        approval_reference="SOME-TICKET-123",
        approved_at="2026-09-24",
        approval_status="PENDING",  # sign-off has not actually happened yet
        temporary_or_permanent="TEMPORARY",
        resolution_phase="unscheduled",
        release_blocker=False,
    )
    monkeypatch.setattr(governance, "APPROVED_EXCEPTIONS",
                         governance.APPROVED_EXCEPTIONS + [fake_pending_entry])
    assert governance.find_approved_exception("ANOTHER_NEW_METRIC", "anything") is None


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
