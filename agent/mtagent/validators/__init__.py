"""Enforcement logic for `agent/policies/AI_LEVERAGE_AND_JUDGMENT.md`.

Each module here is a standalone, independently testable gate -- none of
them import `controller.py`, so they can be unit-tested with plain
synthetic data (see `agent/tests/test_outcome_gate.py`,
`test_business_validation.py`, `test_materiality.py`) without needing a
real pipeline run.
"""
