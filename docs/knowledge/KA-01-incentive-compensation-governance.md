# KA-01 — Incentive Compensation Governance

| Field | Value |
|---|---|
| Topic_ID | KA-01 |
| Purpose | How to govern an incentive plan — not what our plan says. |
| Applicable_Agents | fmcg-decision-leader, business-ai-automation |
| Trigger_Conditions | incentive, payout, slab, commission, quota, plan design |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — every rule value |
| Confidence | HIGH |

## Authoritative sources
- WorldatWork — sales compensation governance (accountable decision rights, quota setting and allocation, measures and weights)
- Salesforce — Incentive Compensation Management: effective dates and deep audit trails

## Key principles
- A plan needs named decision rights: who sets quota, who approves exceptions, who resolves disputes.
- Measures, weights, thresholds, accelerators and caps are each a separate governed decision.
- Every rule carries an effective date and a version; history is never rewritten.
- Exceptions and disputes are recorded, not handled informally.
- An audit trail is a stored artifact, not a conversation.

## Recommended pattern
Role eligibility -> measure -> quota/target -> allocation -> payout mechanics -> threshold/accelerator/cap -> exception -> approval -> effective-dated version -> audit trail.

## Anti-patterns
- Treating a chat thread or an email as the audit trail.
- Changing a rule without a version and effective date.
- Letting external best practice decide what OUR rule is.

## Project application
Our slab master, decision register and approval fields implement this shape. The decision register carries the open items (target basis, C1-C6, caps, proration, FY).

## Project limitations
**External practice defines HOW to govern a rule. It never defines WHAT our rule is.** Finance/HR/MT Leadership decide; this article only says how to record and apply that decision.

## Related project files
- `incentive_working/incentive_decision_register.csv`
- `config/analytics_config.json`
