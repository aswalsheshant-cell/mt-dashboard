# Knowledge Base — router and freshness

Compact, sourced articles on **how** to do something correctly. Read the relevant
topic before solving an unfamiliar problem, instead of researching it again.

## The rule that governs everything here

**External knowledge tells us HOW to build and govern something. It never tells us
WHAT our company's rule is.** Target basis, employee grade, incentive policy, payout
rule and ownership mapping come from Finance / HR / MT Leadership. When one of those
is unresolved, return `INTERNAL_BUSINESS_CONFIRMATION_REQUIRED` — never fill the gap
from an external source.

## Router — read only what the task needs

| Task mentions | Read |
|---|---|
| incentive, payout, slab, commission, quota | KA-01, KA-02, KA-03, KA-07, KA-09 |
| employee mapping, identity, hierarchy, alias | KA-04, KA-06, KA-07 |
| target, quota scope, coverage gap | KA-03 |
| target mismatch, why the target does not tie, quota allocation | KA-11 |
| sales credit, store ownership, employee actuals, split credit | KA-12 |
| who decides, policy owner, approval routing, exception governance | KA-13 |
| rule change, effective date, restatement, historical payout | KA-14 |
| can this be calculated, readiness, why is this blocked | KA-15 |
| totals do not tie, control total, unexplained difference | KA-16 |
| Power Query, ingestion, refresh, ETL | KA-05 |
| data model, star schema, many-to-many, grain | KA-06 |
| RLS, row-level security, persona access | KA-06, KA-08 |
| Excel workbook, formula, tracker | KA-09 |
| privacy, public dashboard, publishing | KA-10 |

Loading every article for every task defeats the purpose.

## Escalation order for an unknown problem

1. Internal project documentation (`CLAUDE.md`, `docs/`, `PROJECT_STATE.md`)
2. These knowledge articles
3. Only if absent or stale — authoritative current sources:
   Microsoft Learn / Microsoft Support (Power BI, Power Query, Excel) ·
   official Claude Code documentation · GitHub Docs ·
   WorldatWork or comparable for compensation-governance methodology

Never research a company-specific rule externally.

## Articles

| ID | Topic | Approval required | Review by |
|---|---|---|---|
| KA-01 | Incentive Compensation Governance | Yes — every rule value | 2027-03-11 |
| KA-02 | Incentive Calculation Auditability | Yes — for any published payout | 2027-03-11 |
| KA-03 | Target / Quota Governance | Yes — scope classification | 2027-03-11 |
| KA-04 | Master Data Matching & Approval | Yes — identity/ownership | 2027-03-11 |
| KA-05 | Power Query Data Quality | No | 2027-03-11 |
| KA-06 | Star Schema & Bridge Tables | No | 2027-03-11 |
| KA-07 | Effective-Dated Rules | Yes — historical restatement | 2027-03-11 |
| KA-08 | Secure Incentive Reporting (RLS) | Who may see what | 2027-03-11 |
| KA-09 | Excel Incentive Engineering | No | 2027-03-11 |
| KA-10 | Sensitive Data Boundary | Not negotiable | 2027-03-11 |

## Freshness

| Kind | Cadence |
|---|---|
| Technical product behaviour (KA-05, 06, 08, 09) | 90–180 days |
| Compensation governance methodology (KA-01, 02, 03, 07) | Annual, or on a policy change |
| Project-derived guidance | On architecture change |

`tests/test_knowledge_base.py` fails when an article is past `Review_By`, so staleness
surfaces on its own rather than being noticed too late.

## What is deliberately not here

No confidential project value — no employee name, ID, grade, target or payout. These
articles are methodology. The numbers live in the restricted incentive area.
