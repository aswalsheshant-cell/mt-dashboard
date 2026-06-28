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
```

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
```
```
