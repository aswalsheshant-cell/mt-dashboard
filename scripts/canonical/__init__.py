"""Canonical financial-truth engine.

Implements Phase 1 of docs/CANONICAL_METRIC_IMPLEMENTATION_PLAN.md: pure
calculation functions for a fixed set of canonical metrics, each conforming
to the metric contract in docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md and the
policies in that document's Architecture Decision Register (ADR-001..008).

Nothing in this package is consumed by dashboard/index.html or
scripts/build_dashboard_data.py yet. It reads dashboard/data.js (the
certified baseline) as its fact source and recomputes each metric
independently, so it can be reconciled against the dashboard's current
production output (see canonical.reconcile) before any dashboard code is
migrated to depend on it.
"""
