# KA-15 — Incentive Calculation Readiness

| Field | Value |
|---|---|
| Topic_ID | KA-15 |
| Purpose | Decide whether a payout row can be calculated at all, and name the exact gate that stops it. |
| Applicable_Agents | fmcg-decision-leader, sales-data-reconciliation, business-ai-automation |
| Trigger_Conditions | can we calculate, readiness, blocked, why is this zero, payout gate |
| Source_Type | Recognised industry body (compensation governance) |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | No — the gate list is method; the inputs are business-owned |
| Confidence | HIGH |

## Authoritative sources
- WorldatWork — sales compensation governance and operations: eligibility, measures, quota
  and administration are separate controls, each of which can independently stop a payout.

## Key principles
- **Blocked and zero are different business statements.** Zero means the person earned
  nothing. Blocked means we cannot say. Never render one as the other.
- Report the **first** failing gate by name, not a generic "not ready". "BLOCKED: no
  actuals" and "BLOCKED: target scope" send the request to different people.
- Readiness is per row and per period. One employee can be ready while another is not.
- A gate that passes today can fail tomorrow (a grade correction, a rule expiry), so
  readiness is recomputed every cycle, not stored as a one-off verdict.

## Recommended pattern — the gates, in order

`IDENTITY` -> `ELIGIBILITY` -> `GRADE` -> `MEASUREMENT_SCOPE` -> `TARGET` ->
`TARGET_SCOPE` -> `TARGET_BASIS` -> `ACTUAL` -> `PERIOD` -> `RULE` -> `CAP` ->
`PRORATION` -> `APPROVAL`

Resulting status:

`READY_TO_CALCULATE` · `CALCULATED_NOT_APPROVED` · `IDENTITY_BLOCKED` · `GRADE_BLOCKED` ·
`TARGET_BLOCKED` · `ACTUAL_BLOCKED` · `RULE_BLOCKED` · `PERIOD_BLOCKED` ·
`BUSINESS_APPROVAL_BLOCKED`

Order matters: an employee with no valid grade is `GRADE_BLOCKED` regardless of what else
is missing, because that is the gate their manager must act on first.

## Anti-patterns
- A single boolean "ready" flag that hides which input is missing.
- Defaulting a missing target or actual to zero to let the formula run.
- Reporting readiness as a percentage without saying what is blocked.
- Treating "calculated" as "approved".

## Project application
`06_Achievement` in the incentive workbook evaluates the gates in order and returns the
first failure by name. Every row is blocked today: grade, actuals or target scope, in that
precedence. `07_Incentive_Calc` mirrors the status and leaves `Final_Calculated_Amount`
blank — never 0 — while any gate is open.

## Project limitations
`CAP` and `PRORATION` gates cannot be evaluated at all yet; no rule defines them.

## Related project files
- `scripts/build_incentive_workbook.py`
- `incentive_working/incentive_readiness.json`
