# Page Layouts — All 18 Pages

How to read this: each page lists its **slicers** (always a row across the top),
its **visuals** with the exact **fields/measures** to drop in, and a suggested
grid placement. Canvas = 1280×720 (16:9). Theme = `HonasaMT_Theme.json`.
Colour rules: positive **#2D9B7F**, negative **#C0392B**, neutral **#7F8C8D**,
background **#FAF7F2**, text **#1F2933**. Use the `MoM Arrow` / `Growth Colour`
measures for conditional formatting. Numbers in **Lacs / Cr** (use `NSV Label`).

Global slicer row (reuse on most pages, sync via View ▸ Sync slicers):
`Month` · `Chain` · `Zone` · `State` · `Brand` · `Category` · `Sub-category` · `Article` · `Data Source Name`

---

## Page 1 — Executive Summary
**Slicers:** Month (single-select, default = latest), Zone, Brand.

**KPI cards (top row, 8 cards):**
| Card | Measure |
|---|---|
| Latest Month Offtake NSV | `Latest Month NSV` (label `NSV Label`) |
| Latest Month Primary NSV | `Total Primary NSV` |
| Previous Month NSV | `Previous Month NSV` |
| MoM Growth % | `MoM Growth %` (arrow via `MoM Arrow`) |
| YoY Growth % | `YoY Growth %` |
| L3M Average | `L3M Average Sales` |
| Growth vs L3M | `Growth vs L3M %` |
| Forecast vs Actual | `Forecast vs Actual %` |

**Second KPI row (7 cards):** Primary vs Offtake Gap (`Primary vs Offtake Gap`),
Top Growing Chain (`Top Growing Chain`), Top Declining Chain (`Top Declining Chain`),
Top Growing Brand (`Top Growing Brand`), Top Growing Category (`Top Growing Category`),
Market Share MoM (`Market Share BPS Change` → `MS BPS Label`), TDP Growth (`TDP MoM Growth %`),
Sales per TDP (`Sales per TDP`).

**Charts:**
- **Monthly NSV trend** (line/column combo): Axis `Date Table[Month]`, values
  `NSV` + `Final Forecast` (forecast dashed). Left half, mid.
- **Top-3 Chain NSV trend** (line): Axis `Month`, Legend `Chain` (Top N filter = 3
  by `NSV`), value `NSV`. Right half, mid.
- **Brand contribution** (donut): Legend `Brand`, value `NSV`, show `Contribution %`.
- **Insight box** (text/card): use `Top Growing Chain`, `Profitability Flag`,
  `Share Gain Flag`, `Growth Driver` to auto-write 2–3 lines.

---

## Page 2 — Primary vs Offtake Overview
**Slicers:** full global row.

**Visuals:**
- **Monthly Primary vs Offtake trend** (line): Axis `Month`, values
  `Total Primary NSV`, `Total Offtake NSV`.
- **Primary vs Offtake Gap** (column): Axis `Month`, value `Primary vs Offtake Gap`
  (colour by sign via `Growth Colour`).
- **Chain-wise P vs O** (clustered bar): Axis `Chain`, values Primary & Offtake NSV.
- **Brand-wise P vs O** (clustered bar): Axis `Brand`.
- **Zone-wise P vs O** (clustered bar): Axis `Zone` (sorted by Zone Sort Order).
- **Category-wise P vs O** (clustered bar): Axis `Category`.
- KPI cards: `Primary vs Offtake Gap`, `Primary vs Offtake Gap %`.

---

## Page 3 — Chain Performance
**Slicers:** Month, Zone, Brand, Category.

**Visuals:**
- **Chain NSV contribution** (treemap/bar): `Chain` × `NSV`, label `Contribution %`.
- **Chain MoM growth** (bar): `Chain` × `MoM Growth %`, `Growth Colour`.
- **Chain YoY growth** (bar): `Chain` × `YoY Growth %`.
- **Top 10 chains by NSV** (bar, Top N=10 by `NSV`).
- **Bottom / declining chains** (bar, Bottom N by `MoM Growth %`).
- **Chain P vs O gap** (bar): `Chain` × `Primary vs Offtake Gap`.
- **Chain L3M trend** (line): Axis `Month`, Legend `Chain`, value `NSV`.

