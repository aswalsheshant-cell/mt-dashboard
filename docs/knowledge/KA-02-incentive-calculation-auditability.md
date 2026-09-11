# KA-02 — Incentive Calculation Auditability

| Field | Value |
|---|---|
| Topic_ID | KA-02 |
| Purpose | Make every payout figure traceable backwards to its inputs and the rule version that produced it. |
| Applicable_Agents | business-ai-automation, sales-data-reconciliation |
| Trigger_Conditions | incentive calculation, payout, audit trail, recalculation |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — for any published payout |
| Confidence | HIGH |

## Authoritative sources
- Salesforce — ICM audit trail and effective-dated rule guidance

## Key principles
- Each calculated row records the rule version, target version and actual source version applied.
- A later rule change must not alter an already-approved period.
- Every step is reproducible from stored inputs alone.
- BLOCKED and zero are different results and must never be collapsed.

## Recommended pattern
Source input -> rule version -> measurement scope -> target -> actual -> achievement % -> slab -> parameter payout -> adjustment -> cap/proration -> final calculated -> approval -> paid.

## Anti-patterns
- Overwriting historical calculations when a rule changes.
- Storing only the final amount without the inputs that produced it.
- Returning 0 when an input is unavailable.

## Project application
The Excel workbook carries RuleVersion, TargetVersion, ActualSourceVersion, CalculationTimestamp and CalculationStatus on every calculation row.

## Project limitations
Approved historical periods are immutable once signed off.

## Related project files
- `incentive_working/`
