# MT Leadership Dashboard

A self-contained, interactive dashboard for **Honasa / Mamaearth Modern Trade (MT)**
covering Primary, Offtake, chain-wise P&L, Forecast, Market Share and data-driven
Insights / Way Forward.

## Open it

Open `dashboard/index.html` in any modern browser — no server or internet needed.
Chart.js is vendored locally (`chart.umd.js`) and all data is baked into `data.js`,
so the dashboard works fully offline.

## Post-merge validation status

FY refactor validation completed on PR #2's branch (`claude/modern-trade-pbi-dashboard-y963w2`):

- Build compiled successfully
- FY logic is now month-driven (Apr-Dec -> next FY, Jan-Mar -> same FY; no fixed
  index/column positions)
- FY27 Primary rendering is fixed (Overview / Primary / Market Share / Performance
  & Comparison all show real FY27 chain-allocated numbers)
- FY25/FY26 numbers remain unchanged
- 12-tab regression (all tabs x FY25/FY26/FY27) passed with no NaN/undefined/blank
  sections or JS errors
- Offtake correctly shows no FY27 data because its source ends Mar'26
- DIST allocation: zero-variance reconciliation, 0 unmapped rows

**PR #2 is still open, pending merge** — this status reflects branch validation,
not a completed merge. Next action once merged: a post-merge dashboard view check
to confirm the deployed build matches this validation.

## Tabs

| Tab | What it shows |
|-----|---------------|
| **Data Explorer** | Cascading drill-down/filter across FY, Month, Channel, Zone, Chain, Brand, Category, Sub-category, Range, Pack Size, Article |
| **Overview** | Headline KPIs, Primary-vs-Offtake monthly trend, channel split, top chains, brand mix |
| **Primary** | Sell-in NSV (FY24-25 vs FY25-26) by month, zone, channel, brand and **chain** (chain-level, secondary-allocated for Distributor primary — see below) |
| **Offtake** | Sell-out trend, zone & state YoY, and a Primary-vs-Offtake inventory-health view by chain |
| **P&L** | Chain-wise gross MRP → net NSV bridge and trade-discount intensity |
| **Category & Pack** | NSV by Sub-category (95%-of-brand rule, see below), Range and Pack Size, plus a top-20 **unique-article** table (from the article-level primary detail) |
| **Forecast** | FY26-27 (TY) target — the business's own monthly target once refreshed via `--forecast-only` (falls back to a seasonally-indexed projection if that source isn't supplied) |
| **Promo & Trade Spend** | Promo calendar activity — count and average consumer discount depth by chain, brand, category |
| **Market Share** | Share-of-business across MT chains |
| **Distribution** | Store universe / distribution footprint by zone, city category, chain and store type |
| **Performance & Comparison** | Rank/compare Chain, Brand, Sub-category, Range, Pack Size or Article side by side (FY-over-FY, YoY, contribution %) in one place |
| **Insights & Way Forward** | Auto-generated risks/opportunities plus prioritised leadership actions |

### The FY/Month/Chain/... filter bar applies dashboard-wide — and so does drilling
Every tab (not just the Explorer) rebuilds live from the current filter
state — pick FY26, a Zone, a Chain, whatever, and every tab you visit
reflects it. **Filters are multi-select:** picking a value in a dropdown ADDS
it to that dimension's selection (✓ marks selected values); picking it again
removes it; the dropdown's first line ("N selected — clear" / "All") clears
the dimension. Values within one dimension are OR'd (Chain = Dmart OR
Apollo); different dimensions are AND'd. Every selected value shows as a
removable chip under the filter bar. Clicking a chart bar/slice (drill) still
FOCUSES on the clicked value — it replaces that dimension's selection with
just that value. **Clicking a chart bar/segment or a table cell (drill) re-renders
the tab you're already on, narrowed to what you clicked** — drilling into
"Dmart" from the Primary tab's chain chart shows Dmart's own Primary view in
place, it does not jump you to a different tab. The Data Explorer tab is
still there whenever you want the raw row-level records for whatever's
currently filtered — visit it any time, it always reflects the active filter.