**Table** (one row per chain): `Chain`, `Latest Month NSV`, `Previous Month NSV`,
`MoM Growth %`, `Last Year Same Month NSV`, `YoY Growth %`, `Contribution %`,
`L3M Average Sales`, `Growth vs L3M %`, `Primary vs Offtake Gap`,
`Forecast vs Actual %`. Conditional-format growth columns with `Growth Colour`.

---

## Page 4 — Chain-wise P&L
**Slicers:** Month, Chain, Brand, Category.
> P&L is computed actuals-first, else from the **Assumption Table** (editable).

**KPI cards:** `Gross Sales`, `Net Sales`, `Gross Margin`, `Gross Margin %`,
`Trade Spend`, `Visibility Spend`, `Scheme Spend`, `Total Spend`,
`Spend % of NSV`, `Contribution Margin`, `CM %`, `Total Primary NSV`,
`Total Offtake NSV`, `Primary vs Offtake Gap`, `Forecast vs Actual %`.

**Visuals:**
- **Chain NSV vs CM %** (combo): Axis `Chain`, column `NSV`, line `CM %`.
- **Chain spend %** (stacked bar): `Chain` × Trade/Visibility/Scheme spend.
- **Chain contribution margin** (bar): `Chain` × `Contribution Margin`.
- **Chain visibility spend** / **trade spend** (bars).
- **Profitability ranking** (bar): `Chain` sorted by `Contribution Margin`,
  data label `Chain CM Rank`, colour by `Profitability Flag`.
- **P&L table:** `Chain`, `Total Primary NSV`, `Total Offtake NSV`, `Gross Sales`,
  `Net Sales`, `Gross Margin`, `Trade Spend`, `Visibility Spend`, `Scheme Spend`,
  `Total Spend`, `Contribution Margin`, `CM %`, `Spend % of NSV`, `MoM Growth %`,
  `Forecast vs Actual %`, `Profitability Flag`.

---

## Page 5 — Forecast Dashboard
**Slicers:** Forecast level toggle (Chain/Brand/Category/Zone/Article via a
field-parameter), Month range.
> Forecast never overwrites actuals; future months use stat base + manual override.

**Visuals:**
- **Actual vs Forecast trend** (line): Axis `Month`, `Actual NSV` (solid),
  `Final Forecast` (dashed), `Actual or Forecast` (combined), `Target NSV M`.
- **Forecast by Chain / Brand / Category** (bars): dimension × `Final Forecast`.
- **Forecast vs Target** (combo): `Final Forecast` column + `Target NSV M` line,
  label `Gap vs Target %`.
- **Forecast vs L3M Average** (bar): `Final Forecast` vs `L3M Avg NSV`.
- **Forecast accuracy** (card + bar where actual exists): `Forecast Accuracy %`.

**Forecast table:** `Month`, `Chain`, `Brand`, `Category`, `Article Code`,
`Actual NSV`, `L3M Avg NSV`, `L6M Avg NSV`, `TY MoM Growth %`, `Forecast NSV`,
`Manual Forecast`, `Final Forecast`, `Target NSV M`, `Gap vs Target`,
`Forecast Accuracy %`.

---

## Page 6 — Brand & Category Deep Dive
**Slicers:** Month, Zone, Chain.

**Visuals:**
- **Brand contribution %** (donut): `Brand` × `NSV`, `Contribution %`.
- **Category contribution %** (donut): `Category`.
- **Brand × Category matrix:** rows `Brand`, columns `Category`, value `NSV`
  + `MoM Growth %`, heat-map background.
