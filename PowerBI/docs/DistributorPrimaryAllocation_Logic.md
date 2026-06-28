# Distributor Primary Allocation — Logic Summary & QC (pre-finalization)

Status: **logic + QC shown for sign-off. NOT finalized.** Article-level steps are
**blocked** pending File 2. Do not generate final files until the 1 variance row
below is corrected/confirmed and File 2 + article-level secondary are supplied.

## Inputs — what we have vs need
| File | Purpose | Status |
|---|---|---|
| **File 1** — MoM Distributor Primary + secondary Cont% (`Dist_primary_cont_based_on_secondary_MOM.xlsx`, Sheet1 full feed / Sheet2 distributor subset) | distributor × month × brand × chain primary NSV + secondary-derived `Cont%` | ✅ present (already modelled as `Fact Primary ShipTo` + `Primary Allocation Map`) |
| **File 2** — Distributor Article-wise Primary Billing | primary NSV/Qty by article/EAN per distributor | ❌ **not received** |
| Article-level secondary/offtake | article ratio + new-article (one-month-prior) logic | ❌ not loaded (offtake folder is templates) |

File 1 columns: Ship To Name, Direct/Distributor, Chain, State, Zone, **NSV** (primary),
**MRP value**, Brand, Month, Cont%. **No Article / EAN / Qty / Category columns.**

## Step-by-step logic & feasibility
- **Step 1 — Ratio from secondary:** `Chain Allocation Ratio % = Chain Secondary ÷
  Total Distributor-Brand Secondary` (Month+Distributor+Brand). In File 1 this ratio
  is already maintained as **`Cont%`** (it is "cont based on secondary MoM"). Raw
  secondary values are not in File 1, only the resulting ratio. ✅ usable now.
- **Step 2 — Chain allocation:** `Allocated Primary = Distributor-Brand Primary ×
  Cont%`. ✅ Implemented (`Fact Primary ShipTo[Primary NSV]` already carries the
  per-chain split; `Primary Allocation Map` holds the dynamic Cont%; DAX measure
  `Allocated Primary (via Cont%)`). MRP allocates the same way. **Qty cannot** —
  no Qty column in File 1.
- **Step 3 — Article allocation:** `Article Ratio % = Article Secondary ÷ Chain
  Secondary` (same Dist+Brand+Chain+Month); `Allocated Article Primary = Chain
  Allocated Primary × Article Ratio %`. ⛔ **Blocked** — needs File 2 + article-level
  secondary.
- **Step 4 — New-article one-month-prior:** if an article first appears in secondary
  in month M, maintain it in primary from **M-1**. ⛔ Blocked (needs article-level
  secondary). Note: the model already has a *related* lead/lag measure
  `Ship-to Primary NSV (Active Articles)` (current-or-previous-month offtake) to
  build on once article data lands.
- **Step 5 — Keys:** Primary `Month+Distributor+Brand`; Chain `+Chain`; Article
  `+Article/EAN`. Article key priority: **EAN → Article Code → cleaned Article
  Description**. ✅ defined; article portion pending File 2.
- **Step 6 — Output columns:** Month, Distributor, Chain, Brand, Article Code, EAN,
  Article Desc, Category, Sub-category, Primary Qty, Primary NSV, Primary MRP,
  Secondary Value, Chain Ratio %, Article Ratio %, Allocated Primary Qty/NSV/MRP,
  New Article Flag, Primary Month Maintained, Mapping Status, Remarks.
  → **Available now:** Month, Distributor, Chain, Brand, Primary NSV, Primary MRP,
  Chain Ratio % (Cont%), Allocated Primary NSV/MRP, Mapping Status, Remarks.
  → **Pending File 2:** Article Code/EAN/Desc, Category/Sub-cat, Qty, Article Ratio,
  Allocated Article Primary, New Article Flag, Primary Month Maintained.
- **Step 7 — QC reconciliation:** see below. **Updated by the eligibility gate
  (Step 3.5):** at *chain* level the split still ties to variance 0, but at
  *article* level allocation is offtake-gated, so the rule becomes
  `Original = Allocated + Blocked` (the blocked bucket is reported separately,
  never forced to 100%).
- **Step 8 — Missing data:** secondary missing → "Secondary Missing - Allocation
  Pending"; article mapping missing but chain ratio present → allocate at chain,
  mark "Article Mapping Pending"; inconsistent names → correction sheet
  (Original / Corrected / Remarks).
- **Step 9 — Deliverables:** allocated working file, chain summary, article summary,
  new-article tracker, QC summary, missing-mapping sheet. → **Chain-level (1,2,7,8)
  can be produced now; article-level (3,4) after File 2.**

## QC dry-run result (chain level, File 1)
- Groups (Month+Distributor+Brand): **9,878**; involving a distributor: **818**.
- **Variance = 0 by construction** for every distributor group where ΣCont% = 100%
  (allocated = original primary, since File 1 is already the chain split).
