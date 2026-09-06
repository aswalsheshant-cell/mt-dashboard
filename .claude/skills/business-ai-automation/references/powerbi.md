# Power BI — the PowerBI/ build kit

## Read before answering

Do not write a measure until you have checked whether it already exists.

```
PowerBI/
├─ README.md                       build order + checklist
├─ docs/DataModel.md               star schema, tables, relationships
├─ docs/DataDictionary.md          every column; which must NOT be renamed
├─ docs/PageLayouts.md             all 18 pages: visuals, fields, slicers
├─ docs/RefreshGuide.md            the monthly refresh SOP
├─ docs/ExportAndVisualSettings.md ₹L/Cr display units, export limits
├─ docs/DistributorPrimaryAllocation_Logic.md
├─ docs/SIS_Reconciliation.md
├─ theme/HonasaMT_Theme.json       View ▸ Themes ▸ Browse
├─ PowerQuery/*.pq                 paste into a Blank Query ▸ Advanced Editor
├─ DAX/*.dax                       paste into the _Measures table
├─ SeedData/{Masters,Mapping,Targets}
├─ RawDataFolders/<watch folders>  drop a file here → Refresh
└─ QuickSetup/                     consolidated PQ + DAX for a one-shot build
```

**Search `PowerBI/DAX/` for the measure name first.** There are 14 DAX files and
~1,400 lines of existing measures — most requests are already covered.

| Ask about | File |
|---|---|
| Date table, FY, month sort | `DAX/00_DateTable.dax` |
| NSV, Qty, growth, MTD/YTD, Cr/Lac labels | `DAX/01_CoreMeasures.dax` |
| Chain P&L, margin | `DAX/02_PnL_Measures.dax` |
| Forecast, target, achievement | `DAX/03_Forecast_Measures.dax`, `08_ForecastQC_Measures.dax` |
| Market share | `DAX/04_Nielsen_Measures.dax` |
| Distribution points | `DAX/05_TDP_Measures.dax` |
| Data-quality cards | `DAX/06_DataQuality_Measures.dax` |
| Primary allocation, article eligibility | `DAX/07_...`, `09_...` |
| SIS reconciliation | `DAX/10_SIS_Reconciliation.dax` |
| Export / display formatting | `DAX/11_ExportDisplay_Measures.dax` |
| TOT (trade terms) | `DAX/12_TOT_Measures.dax` |
| CM2 | `DAX/13_CM2_Measures.dax` |

Why the kit ships no `.pbix`: a `.pbix` is a binary produced only by Power BI Desktop.
Everything that can be pre-built is here. If asked to "produce the pbix", explain this
and point to `PowerBI/QuickSetup/README_QuickSetup.md` — never fabricate a binary.

## Model shape — star, not snowflake

One fact per grain, dimensions joined one-to-many, single direction.

- Facts: `Fact Offtake Sales`, `Fact Primary Sales`, `Fact PnL`, `Fact Nielsen`,
  `Fact TDP`, `Fact PrimaryShipTo`, `Fact PrimaryArticle`.
- Dimensions: `Date Table`, Chain, Brand, Category, Article, Zone, Store, Ship-To.

Rules:

1. **`Date Table` is the only date dimension** and it is marked as the date table.
   Every time-intelligence measure filters `'Date Table'`, never a fact's own date.
2. **Single-direction relationships.** Bi-directional filtering is banned except for a
   deliberate many-to-many bridge, documented in `docs/DataModel.md`.
3. **No calculated columns where a measure will do.** Columns cost model memory and
   do not respond to filter context.
4. **Never rename a column listed in `docs/DataDictionary.md`** — the `.pq` queries and
   every measure bind to those names.
5. Fact tables hold keys and numbers only; all descriptive text lives in dimensions.

## DAX conventions used in this kit — match them

```dax
// Naming: business language, spaces allowed, no Hungarian prefixes.
Total Offtake NSV = SUM ( 'Fact Offtake Sales'[Offtake NSV] )

// Every division uses DIVIDE() — never the "/" operator.
// DIVIDE returns BLANK on a zero denominator; "/" returns Infinity and breaks visuals.
Realisation per Unit = DIVIDE ( [Total Offtake NSV], [Total Offtake Qty] )

// VAR ... RETURN for anything with more than one step. Name the VAR after what it is.
Offtake Growth % =
VAR _current  = [Total Offtake NSV]
VAR _lastYear = CALCULATE ( [Total Offtake NSV], SAMEPERIODLASTYEAR ( 'Date Table'[Date] ) )
RETURN
    DIVIDE ( _current - _lastYear, _lastYear )

// Display measures are separate from calculation measures.
NSV (Cr) = DIVIDE ( [NSV], 10000000 )
```

