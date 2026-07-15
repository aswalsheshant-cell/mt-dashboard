# Growth Engine Build Guide — Executive 4-Page Power BI Dashboard

**Objective:** turn the 0-fail-reconciled May'26 (FY27) offtake build into an
executive dashboard that isolates revenue leakage, tracks modern-trade
execution, and monitors expansion metrics — in one build session.

**Read this first:** this guide *extends* the existing kit — the 18-page spec
in `PageLayouts.md`, the 15-file measure library in `DAX/`, the model spec in
`DataModel.md`, and the theme in `theme/HonasaMT_Theme.json`. It does not
replace any of them. Where a Growth Engine page overlaps an existing page,
this guide says which visuals to reuse rather than respecifying them.

**Honesty contract (applies to every section):** every number named in this
guide is either (a) computed from the committed May'26 build outputs, or
(b) read from a committed seed file, or (c) explicitly marked **[needs
source]** — a leadership figure with no committed data source yet, which must
land in a file/table before it can appear on a visual. Nothing on the
dashboard may show a number that fails either the pipeline's
`Source_To_Model_Reconciliation_Report.csv` (37/37 PASS on May'26) or the
severity gates in `Outlier_Report.csv`.

---

## 1. Business context — what May'26 actually says

From the reconciled build (`agent/pbi_build/FY27_May26/`, 228,280 source rows):

| Fact | Value | Source |
|---|---|---|
| Month NSV (full retention) | ₹4,511.55 L (₹45.1 Cr) | `Source_To_Model_Reconciliation_Report.csv` |
| Month target | ₹38.0052 Cr | `SeedData/Targets/FY2627_Targets.csv` |
| Largest account | Avenue Supermarts ₹1,517.5 L, then Reliance ₹1,493.8 L, Apollo ₹751.2 L | `Pivot_Chain_Category_NSV.csv` |
| Revenue in the blank-site bucket | ₹1,220.13 L = **27.04% of NSV** (9,426 rows) | `Outlier_Report.csv` — severity **High** |
| Unmapped-chain NSV | 0 (8 chains resolved via `ChainAliases.csv`, incl. all Reliance volume) | `Mapping_Exception_Report.csv` |
| Exact duplicate lines removed | 2,466 rows, ₹16.06 L | `Data_Quality_Report.csv` |
| Returns | 11 rows, ≈ −₹0.02 L | `Outlier_Report.csv` — Low |
| Hero-SKU concentration | 13 articles beyond \|z\|>3 within category | `Outlier_Report.csv` — Low |
| Distinct chains / articles | 24 / 529 | reconciliation report |

The single strategic reading: **the business beat its May target (₹45.1 Cr vs
₹38.0 Cr) but 27% of that revenue cannot be steered at store level** — it sits
in the blank-Site-Code bucket. Decomposing that bucket per chain changes the
story materially: **97.8% of it is structural, not broken** — see §1b.

### 1b. Account structural constraints — Reliance & FSN (verified per-row)

| Account | Structure in the May'26 extract | Analytical rule |
|---|---|---|
| **Reliance — Brand Counters** | 24,636 rows, **₹508.18 L**, `Store Type = "Brand Counter"`, ALL with real site codes | **Isolate, never add.** BC sales are already inside the broader zone/state report — adding both double-counts Reliance. Track BC velocity on its own card; exclude from every headline offtake KPI via `Offtake NSV (Adjusted)` (DAX 14§F). |
| **Reliance — zone/state report** | 7,825 rows, **₹985.59 L**, ALL blank Site Code | No store grain **by design** — this extract arrives aggregated. Analyze strictly at **Zone × State** (`Reliance ZoneState NSV`, `Reliance Blank-Site NSV`). Never put Reliance on a store-level visual; blanks there are correct, not defects. |
| **FSN (account "Nykaa")** | 190 rows = **190 distinct EANs** (one row per article), **₹207.87 L**, ALL blank Site Code; Zone/State populated | Purely transactional at SKU grain. Track FSN exceptions strictly at **Article/EAN** level (`FSN Exception NSV`, `FSN Exception Articles`). Zone/State exist and may slice, but store/DC never will. |
| **Everything else blank-site** | 10 small chains, ≈ **₹26.7 L** total | The genuinely **fixable** residual (`Blank-Site NSV (Fixable)`) — this, not ₹1,220 L, is the number to hand the source-system team. |

Consequence for every headline: **`Offtake NSV (Adjusted)` = ₹4,003.37 L
(₹40.03 Cr)** is the double-count-free offtake figure (full-retention
`NSV` ₹4,511.55 L minus the ₹508.18 L BC breakout). Raw `NSV` remains the
reconciliation truth against source and is never modified — the exclusion
lives in measures, never in the data.

Leadership parameters quoted in briefs but with **no committed source yet**
(the dashboard must not display them until the named source lands):

| Parameter | Where it must land first |
|---|---|
| "₹16 Cr baseline" — **RESOLVED 2026-07-14**: it is the monthly **distributor-supplied primary** run-rate, not an offtake target. Verified in the DIST allocation reconciliation (`data.js alloc.recon`): FY27 Apr ₹18.9 Cr + May ₹14.0 Cr, avg ≈ ₹16.4 Cr/month. No conflict with the ₹38.0 Cr offtake target. | already sourced — distributor-converted primary (secondary-based MoM conversion); see also `SeedData/Mapping/DistributorRouted_Articles.csv` for the 23 store-selling SKUs whose sell-in flows only via this route (₹9.0 L Apr+May'26) |
| "19 NPIs" — **RESOLVED 2026-07-13**: derived from the 14-month primary history (rule: first primary appearance in the latest FY = NPI). Data says **32**, not 19 — the briefed count and the derived count differ; `NPI_List.csv` is the editable source of truth. | `SeedData/Masters/NPI_List.csv` (`pbi derive-npi-list`) |
| "~₹10 L incremental monthly NPI business" **[needs source]** | the one-cell `NPI Run Rate Target` table (§5, Page 3) |
| Dark-store flags per account — **RESOLVED 2026-07-13**: business-confirmed none exist in the network. Tracking block intentionally not built (§4). | n/a — reactivation path documented in §4 if dark stores ever launch |
| Chain-wise Market Share (Gross Sales basis), May'26 — **RESOLVED 2026-07-14**: extracted from the leadership deck's slide 4 (MRL/Lulu/Wellness Forever/Reliance Retail), chain names matched via `ChainAliases.csv` (MRL → More Retail, business-confirmed). This is Share-of-Market, not SOA/SOS shelf-visibility — see the honest distinction in §4. | `SeedData/Mapping/ChainMarketShare_May26.csv` |
| SOA / SOS / SOV shelf-visibility numerics **[needs source]** — the deck's "SOS/SOA" slide (20) is 4 store-display **photos** (Sumo Save), not numeric data; no tabular SOA/SOS % exists anywhere in the committed repo yet | `Visibility Tracker` table (§4), format at `templates/Template_Visibility_Tracker.csv` |
| Campaign calendar (TDC shelf tray, Bay Breaker, winter) **[needs source]** | `Visibility Tracker` table (§4) |

---

## 2. Model architecture — the one decision that matters

The 15 `DAX/` files bind to the **Power Query kit model** (`'Fact Offtake
Sales'[Offtake NSV]`, `'Date Table'[MonthStart]`, `Targets[Target NSV]`).
The agent build emits CSVs with different names (`Fact_OfftakeSales[NSV]`,
`Dim_Date`). Importing the CSVs raw breaks every measure. Two valid paths:

**Path A — full kit (use when building the production PBIX):** follow
`QuickSetup/` + `PowerQuery/` as documented; all 15 DAX files and all 18
`PageLayouts.md` pages work natively; keep the agent CSVs as the independent
reconciliation reference (their totals must match the model within 0.5%).

**Path B — fast-start from the agent build (this guide's path):** import the
four CSVs from `agent/pbi_build/FY27_May26/` and rename in Power Query so the
existing measures bind unchanged:

1. **Get Data → Text/CSV**, in this order: `Dim_Date.csv`, `Dim_Chain.csv`,
   `Dim_Article.csv`, `Fact_OfftakeSales.csv`.
   Do **not** import `Fact_Sandbox_SeedMatched.csv` (validation-only subset;
   0 rows on May'26 because the seed article master's EANs are placeholders).
2. In Power Query, rename the fact table **`Fact Offtake Sales`** and its
   columns: `NSV` → `Offtake NSV`, `Sales_Qty` → `Offtake Qty`,
   `MRP_Sales_Value` → `MRP Sales`. Add a `MonthStart` column derived from
   `Month` (`May'26` → 2026-05-01): `Date.FromText("01-" & Text.Replace([Month],"'","-20"))`
   with locale en-IN, or split on `'` and construct with `#date`.
   **Add a `Site Code` column**: the aggregated CSV doesn't carry one, so
   Section-A store measures (`Active Stores`, exact `Store Productivity`)
   need either the kit's store-grain fact (Path A) **or** the per-row source
   CSV — on Path B, load `RawDataFolders/Offtake_Monthly/offtake_store_article_May_26.csv`
   as the fact instead of the aggregated CSV when store-exact numbers are
   required, applying the same renames (its `NSV`/`Sales Qty`/`MRP Sales
   Value`/`Site Code` columns are 1:1). The aggregated CSV's `Store_Count`
   column is only an upper bound when summed — never SUM it across rows.
3. Build **`Date Table`** with `DAX/00_DateTable.dax`; relate
   `Date Table[MonthStart] 1→* Fact Offtake Sales[MonthStart]`.
4. Load `SeedData/Targets/FY2627_Targets.csv` as **`Targets`**; add
   `Target NSV = [Target NSV Cr] * 10^7`; relate on `MonthStart`.
5. Relate `Dim_Chain` (rename **`Chain Master`**) `[Account] 1→*` fact
   `[Chain]`, and `Dim_Article` `[EAN Code] 1→*` fact `[EAN]` — note the fact's
   `Chain` column already carries the mapped *Account* value, and UNMAPPED
   buckets (`UNMAPPED:…`, `(blank)`) intentionally have no dimension row:
   they must stay visible as blanks in slicers, never filtered out.
6. Paste `DAX/00`–`01`, `03` (target measures), `06` (data quality), then
   `14_GrowthEngine_Measures.dax` §A–§C. Skip §D/§E until their gated tables
   exist (§5–§6). Files 02/04/05/07–13 need their own fact tables (P&L,
   Nielsen, TDP, Primary) — add per `DataModel.md` when those pages are built.
7. Apply `theme/HonasaMT_Theme.json` (View → Browse for themes).

Star-schema relationships (all single-direction, 1→*):

```
Date Table[MonthStart]   1 ─→ *  Fact Offtake Sales[MonthStart]
Chain Master[Account]    1 ─→ *  Fact Offtake Sales[Chain]
Dim_Article[EAN Code]    1 ─→ *  Fact Offtake Sales[EAN]
Date Table[MonthStart]   1 ─→ *  Targets[MonthStart]
```

**Why Zone × State, not DC:** in the real May'26 extract `DC Code` is
populated on only 11,251 of 228,280 rows (~5%, D-Mart only). A DC matrix
would silently show one chain. `State` is 100% populated and is now part of
the fact grain — anchor all regional visuals on Zone → State, and expose DC
only as a drill for chains that actually supply it.

---

## 3. Page 1 — Executive Growth Engine

Reuses `PageLayouts.md` Page 1 (Executive Summary) as the base; the Growth
Engine variant swaps the second KPI row and adds the target bridge.

**Slicers:** Month (single-select, default latest), Zone, Brand.

**KPI cards, top row:**
| Card | Measure | May'26 expected |
|---|---|---|
| Total NSV | `NSV` (label `NSV Label`) | ₹45.12 Cr |
| Target Achievement % | `Target Achievement %` (14§B) | ~118.7% vs ₹38.0 Cr |
| YTD Achievement | `YTD Target Achievement %` (14§B) | Apr+May actual vs ₹88.7 Cr YTD target |
| Target Gap | `Target Gap Label` (14§B) | "+7.11 Cr ahead of plan" (45.12 − 38.01) |
| MoM Growth % | `MoM Growth %` (01) | vs Apr'26 |
| YoY Growth % | `YoY Growth %` (01) | needs FY26 history loaded (Path A) — hide the card on a single-month Path B model rather than show blank |
| Leakage % of NSV | `Leakage % of NSV` (14§C) | 27.0% — style red while > 2% |

**Strategic Growth Bridge (waterfall):** Category = `Date Table[Month]`,
Breakdown = Chain (top 8 by `NSV`), Y = `Target Gap Value` (14§B). Reads as:
which accounts put the month ahead of/behind plan. QoQ recovery view: switch
Category to `Date Table[Quarter]` once ≥2 quarters of FY27 data are loaded —
with one month loaded a QoQ vector is not computable and must not be faked.

**Trend combo:** `NSV` (columns) vs `TY Target` (line) by Month — the
plan-vs-actual trajectory. Add `Final Forecast` (03) when the Forecast page's
inputs are loaded.

**Insight box discipline:** only statements traceable to a measure on the
page. May'26 truthful examples: "Month closed ₹45.1 Cr vs ₹38.0 Cr target
(118.7%)." / "₹12.2 Cr (27%) of month NSV has no store attribution — see
Page 4." Never auto-write causal claims ("driven by…") that no measure shows.

---

## 4. Page 2 — Modern Trade & Channel Deep-Dive

Base: `PageLayouts.md` Page 3 (Chain Performance) + Page 8 (Zone & State).

**Slicers:** Month, Zone, Account (Chain Master), Category.

**Main aggregate KPI card:** `Offtake NSV (Adjusted)` (14§F) — **not** raw
`NSV`. This is where the Reliance Brand Counter exclusion is enforced
(May'26: ₹40.03 Cr adjusted vs ₹45.12 Cr full retention). Tooltip must state
"excludes ₹5.08 Cr Reliance Brand Counter breakout — see isolation card".

**Account Matrix (main visual):** Rows = `Chain Master[Account]` → drill to
`Fact[State]`; Columns = `Zone`; Values = `NSV (Lacs)`, `MoM Growth %`,
`Store Productivity (Lacs)` (14§A), `Active Stores` (14§A). Conditional
format `MoM Growth %` (diverging) to make regional growth anchors jump out.
May'26 anchors from the pivot: Avenue Supermarts ₹1,517.5 L (Face-heavy,
₹1,162.1 L), Reliance ₹1,493.8 L raw / **₹985.6 L adjusted** (broadest
category spread), Apollo ₹751.2 L. Reliance rows in this matrix show
zone/state numbers only — its store-level cells are blank **by design**
(§1b), so suppress the "(blank)" store drill for Reliance rather than let
it read as missing data.

**Reliance Brand Counters — isolated tracking (dedicated card + table):**
cards `Reliance BC NSV` (₹508.18 L) and `BC Isolation Check` (must read
"PASS — Brand Counter isolated, zero double-counting"); beneath, a table
Rows = `Zone` → `State`, Values = `Reliance BC NSV`, `Sales Qty`, and
`Active Stores` filtered to `Counter Type = "Brand Counter"` (BC rows are
the one Reliance slice WITH real site codes — 24,636 store-tagged rows —
so BC store velocity is fully computable). This table monitors independent
BC velocity; a visual-level filter `Counter Type = "Brand Counter"` +
`Chain = "Reliance"` keeps it sealed off from every other visual on the page.

**Dark Store Operations — N/A (business-confirmed 2026-07-13):** there are
no dark stores in the network today, so this tracking block is
intentionally NOT built — do not add the slicer, cards, or a placeholder
visual. If dark stores ever launch, reactivate by adding a `Store Format`
column (`Dark Store` / `Standard`) to `SeedData/Masters/ChannelMap_Store.csv`
keyed on `Store Code` and filtering the existing §A measures to it — the
offtake `Store Type` column (Brand/Non-Brand Counter) is *not* a dark-store
flag and must never be proxied as one.

**Chain Market Share (Gross Sales basis) — LIVE, resolved via chain-name
matching:** the leadership deck (`Final MT Offtake May26 Leadership
slide_CORRECTED_V2.pptx`, slide 4) carries a real May'26 Share-of-Market
table for 4 chains. Chain names matched against `ChainMaster.csv` — 3
matched directly (Lulu, Wellness Forever, Reliance Retail), one needed a
new alias (`MRL` → More Retail, business-confirmed). Extracted verbatim
(no numbers invented) to `SeedData/Mapping/ChainMarketShare_May26.csv`:

| Chain | Honasa GS (L) | Total Mkt GS (L) | Share % | MoM (bps) |
|---|---|---|---|---|
| More Retail (MRL) | 59.7 | 2,128.7 | 2.80% | +31 |
| Lulu | 111.5 | 2,848.0 | 3.91% | −21 |
| Wellness Forever | 137.4 | 977.6 | 14.06% | −35 |
| Reliance Retail | 2,052.0 | 19,298.6 | 10.63% | −38 |

Load as a disconnected `Chain Market Share` table; add a card/table on
this page (`Market Share %`, `MoM (bps)`, chain-name resolved through the
same `Chain Master`/`ChainAliases` join everything else uses). **Honest
distinction, do not conflate the two:** this is Share-of-**Market**
(Honasa's Gross Sales ÷ category Gross Sales per chain) — it is NOT
Share-of-**Availability/Shelf** (SOA/SOS). The deck's dedicated
"SOS/SOA – Honasa Portfolio Visibility" slide (20) contains 4 store
**photographs** (Sumo Save shelf displays), not a single numeric SOA/SOS
value — chain-name matching cannot resolve what isn't tabulated. SOA/SOS/SOV
numerics genuinely still need the filled `Visibility Tracker` template below.

**Visibility campaigns vs sales:** the input format the business fills is
now committed at `PowerBI/templates/Template_Visibility_Tracker.csv`
(`Month, Chain, Store Code, Metric ∈ {SOA,SOS,SOV}, Numerator, Denominator,
Campaign` — e.g. SOA numerator = SKUs available, denominator = SKUs listed;
SOS = our facings / total facings; SOV = our media units / category media
units). Until filled sheets land, the honest committed proxies are TDP/ACV
(`05_TDP_Measures.dax`, `PageLayouts.md` Page 10) against `NSV` trend. Once
loaded as `Visibility Tracker`, overlay `SOA %`/`SOS %` (14§E), grade
accounts with `Visibility Grade` (business-confirmed bands: A >50% /
B ≥40% / C ≥30% / D ≥20% / E ≥10% / F below 10%), and use
`Campaign NSV Lift %` sliced by `Campaign` to
attribute spikes (TDC shelf tray, Bay Breaker, winter) to shelf-velocity
change. Campaign ROI is *never* claimed from a sales spike alone — the lift
measure compares campaign months to their own L3M baseline.

---

## 5. Page 3 — Category Dynamics & NPI Tracking

Base: `PageLayouts.md` Page 6 (Brand & Category) + Page 7 (SKU/Article).

**Assortment visuals:** Sub-category decomposition tree (`NSV` by Category →
Sub_Category → Brand); pack-size distribution uses `Dim_Article[Pack Size]`
— fully populated now: article mapping is 100% via the data-derived
`RawDataFolders/Masters/ArticleMaster.csv` (569 EANs consolidated
cross-chain by `derive-article-master`, zero Brand/Category conflicts; a
future production export dropped into the same path replaces it per-file).
SKU velocity: bar of `NSV` by `EAN`, tooltip `Sales Qty`, flag the 13
z-score hero SKUs from `Outlier_Report.csv` (top: 8904417314298 Face
z=9.66) — concentration risk, not an error.

**NPI Accelerator — LIVE (data-derived list):** `pbi derive-npi-list`
generates `SeedData/Masters/NPI_List.csv` from the committed 14-month
primary sell-in history using the business-approved rule *first primary
appearance in the latest FY = NPI*. Current derivation: **32 NPIs**
(FY27 window, from 1,023 articles in history) — note this differs from
the briefed "19"; the CSV is the editable source of truth, prune it if
the business list is narrower. `compile-model` auto-includes the
`NPI List` table and the §D measures (`NPI NSV (Lacs)`,
`NPI Contribution %`, `NPI Count Selling`, `NPI Zero-Sale List`) whenever
the file exists. Still gated: `NPI Run Rate Achievement %` needs the
one-cell `NPI Run Rate Target` table (the quoted ~₹10 L/month has no
committed source — type it into that table to activate).

---

## 6. Page 4 — Revenue Leakage & Exception Diagnostics

This page is the pipeline's exception reports, made executive-visible. Data
source: load `Mapping_Exception_Report.csv` and `Outlier_Report.csv` from the
build folder as disconnected tables (they are per-build diagnostics, not
model facts).

**Leakage Alert Matrix (top-left, the headline):** cards `Blank Site NSV`
(₹1,220.1 L), `Blank Site NSV %` (27.04%), `Leakage Severity` ("High", red),
`Unmapped Chain NSV` (₹0 after aliasing — show it green, it proves the alias
dictionary is working). Beneath: table of `Mapping_Exception_Report.csv`
sorted by `nsv_impact` desc, showing `exception_type`, `value`, `row_count`,
`nsv_impact`, `resolution` — the resolution column already tells the reader
exactly which master file or source-system fix closes each row.

**Ownership framing (put in the page subtitle):** "₹12.2 Cr of May revenue
has no store attribution. ₹11.9 Cr of that is *structural* — Reliance's
zone/state report and FSN's article-grain feed carry no store field by
design. The genuinely fixable residual is **₹26.7 L** across 10 small
chains — that is the number for the source-system team. Every rupee is
still counted in totals."

**Reliance leakage diagnostic matrix (Zone × State):** Rows = `Zone` →
`Fact[State]`, Values = `Reliance Blank-Site NSV` (14§F), row count, and
`% of bucket` (`DIVIDE([Reliance Blank-Site NSV],[Blank Site NSV])`).
May'26 total: ₹985.59 L across 7,825 rows. This is the *correct* grain for
Reliance — the matrix is the analysis, not a workaround; do not add a store
drill here, it will always be empty.

**FSN exception diagnostics table (Article/EAN grain):** Rows =
`Fact[EAN]` (+ `Brand`, `Sub_Category` from the fact's own columns), Values
= `FSN Exception NSV`, `Sales Qty`. May'26: 190 EANs, ₹207.87 L, exactly one
source row per article. Visual-level filter `Chain = "Nykaa"` (the fact
carries the mapped Account name, not the raw "FSN" label). No store or DC
column may appear on this visual.

**Brand Counter isolation validation card:** `BC Isolation Check` (14§F) —
green "PASS — Brand Counter isolated, zero double-counting" when
`Offtake NSV (Adjusted)` + `Reliance BC NSV` rebuilds full-retention `NSV`
to the paisa; red FAIL with the residual otherwise. Place it beside the
leakage cards so the exclusion rule is continuously self-auditing, not a
one-time setup step.

**Price friction & returns:** scatter X = `MRP Sales` Y = `Offtake NSV` by
EAN (points far off the pack = pricing anomalies; the pipeline found 0
qty-without-value rows in May'26 — show the `sales_qty_without_mrp_value`
check as Passed); bar of `Returns NSV` by Chain (`Returns Rows` = 11,
−₹0.02 L — trivially small in May'26; the visual exists so a returns spike
can never hide). Severity chips reuse the pipeline bands via
`Leakage Severity`: Passed / Low / Medium / High / Critical.

---

## 7. Build checklist & sign-off

1. `python -m mtagent pbi run-automated --dax-dir PowerBI/DAX` → all
   automated steps green, reconciliation 0 FAIL.
2. **Automated path (default):** `python -m mtagent pbi compile-model` —
   generates `PowerBI/ModelDefinition.pbip` with the data bindings,
   corrected star schema, and dependency-gated DAX already compiled in
   (65 measures on the real May'26 run, incl. the full §B target and §F
   isolation suites; exclusions itemized in `Model_Compile_Report.json`).
   Step 11 auto-completes with the compile report as evidence. Open the
   .pbip in Power BI Desktop → Refresh → confirm `BC Isolation Check`
   reads PASS — that Desktop open is step 12's verification evidence.
   *Manual path (fallback):* `pbi start-manual-step`, then §2 Path B
   imports/renames and paste DAX 00/01/03/06 + 14§A–C by hand.
3. Either way, `python -m mtagent check-dax` — 0 errors expected from
   file 14 (the known duplicate in 08/09 predates it, and compile-model
   dedupes it automatically).
4. Build pages per §3–§6 in Desktop (report layout is the part that
   stays human). Apply theme. Hide gated visuals' hard errors — gated
   sections show their "awaiting source" caption instead.
6. Validate: every Page-1 card ties to `Source_To_Model_Reconciliation_Report.csv`
   / `Data_Quality_Report.csv` values; `Active Stores` excludes the blank
   bucket (spot-check: filtering Page 2 to a chain with blank-site rows must
   not change `Active Stores` by their count); waterfall sums to
   `Target Gap Value`.
7. Evidence + close: `python -m mtagent pbi mark-complete --step-id
   manual_desktop_actions --evidence-kind screenshot --evidence <path>`.

**Definition of done (the prescriptive test):** a leader reading the four
pages can answer, without asking an analyst: which accounts run efficiently
(Page 2 productivity matrix), exactly how much revenue is trapped in
unassigned buckets and whose fix it is (Page 4, ₹-valued), which NPIs hit
run-rate (Page 3, once the list lands), and whether visibility investment
correlates with shelf velocity (Page 2 overlay, once the tracker lands —
TDP/Nielsen proxy until then).