- **Monthly brand trend** (line): Axis `Month`, Legend `Brand`.
- **Top growing / declining categories** (bars by `MoM Growth %`).
- **Brand MoM** & **Brand YoY** (bars).
- **Brand sections** (bookmarks or a Brand slicer set to each):
  Mamaearth · The Derma Co. · Aqualogica · Dr. Sheth's · BBlunt · Emerging Brands.
  Each section: sub-category trend (FW/Shampoo/Sun Care), hero-SKU callout,
  Qty vs Value (ASP) decomposition table.

---

## Page 7 — SKU / Article Performance
**Slicers:** Month, Brand, Category, Sub-category, Chain, Pack Size.

**Visuals:**
- **Top 20 articles by NSV** (bar, Top N=20).
- **Top growing / declining articles** (bars by `MoM Growth %`).
- **Article contribution %** (treemap).
- **Pack-size performance** (bar): `Pack Size` × `NSV`, `MoM Growth %`.
- **Article MoM / YoY movement** (bars).
- **Article TDP** (bar): `Article` × `TDP`.
- **Sales per TDP** (bar): `Article` × `Sales per TDP`.

**Table:** `Article Code`, `Article Description`, `EAN Code`, `Brand`,
`Category`, `Sub-category`, `Pack Size`, `Latest Month NSV`, `Total Offtake Qty`,
`Previous Month NSV`, `MoM Growth %`, `YoY Growth %`, `Contribution %`, `TDP`,
`Sales per TDP`, `TDP Opportunity Quadrant`.

---

## Page 8 — Zone & State Performance
**Slicers:** Month, Brand, Category, Chain.
**Zone order (enforce sort):** East · North · South-1 · South-2 · West · Pan India.

**Visuals:**
- **Zone NSV** (bar, sorted by Zone Sort Order) + `Contribution %`.
- **Zone growth %** (bar): `Zone` × `MoM Growth %` (and `YoY Growth %`).
- **State NSV** (bar / filled map): `State` × `NSV`.
- **State contribution** (treemap).
- **Chain performance by zone** (matrix: rows `Zone`, cols `Chain`, value `NSV`).
- **Brand performance by zone** (matrix).
- **Category performance by zone** (matrix).

---

## Page 9 — Nielsen Market Share MoM
**Slicers:** Month, Nielsen Category, Zone.

**Visuals:**
- **Market Share trend by month** (line): Axis `Month`, value `Market Share %`,
  Legend `Nielsen Category`.
- **Market Share by Category** (bar): `Nielsen Category` × `Market Share %`.
- **Market Share by Brand** (bar): `Brand` (competitors) × `Market Share %`,
  highlight Honasa brands.
- **Market Share by Zone** (bar): `Zone` × `Market Share %`.
- **Market Share vs Offtake Growth** (scatter): x `Our Brand Growth %`,
  y `MoM Growth %` (offtake), per Category.
- **TDP vs Market Share** (scatter): x `TDP`, y `Market Share %`.
- **Competitor comparison** (bar): top brands by `Market Share %` with `YoY` bps.

**Table:** `Month`, `Nielsen Category`, `Brand`, `Market Value Sales`,
`Our Brand Sales`, `Market Share %`, `Market Share Volume %`,
`Prev Month Market Share %`, `Market Share MoM Change`, `Market Share BPS Change`,
`Last Year Market Share %`, `Market Share YoY BPS`, `TDP`, `Sales per TDP`.

**Important categories:** Facewash, Shampoo, Sunscreen, Face Serum (others as data allows).

---

## Page 10 — TDP Distribution Analysis
**Slicers:** Month, Brand, Category, Sub-category, Chain, Zone, State, Pack Size.
> TDP = Σ ACV % across SKUs. Available at Brand/Category/Sub-cat/Chain/Zone/State/Article/Pack.

**KPI cards:** `TDP`, `ACV %`, `AIC`, `Numeric Distribution`,
`Weighted Distribution`, `Sales per TDP`, `Offtake per TDP`, `TDP MoM Growth %`,
`TDP YoY Growth %`, `TDP Contribution %`.

