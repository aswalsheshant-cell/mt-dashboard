# Addendum: insight tabs worth adding, and the Nielsen / market-share cut

**Status:** proposal, not built. Evidence below was read from the committed repo on 2026-10-04
(`dashboard/data.js`, `dashboard/index.html`, `data/nielsen/`, `PowerBI/`). Nothing here changes
the approved spec for the 11 tabs and 9 subviews; it lists what that spec does not yet cover.

## 1. Handoff gap (read first)

Codex reported commit `8dbf598` (Desktop parser and allocation-join fixes, provisional NPI
measures, extra reconciliation). On GitHub, `codex/powerbi-full-report-20261004` was still at
`3b10980`, so `8dbf598` exists only on the Codex PC. `claude/full-report-on-main` does not have
it. Push it, then merge it here before Task 4. Expect overlap in
`ModernTrade_Report.Dataset/definition/tables/_Measures.tmdl` (NPI measures) and
`scripts/reconcile_powerbi_full.py` (both sides added reconciliation).

## 2. Data already in `data.js` that no tab shows

References counted in `dashboard/index.html`:

| Block | Refs | What it holds | Verdict |
|---|---|---|---|
| `profitability` | 0 | Chain margin on a **standard cost** (14% of MRP COGS + 3% logistics), 60.68% of NSV in total | Candidate tab, gated: this is not CM2 and not an actual COGS extract |
| `correlations` | 0 | Promo discount depth vs lift by chain | Hold: lifts are 0 in the file, note says offtake is "awaiting integration" |
| `unit_economics` | 0 | Units and NSV per unit by zone and month | **Fix first**: FY tags are wrong (see below) |
| `data_quality`, `quality_issues`, `reconciliation`, `executive_deck_sync` | 0-4 | Governance and QC results | Candidate "Data Trust" tab |
| `reliance_brand_counters` | 0 | Empty ("not available in current extracts") | Stale; the displayed breakout is `reliance_bc` |

`unit_economics` breaks THE ONE FY RULE: block `fy25` holds Apr-25..Jul-25 (that is FY26), block
`fy26` holds Aug-25..Jul-26 (spans FY26 and FY27), block `fy27` holds Apr-26..Jul-26. Apr-Jul 2026
sits in both `fy26` and `fy27`, so summing the blocks double counts. It is not displayed, so there
is no live impact, but it must be rebuilt by month and FY derived from the month before any page uses it.

## 3. Proposed additions, in priority order

1. **Market Share and Nielsen** (section 4). Real files exist; the dashboard still says "source not available".
2. **Data Trust and Reconciliation.** One page showing, per source and month: files present, rows,
   duplicate-key rows, source-vs-dashboard match (from `scripts/reconcile_powerbi_full.py`), unmapped
   chains, and the readiness PASS / AWAITING BUSINESS DATA state. All data exists. Aug-26 offtake has
   10,827 repeated month/store/article rows (20,883 across FY27) and the page should say so.
3. **Chain Profitability** from `profitability`, shown only with its basis line, never named CM2, and
   held until Finance settles the COGS scope (blocker B3).
4. **Unit Economics** after the FY-tag rebuild.
5. **Promo Effectiveness** only when promo lift has real offtake behind it. Do not show 0 lift as a result.

## 4. Market share and the Nielsen cut

### What is in the repo

| File | Shape | Content |
|---|---|---|
| `data/nielsen/FW_Jul26_Competitive_Landscape.csv` | 25 brands x Jul-25..Jul-26 | Facewash only. Monthly NSV and share per brand, plus YoY, weighted distribution, stores, L3M, LMAT |
| `data/nielsen/Mamaearth_FW_Monthly_Trend.csv` | 37 months, Jul-23..Jul-26 | Category NSV (Cr), Mamaearth NSV (Cr), share, weighted distribution, stores. Jul-26: 82.3 Cr, 9.2 Cr, 11.2%, 89.2%, 13,097 stores |
| `data/nielsen/Shampoo_Jul26_PackSize_Analysis.csv` | 99 pack sizes | Jul-26, Jun-26, May-26, Jul-25 sales, L3M, L12M, share by base pack size |
| `PowerBI/RawDataFolders/Nielsen_Monthly/` | template only | The folder `Fact_Nielsen` reads is empty |

The model's `Fact_Nielsen` expects month x category x brand x zone with market and brand value
sales. These files are wide (one column per month) and have no zone, so they need reshaping before
they can load. `Nielsen Value Share Pct` is built (Task 3) and returns BLANK until rows exist.

### What must be confirmed before wiring (config/data_source_registry.yml checklist)

| # | Item | Known | Unknown, owner to confirm |
|---|---|---|---|
| 1 | Grain | brand x month (category x brand) | |
| 2 | Business date column | month label (`Jul 26`, `ms_Jul26`) | |
| 5 | Effective-dating | | whether history was restated |
| 6 | Coverage | Facewash Jul-25..Jul-26; Shampoo Jul-26 only | other categories, other months |
| - | **Universe** | | **channel and geography the extract covers (national? MT? one chain?) and the unit of `nsv_*` (Cr?)** |
| - | Source | | which Nielsen report / who pulled it |

The file prefix `FW` is not defined anywhere in the repo. It most likely means Facewash (the category
inside), but it has not been confirmed, and a "Wellness Forever" reading cannot be ruled out from the file.
Until the universe is confirmed, every visual built on these files must say "Nielsen extract, scope
unconfirmed". PR #281 (open draft) already forbids publishing a SAMPLE or ungoverned market-share payload.

### Page design (after the scope is confirmed)

- **Market Share and Nielsen** under Demand and S&OP Planning, replacing the "source not available" card.
- Visuals: brand share table with change in points vs Jul-25 and vs L3M; Mamaearth share and weighted
  distribution trend (37 months); share vs weighted distribution (is share gain distribution-led?);
  new-entrant share (Simple 0.6 to 2.6, Cetaphil 0.0 to 1.0, The Derma Co 0.0 to 1.0); Shampoo pack-size share.
- Every comparison uses equal months. Share is computed from market and brand sales, not by averaging
  percentages. A missing brand-month is blank, not 0.
- First read from the Facewash file (to be labelled "scope unconfirmed"): Mamaearth 8.8% to 11.2% (+2.4
  points) while Garnier (14.5 to 13.3), Pond's (14.2 to 13.0) and Nivea (5.1 to 3.4) lost share.

## 5. Not changed

No data, DAX, Power Query, workflow, baseline or number was changed by this addendum.
