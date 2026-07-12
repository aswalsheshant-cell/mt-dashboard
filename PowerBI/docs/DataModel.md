# Data Model — Star Schema & Relationships

A clean star schema: fact tables in the centre, dimensions/masters around them,
all joined to a single **Date Table**. Filter direction is single (1 → *) unless
noted. Keep auto-detect relationships OFF and create these explicitly.

## Tables

### Dimensions / Masters (the "1" side)
| Table | Key | Notes |
|---|---|---|
| `Date Table` | `Date`, `MonthStart` | Calculated (DAX). Marked as date table. Indian FY Apr–Mar. |
| `Chain Master` | `Chain` | Chain, Account, Chain Type, Primary Zone |
| `Brand Master` | `Brand` | Brand, Brand Group, Sort Order |
| `Category Master` | `Category` (+ `Sub-category`, `Nielsen Category`) | maps internal category → Nielsen category |
| `Article Master` | `Article Code` | EAN, Brand, Category, Sub-category, Range, Pack Size |
| `Zone State Master` | `Zone` / `State` | Zone Sort Order enforces East→…→Pan India |
| `Store Master` | `Store Code` | Store→Chain→Zone→State→City |
| `Nielsen Competitor Master` | `Nielsen Category` + `Brand` | competitor list, Is Honasa flag |
| `Ship-To Master` | `Ship To Name` | Ship-to party → Direct/Distributor, primary chain, zone, state, chains served |

### Facts (the "*" side)
| Table | Grain | Date join |
|---|---|---|
| `Fact Primary Sales` | Week × Store × Article | `Date Table[Date]` → `[Week Start Date]` |
| `Fact Offtake Sales` | Month × Store × Article | `Date Table[MonthStart]` → `[MonthStart]` |
| `Fact P&L` | Month × Chain × Brand × Category (derived) | `Date Table[MonthStart]` → `[MonthStart]` |
| `Fact Nielsen` | Month × Nielsen Cat × Brand × Zone | `Date Table[MonthStart]` → `[MonthStart]` |
| `Fact TDP` | Month × Chain × Article | `Date Table[MonthStart]` → `[MonthStart]` |
| `Fact Primary ShipTo` | Month × Ship-To × Chain × Brand | `Date Table[MonthStart]` → `[MonthStartCalc]` |
| `Fact Primary Article` | Month × Customer(Ship-to) × Chain × Brand × Article — DIST rows pre-exploded across chains by cont% (query 41); `[Chain]` is the allocated "Chain name for Dashboard", never a Ship To Name; unmatched rows carry "Unmapped Chain" | `Date Table[MonthStart]` → `[MonthStart]` |