Formatting style in this kit: uppercase functions, spaces inside parentheses,
`'Table'[Column]` fully qualified for columns, `[Measure]` unqualified for measures.
Keep it — a diff of a `.dax` file should show only the new measure.

### The five DAX rules that prevent wrong numbers

1. **`DIVIDE()` always.** No `/`.
2. **Qualify columns, never qualify measures.** `'Fact Offtake Sales'[Offtake NSV]`
   and `[NSV]`. Mixing these up is the most common source of confusing errors.
3. **`CALCULATE` overwrites filter context; `KEEPFILTERS` intersects it.** Use
   `CALCULATE([NSV], KEEPFILTERS('Dim Chain'[Chain] = "DMART"))` when the user's slicer
   selection must still apply.
4. **`ALL` vs `ALLSELECTED`.** Contribution-to-total on a page that has slicers wants
   `ALLSELECTED` — `ALL` ignores the slicer and gives a percentage that does not sum
   to 100 % on screen.
   ```dax
   Contribution % =
   DIVIDE ( [NSV], CALCULATE ( [NSV], ALLSELECTED ( 'Dim Chain'[Chain] ) ) )
   ```
5. **Time intelligence needs a contiguous date table.** If a measure returns blank for
   FY27, check `DAX/00_DateTable.dax` covers those dates before debugging the measure.

### Indian FY in DAX

Apr–Mar. Derive it in the date table, never hardcode a year list.

```dax
FY Tag  = "FY" & FORMAT ( IF ( MONTH ( [Date] ) >= 4, YEAR ( [Date] ) + 1, YEAR ( [Date] ) ), "00" )
FY Month No = MOD ( MONTH ( [Date] ) - 4, 12 ) + 1     -- 1 = Apr ... 12 = Mar
FY Quarter  = "Q" & ROUNDUP ( DIVIDE ( MOD ( MONTH ( [Date] ) - 4, 12 ) + 1, 3 ), 0 )
```

Then **Sort by column**: `Month Name` sorted by `FY Month No`. Without this every
trend visual shows Apr after Aug. This is the most frequent "the chart looks wrong"
cause in this model.

FY27 and beyond must appear automatically as months arrive — never add a hardcoded
`FY25`/`FY26` branch.

## Power Query (M) conventions

- `00_Parameters.pq` defines `pRootFolder` — **the one thing each machine sets.**
  Never hardcode a path in any other query.
- `01_fnCombineFolder.pq` is the refresh engine: it combines every `.csv`/`.xlsx`/`.xlsb`
  in a watch folder, skips files starting with `_` (templates, archives), and adds
  `[Data Source File]` and `[Refresh Date]` audit columns. Reuse it; do not write a
  second folder-combine.
- Step names in M are descriptive (`OnlyData`, `HeaderIndex`), matching the existing
  files. `Changed Type2` style auto-names are not acceptable.
- **Set data types explicitly at the end of every query.** An untyped column loads as
  `any` and breaks relationships.
- Do the filtering as early as possible so folding survives; do not add an index
  column unless it is needed, because it kills folding.

## Monthly refresh SOP

1. Drop the new month's file into the matching `PowerBI/RawDataFolders/<watch>/` folder.
   Name it so it does **not** start with `_`.
2. Power BI Desktop ▸ **Refresh**.
3. Open the Data Quality page and confirm every card is green
   (`DAX/06_DataQuality_Measures.dax`).
4. Check period completeness: the new month appears, and no prior month changed.
5. Publish.

Full SOP: `PowerBI/docs/RefreshGuide.md`. If a card goes red, stop and switch to
`sales-data-reconciliation` — do not "fix" it by editing the measure.

## Performance

- Import mode, not DirectQuery, for this model.
- Remove unused columns in Power Query, not in the report — unused columns still load.
- High-cardinality text columns (site code, EAN, bill number) are the memory cost;
  keep them only where a visual actually needs them.
- Avoid `FILTER(ALL(BigFactTable), ...)`; filter the dimension instead.
- Measures over calculated columns; calculated columns over calculated tables.

