# Metric Registry

**Created:** 2026-09-13, in response to a request for a governed measure catalog —
"a visual cannot invent a KPI; it must consume a registered measure." This is new
governance, not a restatement: no such registry existed before this file, and the
gap it closes is real — the same number (e.g. Primary NSV) is currently computed by
several different `index.html` functions independently rather than reading one
shared value, which is exactly the drift risk this registry exists to catch.

**Scope of this pass:** the headline measures actually computed today, sourced from
`scripts/build_dashboard_data.py`'s block functions and `dashboard/index.html`'s
render functions — not a hypothetical full catalog. Add a row whenever a new KPI
is introduced; do not backfill hypothetical future measures.

**The rule going forward:** before adding a new number to any dashboard card, chart
or table, check this file first. If an equivalent measure is already registered,
reuse its formula and source — do not recompute it independently in a new function.
If it's genuinely new, add a row here in the same commit that adds the visual.

| Measure_ID | Business Question | Formula | Grain | Fact Source | FY Logic | Comparable Across | UI Location(s) | Status |
|---|---|---|---|---|---|---|---|---|
| `PRIMARY_NSV` | What did Honasa bill? | SUM(`Inv. Net value(LOC)`) net of MRN/Cancel, /1e5 for Lakh | Month x Chain x Article (FY27+); Month x Chain (FY25/26 pre-agg) | `primary_block()` (FY25/26), `detail_records_real()` -> `detail_meta.fyx_primary` (FY27+) | THE ONE FY RULE, `fy_tag_from_ym()` | FY26 full year; FY27 Apr-Aug so far (Aug'26 ingested 2026-09-13) | Channel & Chain Performance > Primary Sales; Executive Cockpit; Performance & Comparison | LOCKED (BL-01/BL-14) |
| `OFFTAKE_NSV` | What did the customer sell (chain POS)? | SUM of monthly chain-store-article extracts, Reliance Brand Counter isolated (Store Type, not Chain Name, for Apr-Jun'26) | Month x Chain x Article | `offtake_block()` / `offtake_rebuild_block()` | THE ONE FY RULE | FY26 full year; FY27 Apr-Aug | Inventory & Supply Health > Offtake Velocity; Performance & Comparison | LOCKED (BL-07/BL-08) |
| `SECONDARY_NSV_FY25` | What did distributors bill to retailers, Apr'24-Mar'25 (the only real FY25 series)? | SUM(NSV) from the FY25 distributor secondary extract | Month x Chain x Brand | `load_fy25_secondary()` -> `offtake.secondary_*` / `offtake.by_chain[].secondary_fy25` | THE ONE FY RULE | FY25 only — **never compared to FY26/27 Primary or Offtake as if the same measure** | Performance & Comparison > FY25 Distributor Secondary section, Unified Sales Trend (dashed) | AVAILABLE, explicitly disclosed as a different measure |
| `PRIMARY_OFFTAKE_GAP` | Where does Primary diverge from Offtake, and is that comparison even valid? | `Primary NSV - Offtake NSV`, computed only where both series exist for the same period/chain; matched/primary-only/offtake-only chains kept separate, never blended into one ratio | Month; Chain (matched universe only) | `primary_offtake_gap_block()` | Per-FY, gated on `by_channel` scope match (FY26 clean; FY27 flagged NOT_FULLY_COMPARABLE, EB2B/SIS ~5.2%) | FY26 (clean); FY27 YTD (flagged) | Performance & Comparison > Primary-Offtake Gap | LOCKED, comparability status is part of the output, not assumed |
| `CM2` | What's the trade-adjusted contribution margin? | `NSV - SUM(approved P&L expense rows)`; template/example rows explicitly filtered out (see FM-01) | Month x Chain x Brand x Category x Expense Head | `cm2_block()`, reading `PowerBI/SeedData/Masters/PL_Expense_Input.csv` | THE ONE FY RULE | Whatever period has real (non-template) expense rows loaded — currently NONE, so `cm2.has_expense_data = false` and CM2 = NSV | P&L tab | Methodology `VALIDATED` (mechanism correct); Data `NOT LOADED` (only template rows exist) — **do not read the current CM2% as real margin** |
| `CM2_PROVISIONAL_COGS_LOGISTICS` (BL-16) | What would CM2 be with a COGS/logistics rate-card layer applied? | `NSV - (COGS% x GMV/MRP) - (Logistics% x NSV)`, rate card real (business-supplied screenshot, 2026-07-24) but self-certified "approved" stamp rejected on evidence | Month (rate-card grain only — no chain/brand split exists for the rate itself) | `PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv` + `recovered_governance_20260724/` (D1-D11 decision register) | N/A (FY27 rate card only) | Not comparable to `CM2` above — different, wider expense scope | Not wired into any dashboard block (staged only, per its own commit) | `CLOSED_PROVISIONAL` technical / `PENDING_APPROVAL` Finance (BL-16) |
| `TOT_PCT` | What % of MRP is passed on as on-invoice trade margin? | `SUM(Pass-on Value) / SUM(MRP)`, source priority: `Avg Tot` column -> computed from `Inv. Tax Amount(LOC)` -> GST rate-table fallback (last resort) | Month x Chain x Article | `tot_block()` | THE ONE FY RULE | FY26-FY27 article-level detail | P&L tab > Chain-wise TOT% | LOCKED (source-priority order is the governed rule, not the fallback) |
| `PVM_BUCKETS` (Price-Volume-Mix) | How much of a NSV delta is price vs. volume vs. mix? | Standard PVM decomposition at article grain, bucketed so Price+Volume+Mix reconciles exactly to the total delta (0.00 variance tested) | Article, rolled to Chain/Category | `pvm_block()` | Same-period basis (`same_period_block()`) | Wherever a like-for-like same-period window exists | Performance & Comparison / drill-through | LOCKED, reconciliation-tested |
| `TARGET_ACHIEVEMENT_PCT` | Are we on track against the FY27 target? | `Actuals(PTD) / Target(PTD) x 100`, PTD window derived from which months actually have actuals, never assumed | Month x Zone x Chain, rolled to FY | `targets_block()` | THE ONE FY RULE, period-to-date derived from `same_period` | FY27 vs its own target only | Executive Cockpit; Zone/Chain Scorecard | LOCKED; basis (Primary vs Offtake) is a documented open **ASSUMPTION** (offtake), not yet business-confirmed — see `docs/PROJECT_STATE.md` |
| `MAPPING_COMPLETENESS_PCT` | How much of chain-level Primary is on a governed, evidence-based chain mapping rather than a raw/unmapped string? | `matched NSV / total NSV`, matched = has a real secondary-cont%-evidenced or governed alias | Month x Distributor | `mapping_health_block()` | Wherever Direct/Dist. allocation runs | Zone/Chain Scorecard warning banner | LOCKED; the dashboard already shows "chain-level Primary reporting: not yet reliable" below the 85% governance threshold |
| `SIS_RECONCILIATION` | Which of the 3 historical reference figures for Primary SIS FY26 is correct, and what does the audit trail show? | Per-FY: `total_sis_sales` (Sales-type rows) + `mrn_returns` (negative) + `cancelled_invoices` = `net_sis_value`; plus by-chain/by-month/by-brand breakdown from the FULL uncapped source | Month x Chain x Brand, rolled to FY | `_sis_reconciliation()` -> `detail_meta.sis_reconciliation` / `detail_meta.sis_gap_status` | THE ONE FY RULE | FY26 (resolved), FY27 (in progress, Apr-Aug so far) | Data Explorer > "SIS Reconciliation — audit trail" (added PR #155, Phase 1) | RESOLVED (2026-07-03): Rs 250.17 L confirmed correct for FY26; Rs 236 L and Rs 275.44 L (gross) confirmed NOT correct |
| `ARTICLE_ELIGIBILITY_TIER` | Which Dist. rows are eligible for chain allocation, and on what evidence tier? | Per row: `Eligible` (secondary match) / `Eligible_TAT` (match within tolerance window) / `Not_Eligible` / `Brand_Not_Listed` / `Article_Not_Listed`, each with a `eligibility_confidence_pct` | Customer x Article x Month (row-level) | `allocate_dist_primary()` -> `alloc.governance.{eligibility_tier_counts, not_eligible_nsv_lakh, not_eligible_pct}` | Wherever Dist. allocation runs | Wherever Direct/Dist. allocation runs | Channel & Chain Performance > Primary Sales, "Methodology & Data Quality" details block | LOCKED; gated by `_check_governance_gate()` (release gate on `not_eligible_pct`) |
| `PROMO_INTENSITY` | How many promotions ran, at what average depth, per chain? | `n_promos` (count), `avg_depth` (mean discount %, displayed as `promo_depth`), `chains_in_promo`, `brands_in_promo`; correlated against sell-through (Pearson) | Month x Chain x Brand | `promo_block()` -> `data.promo` | THE ONE FY RULE | Wherever the promo source file covers | Demand & S&OP Planning > Promotional Impact | AVAILABLE for depth/intensity; spend/uplift/ROI sub-measures are **not computed anywhere** (no real source — see "Known Source Gaps" below, do not confuse with a missing-HTML gap) |

## What this registry deliberately does not cover yet

The proposed architecture describes a much larger set of measures (Assortment
Opportunity Score, Promotion ROI, Nielsen market-share deltas, TDP distribution,
Forecast QC/coverage, Forecast scenario bands). None of those are currently computed
anywhere in this codebase — they are not omitted from this table by oversight, they
simply don't exist as production measures yet. Adding a row for a measure that isn't
computed would misrepresent the registry as more complete than the dashboard actually
is. See "Known Source Gaps" below for the evidence behind each one (Phase 2, 2026-09-18) —
they are not all the same kind of gap: Nielsen/TDP/Promo-ROI need a new registered
source; Forecast QC needs new transformation logic against an already-registered source.

## Duplicate-KPI check performed while building this registry

Grepped `dashboard/index.html` for independent recomputation of the same headline
numbers (the concrete risk this registry exists to prevent). Found: Primary NSV and
Offtake NSV are each read from a single source block (`D.primary`, `D.offtake`)
everywhere checked — no second independent calculation of either was found in this
pass. This is a spot-check, not an exhaustive audit of every one of the dashboard's
inline calculations; treat "no duplicate found this pass" as encouraging, not as
proof none exists.

## Source-of-Truth, Power BI Parity & Drift Classification (Phase 2 — 2026-09-18)

**Purpose:** before building a Data Quality engine or an insight layer on top of
these measures, this section answers "is there one agreed definition, or have
Python / HTML / Power BI quietly drifted into three?" — for every measure above.
This section changes no calculation and adds no new computed field; it is a
lineage/parity map only.

**Method:** for each Measure_ID, checked (a) whether `config/data_source_registry.yml`
already registers the underlying raw dataset (it registers datasets, not computed
metrics — a metric can be real without a registry entry if it's derived entirely
inside `build_dashboard_data.py` from an already-registered dataset), (b) whether a
Power BI DAX/PQ file defines the same measure, and (c) whether that DAX file has ever
been executed against real data. **No `.pbix` exists in this repo and no Power BI
Desktop instance is reachable from this environment** — every "Power BI" cell below
therefore reports what the DAX/PQ *text* defines, never a validated computed value.
That is why no measure below is classified as PowerBI-side `MATCH`: MATCH would
require comparing two actually-computed numbers, and only one side is ever computed.

Drift classification key: `MATCH` (Python and HTML both compute and display the same
number from the same source), `PARTIAL` (Python/HTML agree; a Power BI DAX file
defines the same measure in text but has never been executed/validated, so equality
is unverified, not contradicted), `POWER_BI_ONLY` (a DAX measure exists for something
Python never computes, usually because the source itself doesn't exist), `SOURCE_UNAVAILABLE`
(no real source anywhere for either side).

| Measure_ID | Source-of-Truth Dataset (`data_source_registry.yml`) | Power BI Implementation | Power BI Validation Status | Drift Classification | Data-Quality Dependency |
|---|---|---|---|---|---|
| `PRIMARY_NSV` | `primary_article_monthly`, `primary_aug26_adhoc` | `01_CoreMeasures.dax` (`Total Primary NSV`) | Unexecuted (no `.pbix`) | PARTIAL | Depends on `chain_allocation_tool` mapping completeness (see `MAPPING_COMPLETENESS_PCT`) |
| `OFFTAKE_NSV` | `offtake_preagg_fy25_fy26`, `offtake_article_fy27_patch` | `01_CoreMeasures.dax` (`Total Offtake NSV`) | Unexecuted | PARTIAL | RBC (Reliance Brand Counter) isolation correctness — BL-07 |
| `SECONDARY_NSV_FY25` | `fy25_secondary_chain_brand_detail` | `14_SecondarySales_Measures.dax` | Unexecuted | PARTIAL | FY25-only; must never be diffed against FY26/27 Primary/Offtake as if comparable |
| `PRIMARY_OFFTAKE_GAP` | (derived from the two datasets above, no separate registry entry) | Not present as a named DAX measure (Page 2's "Primary vs Offtake Gap" visual references `[Primary vs Offtake Gap]` in `01_CoreMeasures.dax`, but that DAX subtracts the *raw* Primary/Offtake totals — it does not implement the matched/comparable-universe restriction the Python `primary_offtake_gap_block()` applies) | Unexecuted | **DIFFERENT** — documented, not silently resolved: Python restricts the comparison to a matched chain/period universe and flags FY27 `NOT_FULLY_COMPARABLE`; the DAX measure does not | Comparability-scope logic (Python-only; not ported) |
| `CM2` | `cm2_pl_expense_input` (currently template rows only) | `13_CM2_Measures.dax` | Unexecuted | PARTIAL (mechanism); both sides currently return CM2≈NSV since no real expense rows are loaded | `Total Expense Amount Loaded = 0` — see existing "No-expense-data note" in `PageLayouts.md` |
| `CM2_PROVISIONAL_COGS_LOGISTICS` | Not in `data_source_registry.yml` (staged, not wired) | Not present in `PowerBI/DAX/` — this is a standalone reference calc, not part of the DAX build kit | N/A | POWER_BI_ONLY does not apply; this is Python-only, unwired | `PENDING_APPROVAL` (BL-16) — do not treat as CM2 |
| `TOT_PCT` | `primary_article_monthly` | `12_TOT_Measures.dax` | Unexecuted | PARTIAL | GST fallback-rate rows require Finance sign-off (`GST Rate QC Table`, `Finance_Approved` column) |
| `PVM_BUCKETS` | (derived, no separate dataset) | Not present as a named DAX measure anywhere in `PowerBI/DAX/` | N/A | PYTHON_ONLY | Same-period window definition (`same_period_block()`) |
| `TARGET_ACHIEVEMENT_PCT` | Target file registered informally via `targets_block()`'s `source` field (`PowerBI/SeedData/Targets/FY2627_Targets.csv`) — **not yet a `data_source_registry.yml` entry**, a real gap this pass found | `03_Forecast_Measures.dax` | Unexecuted | PARTIAL | Basis (Primary vs Offtake) is an open, undocumented-as-business-approved ASSUMPTION per `docs/PROJECT_STATE.md` |
| `MAPPING_COMPLETENESS_PCT` | `chain_allocation_tool` | Not present as a named DAX measure | N/A | PYTHON_ONLY | Governs the 85% threshold banner — threshold itself is a UI constant in `index.html`, not in `config/baselines.json` (found this pass; flagged, not changed) |
| `SIS_RECONCILIATION` | Derived from `primary_article_monthly` (`_Chan == "SIS"` slice), no separate registry entry | `10_SIS_Reconciliation.dax` | Unexecuted | PARTIAL | None outstanding — status is RESOLVED per the business confirmation logged in the measure's own field |
| `ARTICLE_ELIGIBILITY_TIER` | `chain_allocation_tool` | `09_ArticleAllocation_Eligibility.dax` | Unexecuted | PARTIAL — **HTML is more detailed than the DAX file** (adds `eligibility_confidence_pct` and override tracking not in the DAX version) | `_check_governance_gate()` release gate |
| `PROMO_INTENSITY` | `promotions_offtake_correlation` | `15_Promo_Measures.dax` | Unexecuted | PARTIAL for depth/intensity; **POWER_BI_ONLY** for the DAX file's spend/uplift/ROI measures (no real source for those anywhere) | See "Known Source Gaps" below |

**Drift summary (13 measures classified):** 11 PARTIAL (Python+HTML agree; Power BI
DAX text unexecuted, so equality can't be confirmed either way), 1 DIFFERENT
(`PRIMARY_OFFTAKE_GAP` — Python's comparability-scope restriction is not ported to
the DAX measure; **not fixed here**, per this phase's scope), 2 PYTHON_ONLY
(`PVM_BUCKETS`, `MAPPING_COMPLETENESS_PCT` — no corresponding DAX measure exists at
all, which is not a defect, just an unported measure), 1 POWER_BI_ONLY sub-case
(Promo spend/ROI). Zero measures found where Python and HTML themselves disagree —
the drift risk this registry exists to catch has not materialized between those two.

## Known Source Gaps (Phase 2 classification — distinct from a missing-HTML-render gap)

These are cases where a Power BI page/DAX file describes a measure that **no real
source file registers anywhere in this repo** — confirmed by grep, not assumed.
Per CLAUDE.md's "No dummy data" rule, the correct response is registering a real
source (see CLAUDE.md's "New data source checklist"), never fabricating a number
for either HTML or Power BI.

| Measure | Power BI reference | Evidence checked | Classification |
|---|---|---|---|
| Nielsen Market Share | `04_Nielsen_Measures.dax`, PageLayouts.md Page 9 | Zero occurrences of "Nielsen" in `scripts/build_dashboard_data.py` or `docs/DATA_AVAILABILITY_MATRIX.md`; `index.html`'s `market-share` sub-view is explicitly built empty, with an in-code comment recording that a prior version's fabricated competitor shares were removed | **C — metric definition exists, source does not** |
| TDP Distribution | `05_TDP_Measures.dax`, PageLayouts.md Page 10 | Zero occurrences of "TDP" in `scripts/build_dashboard_data.py`; zero in `index.html`; CLAUDE.md's claim that "Performance & Comparison" covers Page 10/TDP does not match what that tab actually renders (NSV YoY comparisons only) | **C — metric definition exists, source does not** |
| Forecast QC (`QC Tie-Out`, `QC Mapping Coverage %`, `QC SO Coverage %`, `QC Unmapped SO Stores`) | `08_ForecastQC_Measures.dax`, PageLayouts.md Page 5 | `targets_block()` (the real forecast computation) produces achievement/run-rate/DERIVED zone-chain splits only — no Sales-Person-to-Store ownership join, no coverage counters, anywhere in `build_dashboard_data.py`. `Store_SO_Mapping.csv` is a real, registered file (`config/data_source_registry.yml`), but nothing currently joins it against the forecast for QC purposes | **D — source data exists (`Store_SO_Mapping.csv`), the transformation/join does not** (different from Nielsen/TDP: this one doesn't need a new source, it needs new Python logic — out of scope for this phase) |
| Promo spend / uplift / ROI | `15_Promo_Measures.dax` | `promo_block()` computes depth/intensity/correlation only; `index.html`'s own code comment records that a prior version's fabricated 4-campaign spend/uplift/ROI numbers were removed | **C — metric definition exists, source does not** |

## Cross-references

- `config/data_source_registry.yml` — dataset-level lineage (source path, grain, date
  range, `validation_status`, `source_priority`). This registry is metric-level and
  points to it rather than duplicating its fields.
- `config/baselines.json` — the only place thresholds are currently enforced
  (`frozen_history` / `approved_current` / `tracked_universe` classes, exact-match
  checks run by `scripts/ci_validate_datajs.py`). No new thresholds were invented in
  this pass; `MAPPING_COMPLETENESS_PCT`'s 85% banner threshold is a UI constant, not
  in this file — flagged above, not changed.
- `docs/BUSINESS_LOGIC_REGISTRY.md` — authoritative for business RULES (BL-01..BL-16)
  and their approval status; this registry does not restate rule text, only points to
  the relevant BL-ID per measure.