### Helper / input tables
| Table | Role |
|---|---|
| `Primary Allocation Map` | secondary-derived Cont% by Month×Ship-To×Chain×Brand. Disconnected — read by DAX. Drives primary onto chains. |
| `Primary Allocation Override` | manual Cont% override (optional, ALL-wildcards). Disconnected — DAX prefers it. |
| `Assumption Table` | P&L inputs (margin %, spends) by Month×Chain×Brand×Category. Disconnected — read by DAX with ALL-fallback. |
| `Forecast Override` | manual forecast / growth assumption. Disconnected — read by DAX. |
| `Targets` | monthly FY target NSV. Joined on `Date Table[MonthStart]`. |
| `Store SO Mapping` | store → sales officer + split. Join `Store Code` → `Store Master[Store Code]` (or to facts). |
| `Sales Team Mapping` | unpivoted store × sales-person × Cont% (from Store SO Mapping). Used by the Forecast page for sales-person target ownership. Relate `Store Code` → `Fact Offtake Sales[Store Code]` (single, or keep disconnected and resolve in DAX). |
| `GST Rate QC Table` | Finance/Tax sign-off sheet for TOT%: Category, HSN Code, Pre/Post-GST%, Effective_From override, Confidence, Finance_Approved, auto-computed Impact_on_TOT_pct (query 37, from `SeedData/Masters/GST_Rate_QC_Table.csv`). Disconnected — read via `LOOKUPVALUE()` by the TOT% measures (`DAX/12_TOT_Measures.dax`). Every row starts Finance_Approved=Pending; several are LOW-confidence best-effort assumptions — see the CSV's Confidence/Note columns. |
| `GST Config` | Single editable cell: the GLOBAL default GST cutover date (query 38, from `SeedData/Masters/GST_Config.csv`) — default 2025-09-22 (GST Council's confirmed GST 2.0 effective date). Used by TOT% whenever a category's own `Effective_From` is blank. Disconnected — read via `MINX()`. |
| `PL Expense Input` | Month-on-month P&L expense input for CM2 (query 39, from `SeedData/Masters/PL_Expense_Input.csv`), editable by Finance/Ops — never hardcoded. **Related** to `Date Table[MonthStart]` (unlike the other helper tables above, which stay disconnected) so `DAX/13_CM2_Measures.dax`'s MoM Expense/CM2 Change measures work. `Resolved Chain`/`Resolved Brand`/`Resolved Category`/`Bad Brand Or Category` are calculated columns (not measures) — see that DAX file's setup note. |
| `CustCode Chain Map` | Customer Code → most-common Chain (query 40, derived from `Fact Primary Article` — add it AFTER query 16). Disconnected — read via `LOOKUPVALUE()` by `PL Expense Input[Resolved Chain]`. |
| `Dist Cont Weights` | Secondary-derived Distributor→Chain monthly split for the article-level DIST allocation (query 41, from `RawDataFolders/Dist_primary_cont_based_on_secondary_MOM.xlsx`, sheet "Dist Primary Conv to Chain Art"). Referenced BY query 16's merge — add it BEFORE re-applying 16. `[Raw Pct Sum]` ≠ 100 flags cont% variance pre-normalisation (QC rule 19). Not loaded to the model page itself (query-time only), so no relationship. |
| `NPI List` | **optional / gated** — load from `SeedData/Masters/NPI_List.csv` (columns: `Article` or `EAN`; the same file the offline agent's diff engine reads) once leadership supplies the NPI universe. Disconnected — `DAX/14_GrowthEngine_Measures.dax` §D resolves it via `TREATAS`. Do not paste §D before this table exists. |
| `NPI Run Rate Target` | **optional / gated** — one-cell Enter-Data table, column `[Target NSV Lacs]`, holding the leadership NPI monthly run-rate figure. Read by `DAX/14_GrowthEngine_Measures.dax` §D — the number is never hardcoded in DAX. |
| `Visibility Tracker` | **optional / gated** — monthly SOA/SOS/SOV audit input (`Month, Chain, Store Code, Metric ∈ {SOA,SOS,SOV}, Numerator, Denominator, Campaign`). No committed source exists yet — TDP/ACV (`DAX/05`) + Nielsen (`DAX/04`) are the committed proxies until it lands. Read by `DAX/14_GrowthEngine_Measures.dax` §E. Schema + collection SOP: `docs/GrowthEngine_BuildGuide.md` §6. |
| `_Measures` | holds all measures, no data. |

## Relationships (create exactly these)

```
Date Table[Date]        1 ─→ * Fact Primary Sales[Week Start Date]
Date Table[MonthStart]  1 ─→ * Fact Offtake Sales[MonthStart]
Date Table[MonthStart]  1 ─→ * Fact P&L[MonthStart]
Date Table[MonthStart]  1 ─→ * Fact Nielsen[MonthStart]
Date Table[MonthStart]  1 ─→ * Fact TDP[MonthStart]
Date Table[MonthStart]  1 ─→ * Targets[MonthStart]

Chain Master[Chain]     1 ─→ * Fact Offtake Sales[Chain]
Chain Master[Chain]     1 ─→ * Fact Primary Sales[Chain]
Chain Master[Chain]     1 ─→ * Fact P&L[Chain]
Chain Master[Chain]     1 ─→ * Fact TDP[Chain]

Brand Master[Brand]     1 ─→ * Fact Offtake Sales[Brand]
Brand Master[Brand]     1 ─→ * Fact Primary Sales[Brand]
Brand Master[Brand]     1 ─→ * Fact P&L[Brand]
Brand Master[Brand]     1 ─→ * Fact TDP[Brand]
Brand Master[Brand]     1 ─→ * Fact Nielsen[Brand]

Category Master[Category] 1 ─→ * Fact Offtake Sales[Category]
Category Master[Category] 1 ─→ * Fact Primary Sales[Category]
Category Master[Category] 1 ─→ * Fact P&L[Category]
Category Master[Category] 1 ─→ * Fact TDP[Category]
Category Master[Nielsen Category] 1 ─→ * Fact Nielsen[Nielsen Category]   (or via bridge)

Article Master[Article Code] 1 ─→ * Fact Offtake Sales[Article Code]
Article Master[Article Code] 1 ─→ * Fact Primary Sales[Article Code]
Article Master[Article Code] 1 ─→ * Fact TDP[Article Code]

Store Master[Store Code] 1 ─→ * Fact Offtake Sales[Store Code]
Store Master[Store Code] 1 ─→ * Fact Primary Sales[Store Code]
Store Master[Store Code] 1 ─→ * Store SO Mapping[Store Code]

Zone State Master[Zone]  1 ─→ * Fact Offtake Sales[Zone]   (or model zone via Store Master only)

Date Table[MonthStart]   1 ─→ * Fact Primary ShipTo[MonthStartCalc]
Chain Master[Chain]      1 ─→ * Fact Primary ShipTo[Chain]
Brand Master[Brand]      1 ─→ * Fact Primary ShipTo[Brand]
Ship-To Master[Ship To Name] 1 ─→ * Fact Primary ShipTo[Ship To Name]

Date Table[MonthStart]   1 ─→ * Fact Primary Article[MonthStart]
Chain Master[Chain]      1 ─→ * Fact Primary Article[Chain]
Brand Master[Brand]      1 ─→ * Fact Primary Article[Brand]
Category Master[Category] 1 ─→ * Fact Primary Article[Category]

Date Table[MonthStart]   1 ─→ * PL Expense Input[MonthStart]
```
`GST Rate QC Table`, `GST Config`, and `CustCode Chain Map` are intentionally NOT in this list — all three kept disconnected, read via `LOOKUPVALUE()` / `MINX()` (see `DAX/12_TOT_Measures.dax` and `DAX/13_CM2_Measures.dax`). `PL Expense Input` IS related to `Date Table` (for MoM Expense/CM2 Change) but has NO relationship to `Fact Primary Article` — Chain/Brand/Category-wise CM2 bridges the two tables explicitly in DAX instead, since the Customer-Code-first/Chain-fallback matching isn't a clean 1:many key.

### Ship-to primary allocation (new)
- `Fact Primary ShipTo` carries primary NSV **already allocated to Chain** by the
  secondary-derived `Cont%` (Direct = 100% to one chain; Distributor = split).
- `Primary Allocation Map` and `Primary Allocation Override` stay **disconnected**
  (no relationship) — they're read by the `07_PrimaryAllocation` measures, so the
  Cont% is dynamic and month-wise, never hardcoded in a measure.
- `Ship-To Master` is a normal dimension on `Ship To Name`. A distributor serves
  several chains, so the Ship-To↔Chain link lives in the fact, not the dimension.

### Modelling notes
- **Zone/State:** the cleanest design is to keep Zone/State on `Store Master`
  only and let stores carry the geography. The fact tables also carry Zone/State
  for files that arrive pre-aggregated above store level, so a direct
  `Zone State Master[Zone] → Fact[Zone]` relationship is provided as a fallback.
  Pick one consistent path to avoid ambiguous filters.
- **Nielsen Category bridge:** because several internal categories map to one
  Nielsen category, relate `Category Master[Nielsen Category]` to
  `Fact Nielsen[Nielsen Category]`. If that causes a many-to-many, use a small
  distinct `Nielsen Category` bridge table.
- **Primary vs Offtake at different grain** is fine: both relate to the same
  Date Table (Primary at day/week, Offtake at month). Comparison measures
  aggregate both to month.
- Set **Zone** sort by `Zone Sort Order`, **Month** by `Month Year Sort`,
  **Brand** by `Brand Sort Order`, **Category** by `Category Sort Order`.

## Hierarchies (drill-down / drill-up)

Native Power BI drill icons (the ⊙▼ / ⊙▲ chart-corner arrows and right-click
"Drill down / Expand") only appear when a visual's axis field is an explicit
**Hierarchy** object (Modeling ribbon → right-click the top field → "Create
Hierarchy" → drag child levels in) or a manually stacked multi-field axis.
None of these existed in the model until now — the star-schema tables above
already carry all the needed columns, so no new relationships are required,
only hierarchy objects on top of existing fields.

Create these on the dimension tables:

| Hierarchy | Table | Levels (top → bottom) | Used on |
|---|---|---|---|
| **Geography** | `Zone State Master` (or `Store Master`) | Zone → State → Chain → Store | Zone & State Performance page, Chain Performance page |
| **Product** | `Article Master` | Category → Sub-category → Brand → Article | SKU / Article Performance page, TDP Distribution page |
| **Product (pack)** | `Article Master` | Category → Brand → Pack Size → Article | SKU / Article Performance page (alt. drill path) |
| **Time** | `Date Table` | FY → Quarter → Month | any trend visual with `Date Table[MonthStart]` on the axis (Date Table is already marked as the model's date table, so Power BI auto-adds a Year/Quarter/Month/Day time hierarchy — this row makes the FY-based version explicit since Honasa's FY is Apr–Mar, not calendar-year) |

**Build steps in Power BI Desktop** (once per hierarchy):
1. Model view → open the dimension table → right-click the top-level field
   (e.g. `Zone`) → **Create Hierarchy**.
2. Drag the remaining levels in, in order (e.g. `State`, then `Chain`, then
   `Store`).
3. On each visual that uses the top field on its axis, drop the *hierarchy*
   object (not the bare field) — the drill arrows appear automatically in the
   visual's top-right corner.
4. Set **"Expand all down one level in the hierarchy"** vs **"Drill down"**
   per visual as preferred (right-click the visual → Drill options), so users
   can drill down to Store/Article and back up to Zone/Category with one
   click, mirroring the HTML dashboard's filter-chip drill-up.

This section closes the one confirmed gap found in this pass: the DAX/model
files already support every level of these hierarchies as flat columns, but
no `Hierarchy` object was ever defined, so the report-level drill icons would
not have appeared without this step. See `PageLayouts.md` for the specific
visuals each hierarchy should be dropped onto.
```
