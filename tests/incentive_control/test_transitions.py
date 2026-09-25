"""Phase 3B, STEP 4 -- state-transition control tests."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from incentive_control.transitions import (  # noqa: E402
    AmendmentRequiredError,
    TransitionError,
    is_allowed_transition,
    requires_amendment,
    validate_transition,
)


def test_pending_to_approved_allowed():
    assert is_allowed_transition("PENDING_LEADERSHIP", "APPROVED")
    assert is_allowed_transition("PENDING_FINANCE", "APPROVED")


def test_terminal_statuses_do_not_transition_out():
    assert not is_allowed_transition("REJECTED", "APPROVED")
    assert not is_allowed_transition("NOT_APPLICABLE", "PENDING_LEADERSHIP")


def test_clarification_required_can_move_to_pending_or_resolved():
    assert is_allowed_transition("CLARIFICATION_REQUIRED", "PENDING_LEADERSHIP")
    assert is_allowed_transition("CLARIFICATION_REQUIRED", "APPROVED")


def test_requires_amendment_false_when_not_currently_approved():
    assert requires_amendment("PENDING_LEADERSHIP", None, "APPROVED", "H1_ONLY") is False


def test_requires_amendment_false_when_response_unchanged():
    assert requires_amendment("APPROVED", "H1_ONLY", "APPROVED", "H1_ONLY") is False


def test_requires_amendment_true_when_response_changes():
    assert requires_amendment("APPROVED", "H1_ONLY", "APPROVED", "H2_PENDING") is True


def test_requires_amendment_true_when_moving_off_approved():
    assert requires_amendment("APPROVED", "H1_ONLY", "REJECTED", None) is True


def test_validate_transition_raises_transition_error_for_disallowed_move():
    with pytest.raises(TransitionError):
        validate_transition("REJECTED", "APPROVED", has_amendment_fields=True)


def test_validate_transition_raises_amendment_required_without_fields():
    with pytest.raises(AmendmentRequiredError):
        validate_transition(
            "APPROVED", "APPROVED", has_amendment_fields=False,
            current_response="H1_ONLY", new_response="H2_PENDING",
        )


def test_validate_transition_passes_with_amendment_fields():
    validate_transition(
        "APPROVED", "APPROVED", has_amendment_fields=True,
        current_response="H1_ONLY", new_response="H2_PENDING",
    )  # must not raise


def test_validate_transition_passes_for_ordinary_first_approval():
    validate_transition(
        "PENDING_LEADERSHIP", "APPROVED", has_amendment_fields=False,
        current_response=None, new_response="H1_ONLY",
    )  # must not raise -- not an amendment, no fields needed
