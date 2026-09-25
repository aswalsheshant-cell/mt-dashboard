"""Phase 3A, STEP 9 -- reconciliation scaffold tests. Purely synthetic
numbers; no real FY27 population/payout figures."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from incentive_control.reconciliation import PopulationReconciliation, check  # noqa: E402


def test_reconciles_exactly():
    recon = PopulationReconciliation(
        total_eligible=100.0, calculated=60.0, governed_exclusions=10.0,
        blocked=25.0, unmapped=5.0,
    )
    assert recon.difference == 0.0
    assert recon.reconciles
    check(recon)  # must not raise


def test_difference_detected():
    recon = PopulationReconciliation(
        total_eligible=100.0, calculated=60.0, governed_exclusions=10.0,
        blocked=25.0, unmapped=4.0,  # 1 short
    )
    assert recon.difference == 1.0
    assert not recon.reconciles
    with pytest.raises(AssertionError):
        check(recon)


def test_tolerance_is_explicit_not_implicit():
    recon = PopulationReconciliation(
        total_eligible=100.0, calculated=60.0, governed_exclusions=10.0,
        blocked=25.0, unmapped=4.999, tolerance=0.01,
    )
    assert recon.reconciles  # within the explicitly stated tolerance
    check(recon)  # must not raise
