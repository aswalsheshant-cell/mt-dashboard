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

## What this registry deliberately does not cover yet

The proposed architecture describes a much larger set of measures (Assortment
Opportunity Score, Promotion ROI, Nielsen market-share deltas, Forecast scenario
bands). None of those are currently computed anywhere in this codebase — they are
not omitted from this table by oversight, they simply don't exist as production
measures yet. Adding a row for a measure that isn't computed would misrepresent
the registry as more complete than the dashboard actually is.

## Duplicate-KPI check performed while building this registry

Grepped `dashboard/index.html` for independent recomputation of the same headline
numbers (the concrete risk this registry exists to prevent). Found: Primary NSV and
Offtake NSV are each read from a single source block (`D.primary`, `D.offtake`)
everywhere checked — no second independent calculation of either was found in this
pass. This is a spot-check, not an exhaustive audit of every one of the dashboard's
inline calculations; treat "no duplicate found this pass" as encouraging, not as
proof none exists.
