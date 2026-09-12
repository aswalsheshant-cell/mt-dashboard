---
name: honasa-cm2-expense-classification
description: |
  Deterministic CM2 expense classification, allocation and reconciliation for the Honasa /
  Mamaearth MT Dashboard. Use this skill for: CM2, expense classification, expense mapping,
  indirect claims, distributor claims, BA salary, supervisor cost, merchandiser cost,
  incentive, reimbursement, visibility or rental spend, trade expense, TOT, scheme or claim,
  COGS, unallocated expense, Brand CM2 mismatch, Chain CM2 mismatch, provisional expense,
  GST treatment, expense allocation, new expense files, unknown expense heads,
  CM2 formula changes.
---

# Honasa MT Dashboard — CM2 Expense Classification & Allocation Skill

## Purpose
Turn raw expense files into a governed, reproducible CM2 expense fact table. Every amount is
classified through an approved taxonomy, separated by accounting status and tax basis,
allocated only by approved drivers, and reconciled by Brand, Chain, Month and expense
category. Unresolved expense stays visible in an unallocated bucket — it is never forced onto
a dimension to make a total tie.

**Called by** `honasa-dashboard-qc-reconciliation` whenever it detects a CM2 or expense
condition (see that skill's *CM2 & expense escalation* section).

## Prime directive
> A CM2 component difference is **not** rounding until the observed difference has been shown
> to be ≤ the **maximum theoretical rounding difference**, computed from line count, decimal
> precision and rounding method. Anything larger is a coverage, mapping, duplication or
> formula defect and must be reclassified.

## Governing configuration (never hard-code business rules)
| File | Role |
|---|---|
| `config/cm2_expense_taxonomy.csv` | Source expense name → normalized head, group, tax basis, accounting status, CM2 inclusion, allocation rule |
| `config/cm2_allocation_rules.csv` | Allocation rule master with driver, residual treatment and APPROVED/DRAFT/RETIRED/BLOCKED status |
| `config/cm2_formula.csv` | Version-controlled CM2 formula, component by component |
| `outputs/cm2/fact_cm2_expense.schema.csv` | Field contract for the expense fact table |
| `outputs/cm2/unknown_expense_heads.csv` | Register of source names absent from the taxonomy |

The skill learns by **updating these configs under approval**, never by silently editing code
for each new file.

## Controlled vocabularies
- `CM2_Inclusion_Status` — `INCLUDE` | `EXCLUDE` | `PENDING_APPROVAL` (never blank, never yes/no)
- `Accounting_Status` — `ACTUAL` | `PROVISIONAL` | `ACCRUED` | `PENDING` | `REJECTED` | `REVERSED`
- `Direct_or_Shared` — `DIRECT` | `SHARED` | `CORPORATE` | `UNMAPPED`
- `Allocation rule Status` — `APPROVED` | `DRAFT` | `RETIRED` | `BLOCKED`

## Expense hierarchy
`PRODUCT COST` · `TRADE EXPENSE` · `FIELD FORCE COST` · `VISIBILITY AND RENTAL` ·
`SHARED OR CORPORATE` · `TAX`

Held separately and never merged: `Claim_Base_Excl_GST`, `GST_Amount`, `Claim_Amount_Incl_GST`,
`Balance_Provision`. CTC, reimbursement and incentive stay three distinct heads.

## Allocation priority
1. Direct source tagging — approved Chain **and** Brand present → book directly.
2. Direct Chain tagging — Chain only → hold at Chain; Brand dimension goes to *Unallocated Brand Expense*.
3. Direct Brand tagging — Brand only → hold at Brand; Chain dimension goes to *Unallocated Chain Expense*.
4. Employee / role assignment — validated employee→Chain or employee→Zone tags.
5. Store-universe driver — active-store or counter count, only for coverage-driven cost.
6. NSV contribution — **only** where explicitly approved per expense head. Never the default.
7. Unallocated bucket — no approved rule → retain in `Unallocated Brand Expense`,
   `Unallocated Chain Expense` or `Shared MT Expense`.

## Exact arithmetic
- Allocate with `decimal.Decimal`, never binary float.
- Compute on unrounded values; round only at display/export.
- On a rounding residual: compute the exact residual, assign it by the rule's
  `Residual_Treatment` (default `LARGEST_REMAINDER_THEN_LOWEST_ID`), record the recipient row,
  then assert allocated total **equals** source total exactly.
- Never absorb a material difference into a rounding adjustment.
- `Expense_Record_ID` = `sha256(Source_File|Source_Sheet|Source_Row|Expense_Head|Period|Amount_Excl_GST_L)[:16]`.
  **Never** Python `hash()` — `PYTHONHASHSEED` randomises it per process and breaks build
  reproducibility (this bug was already fixed once in `detail_records_representative()`).

## Double-count checks (run on every load)
Flag, never auto-delete:
- current-period claim + balance provision counted together
- the same CTC present in more than one employee sheet
- reimbursement present in both the CTC and Expense columns
- incentive present in both payroll and claim files, **or spread across several `Payout` types
  in one sheet** (a live defect in `MT_Spend.xlsx` — see below)
- shared Supervisor cost allocated more than once
- Chain expense loaded directly *and* through an allocation rule
- GST counted in both base and total
- duplicate source rows (exact multiset comparison on the dedup key)
- overlapping versions of the same expense file
- monthly and quarterly totals loaded together

## Reconciliation identities (must hold exactly)
```
Direct Brand Expense + Allocated Brand Expense + Unallocated Brand Expense = Total CM2 Expense
Direct Chain Expense + Allocated Chain Expense + Unallocated Chain Expense = Total CM2 Expense
Amount_Excl_GST + GST_Amount = Amount_Incl_GST         (where all three are present)
sum(Allocated_Amount_L) per source record             = source amount
sum(Allocation_Percentage) per source record          = 1.0
```
A check may PASS only when the **complete** expense universe is represented. An unallocated
bucket that is correctly sized and visible may stand as WARN; it must never be hidden.

## New-file workflow
1. Inventory the file — sheets, columns, grain, period, row count, totals.
2. Detect grain and accounting basis (excl-GST / GST / incl-GST / mixed / unknown).
3. Compare against previously loaded files; check period and row overlap.
4. Run the duplicate checks above.
5. Map every source expense name through the taxonomy.
6. Route unknown names to `Unmapped Expense Head` and append to the unknown-head register.
7. Apply **approved** rules only.
8. Leave `DRAFT` / `BLOCKED` rule rows pending — carried at zero into CM2, never dropped.
9. Produce a proposed mapping report.
10. **Stop for approval.** Do not update production CM2.
11. Rebuild only after written approval.
12. Run the full reconciliation and regression suite.

## Known live defects in the current sources
- **`PL_Expense_Input.csv` holds 3 EXAMPLE rows, not real data** (12.5L Dmart, 28.4L Reliance,
  6.75L Apollo). Production CM2 therefore shows a 0.1% expense ratio. Treat every CM2 figure
  as unreliable until real data replaces these rows.
- **`MT_Spend.xlsx` incentive double-count.** The `Incentive` column is populated across
  several `Payout` values in the same sheet — sheet `BA `: `Salary` rows 14.80L +
  `Incentive` rows 11.13L + `Expense` rows 0.08L = 26.01L naive. Whether these are distinct
  components or the same incentive restated is a Finance question. Do not sum blindly.
- **`MTIndirect_Claim` has no expense-head column** and `Final Status` is blank on all 58 rows
  → every row is `PROVISIONAL`.
- **No distributor→chain crosswalk exists.** Distributor names encode chain hints in free text
  (e.g. `Az Enterprises(Apollo/More)Mt`). Parsing them is prohibited guessing; `ALLOC-008`
  stays `BLOCKED` until a governed crosswalk is supplied.

## Dashboard presentation contract
Separate, individually labelled cards — actual and provisional never blended silently:
`CM2 Actual` · `CM2 Provisional` · `Pending Approval Expense` · `Unallocated Brand Expense` ·
`Unallocated Chain Expense` · `Shared MT Expense` · `Total Expense Excluding GST` ·
`GST Amount` · `Included CM2 Expense` · `Excluded Expense`

Show the active `Formula_Version` and `Rule_Version`. While `config/cm2_formula.csv` carries
`Status = DRAFT`, the dashboard must render:

> **CM2 PROVISIONAL — FORMULA APPROVAL PENDING**

Never present a draft-formula figure as finalized CM2.

## Prohibited actions
- Guessing Chain or Brand from a distributor, employee or article name
- Fuzzy matching as a final resolution
- NSV-share allocation unless approved for that specific expense head
- Combining balance provision with current-period claims
- Deducting GST from net-of-tax NSV
- Deducting TOT again (already netted into NSV upstream by `cm2_block`)
- Forcing allocation to make component totals reconcile
- Auto-deleting duplicate candidates
- Editing raw source files
- Marking a WARN accepted without a named owner and closure criterion
