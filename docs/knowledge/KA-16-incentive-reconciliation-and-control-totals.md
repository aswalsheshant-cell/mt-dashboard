# KA-16 — Incentive Reconciliation & Control Totals

| Field | Value |
|---|---|
| Topic_ID | KA-16 |
| Purpose | Prove that every stage of the incentive cycle still ties to its source, and expose what does not. |
| Applicable_Agents | sales-data-reconciliation, fmcg-decision-leader, business-ai-automation |
| Trigger_Conditions | totals do not tie, reconciliation, control total, finance check, unexplained difference |
| Source_Type | Recognised industry body (compensation governance) |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | No — method; the approval files it reconciles to are business-owned |
| Confidence | HIGH |

## Authoritative sources
- WorldatWork — governance and operations: reconciliation and exception handling are core
  compensation controls, not a finance afterthought.
- Salesforce (Spiff) — retained version history across quotas, assignments, approvals and
  adjustments supports stage-by-stage reconciliation.

## Key principles
- Reconcile at **every** stage, not only at the end. A single end-to-end check tells you
  something broke, not where.
- **Every control total must expose an unexplained difference explicitly**, even when it is
  zero. A reconciliation with no residual line is not a reconciliation.
- Reconcile within a grain. Adding figures across grains (roles, chains, planning levels)
  manufactures a difference that was never there.
- A residual is a finding to investigate, never a plug to write off.

## Recommended pattern — the control chain

| Stage | Ties to |
|---|---|
| Raw actual | attributed + pending + ambiguous + missing-population + out-of-coverage |
| Source target | normalised target (normalisation must not move the total) |
| Employee target allocation | source target, where scope supports it |
| Achievement population | eligible population |
| Calculated incentive | its parameter components |
| Final incentive | gross ± approved adjustment |
| Approved incentive | Finance approval file |
| Paid incentive | payment reference |

Assert the total is unchanged after any cleaning step. If canonicalisation changes a total,
the canonicalisation is wrong.

## Anti-patterns
- "Rounding difference" as an explanation for a material residual.
- Reconciling only the rows that mapped.
- Summing role-level credit into a company total (see KA-12).
- Silently excluding unmapped records so the check passes.

## Project application
- Target: file total asserted identical before and after canonicalisation; the
  Rs 10,146.78 L gap to the business target is decomposed, with Rs 2,456.83 L (24%)
  reported as unexplained rather than absorbed (KA-11).
- Actuals: all four role lines reconcile to Rs 14,118.82 L with a **zero** difference, with
  out-of-coverage value reported separately by population.
- Workbook: `11_Data_Quality` carries the counts; `10_Summary` carries no payout figure.

## Project limitations
Stages from "calculated incentive" downward cannot be reconciled yet — nothing is
calculated, and no Finance approval file exists.

## Related project files
- `scripts/target_scope_diagnostic.py`
- `scripts/build_actual_attribution.py`
- `incentive_working/actual_attribution_reconciliation.csv`
