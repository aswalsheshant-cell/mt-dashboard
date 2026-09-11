# KA-07 — Effective-Dated Employee & Incentive Rules

| Field | Value |
|---|---|
| Topic_ID | KA-07 |
| Purpose | Keep history correct when people move, grades change and plans are revised. |
| Applicable_Agents | business-ai-automation, fmcg-decision-leader |
| Trigger_Conditions | effective date, valid from, transfer, grade change, rule version, historical recalculation |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — for any historical restatement |
| Confidence | HIGH |

## Authoritative sources
- Salesforce — ICM effective dating and audit trail guidance

## Key principles
- Assignments and rules carry Valid_From / Valid_To, not just a current value.
- A transfer, grade change, target revision or plan change applies forward from its effective date.
- Prior approved periods keep the version that applied at the time.
- When historical assignment data is unavailable, say so — do not apply today's mapping backwards.

## Recommended pattern
Store Valid_From, Valid_To, Rule_Version, Employee_Assignment_Version, Target_Version. Join on the period being calculated, not on the current row.

## Anti-patterns
- Applying the current Store-SO mapping to an earlier month.
- Letting a grade correction silently change a signed-off payout.
- A single current-state employee master used for all history.

## Project application
Our Store-SO mapping covers Apr'26 and May'26 only; Jun and Jul have no assignment data. Those months are flagged as missing rather than back-filled with current ownership.

## Project limitations
We do not yet hold effective-dated employee assignment history. Until we do, per-month ownership before Apr'26 is unknown.

## Related project files
- `PowerBI/SeedData/Mapping/Store_SO_Mapping.csv`
