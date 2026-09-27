# MT Dashboard integration and current limitations

Repository inspected: aswalsheshant-cell/mt-dashboard, commit 10044f142ff48d1bc663526cc696416e3849567d, 2026-09-27. Re-read current code and decisions before using commands. This skill does not certify that current inputs are approved or that the project's future shadow engine exists.

## Existing components to reuse

- docs/RUNBOOK.md: input locations, flattened slab requirement and build order.
- scripts/build_incentive_identity.py: identity/grade preparation; inspect its current CLI.
- scripts/target_scope_diagnostic.py: target-scope diagnostics.
- scripts/build_actual_attribution.py: ownership-based DMS crediting, role-by-role reconciliation.
- scripts/build_incentive_workbook.py: existing workbook with 06_Achievement and 07_Incentive_Calc; at the inspected ref it is a blocked working model, not a completed payout engine.
- docs/knowledge/KA-12-sales-crediting-and-employee-attribution.md, KA-15-incentive-calculation-readiness.md and KA-16-incentive-reconciliation-and-control-totals.md: attribution, gate order and controls.
- docs/FY27_INCENTIVE_RESPONSE_OPERATING_PROCEDURE.md: real response ingestion and amendments; use this later operational procedure rather than older instructions to hand-edit the register.
- scripts/incentive_control/business_rules.py: extract_approved_rules and canonical_measurement_basis enforce closure before consumption. These functions do not calculate payouts.

The attribution script's TotalTertiaryValue is a named DMS measure, not automatic proof it satisfies a slab labeled Primary Sales. Resolve that mismatch through the approved target/measurement basis and source contract before calculating achievement.

## Decision and row gates

The inspected decision model includes NC-01; TG-01 through TG-05; GRAIN-01; DM-01; BASUP-01; D1A/D1B; and RES-01. Inspect the live model for enums and allowed states rather than hardcoding answers. The decision closure gate does not, by itself, validate every C1-C6 scheme rule, cap or proration parameter. Those remain additional calculation prerequisites.

D1A/D1B must establish a compatible measurement basis. Ambiguous owner replies become CLARIFICATION_REQUIRED. Approved changes require fresh evidence and an amendment reason. Existing source documentation describes an ordered row-gate chain: IDENTITY, ELIGIBILITY, GRADE, MEASUREMENT_SCOPE, TARGET, TARGET_SCOPE, TARGET_BASIS, ACTUAL, PERIOD, RULE, CAP, PRORATION, APPROVAL. Report the first failure and retain the rest. Do not treat all resolved decisions as payout approval. For a new shadow-calculation extension, distinguish scheme/input authorization from Finance payout authorization explicitly: approved scheme rules and inputs permit a shadow result marked CALCULATED_NOT_APPROVED; Finance authorization is still required for payout approval or release. The inherited APPROVAL gate must retain its documented live meaning. Inspect that meaning before mapping it to either status; if the existing workbook gates shadow output on Finance approval, preserve that behavior unless an authorized change explicitly separates the modes. Never silently reinterpret or bypass the gate.

## Commands already present

Run from the actual repository root after checking current --help and input existence:

```text
python scripts/validate_incentive_decisions.py --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json
python scripts/incentive_decision_gate.py --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json
python scripts/incentive_readiness_report.py --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json
python -m pytest tests/incentive_control/ tests/test_incentive_identity.py tests/test_incentive_workbook.py -q
```

Use scripts/record_incentive_decision.py only to transcribe a real, evidenced decision through its supported CLI. Never use synthetic fixture approvals to populate the real register. Missing real register means missing input, not permission to initialize one with guessed approvals.

To build the existing working workbook, pass real --employees, --slabs and --targets paths to scripts/build_incentive_workbook.py; run target-scope and actual-attribution preparation in the documented order first. Quote paths with spaces/ampersands. The runbook's D: location may not be available in cloud sessions. The flattened slab was found in Downloads during this review; its presence does not verify its current approval or authorize moving private inputs into Git.

When a tracker or shadow calculation extension is requested, inspect the current workbook and scripts first, add only the missing behavior, run regression tests and preserve restricted outputs. Recalculate Excel formulas in a supported spreadsheet engine before claiming evaluated results; reading formulas or cached values with a library is not recalculation.
