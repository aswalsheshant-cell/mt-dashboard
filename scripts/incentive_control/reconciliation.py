"""Reconciliation scaffold for the future incentive calculation (Phase 3A,
STEP 9). Interface and invariant only -- no real FY27 payout figures are
computed or referenced here.

Future invariant, once a real calculation exists:

    Total Eligible Incentive Population
    =
    Calculated + Governed Exclusions + Blocked + Unmapped

    difference == 0 (within an explicit, Finance-approved tolerance)

This mirrors the existing `scripts/release_gate.py` / `scripts/canonical_gate_checks.py`
pattern of a named, auditable tolerance rather than an implicit "close
enough". The tolerance here defaults to 0 (exact) until a business owner
sets a different one -- fail-closed, matching this phase's own rule that
nothing here embeds an assumed business value.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PopulationReconciliation:
    total_eligible: float
    calculated: float
    governed_exclusions: float
    blocked: float
    unmapped: float
    tolerance: float = 0.0

    @property
    def difference(self) -> float:
        return self.total_eligible - (
            self.calculated + self.governed_exclusions + self.blocked + self.unmapped
        )

    @property
    def reconciles(self) -> bool:
        return abs(self.difference) <= self.tolerance


def check(recon: PopulationReconciliation) -> None:
    """Raises AssertionError if the population does not reconcile within
    tolerance. Callers (a future release gate, not this phase) treat that
    as a hard release blocker, same as every other reconciliation check in
    this repo -- never a warning that gets waved through."""
    if not recon.reconciles:
        raise AssertionError(
            f"Population reconciliation failed: total_eligible={recon.total_eligible} != "
            f"calculated({recon.calculated}) + governed_exclusions({recon.governed_exclusions}) "
            f"+ blocked({recon.blocked}) + unmapped({recon.unmapped}) "
            f"(difference={recon.difference}, tolerance={recon.tolerance})"
        )
