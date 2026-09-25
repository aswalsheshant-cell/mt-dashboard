# FY27 Incentive Decision Control Framework — Phase 3A

Generated 2026-09-25. Safe-parallel engineering built while the FY27
incentive decision pack (`incentive_working/target_scope_decision_pack.md`)
awaits Leadership and Finance responses. **This framework does not decide
business policy and cannot produce a payout** — it only enforces that no
downstream calculation proceeds without a fully-approved decision, recorded
with an approver, a date, and evidence.

## Architecture note (Step 1 — what was reused, what's new)

Before writing any new code, the repo's existing governance patterns were
inspected and reused rather than reinvented:

| Existing pattern | Where | Reused as |
|---|---|---|
| `NotAvailable` sentinel — missing must never silently become a real value | `scripts/canonical/policies.py` | `models.DecisionGateBlocked` exception hierarchy — a missing/unapproved decision `raise`s, it never returns a default value the caller might mistake for a real one |
| `ApprovedException.is_fully_approved()` — an approval only counts when approver/reference/date are ALL populated | `scripts/canonical/governance.py` | `DecisionRecord.is_fully_approved()` — same four-field (plus status + valid-response) guard, applied to Leadership/Finance decisions instead of reconciliation exceptions |
| Deterministic PASS/FAIL print + exit-code CLI, single-purpose narrowly-scoped gate script | `scripts/check_assumption_coverage.py`, `scripts/canonical_gate_checks.py`, `scripts/release_gate.py` | `scripts/validate_incentive_decisions.py`, `scripts/incentive_decision_gate.py` |
| JSON Schema draft-07 contract file per data domain | `schemas/compliance_metrics.schema.json` et al. | `schemas/fy27_incentive_decision.schema.json` |
| Narrowly-scoped, uniquely-named, path-gated CI workflow (not folded into a broad existing one) | `.github/workflows/assumption-coverage-gate.yml` | `.github/workflows/incentive-decision-gate.yml` |
| `jsonschema` package already pinned in `requirements.txt` | — | used directly for schema validation, no new dependency added |

**Why a new `scripts/incentive_control/` package instead of extending
`scripts/canonical/`:** `canonical/` is the Canonical Financial Truth engine
for dashboard Primary/Offtake/P&L reconciliation — a different governed
domain (dashboard data correctness) from this phase's subject (human
decision-approval workflow for the incentive scheme). Reusing its *patterns*
while keeping this as a sibling package avoids conflating two governance
domains that happen to share a fail-closed philosophy but govern different
things. Nothing in `canonical/` was modified.

## What this framework is, and is not

**Is:**
- A schema (`schemas/fy27_incentive_decision.schema.json`) the real,
  restricted register must conform to.
- A validator (`scripts/validate_incentive_decisions.py` /
  `scripts/incentive_control/validator.py`) catching internal
  inconsistencies (duplicate IDs, an APPROVED row missing its approver,
  a response outside the allowed set, D1A/D1B conflicts, etc.).
- A closure gate (`scripts/incentive_decision_gate.py` /
  `scripts/incentive_control/gate.py`) answering `READY_FOR_SHADOW_CALCULATION`
  or which `BLOCKED_*` state applies.
- A business-rule interface (`scripts/incentive_control/business_rules.py`)
  a future calculation engine would consume — `DecisionResult` objects,
  never raw email text or a default.
- An audit-event schema (`scripts/incentive_control/audit.py`) with a
  built-in guard that refuses to log anything that looks like restricted
  data.
- A reconciliation scaffold (`scripts/incentive_control/reconciliation.py`)
  stating the future population invariant, with no real figures.

**Is not:**
- An incentive calculation engine. No payout, no shadow figure, no
  achievement percentage is computed anywhere in this package.
- A place where any real Leadership or Finance decision is recorded. Every
  test fixture uses an obviously synthetic approver name
  (`SYNTHETIC_FIXTURE_APPROVER`), a synthetic date (`2099-01-01`), and a
  synthetic evidence reference.
- A relaxation of `incentive_working/`'s gitignored/restricted status —
  unchanged; this framework's CI explicitly asserts that directory is
  absent from the checkout.

## How the real register plugs in (once responses arrive)

1. A person updates `incentive_working/FY27_INCENTIVE_DECISION_REGISTER.md`
   (human-facing) with the real response, approver, date, and evidence.
2. The same update is mirrored into a machine-readable
   `incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json` (gitignored,
   validated against `schemas/fy27_incentive_decision.schema.json`) — this
   file does not exist yet; it is created the first time a real response
   is recorded.
3. Run `python3 scripts/validate_incentive_decisions.py --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json`
   to confirm internal consistency.
4. Run `python3 scripts/incentive_decision_gate.py --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json`
   to see the current gate state.
5. No agent sets `current_status` to `APPROVED` — that value is only ever
   written by a person transcribing a real decision.

## D1 conflict control

```
D1A (Leadership intent)  vs  D1B (Finance source confirmation)

Both fully approved AND D1A.selected_response == D1B.selected_response
    → both release; canonical_measurement_basis() returns that value

Both fully approved AND D1A.selected_response != D1B.selected_response
    → BLOCKED_BASIS_CONFLICT (scripts/incentive_control/gate.py) — no
      basis is chosen automatically; both parties are notified jointly

Either side not yet fully approved
    → BLOCKED_LEADERSHIP_DECISION or BLOCKED_FINANCE_INPUT respectively
```

## RES-01 materiality

`REQUIRED_DECISIONS["RES-01"]["required_for_gate"] == "MATERIAL"` — evaluated
by `gate.res01_is_material()`. No Finance-approved materiality threshold
exists yet (`RES01_MATERIALITY_THRESHOLD_L = None`), so RES-01 is currently
treated as **always material** — fail-closed, not fail-open. When Finance
sets a real threshold, that constant is the one place to update it; nothing
else in the gate logic needs to change.

## Test coverage

`tests/incentive_control/` — 28 tests, all against synthetic fixtures
(`tests/fixtures/incentive_decisions/`): the 10 required cases from the
governing instruction (all-pending, Leadership-only, Finance-only, D1
conflict, APPROVED-without-evidence, APPROVED-without-approver,
out-of-enum response, duplicate ID, ambiguous free text, fully-ready), plus
coverage for `raise`-not-default behaviour, REJECTED/NOT_APPLICABLE
resolution, the audit guard, and the reconciliation scaffold.

## CI

`.github/workflows/incentive-decision-gate.yml` — narrowly path-scoped to
this framework's own files, runs only against synthetic fixtures, and
explicitly asserts `incentive_working/` is absent from the CI checkout
before running anything. Adding this as a *required* GitHub branch-protection
status check needs repository Settings/admin access this session does not
have — that is a manual step for a repo admin (Settings → Branches → branch
protection rule for `main` → Require status checks to pass → select
"Incentive Decision Control Gate: schema + validator + closure gate
(synthetic)"), not something bypassed or worked around here.

## Current real-world status (unaffected by this phase)

```
BLOCKED_LEADERSHIP_DECISION
+
BLOCKED_FINANCE_INPUT
```

This is correct. Nothing in Phase 3A changes it — it changes only once a
person records real, evidenced approvals in the restricted register.
