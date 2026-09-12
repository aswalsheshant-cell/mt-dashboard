# `outputs/cm2/` — CM2 expense staging

Staging area for the CM2 expense classification workflow owned by the
`honasa-cm2-expense-classification` skill.

**Nothing in this folder feeds production.** `dashboard/data.js` is untouched by anything
here. The CM2 block in production is still computed by `cm2_block()` from
`PowerBI/SeedData/Masters/PL_Expense_Input.csv`.

## Contents

| File | Status |
|---|---|
| `fact_cm2_expense.schema.csv` | Field contract for the expense fact table. Schema only — the fact table itself is **not** generated until Finance approves the taxonomy, formula and allocation rules. |
| `unknown_expense_heads.csv` | 16 source names/designations observed in the supplied files that have no governed mapping. All `OPEN`. |

## Current release position — 2026-07-24

`config/cm2_formula.csv` carries `Status = DRAFT`, so every CM2 figure must be presented as:

> **CM2 PROVISIONAL — FORMULA APPROVAL PENDING**

Taxonomy inclusion state: **0 rows `INCLUDE`**, 42 `PENDING_APPROVAL`, 5 `EXCLUDE`.
Allocation rules: **1 `APPROVED`** (`ALLOC-000`, the retain-unallocated fallback — no business
judgement required), 6 `DRAFT`, 2 `BLOCKED`.

Because no taxonomy row is `INCLUDE` and only the unallocated fallback is approved, running the
workflow today would classify the full expense universe into visible unallocated buckets and
contribute **zero** to CM2. That is the intended safe state.

## Why production CM2 is currently unreliable

`PL_Expense_Input.csv` holds **3 EXAMPLE rows totalling 47.65 L**, not real data — against
42,373.35 L of NSV, i.e. an implausible 0.1% expense ratio. Real Q1 FY27 expense evidence now
in hand is roughly 30× that:

| Source | Q1 FY27 | Basis |
|---|---|---|
| Indirect claims (base) | 818.45 L | excl-GST, all provisional |
| Field force CTC | 692.94 L | payroll |
| Field force reimbursement | 18.22 L | payroll |
| Field force incentive | 29.81 L | payroll — **subject to a double-count question** |
| *(memo)* claim GST | 122.36 L | excluded from CM2 |
| *(memo)* balance provision | 1,034.01 L | carry-forward, excluded from current period |

None of it is loaded. Loading requires the Finance decisions listed in the checkpoint report.

## Workflow

See `.claude/agents/honasa-cm2-expense-classification.md`. Summary: inventory → detect grain →
duplicate checks → map through taxonomy → unknown heads to register → apply **approved** rules
only → proposed mapping report → **stop for approval** → rebuild → full reconciliation suite.
