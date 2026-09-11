# KA-13 — Incentive Decision Rights & Exception Governance

| Field | Value |
|---|---|
| Topic_ID | KA-13 |
| Purpose | Say who owns each incentive decision, so an open question is routed instead of guessed. |
| Applicable_Agents | fmcg-decision-leader, executive-commercial-storytelling, agent-skill-governance |
| Trigger_Conditions | who decides, approval, exception, policy owner, escalation, sign-off |
| Source_Type | Recognised industry body (compensation governance) |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — the matrix itself needs business endorsement |
| Confidence | HIGH |

## Authoritative sources
- WorldatWork — sales compensation governance: define decision rights across Sales, HR and
  Finance for plan design, quota setting, measures and weights, exceptions, mid-cycle
  changes and payout administration.
- WorldatWork — governance and operations are foundational: reconciliation, exception
  handling and clear accountability matter as much as plan design.

## Key principles
- Every unresolved item has exactly one accountable function. "The business" is not an owner.
- **Analytics never invents policy to unblock its own calculation.** A blocked number is a
  correct output when the rule is missing.
- An exception needs an owner, an impact and a due status, or it is just a note.
- Mid-cycle changes need the same approval path as the original plan.

## Recommended pattern — decision rights matrix

| Function | Owns |
|---|---|
| **MT Leadership** | Performance measures, weighting, target basis, target scope, business-policy approval |
| **Finance** | Payout mechanics, caps, provision and budget, financial reconciliation, final payout approval |
| **HR** | Eligibility, designation and incentive grade, joiner/leaver policy, proration, employment status |
| **MT Operations** | Employee/store/account ownership, WoA identity approval, territory assignment |
| **Analytics / agent** | Data validation, calculation, reconciliation, exception detection, impact sizing, documentation — **never policy** |

Each open decision carries: `Decision_ID`, question, owner, impact, affected employees,
affected value where calculable, due status, approval status.

## Anti-patterns
- Recording a decision with no owner, or with several.
- Letting an analyst pick "the reasonable interpretation" of an ambiguous rule.
- Leaving unresolved rules as comments inside a workbook instead of a register.
- Re-asking a question that already has an approved, unexpired answer.

## Project application
Owners assigned in `incentive_working/incentive_decision_register.csv` and mirrored into
`12_Rule_Decisions` of the incentive workbook. Open items route as: target scope and target
basis to MT Leadership; caps, proration mechanics and C1-C6 payout treatment to Finance;
missing incentive grades to HR; WoA identity approvals to MT Ops.

## Project limitations
The matrix is our reading of who should own what. It is not yet endorsed by those functions.

## Related project files
- `incentive_working/incentive_decision_register.csv`
- `incentive_working/target_scope_decision_pack.md`
