# Distributor Primary Allocation — Logic Summary & QC (pre-finalization)

Status: **logic + QC shown for sign-off. NOT finalized.** Article-level steps are
**blocked** pending File 2. Do not generate final files until the 1 variance row
below is corrected/confirmed and File 2 + article-level secondary are supplied.

> **HTML dashboard note (2026-07-03):** this same chain-level, secondary-driven
> allocation method (Distributor Cont% split, Direct rows unambiguous) is now
> also implemented for `dashboard/index.html`'s Primary/P&L/Insights tabs — see
> `apply_chain_allocation()` in `scripts/build_dashboard_data.py` and the
> `--primary-only` refresh mode in `dashboard/README.md`. It reuses
> `Dist_primary_cont_based_on_secondary_MOM.xlsx` directly (chain-level, not
> yet down to article/EAN — that finalization is still tracked below).

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

### QC dry-run result (chain level, File 1) — FY24-25
Same dry-run repeated on `Primary_ShipTo_FY24-25.csv`, one methodological difference
called out below.
- Groups (Month+Ship To Name+Brand): **7,156**; involving a distributor: **626**.
- **Variance = 0 by construction** for every distributor group with a non-zero total
  — but for a different reason than Apr'25–May'26. There, `Cont%` is an
  *independently reported* secondary-derived ratio that can genuinely disagree with
  the primary split (that's what the R.C. Trade Link case above caught). FY24-25's
  source has no separate secondary ratio column at all — `Cont%` here is *derived*
  as `row NSV ÷ group total NSV`, so it reconciles to the input by definition. This
  file cannot surface a Cont%-disagreement anomaly the way the Apr'25–May'26 one
  did; it can only surface zero/offsetting-total groups (below).
- **44 zero-total groups found** (Distributor, Ship-To × Brand × Month, all rows in
  the group sum to ₹0 Lakh — genuinely no sale that month, not a data error): listed
  in full in `SeedData/Mapping/QC_ZeroTotalGroups_FY24-25.csv`. `Cont%` is left
  **blank** for these 51 rows (not fabricated as 0% or split evenly) — same
  no-invented-numbers rule as the R.C. Trade Link fix. No negative-return-miscoded
  case like R.C. Trade Link turned up in this file.
- Coverage: 12 months (Apr'24–Mar'25), 40 distributors, 6 brands, 38 chains.

**FY24-25 coverage added (chain level only):** `PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY24-25.csv`
now supplies the full Apr'24–Mar'25 year at the same Ship-To x Chain x Brand x Month
grain as File 1 (7,883 rows; totals reconcile to the existing FY25 Primary NSV to
within 0.03%). This closes the specific gap `apply_chain_allocation()` in
`scripts/build_dashboard_data.py` names in its own comment ("e.g. FY24-25, which the
allocation file doesn't cover") — for the **dashboard build**, the equivalent rows are
in `PowerBI/SeedData/Mapping/DistPrimary_Sheet1_FY24-25.csv`, built against a real copy
of `Dist_primary_cont_based_on_secondary_MOM.xlsx` (column order, the `Unique` dedup
key, and the `Cont%` convention — blank for Direct rows, not `100` — all match that
file exactly); paste them in as more rows and re-run `--primary-only` to extend
`load_chain_allocation_weights()` to FY24-25.

**Bug found and fixed against that same real file:** `load_chain_allocation_weights()`
hardcoded `sheet_name="Sheet2"`, but the actual `Dist_primary_cont_based_on_secondary_MOM.xlsx`
only has `Sheet1` and `Dist Primary Conv to Chain Art` — no `Sheet2` at all. Running the
function against the real file threw `ValueError: Worksheet named 'Sheet2' not found`,
which would have crashed the entire `--primary-only` build (nothing catches that error
at the call site). Fixed to try `Sheet2` first, then fall back to `Sheet1`, so a rename
either way doesn't break the build. Re-verified against the real file after the fix:
9,282 (ship-to, brand, month) weight keys load successfully, and this file's own
`Cont%` column confirms the existing derivation approach — every Distributor group's
`Cont%` sums to 100.00 within float rounding (max deviation 0.02 across 818 groups).

### FY24-25 Cont% methodology — ship-to total, applied uniformly across brands
Superseding the per-(Ship-To, **Brand**, Month) derivation described in the QC
dry-run above. Confirmed against the real Apr'25–May'26 file that its `Cont%` genuinely
varies by brand within one ship-to/month (e.g. one ship-to's Aqualogica split
4%/32%/22%/42% across 4 chains, while its BBlunt split only 16%/84% across 2, same
month) — that's possible there because FY25-26+ has an *independently reported*
secondary-derived ratio per brand. **FY24-25 has no such independent source.** Per
explicit instruction, FY24-25 Distributor rows now use a **ship-to total ratio,
applied uniformly across every brand at that ship-to/month** instead:
```
Chain Ratio[chain]  =  SUM(NSV, all brands, that chain)  /  SUM(NSV, all brands, all chains)
                       -- per (Ship-To, Month)
New NSV[brand, chain]  =  Brand Total NSV[brand]  x  Chain Ratio[chain]
Cont%[brand, chain]    =  Chain Ratio[chain] x 100   -- same value for every brand
```
Effects, all verified on `DistPrimary_Sheet1_FY24-25.csv`:
- **Row count grew from 1,351 to 2,237** (Distributor rows) — a brand now gets a row
  for every chain the *ship-to* touched that month, not just the chains that brand's
  own original rows happened to list.
- **Per-(Ship-To, Brand, Month) and per-(Ship-To, Month) NSV totals are unchanged**
  (max diff 3e-6, float rounding) — this redistributes *where* a brand's total lands
  across chains, never changes how much of that brand the ship-to billed.
- **Chain-level rollup totals are mathematically identical to the old per-brand
  derivation** — `ChainMapping_Rollup.csv`'s FY25 totals per chain (D-Mart ₹85.30 Cr,
  Reliance Retail ₹64.39 Cr, etc.) don't move at all, because
  `Σ(brand_total × chain_ratio) over brands = chain_ratio × Σ(brand_total) = chain_total`
  by construction. Only the brand × chain split *within* each chain changes.
- **Known artifact, not a bug:** because the ratio now blends every brand's activity
  (including returns/credits) into one ship-to-level number, a brand with a small
  positive total at a ship-to/month where another brand posted a return can come out
  with a **negative `Cont%` or one over 100%** for a specific chain — e.g.
  `Arc Foods And Beverages_Mt_H&G / Aqualogica / Aug'24` shows -4.44% for Apollo
  Healthco and 104.44% for H&G. The two still sum to 100% and the brand's total NSV
  is unchanged; it's the visible cost of not having brand-specific data to keep each
  brand's own sign/shape intact.

**Flag, as requested: FY24-25's Cont% is derived from the primary split itself, not
independently cross-checked.** It can validate zero-total/missing groups (the 44
found above still apply) and confirm every group reconciles to its own input by
construction. It **cannot** catch a *disagreement* between the primary split and an
independent secondary-derived ratio, because no such independent source exists for
FY24-25 — unlike Apr'25–May'26, where that disagreement check is what caught the
R.C. Trade Link error. **FY25-26+ is untouched by any of this** — it keeps its
existing brand-specific, independently reported secondary-derived split as the
source of truth.

> **FY25 article-level distributor billing is not available, therefore chain × article
> view is available only from FY25-26 onward.** Chain-level allocation (above) covers
> FY24-25 in full; article-level does not, and isn't estimated from offtake mix as a
> substitute — that would mix two different measurement bases (billed primary vs.
> sold-through secondary) into one number without a documented, signed-off method, so
> FY24-25 stays at chain/month grain only until a real File 2 extract for that year is
> supplied.

A `Chain Mapping` rollup (`PowerBI/SeedData/Masters/ChainMapping_Rollup.csv`) buckets
the long tail of small/regional chains to "Others", keeping D-Mart, Reliance Retail,
Lulu, More Retail, Apollo Healthco, Wellness Forever, H&G, Sancus, EB2B and CNC as
their own rows. **Metro-CNC-RRL** (₹6.96 Cr FY25 NSV) is mapped to **CNC**, not
Reliance Retail — overriding the existing `CHAIN_ALIASES` entry in
`build_dashboard_data.py`, which currently treats `metro-cnc-rrl` as a Reliance Retail
alias. That alias table is untouched by this change (editing it would silently
reclassify Metro-CNC-RRL dashboard-wide, beyond just this rollup); if the dashboard's
own Primary/Chain views should also show it under CNC rather than Reliance Retail,
that alias needs updating separately as a deliberate follow-up.

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

## File 2 header mapping — LOCKED (query 16)
Confirmed from the File 2 header row (SAP invoice export). No assumptions.

| Canonical (model) | File 2 source header |
|---|---|
| Month / MonthStart | `Month` |
| FY Year | `FY` |
| Ship To Name (distributor) | `Ship To Name` |
| Chain | `Chain name` |
| Brand | `brand` |
| Article Code | `Article Code` |
| EAN Code | `EAN No.` |
| Article Description | `Description` |
| Category | `category` |
| Sub-category | `sub_category` |
| Range | `range` |
| Primary Qty | `Inv Qty` |
| Primary NSV | `Inv. Net value(LOC)` — **CONFIRMED** actual invoice net value (rupees); do **not** use `sale in lac` (Lac/Cr only in reporting measures) |
| Primary MRP | `Total MRP sales` |
| Customer Code | `Cust-SAP Code` (first occurrence) |
| Store Code | `Store Code` |
| Zone / State / Format / Channel | `Zone` / `State` / `Format` / `Channel` |

Article key = EAN → Article Code → cleaned Description. All other invoice columns
(PO no., Inv no./date, tax, plant, addresses, duplicate Customer Name/Cust-SAP,
etc.) are intentionally not loaded. **Direct/Distributor** is not in File 2 — it is
sourced from `Ship-To Master` / File 1 by `Ship To Name`.

## Offtake (store × article) header mapping — LOCKED (query 11)
Confirmed from the store×article offtake header row. No assumptions.

| Canonical (model) | Offtake source header |
|---|---|
| Month / MonthStart | `Month` (`Revised Month` kept as alternate period) |
| FY Year | `Year` |
| Chain | `Chain Name` |
| Zone / State / City | `Zone` / `State` / `City` |
| Store Code / Store Name | `Site Code` / `Site Name` |
| Brand | `Brand` |
| Category / Sub-category / Range | `Category` / `Sub_category` / `Range` |
| Pack Size | `Net Weight` |
| Article Code | `Article` (`Article_1` → `Article Code Alt`) |
| EAN Code | `EAN` |
| Article Description | `Description as per Fountain` (`Chain Article Description` kept) |
| Offtake Qty | `Sales Qty` |
| Offtake NSV | `NSV` |
| MRP Sales | `MRP Sales Value` (`MRP` → `MRP Rate`) |
| Sales Person / SO Emp Code | `SO/ASE Name` / `SO/ASE Emp Code` |
| Store Type / DC Name / Margin / PPT Category | same |

- Article key = **EAN → Article Code → cleaned Description** (identical rule to
  File 2, so the eligibility gate joins Chain × Brand × Article across both).
- Only 1 minor judgement: `Article` → Article Code, `Article_1` → alternate.
  Because EAN is the priority join key, this does not affect eligibility matching.
- **No allocation logic changed** — this only lands the offtake validation base
  that DAX 09 already reads.

## To finalize (what I need from you)
1. **Confirm File 2's actual column headers** (so query 16 `Renamed` mapping is
   exact) — I can't read the `.xlsb` schema here.
