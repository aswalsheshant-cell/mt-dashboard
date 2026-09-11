# KA-14 — Rule Versioning & Effective Dating

| Field | Value |
|---|---|
| Topic_ID | KA-14 |
| Purpose | Stop a later rule clarification from silently rewriting a payout that was already approved. |
| Applicable_Agents | fmcg-decision-leader, business-ai-automation, sales-data-reconciliation |
| Trigger_Conditions | rule change, effective date, recalculation, restatement, historical payout, version |
| Source_Type | Official vendor documentation |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — every rule version needs an approver |
| Confidence | HIGH |

## Authoritative sources
- Salesforce (Spiff incentive compensation) — system activity logs retain version history of
  payout rules, quotas, assignments, approvals and adjustments; changes are staged and
  promoted rather than edited in place.

## Key principles
- A rule is data with a lifetime, not a constant in a formula.
- **A calculated row stores the rule version it used.** Without it, you cannot explain a
  past payslip, and you cannot prove a restatement was intended.
- Changing a rule never edits history. It creates a new version with a start date; the old
  version keeps its rows.
- A recalculation of a closed period is a restatement and needs its own approval.
- Test a rule change against a copy before it touches the live cycle.

## Recommended pattern
Every rule carries: `Rule_ID`, `Rule_Version`, `Rule_Type`, `Valid_From`, `Valid_To`,
`Approval_Status`, `Approved_By`, `Approval_Date`, `Source_Document`, `Supersedes`,
`Change_Reason`.

Every calculated row carries `Applied_Rule_ID` and `Applied_Rule_Version`, plus the target
and actual source versions it consumed. Join a row to its rule by `Valid_From <= period <
Valid_To`, never by "the current rule".

## Anti-patterns
- Editing a slab rate in place because "it was always meant to be this".
- A rule with no start date — it silently applies to all history.
- Recalculating a closed cycle as part of a routine refresh.
- Version numbers that live only in a filename.

## Project application
`00_Control` holds `Rule version = PENDING` and `07_Incentive_Calc` carries `Rule_Version`,
`Target_Version` and `Actual_Source_Version` on every row. Nothing is stamped with a real
version yet because C1-C6, caps and proration are unresolved — which is the point: a row
cannot claim a rule version that does not exist.

## Project limitations
No approved rule version exists for FY27. Until one does, no row can move past
`BUSINESS_RULE_BLOCKED`.

## Related project files
- `scripts/build_incentive_workbook.py`
- `incentive_working/incentive_decision_register.csv`