### Category → Sub-category drill chart, on every tab
Every single tab (Overview, Primary, Offtake, P&L, Category & Pack, Forecast,
Promo, Market Share, Distribution, Performance & Comparison, Insights, Data
Explorer) carries an **"NSV by Category"** bar chart at the bottom, driven
off the article-level detail (REC) and respecting whatever filters are
currently active. Click a Category bar to drill into that category's
**Sub-categories** in place (chart title becomes `Sub-categories of "X"`); a
**"← All Categories"** button backs out. This works even on tabs whose own
native data source (Offtake/P&L/Universe/Promo) has no Category dimension at
all, since it's powered independently by the article-level detail rather than
each tab's own aggregates.

Two honest limits, by design, not bugs:
- **FY26-27 actuals (Apr'26 onward) come from the article-wise primary
  only** — the pre-aggregated FY24-26 workbook ends Mar'26. Selecting FY27
  now renders REAL numbers on Overview / Primary / Market Share (exact,
  chain-allocated `detail_meta.fyx_primary['FY27']` aggregates, computed from
  the FULL uncapped File 2 data) and keeps TOT%/CM2 visible on P&L. The FY is
  derived from each row's month+year (Apr–Dec → next FY, Jan–Mar → same FY),
  never a fixed index, so FY28 flows in automatically once Apr'27 rows arrive.
  **Offtake**
  genuinely has no FY27 (the sell-out master ends Mar'26) and still shows an
  explicit "no data" message rather than silently falling back to FY26.
- **Not every dimension applies to every tab** — e.g. Offtake has no
  Brand/Category breakdown in its source, Distribution's store universe
  isn't tracked by FY/Month, P&L is chain-level only. Each tab says so
  inline (small italic note) rather than silently ignoring the filter.

### Category & Pack: unique articles, Range, and the 95%-of-brand sub-category rule
- The **Top 20 articles** table shows each article **once**, summed across
  every chain/month/etc. in the current filter — not the same article
  repeated once per chain. Drill into a Chain (a chip, or any chart's
  click-to-drill) to see that chain's own unique-article ranking. The table
  and the Explorer's detail table both now include a **Range** column
  (the product range/variant, e.g. "Onion", "Niacinamide", "Rice Water" —
  one level more granular than Sub-category, one level up from Article).
- The **NSV by Sub-category** donut applies a per-brand 95% rule: within
  each brand, keeps the sub-categories that cumulatively cover 95% of that
  brand's NSV; the combined long tail across all brands is clubbed into
  **"Other"** — so one brand's rare sub-category doesn't get diluted by
  another brand's very different assortment mix.
- **Performance & Comparison** also has Range and Article as comparison
  dimensions (in addition to Chain/Brand/Sub-category/Pack Size) for a full
  Article → Pack Size → Range → Sub-category → Category deep-dive hierarchy.

### Primary is chain-level, not distributor-name-wise
Distributor-billed ("Dist.") primary rows are re-split across the chains a
ship-to actually serves, weighted by that chain's share of the ship-to's own
secondary/offtake billing that Month × Brand — the same method the Power BI
model uses for its Ship-to allocation (`PowerBI/docs/DistributorPrimaryAllocation_Logic.md`).
Direct-billed rows are unambiguous (1 ship-to = 1 chain) and are never
re-split. Coverage (how much Distributor primary has a matching allocation
entry, vs falling back to its original single-chain tag) is reported in
`DASH.chain_allocation_qc` and shown as a note on the Primary tab.

### Article-level DIST → Chain allocation (Customer × Article grain)
The article-level detail (File 2, everything REC-driven: Explorer, Category &
Pack, TOT%, CM2) gets its own allocation, done row-level BEFORE any grouping:
rows with **`PO Type = 'Dist.'`** have a blank **"Chain name for Dashboard"**
in the source and are exploded across chains using
`Dist_primary_cont_based_on_secondary_MOM.xlsx` (sheet *"Dist Primary Conv to
Chain Art"*, keyed Ship To Name × Brand × Month — that sheet has no Cust-SAP
Code column; the code↔ship-to bridge lives in the primary file itself, and
Cust-SAP Code is carried through every QC table). `Inv Qty / Total MRP sales /
NSV / Tax` are scaled by the cont% (normalised to sum to exactly 100% per
key, so **input totals equal output totals by construction** — deviations are
flagged before normalisation); article MRP is per-unit and is NOT scaled;
`Avg Tot` is a ratio, invariant under the split. Direct rows keep their own
"Chain name for Dashboard". Dist. rows with no cont-sheet entry get
**"Unmapped Chain"** — never blank, never the distributor's Ship To Name; the
Chain filter therefore lists only real chains (+ "Unmapped Chain"), and Ship
To Name remains a customer/distributor field only.

The **Primary tab**'s "Distributor primary → Chain allocation" section shows:
the zero-variance reconciliation (original vs allocated for NSV, Total MRP
sales, Inv Qty, Tax — overall, by Month, by Brand), allocation counters
(unmapped rows/value, rows missing Avg Tot, cont% keys ≠ 100, source rows
where Chain = Ship To Name), the missing-mapping QC table, the
Month × Brand × Cust-SAP Code × Ship To QC table (full Excel export), and the
Customer × Article × Month × Chain allocation table with weighted Avg Tot
(= SUM(NSV × Avg Tot)/SUM(NSV), Total-MRP-sales-weighted fallback — never a
simple average; full Excel export). Power BI mirrors this in queries 16 + 41.

### TOT% (Trade Offer Terms % / On-Invoice Margin Pass-on %) — P&L tab, sourced from actual Primary file data
`TOT% = SUM(Pass-on Value) / SUM(MRP)` — never a simple average of row-level
TOT% percentages — computed chain/category/pack-size-wise from the full
(uncapped) article-level primary detail, not the 20k-row browser export, so
it's exact. Pass-on Value is sourced per row with a **3-tier priority**:

1. **Source TOT%** — the Primary file's own `Avg Tot` column (Customer ×
   Article grain, a 0-1 fraction) is used directly: `Pass-on Value = MRP × Avg Tot`.
2. **Calculated using Actual Tax Amount** — if `Avg Tot` is blank/invalid,
   use the row's actual `Inv. Tax Amount(LOC)`: `Pass-on Value = MRP − NSV − Tax`.
3. **Calculated using GST Rate Table fallback** — only if *both* are
   blank/invalid, estimate Tax from Category + cutover date via the editable
   **QC table** `PowerBI/SeedData/Masters/GST_Rate_QC_Table.csv` — columns
   `Category, HSN_Code, Pre_GST_Rate_Pct, Post_GST_Rate_Pct, Effective_From,
   Confidence, Finance_Approved, Impact_on_TOT_pct, Note`. A per-category
   cutover override lives in that table's `Effective_From` column; if blank,
   the **global, editable** default cutover date in
   `PowerBI/SeedData/Masters/GST_Config.csv` applies — default
   **2025-09-22** (the GST Council's confirmed GST 2.0 effective date), a
   single cell to edit if Honasa's internal billing cutover differs.

**The GST rate table is fallback-only** — it has zero effect on TOT% for any
row where `Avg Tot` or `Inv. Tax Amount(LOC)` is present. The P&L tab's TOT%
card shows a dynamic status banner: **green** ("TOT% sourced from actual
Primary file data") when the fallback wasn't needed, or **amber**
("Partially provisional: N% of MRP relies on the GST rate table fallback")
scoped to just that portion when it was. A **TOT% source QC summary** table
shows the exact row counts: rows using Source TOT%, rows calculated using
Actual Tax Amount, rows using GST Rate Table fallback, fallback % of total
MRP, blended TOT%, and rows where MRP/NSV/`Avg Tot`/`Inv. Tax Amount(LOC)`
are all blank/invalid (excluded from the calc entirely, not silently
included at zero).

**Wherever the fallback tier IS used, treat it as a best-effort assumption,
not an authoritative figure — every QC-table row starts `Finance_Approved =
Pending`.** Several categories are marked **LOW confidence** (no official
HSN-code-level source was available to classify which Honasa/Mamaearth
categories moved to the 5% merit slab vs stayed at 18%). `Impact_on_TOT_pct`
is auto-computed on every `--detail-only` rebuild — how much blended TOT%
would move, in percentage points, if that one category's rate assumption
were wrong, **scoped only to that category's own fallback-tier rows** (a
category with 100% Avg Tot coverage shows `Impact_on_TOT_pct = 0` regardless
of its Confidence rating, since the rate table isn't being used for it at
all) — use it to prioritise which LOW-confidence rows to chase down first.
Fill in `HSN_Code` and flip `Finance_Approved` to `Yes` per row as Finance
confirms, edit `GST_Config.csv` if the cutover date needs correcting, then
re-run `--detail-only` to refresh TOT% dashboard-wide (and in Power BI —
`DAX/12_TOT_Measures.dax` reads the same two files via queries 37/38).

`On-Invoice Margin Pass-on Value = MRP − NSV − Tax` (Tax shown in the UI is
back-derived from whichever tier drove Pass-on Value, so it's always
internally consistent). `Incremental Pass-on Impact` = the month-over-month
change in Pass-on Value; `MoM TOT Δ pp` = the month-over-month change in
TOT% itself, in percentage points. Both are exposed per-chain (P&L tab card)
and per-pack-size (Category & Pack tab's Pack Size chart export — see below).

### P&L / CM2 (Contribution Margin 2) — P&L tab
`CM2 = NSV − P&L Expenses`. NSV here is already net of TOT%/tax (see above),
so no further deduction happens for CM2 — it's simply whatever's left after
subtracting matched P&L expenses.

**Expenses are never hardcoded.** They're maintained month-on-month in the
editable `PowerBI/SeedData/Masters/PL_Expense_Input.csv` — columns `Month,
FY, Chain, Customer Code, Customer Name, Zone, State, Brand, Category, Sub
Category, Expense Head, Expense Type, Expense Amount (INR Lakh), Remarks,
Source, Updated By, Updated Date`. **`FY` must use a format containing
"yy-yy" (e.g. `FY25-26`) or the dashboard's own short form (e.g. `FY26`)** —
either works, but a bare number or an unrecognised format will silently land
the row in the QC panel's "Blank Month" count instead of matching.

**Matching priority:** Customer Code is tried first (resolved to a Chain via
a lookup built from the primary data itself — a Customer Code doesn't need
to spell the Chain name correctly, or at all); Chain name is the fallback.
A row satisfying neither is **unmapped** — its amount is excluded from CM2
and chain-wise rollups, but tracked in the QC summary below, never silently
dropped. **An expense row only attributes to a Brand/Category bucket if it
specifies that dimension itself** — no proportional/estimated allocation is
invented for rows that don't (e.g. a Chain-only "BA Cost" row reduces that
chain's CM2 but doesn't appear in any Brand-wise or Category-wise view).

The P&L tab's CM2 section shows: NSV, TOT Value/%, Total P&L Expense,
Expense % of NSV, CM2 Value/%, MoM CM2 movement, chain-wise CM2 (chart +
table), Expense Head-wise contribution, and an 8-metric QC summary (total
expense loaded, mapped/unmapped amount, unmapped chain/customer rows,
unmapped brand/category rows, blank Month rows, blank Expense Head rows,
duplicate rows). **If no real expense data has been loaded yet, an explicit
banner says so** rather than silently showing CM2 == NSV as if it were a
final number. Edit `PL_Expense_Input.csv` and re-run `--detail-only` to
refresh CM2 dashboard-wide (and in Power BI — `DAX/13_CM2_Measures.dax`
reads the same file via query 39).

## Export & download

Every page, chart and table can be downloaded — all client-side, no server
round-trip, so it works fully offline just like the rest of the dashboard
(html2canvas, jsPDF and SheetJS/xlsx are vendored locally: `html2canvas.min.js`,
`jspdf.umd.min.js`, `xlsx.core.min.js`).

### Export the full page (PDF or PNG)
Click **⭳ Download Page** in the filter bar (top-right, next to Reset
filters) ▸ choose **PDF** or **PNG Image**. The export captures the tab
you're currently on, exactly as filtered:
- A header with the dashboard title, tab name, active-filter summary, and
  the FY24-25 vs FY25-26 period note.
- Every KPI card and chart, with their current data labels.
- A footer: `Source: MT Dashboard | Exported on <date/time> | <data.js build note>`.
- **Long tables (>8 rows) are excluded from the page image** and replaced
  with a short note pointing at that card's own **Export Table** button —
  a table that size gets cut across PDF pages or squeezed unreadably
  otherwise, so it's exported to Excel separately instead (see below).
- PDF export auto-paginates across as many A4 pages as the content needs.

### Export one chart (PNG / CSV / Excel)
Every chart has a small **⭳** download icon in its top-right corner. Click
it ▸ choose:
- **PNG Image** — just that chart, as currently drawn (labels included).
- **CSV Data** — the chart's own labels + values (and a Share % column for
  single-series charts).
- **Excel Data** — same data as CSV, in `.xlsx`, with a header block (chart
  title, active filters, export timestamp, data.js build note) above the
  data rows. Falls back to CSV automatically if the xlsx library can't load.

Filenames follow `MT_Dashboard_<Tab>_<Chart>_<Month/FY>_<timestamp>` —e.g.
`MT_Dashboard_Category_Pack_TopRanges_May26_20260703_2054.xlsx` — so exports
from different tabs, charts or points in time never collide or overwrite
each other.

The **Category & Pack** tab's **Pack Size** chart export additionally
includes `Weighted TOT%`, `On-Invoice Margin Pass-on Value`, `MoM TOT Δ pp`
and `Incremental Pass-on Impact` columns per pack size (see the TOT%
methodology note above) — every other chart's export is just its own
labels/values.

### Export a table
Every card containing a table gets an **⭳ Export Table** button above it.
This exports exactly what's on screen — same rows, same filters, same
column order — as `.xlsx` (falls back to `.csv`). The **Data Explorer**'s
own **⭳ Export ALL filtered records (CSV)** button is separate: it exports
every row-level record matching the active filters, not just what's
paginated/visible in a summary table.

### Drill-down-aware exports
Chart and table exports always read whatever the chart/table itself is
currently showing — so if you've clicked into a Category → Sub-category
drill, or filtered down to one Chain, the export reflects that scoped view,
not the full unfiltered dataset. Nothing needs re-selecting before exporting.

### Value & quantity formatting (consistent across every export)
- **₹ values:** below ₹100 L → shown as `₹75.5 L`; ₹100 L and above → shown
  as `₹2.50 Cr` (e.g. ₹250.17 L = `₹2.50 Cr`). This threshold and rounding
  is identical on-screen, in chart data labels, and in every CSV/Excel/PDF
  export.
- **Quantity:** always shown as `Qty Cr` (e.g. 1,25,00,000 units = `1.25 Cr
  Qty`) unless the quantity is small enough that Cr would round to ~0, in
  which case it falls back to `Qty L` (e.g. 12,50,000 units ≈ `0.13 Cr Qty`,
  right at that boundary). **Quantity units are never mixed with value
  Cr/L** — a Qty column will never say "₹" and a value column will never
  say "Qty".

### Power BI exports
The Power BI build kit has the same three export levels wherever Power BI
supports them natively — full-page PDF export, per-visual "Export data" to
Excel/CSV, and matching ₹ L/Cr / Qty Cr/L display-label DAX measures
(`PowerBI/DAX/11_ExportDisplay_Measures.dax`). Power BI has no per-chart
PNG export and no client-side filename templating, and per-visual export
data is subject to license row caps — full walkthrough and the complete
list of limitations are in `PowerBI/docs/ExportAndVisualSettings.md`.

## Data sources

Built from the Honasa MT working files (FY24-26), kept in Google Drive (not committed):

- **Primary FY-2024-26.xlsx** — row-level primary sell-in (NSV, MRP, chain, brand, zone, channel)
- **Chain Offtake Master File State Wise FY 24-26.xlsx** — chain-wise & zone/state offtake pivots
- **Universe MT.xlsx** — MT store universe (distribution footprint)
- **Promo Master -MT.xlsx** — promo / trade-spend calendar

All monetary values are **INR Lakh** in the data and displayed as **INR Crore** (Cr = Lakh / 100)
where labelled.

## Rebuilding `data.js`

```bash
pip install pandas openpyxl
# place the four source workbooks (+ the offtake text dump 'offtake_flat.txt') in <src>
python scripts/build_dashboard_data.py --src <src> --out dashboard/data.js
```

`scripts/build_dashboard_data.py` normalises chain/brand/zone spellings across the four
files onto a common key, aggregates every view, derives the P&L bridge and forecast, and
emits `window.DASH` into `data.js`.

## Assumptions & caveats

- **P&L** uses real Primary data for the gross **MRP → net NSV** bridge. COGS is not in the
  source, so this is a **gross-to-net trade contribution** view (retail margin + taxes + trade
  terms), not a full statutory P&L.
- **Market share** is **internal share-of-business + distribution reach**; external category
  share vs competitors is not in the source data.
- **Forecast** is directional for planning (seasonally-indexed run-rate at the realised offtake
  YoY rate, clamped to 0-60%), not a financial commitment. Refresh monthly as actuals land.

## Data Explorer (drill-down & filters)

A **Data Explorer** tab plus a global **filter bar** (below the header, visible
on every tab) provide cascading drill-down across: FY · Month (Apr→Mar) ·
Channel · Zone · Chain · Brand · Category · Sub-category · Pack Size · Article.

- **Cascading:** each dropdown's options recompute from the currently filtered set.
- **Click-to-filter:** clicking any Explorer chart bar/segment applies that slice.
- **Reset filters** clears everything; active slices show as removable chips.
- **Detail table** + **Export filtered CSV** reflect all active filters.
- KPIs, charts and the table update live.

Data source: `DASH.detail_records` (columns: Month, FY, Channel, Zone, Chain,
Brand, Category, SubCategory, PackSize, Article, NSV, MRP, Qty).

### Every tab drills down — not just the Explorer
Every leadership tab (Overview, Primary, Offtake, P&L, Category & Pack, Promo &
Trade Spend, Market Share, Distribution) has its own **click-to-drill**
charts and clickable table cells (dashed underline = clickable). Clicking a
chain bar, brand slice, zone, category, pack size or article — on **any**
tab — sets that one filter and jumps to the Data Explorer's row-level detail
for that slice, exactly like clicking a Explorer chart does. Chips in the
filter bar (or **Reset filters**) drill back up. This makes the whole
dashboard one connected drill-down surface instead of the Explorer tab being
a separate, disconnected view.

Two tabs are intentionally **not** wired to this (data limitation, not an
oversight): **Forecast** (a time projection, not a dimension breakdown) and
parts of **Distribution**/**Promo** that group by fields the row-level detail
doesn't carry (City Category, Store Type — those come from the Universe file,
which has no article-level grain).

> The shipped `detail_records` is **representative**: Chain/Brand/Zone/Channel/
> Month/FY totals are anchored to the real primary aggregates, while Category,
> Sub-category, Pack Size and Article are Honasa-taxonomy placeholders
> (`DASH.detail_meta.representative = true`). To make it fully real, have
> `scripts/build_dashboard_data.py` emit `detail_records` from the granular
> primary/offtake source at that 13-column grain and replace the array.

## Refreshing the dashboard data (run instructions)

`dashboard/data.js` is generated by `scripts/build_dashboard_data.py` from the
source Excel files. **Keep the source Excel files OUT of the repo** — they are
large and git-ignored (`*.xlsx`, `*.xlsb`). Only the generated `dashboard/data.js`
is committed after a refresh.

### File placement
Put your source files in a working folder (your `--src`, e.g. a Drive-synced
`P&L DATA` folder — not inside the repo). For the Data Explorer drill-down, add
**File 2** there named exactly **`primary_article.xlsb`** (the original name
`MT, Eb2B & SIS primary April_23 to May_26.xlsb` is also accepted):

```
<your-source-folder>/primary_article.xlsb
```

### One-time deps
```
pip install pandas pyxlsb openpyxl
```

### A) Refresh ONLY the Explorer drill-down (lightweight — recommended)
Needs just File 2 in `--src`; leaves the leadership tabs untouched:
```
cd <repo-root>            # e.g. /home/user/mt-dashboard
python scripts/build_dashboard_data.py --detail-only \
  --src "<your-source-folder>" \
  --out dashboard/data.js
```

### B) Refresh ONLY Primary / P&L / Insights (chain-level allocation)
Needs **`Primary_FY202426_10.xlsx`** in `--src` (business-confirmed primary
source; must have a `Dump` sheet with `Bill to customer`, `Direct/Distributor`,
`Chain Name`, `NSV`, `MRP value`, `Brand`, `Month`, `FY`, `Channel`), plus
optionally **`Dist_primary_cont_based_on_secondary_MOM.xlsx`** (Sheet2 = the
secondary-derived Distributor→Chain Cont% split) for proper chain-level
allocation of Distributor-billed primary. Reuses the Offtake/Universe/Promo
blocks already in `data.js`, so those source files aren't needed:
```
cd <repo-root>
python scripts/build_dashboard_data.py --primary-only \
  --src "<your-source-folder>" \
  --out dashboard/data.js
```
Prints the FY25/FY26 primary total and the chain-allocation coverage %
(how much Distributor primary got a secondary-based chain split vs falling
back to its raw single-chain tag — see `DASH.chain_allocation_qc`).

### C) Refresh ONLY the Forecast tab (real TY / FY26-27 target)
Needs **`FY2627_TGT_and_sales_team_mapping.xlsb`** in `--src` (Sheet1: `FY`,
`Qtr`, `Month`, `TGT FOR TY` in ₹ Crore). Replaces the seasonally-projected
FY26-27 estimate with the business's own monthly TY target (same source the
Power BI Forecast page uses — total ₹441.33 Cr). Reuses the Offtake block
already in `data.js` for FY24-26 history:
```
cd <repo-root>
python scripts/build_dashboard_data.py --forecast-only \
  --src "<your-source-folder>" \
  --out dashboard/data.js
```
**Note:** this is the *target*, not offtake *actuals* for FY26-27 — the
Offtake tab's own FY24-26 history won't extend into FY26-27 until an updated
offtake source (covering Apr'26 onward) is supplied and a full rebuild
(option **D** below) is run — there's no dedicated `--offtake-only` mode yet.

### D) Full rebuild (also refreshes KPIs / charts / P&L / forecast)
Needs ALL sources in `--src` (`primary.xlsx`, offtake, `universe.xlsx`,
`promo.xlsx`) **plus** `primary_article.xlsb`:
```
cd <repo-root>
python scripts/build_dashboard_data.py \
  --src "<your-source-folder>" \
  --out dashboard/data.js
```
Note: the full rebuild still uses `primary.xlsx` (single Chain Name tag, no
allocation) for the Primary/P&L/Insights blocks — run **B) afterwards** if you
want chain-level allocated primary as well.

On success it prints `detail_records: N rows (REAL)` and
`detail_meta.representative` flips to **false** — the amber banner disappears and
the SIS card shows the exact Primary SIS total from File 2's own Channel field
(computed from the full source, independent of the row cap — see
`detail_meta.channel_totals`). **Primary SIS FY26 = ₹250.17 L** (business-confirmed
2026-07-03; ₹236 L and ₹275.44 L gross are both confirmed NOT correct — see
`PowerBI/docs/SIS_Reconciliation.md` for the investigation and resolution record).

### Then
Open `dashboard/index.html` in any browser to validate, then commit **only**
`dashboard/data.js`:
```
git add dashboard/data.js
git commit -m "Refresh dashboard data"
```

## AI Analyst tab (13th tab)

The **AI Analyst** tab answers plain-English questions about the loaded dashboard data — entirely in the browser, with no network dependency. All answers are derived from `window.DASH`; no numbers are invented.

### How it works

- Type or paste a question (e.g. *"Top 5 chains by NSV for FY26"*, *"NSV by zone"*, *"What is the offtake for FY27?"*).
- Press **Ask** or **Enter**. The router classifies the intent and extracts the answer from the pre-aggregated data blocks already in `data.js`.
- Results are shown as a KPI card (scalar), ranked table, or an unsupported-query notice.
- A **Source** line and **Confidence** badge (HIGH / MEDIUM / LOW) accompany every answer so users know where the number comes from.
- A **Session audit log** (toggle at the bottom) records every Q&A pair in `localStorage` (max 100 entries). Clearing the browser's site data clears it.

### Ollama integration (optional narration)

After routing succeeds, the AI Analyst optionally asks a local [Ollama](https://ollama.com) instance to add a one-to-two-sentence commentary.

- Ollama endpoint: `http://localhost:11434/api/generate` (default model: `llama3`).
- If Ollama is not running, the request times out silently in **8 seconds** and the data answer is shown without commentary — the tab is fully functional offline.
- To enable: `ollama serve` + `ollama pull llama3` on the same machine that runs the browser.

### Negative NSV

Negative NSV values are **valid business data** (returns / credit notes) and are never flagged as errors, either in the AI Analyst or anywhere else in the dashboard.

## Testing

### Python syntax validation

```bash
python -m py_compile scripts/build_dashboard_data.py
```

### AI analyst unit tests (95 tests)

```bash
python scripts/ai_analyst/run_tests.py
```

### Browser smoke test (Playwright)

Requires Playwright and Chromium:

```bash
# install once
pip install pandas pyxlsb openpyxl
# serve the dashboard
python -m http.server 8090 --directory dashboard &
# run test (Node 18+ required)
node -e "
const {chromium}=require('playwright');
(async()=>{
  const b=await chromium.launch();
  const p=await b.newPage();
  const errs=[];
  p.on('pageerror',e=>errs.push(e.message));
  await p.goto('http://localhost:8090/');
  await p.waitForTimeout(3000);
  const tabs=await p.\$\$eval('nav button',bs=>bs.length);
  console.log('tabs:',tabs,'errors:',errs.length);
  await b.close();
})();
"
```

Expected output: `tabs: 13  errors: 0`

## Rollback

To revert the dashboard to the previous commit:

```bash
# Safe revert (creates a new commit, does not rewrite history)
git revert <commit-hash>

# Or restore just index.html from the previous known-good commit
git checkout <previous-commit> -- dashboard/index.html
git commit -m "Rollback dashboard/index.html to <previous-commit>"
```

`data.js` does not need to be restored unless the data itself changed — it is a separate committed file and is not rewritten by dashboard code changes.

To find the previous known-good commit:

```bash
git log --oneline dashboard/index.html
```