**Visuals:**
- **Brand-wise TDP / Article-wise TDP / Category-wise TDP / Chain-wise TDP** (bars).
- **TDP vs Sales** (scatter): x `TDP`, y `NSV`, play axis `Month`.
- **TDP vs Market Share** (scatter): x `TDP`, y `Market Share %`.
- **Sales per TDP ranking** (bar).
- **Low TDP / High velocity** (table filtered to quadrant
  `Low TDP / High Velocity — EXPAND`).
- **High TDP / Low velocity** (table filtered to
  `High TDP / Low Velocity — FIX PRODUCTIVITY`).
- **Growth driver** (bar/table): `Growth Driver`, `Sales Growth vs TDP Growth`.

Answers the leadership question — distribution-led vs velocity-led — via
`Growth Driver` and `TDP Opportunity Quadrant`.

---

## Page 11 — Raw Data Export View
**Slicers:** Month, Chain, Zone, State, Brand, Category, Sub-category, Article, Data Source.

**Single wide table** (export-friendly; turn OFF totals, enable word-wrap off):
`Month`, `Chain`, `Account`, `Zone`, `State`, `City`, `Store Code`,
`Store Name`, `Brand`, `Category`, `Sub-category`, `Range`, `Pack Size`,
`Article Code`, `Article Description`, `EAN Code`, `Total Primary NSV`,
`Total Primary Qty`, `Total Offtake NSV`, `Total Offtake Qty`, `Total MRP Sales`,
`Trade Spend`, `Visibility Spend`, `Scheme Spend`, `Contribution Margin`, `CM %`,
`Market Share %`, `TDP`, `ACV %`, `AIC`, `Contribution %`, `MoM Growth %`,
`YoY Growth %`.

Export: visual *…* ▸ Export data ▸ Summarized or Underlying. Permissions per
`RefreshGuide.md` §5.

---

## Page 12 — Data Quality Check
**Visual: matrix/table** with three columns — Error Type · Impacted Rows · Action.
Build a small disconnected `DQ Checks` table (Enter Data) listing each check name
+ its action text, then put the matching measure beside it. Measures
(`06_DataQuality_Measures.dax`):

Missing Month, Missing Chain, Missing Zone, Missing State, Missing Brand,
Missing Category, Missing Article Code, Missing EAN, Duplicate Store Count,
Duplicate Article Count, Blank NSV Values, Negative Sales Values, Unmapped Chain,
Unmapped Brand, Unmapped Category, Unmapped Zone, Missing TDP,
Missing Market Share, Missing PnL Assumptions.

Top cards: `Data Health %` (KPI, green ≥99%), `Total DQ Issues`.
Conditional format Impacted Rows: 0 → green, >0 → red.

**Suggested `DQ Checks` helper rows (Error Type | Action):**
- Missing Chain | Add chain to ChainMaster.csv & refresh
- Unmapped Brand | Add brand to BrandMaster.csv
- Negative Sales | Fix source row / credit note
- Missing EAN | Update ArticleMaster.csv
- Missing TDP | Add SKU to TDP_Monthly file
- Missing PnL Assumptions | Add month row to AssumptionTable.csv

---

## Page 18 — Refresh Guide (in-report)
A text page reproducing `RefreshGuide.md`: where to paste files, format,
do-not-rename columns, post-refresh checks, and how to export. Use text boxes +
the same theme. (Pages 13–17 in the leadership deck are field-execution images —
optional to recreate; not data pages.)

---

### Field parameters to create (for level toggles)
- **Forecast Level** = { Chain, Brand, Category, Zone, Article } → drives Page 5.
- **TDP Level** = { Brand, Category, Sub-category, Chain, Zone, State, Article,
  Pack Size } → drives Page 10 axis.
Use Modeling ▸ New parameter ▸ Fields.
