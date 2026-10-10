# Full report parity: HTML dashboard to Power BI pages

Rebuilt by `scripts/build_full_report_pages.py`. Do not edit by hand.

Basis: Built from PageLayouts.md, model.bim and full_report_sources.json. Statuses are source-side only, not a Desktop result.

Required window: 2025-04 to 2026-08. HTML tabs: 11. HTML subviews: 11 (CLAUDE.md lists 9; `index.html` has 11).

## Tab and subview to page

| HTML tab | Subview | Power BI page | Page status | Why |
|---|---|---|---|---|
| Data Explorer | - | 11 Raw Data Export View | NO_SOURCE | No data files for: Fact Nielsen, Fact TDP |
| Executive Cockpit | - | 1 Executive Summary | NO_SOURCE | No data files for: Fact Nielsen, Fact TDP |
| Channel & Chain Performance | primary | 2B Ship-to Primary Allocation | PARTIAL | Months missing for: Fact Offtake Sales, Fact Primary ShipTo |
| Channel & Chain Performance | primary | 3 Chain Performance | PARTIAL | Months missing for: Fact Offtake Sales |
| Channel & Chain Performance | category | 6 Brand & Category Deep Dive | PARTIAL | Months missing for: Fact Offtake Sales |
| Channel & Chain Performance | reliance | 20 Reliance Brand Counter | PARTIAL | Months missing for: Fact Offtake Sales |
| Inventory & Supply Health | gap, velocity | 2 Primary vs Offtake Overview | PARTIAL | Months missing for: Fact Offtake Sales |
| Inventory & Supply Health | coverage | 8 Zone & State Performance | PARTIAL | Months missing for: Fact Offtake Sales |
| Inventory & Supply Health | tdp | 10 TDP Distribution Analysis | NO_SOURCE | No data files for: Fact Nielsen, Fact TDP |
| Inventory & Supply Health | storecuts | 21 State, Pack & Store Type | NO_SOURCE | No data files for: Fact Inhouse Distribution, Fact Pack Size, Fact Sales Cuts, Fact Store Type |
| Demand & S&OP Planning | forecast | 5 Forecast Dashboard | PARTIAL | Months missing for: Fact Offtake Sales |
| Demand & S&OP Planning | market-share | 9 Nielsen Market Share MoM | NO_SOURCE | No data files for: Fact Nielsen, Fact Nielsen Brand Cut, Fact Nielsen Pack, Fact Nielsen Pack Brand, Fact TDP |
| Demand & S&OP Planning | promo | 19 Promotional Impact | MODEL_ERROR | Measures use tables that do not exist: Dim_Calendar, Dim_PromoCalendar, Fact_ClaimMaster, Fact_Secondary_TOT_Hierarchy |
| P&L | - | 4 Chain-wise P&L | PARTIAL | Months missing for: Fact Offtake Sales |
| Performance & Comparison | - | 8 Zone & State Performance | PARTIAL | Months missing for: Fact Offtake Sales |
| Commercial Analytics | - | 7 SKU / Article Performance | NO_SOURCE | No data files for: Fact TDP |
| Operational Alerts | - | 22 Operational Alerts | NO_MODEL_SOURCE | Nothing in the model feeds this view |
| Store Audit Scorecard | - | 23 Store Audit Scorecard | NO_MODEL_SOURCE | Nothing in the model feeds this view |
| Supply Chain & Inventory | - | 24 Supply Chain & Inventory | NO_MODEL_SOURCE | Nothing in the model feeds this view |

## Pages in the layout with no HTML tab

- Page 12 Data Quality Check (PARTIAL): internal page, no HTML equivalent.
- Page 18 Refresh Guide (NO_MODEL_SOURCE): internal page, no HTML equivalent.

## Pages proposed because PageLayouts.md has none

- Page 19 Promotional Impact: 19 measures, status MODEL_ERROR.
- Page 20 Reliance Brand Counter: 7 measures, status PARTIAL.
- Page 21 State, Pack & Store Type: 36 measures, status NO_SOURCE.
- Page 22 Operational Alerts: 0 measures, status NO_MODEL_SOURCE.
- Page 23 Store Audit Scorecard: 0 measures, status NO_MODEL_SOURCE.
- Page 24 Supply Chain & Inventory: 0 measures, status NO_MODEL_SOURCE.

## Measure names in the layout text that are not in the model

Each is either a column/field written in backticks or a measure the layout expects but the model lacks. Check before building the visual.

- Page 3: `DataModel.md`
- Page 4: `Bad Brand Or Category`, `README.md`, `Resolved Brand`, `Resolved Category`, `Resolved Chain`, `TOT Method`, `TOT Pass-on Value`
- Page 7: `Article`, `DataModel.md`
- Page 8: `DataModel.md`
- Page 9: `Account Category`, `Account MoM %`, `Category % Of Chain`, `Face Wash Account Share %`, `IN URB MT`, `Our Articles`, `Share Gap Lakh`, `White Space Flag`, `YoY`
- Page 10: `DataModel.md`
- Page 11: `RefreshGuide.md`
- Page 12: `DQ Checks`
- Page 18: `RefreshGuide.md`

## Status meaning

- READY: every source table the page reads has data for the whole window.
- PARTIAL: some months missing. Show what exists, label it partial.
- NO_SOURCE: a source table has no data files. Show the incomplete banner.
- NO_MODEL_SOURCE: HTML-only view. Needs a source and a query before it can show numbers.
- MODEL_ERROR: a measure names a table that is not in the model. Fix the DAX first.
