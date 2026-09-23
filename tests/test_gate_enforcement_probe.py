"""Throwaway probe for Phase 18 ruleset enforcement verification.

This file exists only on the test/gate-enforcement-verification branch,
opened as a throwaway PR that is closed without merging once the proof is
recorded in docs/MAIN_BRANCH_PROTECTION_AUDIT.md. It deliberately fails so
the "Production Acceptance Gate" required check reports failure, to prove
the branch ruleset actually blocks a merge in that state -- not just that
the check is configured. Do not merge this file into main.
"""


def test_intentional_failure_for_ruleset_enforcement_proof():
    assert False, "intentional failure for ruleset enforcement proof (Phase 18 Stage A)"