- ❗ **1 group fails** ΣCont% = 100%: **`Dec'25 | R.C. Trade Link H&G | Aqualogica`**
  → ΣCont% = **300%** across 3 chain rows (each ~100%). → **Variance ≠ 0 here.**
  **Action:** correct the Cont% for this distributor-brand-month so the 3 chains
  sum to 100%, then re-run. Per the "do not finalize unless variance is zero" rule,
  the final files are held until this is fixed/confirmed.
- Coverage: 14 months (Apr'25–May'26), 42 distributors, 9 brands, 47 chains.

## Step 3.5 — OFFTAKE ELIGIBILITY GATE (added; validation base = secondary offtake)
Before any Chain × Brand × Article × Month primary is allocated, it must be
**proven by secondary offtake**. This prevents inflating contribution for a
brand/article that the chain does not actually list.

**Eligibility rule** — for primary month **M**, allow allocation only if the same
**Chain × Brand × Article** has secondary offtake in **M** or **M+1**
(M+1 covers distributor→chain billing/offtake TAT; e.g. an article first seen in
offtake in May'26 may legitimately carry primary in Apr'26). If there is no
offtake in M or M+1 → **block, do not allocate** (keep as exception).

**Eligibility Status** (`Eligibility Status` measure):
| Status | Condition |
|---|---|
| `Eligible` | offtake found in same month M |
| `Eligible due to TAT` | offtake found only in next month M+1 |
| `Brand not listed` | chain has **no** offtake for this brand in M or M+1 |
| `Article not listed` | chain has the brand's offtake but **not this article** in M or M+1 |
| `Not Eligible` | no offtake found in M or M+1 |

**Allocation Status** (`Allocation Status` measure): `Allocated` only for eligible
records; otherwise `Blocked - Brand Not Listed` / `Blocked - Article Not Listed` /
`Blocked - No Offtake Evidence`. **Distributor primary is never force-fitted to
unsupported chains/articles to reach 100%.**

**Article ratio is over ELIGIBLE articles only** — `Article Allocation Ratio % =
article secondary (M+M+1) ÷ Σ secondary of *eligible* articles` in that
Chain×Dist×Brand×Month; blocked articles get 0. Where a Chain×Brand has primary
(via Cont%) but **no** eligible article, that chain-allocated primary becomes the
**Blocked** bucket.

### Revised reconciliation (replaces "force variance 0")
Per **Month × Distributor × Brand**:
```
Original Primary  =  Allocated (eligible)  +  Blocked (no offtake evidence)
QC Reconciliation Variance = Original − (Allocated + Blocked)  →  MUST be 0
```
Allocated no longer equals Original by force — the **Blocked** portion is reported
separately. Reconciliation is exact: nothing lost, nothing forced.

### New-article one-month-prior
`New Article Flag` = offtake first appears in M+1 (and M is empty) → primary is
**allowed in M** (held one month prior). `Primary Month Maintained` records that
month. Implemented via `First Offtake Month (CBA)`.

### Required validation columns (output)
Month · Distributor · Ship-to Party Name · Chain · Brand · Article Code · EAN ·
Primary NSV · Primary Qty · **Secondary Offtake NSV (same month)** ·
**Secondary Offtake NSV (next month)** · **First Offtake Month** ·
**Eligibility Status** · **Allocation Status** · **Exception Reason**.

### QC outputs (eligibility-aware)
1. Distributor × Month × Brand **Original Primary** (`QC Orig Primary (Dist-Brand)`)
2. **Allocated Primary** (`QC Allocated Primary Total`)
3. **Blocked / Unallocated Primary** (`QC Blocked Primary Total`)
4. **Variance** (`QC Reconciliation Variance`, must be 0)
5. **Blocked article count** (`QC Blocked Article Count`)
6. **List: Chain × Brand × Article where primary exists but offtake missing**
   (filter `Allocation Status` starts with "Blocked")
7. **List: new articles (first offtake) where primary allowed only one month prior**
   (filter `New Article Flag` ≠ blank)
8. **Final reconciliation separates valid allocation vs exception/unallocated**
   (`QC Mapping Coverage %` + `QC Blocked Coverage %` = 100%)

Measures: `DAX/09_ArticleAllocation_Eligibility.dax`. Eligibility runs against
`Fact Offtake Sales` (present); article primary needs `Fact Primary Article`
(File 2, pending).

## To finalize (what I need from you)
1. **File 2 — Distributor Article-wise Primary Billing** (with Article Code / EAN /
   Article Description / Qty).
2. **Article-level secondary/offtake** (article × chain × distributor × brand ×
   month) for Step 3 ratio and Step 4 new-article logic.
3. Fix/confirm the **R.C. Trade Link H&G / Aqualogica / Dec'25** Cont% (→ sum 100%).
4. Confirm: **Primary Qty** is unavailable in File 1 — should Qty come from File 2,
   or be derived (NSV ÷ ASP)?