2. Load File 2 → `Primary_Article_Monthly\`, and the store×article offtake →
   `Offtake_Monthly\`, then **Refresh** in Power BI Desktop.
3. Keep **`Dec'25 | R.C. Trade Link H&G | Aqualogica`** as an **open exception**
   (Cont% 100% pending source correction) — do not auto-fix.
4. Confirm **Primary Qty** comes from File 2 (it does carry article qty) — used for
   `Allocated Article Primary Qty`.

---

## 2026-07-04 update — article-level DIST allocation from the CONFIRMED headers

File 2's actual headers are now confirmed from the maintained file (ask #1
above is resolved). Two things changed:

**1. Confirmed column mapping (query 16 is locked to these — the real header
row is row 2 of the sheet; row 1 is a reference/annotation row):**
`FY, Month, Channel, Inv. Date, Cust-SAP Code, Ship To Name, EAN No.,
net_content, brand, PPT Category, category, sub_category, range, Description,
MRP (article MRP), Inv Qty, Inv. Net value(LOC), Inv. Tax Amount(LOC),
Total MRP sales, Avg Tot, MTD-Sale type, PO Type, "Chain name for Dashboard"
(one header cell containing a line break), Zone, State`.
**The Direct/Dist. flag lives in `PO Type`** (values `Direct` / `Dist.`) —
NOT in `MTD-Sale type`, which holds `Sales / MRN / Cancel Invoice / FOC`.
When splitting the .xlsb into monthly CSVs, pass `--header-row 1` to
`scripts/split_primary_article_xlsb.py`.

