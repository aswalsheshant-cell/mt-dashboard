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
- ✅ **CLOSED** — the only failing group, **`Dec'25 | R.C. Trade Link H&G |
  Aqualogica`**, was 3 rows all for **one chain (Health & Glow)** — two zero-NSV
  rows + one negative return (−₹10,524.79), each wrongly carrying Cont% 100% →
  ΣCont% 300%. **Corrected:** zero-NSV rows → 0%, return row → 100% (chain total =
  100%; negative return value preserved per the no-delete rule). Logged in
  `SeedData/Mapping/Mapping_Corrections.csv`. **Now 0 distributor groups have
  ΣCont% ≠ 100%** — chain-level variance is 0 across the board.
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

---

## Export-ready QC / exception table specs
> **Status: QC / export tables only.** These are NOT the final allocation output
> and must NOT be merged/finalized until File 2 + article-level secondary offtake
> are loaded and validated. Build each as a Power BI **table visual** (totals off,
> word-wrap off) so it is click-to-export to Excel/CSV. Reconciliation stays
> **Original Primary = Allocated + Blocked, variance 0** — blocked value is NEVER
> pushed into eligible articles.

### Export Table A — "Primary Exists but No Offtake Evidence"
Grain: Month × Distributor × Ship-to × Chain × Brand × Article.
**Filter:** `Allocation Status` starts with "Blocked" (i.e. `Article Eligible = 0`)
— rows where distributor primary exists but the Chain×Brand×Article has no
secondary offtake in M or M+1.

| Column | Source / measure |
|---|---|
| Month | `Date Table[Month]` |
| Distributor | `Ship-To Master[... Distributor]` (Direct/Distributor = Dist.) |
| Ship-to Party Name | `Fact Primary ShipTo[Ship To Name]` |
| Chain | `Chain Master[Chain]` |
| Brand | `Brand Master[Brand]` |
| Article Code | `Article Master[Article Code]` |
| EAN | `Article Master[EAN Code]` |
| Article Description | `Article Master[Article Description]` |
| Primary NSV | `Chain Allocated Primary NSV` |
| Primary Qty | `SUM('Fact Primary Article'[Primary Qty])` *(File 2)* |
| Secondary Offtake NSV Same Month | `Offtake NSV (CBA, M)` |
| Secondary Offtake NSV Next Month | `Offtake NSV (CBA, M+1)` |
| Eligibility Status | `Eligibility Status` |
| Allocation Status | `Allocation Status` |
| Exception Reason | `Exception Reason` |

Purpose: the QC "list 6" — every Chain×Brand×Article carrying primary with **no
offtake evidence**, so the team can confirm whether the article is genuinely not
listed in that chain (block) or an offtake-data gap (fix), before finalizing.

### Export Table B — "New Article Tracker"
Grain: Chain × Brand × Article.
**Filter:** `New Article Flag` ≠ blank — articles whose **first offtake** appears in
M+1, so primary is allowed **one month prior** (M).

| Column | Source / measure |
|---|---|
| Chain | `Chain Master[Chain]` |
| Brand | `Brand Master[Brand]` |
| Article Code | `Article Master[Article Code]` |
| EAN | `Article Master[EAN Code]` |
| Article Description | `Article Master[Article Description]` |
| First Offtake Month | `First Offtake Month (CBA)` (format `mmm'yy`) |
| Allowed Primary Month | `Primary Month Maintained` (= First Offtake Month − 1) |
| First Offtake NSV | `CALCULATE([Total Offtake NSV], 'Date Table'[MonthStart] = [First Offtake Month (CBA)])` |
| Primary NSV in Allowed Month | `CALCULATE([Chain Allocated Primary NSV], 'Date Table'[MonthStart] = Allowed Primary Month)` |
| Eligibility Status | `Eligibility Status` (= "Eligible due to TAT") |
| Remarks | `New Article Flag` text ("New Article - primary held 1 month prior") |

Purpose: the QC "list 7" — auditable record of the one-month-prior rule (which
article, where first seen, and the prior month its primary is permitted in).

### Export Table C — "Allocation QC Summary"
Grain: Month × Distributor × Brand (add Chain as an optional drill row).

| Column | Measure |
|---|---|
| Month | `Date Table[Month]` |
| Distributor | Ship-to (Dist.) |
| Brand | `Brand Master[Brand]` |
| Original Primary NSV | `QC Orig Primary (Dist-Brand)` |
| Allocated Primary NSV | `QC Allocated Primary Total` |
| Blocked Primary NSV | `QC Blocked Primary Total` |
| Variance | `QC Reconciliation Variance` *(must = 0)* |
| Coverage % | `QC Mapping Coverage %` |
| Blocked % | `QC Blocked Coverage %` |
| Blocked Article Count | `QC Blocked Article Count` |

Reconciliation identity enforced: **Original = Allocated + Blocked**,
`Variance = 0`, `Coverage % + Blocked % = 100%`. Conditional-format `Variance` red
when ≠ 0. All three tables are **QC/export only** until File 2 + article-level
offtake arrive and are signed off.

## Input files located (Google Drive `…/P&L DATA`)
| Role | File | Size | Maps to |
|---|---|---|---|
| **File 2 — article-wise primary** | `MT, Eb2B & SIS primary April_23 to May_26.xlsb` | ~175 MB | `Fact Primary Article` (query 16) → folder `Primary_Article_Monthly` |
| **Article-level secondary (store×article)** | `FY-24-26 Chain offtake Store Wise File till May.xlsb` | ~185 MB | `Fact Offtake Sales` (query 11) → folder `Offtake_Monthly` |
| Offtake (compiled) | `May Chain Offtake Compiled Data.xlsx` | ~140 MB | optional cross-check |
| Offtake (zone/state) | `FY-2024-26 Updated Zone & State wise offtake file.xlsx` | ~83 MB | zone/state validation |
| Offtake (zone) | `FY-2024-26 Updated Zone Wise Offtake File (4).xlsx` | ~20 MB | zone validation |

### Where the live reconciliation runs (important constraint)
These files are **140–185 MB**. The numeric live validation (variance, coverage %,
blocked list) must run in **Power BI Desktop on a real machine** via the folder
refresh — it cannot be ingested in a lightweight/cloud sandbox, and `.xlsb` is not
readable by text connectors. The model + DAX 09 are built to produce the three QC
tables automatically on refresh. **To get the live numbers from me directly,**
share a **trimmed extract** (e.g. one month — May'26 — or one distributor, as CSV
with: Month, Distributor/Ship-to, Chain, Brand, Article Code, EAN, Article Desc,
Primary NSV, Primary Qty for File 2; and Month, Chain, Brand, Article Code, EAN,
Offtake NSV for the article-level offtake). I will run the full reconciliation on
the sample and confirm `Original = Allocated + Blocked, variance 0` before anything
is finalized.


### Drive-route status (cloud session) — BLOCKED, use local route
- The session's egress proxy **denies Google Drive (403 policy denial)** for direct
  download, and the Drive MCP returns the whole ~175 MB `.xlsb` inline (infeasible)
  and cannot text-read `.xlsb`. So File 2 **cannot be read or split inside the
  cloud session.** Headers are therefore **not assumed**.
- Local route (where the file lives): run
  `scripts/split_primary_article_xlsb.py` — it prints the exact header row and
  writes month-wise CSVs (`primary_article_<MON><YY>.csv`) into
  `RawDataFolders/Primary_Article_Monthly/`. Paste the printed header line back
  to lock the query-16 `RenameColumns` mapping with zero guessing.

## To finalize (what I need from you)
1. **Confirm File 2's actual column headers** (so query 16 `Renamed` mapping is
   exact) — I can't read the `.xlsb` schema here.
2. Load File 2 → `Primary_Article_Monthly\`, and the store×article offtake →
   `Offtake_Monthly\`, then **Refresh** in Power BI Desktop.
3. Keep **`Dec'25 | R.C. Trade Link H&G | Aqualogica`** as an **open exception**
   (Cont% 100% pending source correction) — do not auto-fix.
4. Confirm **Primary Qty** comes from File 2 (it does carry article qty) — used for
   `Allocated Article Primary Qty`.