**2. Article-level allocation now happens INSIDE `Fact Primary Article`
(query 16), using `Dist Cont Weights` (query 41, from
`Dist_primary_cont_based_on_secondary_MOM.xlsx`, sheet "Dist Primary Conv to
Chain Art", dropped into `RawDataFolders\`):**
- `PO Type='Dist.'` rows (whose "Chain name for Dashboard" is blank) are
  exploded across chains by the secondary-derived cont%, joined on
  **Ship To Name × Brand × Month** — the cont sheet has NO Cust-SAP Code
  column; the code↔ship-to bridge lives in the primary file itself, and
  Cust-SAP Code is retained through the allocation for the QC tables.
- `Inv Qty / Total MRP sales / NSV / Tax` are scaled by the cont% fraction
  (normalised to sum to exactly 1 per key → totals reconcile to the input by
  construction; raw sums ≠ 100 are flagged via `[Raw Pct Sum]`).
- Article MRP is per-unit and is **not** scaled. `Avg Tot` is a ratio,
  invariant under a proportional split — summed aggregation downstream yields
  exactly the sales-weighted Avg Tot.
- Direct rows keep their own "Chain name for Dashboard". Unmatched Dist. rows
  get **Chain = "Unmapped Chain"** — never blank, never the Ship To Name.
- Verified against the real files (Python mirror of the same logic in
  `scripts/build_dashboard_data.py`): **zero variance** on NSV / Total MRP
  sales / Inv Qty / Tax, overall and by Month and by Brand.

### Nearest-month fallback + patch-proposal workflow (2026-07-04)

Keys with primary billing but no cont-sheet entry for that exact month now
use the **same Ship-To × Brand's split from the nearest month within ±3
months** (still the business's own secondary data, never an invented mix) —
QC-tagged `Mapped (nearest YYYY-MM)`, never silently blended. Rows with no
cont data at all stay `Unmapped Chain`.

Every build regenerates **`SeedData/Mapping/DistCont_Patch_Proposed.csv`** —
one reviewable row per proposed cont-sheet addition (nearest-month copies at
Medium confidence; name-inferred single-chain proposals like Guardian(DL) at
LOW confidence; `<<FILL>>` where business input is required). **Paste the
approved rows into the cont xlsx** to make the fix permanent: the exact-month
match then takes over, the fallback stops firing, and Power BI (query 41,
which reads only the xlsx) picks the fix up too.

### Applied patch log (do not delete — audit trail)

| Patch ID | Date | Rows | What | Where recorded |
|---|---|---|---|---|
| `PATCH-2026-07-04` | 2026-07-04 | 27 | 24 adjacent-month splits (business-approved, Medium confidence) + 3 Guardian(DL) rows → 100% `Guardian Healthcare` (business clarified: Direct chain mis-tagged as Dist. in primary) | Rows tagged `PATCH-2026-07-04\|<ShipTo>\|<Brand>\|<Month>` in the cont xlsx's **Unique code** column; full row detail + approval notes in `SeedData/Mapping/DistCont_Patch_Approved_2026-07-04.csv` |

To find patched rows later: filter the cont sheet's Unique code column on the
patch ID, or diff against the approved CSV. Pending upstream corrections tied
to this patch: (1) Guardian(DL) `PO Type` → `Direct` in the primary file;
(2) review `Guardian Healthcare-Delhi` vs `Guardian Healthcare` — normalise
if the same chain.
