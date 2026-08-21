---
name: mt-powerbi-dax
description: |
  Core DAX measures, Power Query M patterns, and semantic model design for MT Power BI reports.
  Use this skill when the user asks to: write a DAX measure (NSV, GM%, YTD total, store rank),
  design a star schema, build M scripts for ETL, create a date table, fix a measure, or design
  Power BI drill paths. Also triggers on: "write a DAX measure", "YTD calculation", "cumulative",
  "rank by", "moving average", "Power Query", "data model", "semantic model", "drill down",
  "PBIP measure", "slicer behavior", "filter context".
  Do NOT use for Python scripting, SQL queries, or dashboard frontend logic — route those
  to relevant skills.
---
# MT Power BI & DAX

Core DAX measures, Power Query M patterns, and star-schema design for MT semantic models.
Build measures that are filter-aware, time-intelligent, and testable.

## DAX Measure Design Tier

**S — Always enforce:**
- Measure names are UPPERCASE with prefix: `METRIC_NSV`, `METRIC_GM_PCT`, `METRIC_YTD_NSV`
- Comments above measure state: purpose, grain, expected filters, edge cases
- Explicit CALCULATE() with clear filter overrides (not implicit ALL)
- Handle division by zero: `DIVIDE([Numerator], [Denominator], 0)` or `IFERROR(., 0)`
- No hardcoded years/periods—derive from date slicer via `MAX(Dates[Date])`, `YEAR()`, etc.

**A — DAX patterns by measurement type:**
- **Rate (GM%, Market Share %):** `DIVIDE([Numerator_LY], [Denominator_LY])` with % formatting
- **YTD/Running Total:** `CALCULATE([Base Measure], DATESBETWEEN(Dates[Date], FY_START, MAX(Dates[Date])))`
- **Prior Period (YoY, MoM):** `CALCULATE([Base Measure], DATEADD(Dates[Date], -1, YEAR))` or MONTH
- **Rank:** `RANKX(ALLSELECTED(Dimension), [Measure], , DESC)` with tie handling
- **Top N Filter:** `IF(RANKX(...) <= N, [Measure], BLANK())`

**B — Semantic model star schema:**
- **Fact tables:** (Primary, Offtake, P&L) — contain only numeric measures (NSV, Qty, Expense)
- **Dimension tables:** (Chain, Brand, Category, Date, Geography) — linked via surrogate keys
- **Bridge table** (for many-to-many, e.g., Product ← Bridge → Promotion)
- **Date table:** Always explicit (not generated) with columns: Date, Year, Month, FY, Quarter, Week
- **Relationships:** One-to-many only; no circular or active relationships to same table

**C — Performance optimization:**
- Disable auto date/time hierarchy
- Summarize columns before relationship (if grain mismatch)
- Avoid CALCULATE-heavy measures; use variables instead
- Index fact tables on foreign keys

## Core DAX Measures (Copy-Paste Ready)

### 1. Primary NSV (Foundational)

```dax
METRIC_NSV = 
COMMENT: Primary Net Sales Value in ₹ Lakh. Grain: Chain × Month × Brand × Pack_Size.
COMMENT: Filters applied: Chain, Date (Month), Brand, Category. All Offtake grain ignored.
SUMX(
    SUMMARIZE(
        'Primary_Raw',
        'Primary_Raw'[Chain],
        'Primary_Raw'[Month],
        'Primary_Raw'[Brand],
        'Primary_Raw'[Pack_Size]
    ),
    'Primary_Raw'[NSV_Lakhs]
)
```

### 2. Gross Margin % (With Division Guard)

```dax
METRIC_GM_PCT = 
COMMENT: Gross Margin %. = (Gross Margin ₹ / NSV ₹) × 100.
COMMENT: Returns BLANK if NSV = 0 (avoids #DIV/0! error).
VAR gmLakhs = SUMX('P&L_Raw', 'P&L_Raw'[GM_Lakhs])
VAR nsvLakhs = [METRIC_NSV]
RETURN
DIVIDE(gmLakhs, nsvLakhs, BLANK()) * 100
```

### 3. Year-to-Date NSV (With FY Context)

```dax
METRIC_NSV_YTD = 
COMMENT: Cumulative NSV from FY start (Apr 1) to selected month.
COMMENT: Resets when user changes FY filter.
VAR selectedFY = MAX('Date'[FY])
VAR SelectedMonth = MAX('Date'[Month_Num])  // 1=Jan, ..., 12=Dec
VAR FYStartMonth = 4  // Apr = start of FY
VAR AdjustedMonthInFY = IF(SelectedMonth >= FYStartMonth, SelectedMonth - FYStartMonth + 1, SelectedMonth + 9)
RETURN
CALCULATE(
    [METRIC_NSV],
    FILTER(
        'Date',
        'Date'[FY] = selectedFY &&
        IF('Date'[Month_Num] >= FYStartMonth,
            'Date'[Month_Num] <= SelectedMonth,
            'Date'[Month_Num] >= FYStartMonth || 'Date'[Month_Num] <= SelectedMonth
        )
    )
)
```

### 4. Year-over-Year Growth (MoM equivalent)

```dax
METRIC_NSV_YoY = 
COMMENT: NSV growth vs same month prior year. Returns % (not decimal; show as %).
VAR currentNSV = [METRIC_NSV]
VAR priorYearNSV = CALCULATE(
    [METRIC_NSV],
    DATEADD('Date'[Date], -1, YEAR)
)
RETURN
DIVIDE(currentNSV - priorYearNSV, priorYearNSV, BLANK()) * 100
```

### 5. Store Rank (By Offtake, Per Chain)

```dax
METRIC_STORE_RANK = 
COMMENT: Rank each store by Offtake (descending) within selected chain.
COMMENT: Ties handled: DENSE_RANK (no gaps).
RANKX(
    ALLSELECTED('Store'[Store_Code]),
    [METRIC_OFFTAKE_QTY],
    ,
    DESC
)
```

### 6. Market Share %

```dax
METRIC_MARKET_SHARE_PCT = 
COMMENT: Mamaearth NSV / Total Market NSV (including competitors).
COMMENT: Requires 'Universe' dimension with Total Market NSV.
VAR mamaEarthNSV = [METRIC_NSV]
VAR marketNSV = CALCULATE(
    SUMX('Universe_Raw', 'Universe_Raw'[Total_Market_NSV_Lakhs]),
    ALLEXCEPT('Universe_Raw', 'Universe_Raw'[Month], 'Universe_Raw'[Chain])
)
RETURN
DIVIDE(mamaEarthNSV, marketNSV, BLANK()) * 100
```

### 7. Trade Spend ROI Multiple

```dax
METRIC_TRADE_SPEND_ROI = 
COMMENT: NSV / Trade Spend (ratio). Shows productivity of promotional investment.
COMMENT: ROI >= 3.0x is efficient; < 1.5x signals repricing/reallocation needed.
VAR nsvLakhs = [METRIC_NSV]
VAR spendLakhs = SUMX('P&L_Raw', 'P&L_Raw'[Trade_Spend_Lakhs])
RETURN
DIVIDE(nsvLakhs, spendLakhs, BLANK())
```

### 8. Moving Average (12-Month for Offtake Trend)

```dax
METRIC_OFFTAKE_MA12 = 
COMMENT: 12-month moving average of offtake quantity.
COMMENT: Smooths seasonal variation for trend detection.
VAR selectedDate = MAX('Date'[Date])
VAR priorMonths = DATESBETWEEN('Date'[Date], DATEADD(selectedDate, -11, MONTH), selectedDate)
RETURN
CALCULATE(
    AVERAGEX(priorMonths, [METRIC_OFFTAKE_QTY]),
    ALLEXCEPT('Offtake_Raw', 'Offtake_Raw'[Chain], 'Offtake_Raw'[Brand])
)
```

### 9. Percentage Distribution (Store Contribution to Total)

```dax
METRIC_STORE_PCT_OF_CHAIN = 
COMMENT: Each store's offtake as % of chain total.
COMMENT: Example: "This store is 2.3% of chain offtake."
VAR storeOfftake = [METRIC_OFFTAKE_QTY]
VAR chainTotal = CALCULATE(
    [METRIC_OFFTAKE_QTY],
    ALLEXCEPT('Store', 'Store'[Chain])
)
RETURN
DIVIDE(storeOfftake, chainTotal, BLANK()) * 100
```

### 10. Conditional Measure (Retail vs Institutional)

```dax
METRIC_NSV_RETAIL_ONLY = 
COMMENT: NSV from retail channels only (excludes institutional/online).
COMMENT: Filters on 'Store'[Channel] = "Retail".
CALCULATE(
    [METRIC_NSV],
    'Store'[Channel] = "Retail"
)
```

## Power Query M Patterns

### 1. Safe File Load with Error Handling

```m
let
    FilePath = Excel.CurrentWorkbook(){[Name="SourcePath"]}[Content]{0}[Column1],
    Source = try
        Excel.Workbook(File.Contents(FilePath & "\Primary_ShipTo.xlsb"))
    otherwise
        error "File not found: " & FilePath & "\Primary_ShipTo.xlsb. Check MT_SOURCES_DIR."
    ,
    Sheet = Source{[Item="Data",Kind="Sheet"]}[Data],
    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars=true]),
    Cleaned = Table.TransformColumnNames(Promoted, Text.Trim),
    CleanedLower = Table.TransformColumnNames(Cleaned, Text.Lower)
in
    CleanedLower
```

### 2. Month Label Derivation (Apr–Mar FY)

```m
let
    Source = your_table,
    AddFY = Table.AddColumn(
        Source,
        "FY",
        each
            let month = Date.Month([Date])
            let year = Date.Year([Date])
            in
            if month >= 4 then "FY" & Text.From(year - 2000 + 1)
            else "FY" & Text.From(year - 2000)
    ),
    AddMonthLabel = Table.AddColumn(
        AddFY,
        "Month_Label",
        each
            Text.ProperCase(Text.Start(Date.MonthName([Date]), 3)) & "-" & 
            Text.End(Text.From(Date.Year([Date])), 2)
    )
in
    AddMonthLabel
```

### 3. Reconciliation Check (Duplicate Detection)

```m
let
    Source = your_table,
    AddKey = Table.AddColumn(
        Source,
        "Grain_Key",
        each [Chain] & "|" & [Month] & "|" & [Brand] & "|" & [Pack_Size]
    ),
    DuplicateCount = Table.Group(
        AddKey,
        {"Grain_Key"},
        {{"Count", each Table.RowCount(_)}}
    ),
    Duplicates = Table.SelectRows(DuplicateCount, each [Count] > 1)
in
    if Table.RowCount(Duplicates) > 0 then
        error "Grain violation detected: " & Text.From(Table.RowCount(Duplicates)) & " duplicates"
    else
        Source
```

### 4. Date Table Generation

```m
let
    StartDate = #date(2024, 4, 1),  // FY25 start
    EndDate = #date(2027, 3, 31),   // FY27 end
    DayCount = Duration.Days(EndDate - StartDate) + 1,
    Dates = List.Dates(StartDate, DayCount, #duration(1, 0, 0, 0)),
    Table = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}, null, ExtraValues.Error),
    SetType = Table.TransformColumnTypes(Table, {{"Date", type date}}),
    AddYear = Table.AddColumn(SetType, "Year", each Date.Year([Date])),
    AddMonth = Table.AddColumn(AddYear, "Month_Num", each Date.Month([Date])),
    AddMonthName = Table.AddColumn(AddMonth, "Month", each Text.ProperCase(Text.Start(Date.MonthName([Date]), 3))),
    AddFY = Table.AddColumn(
        AddMonthName,
        "FY",
        each
            let m = [Month_Num]
            let y = [Year]
            in if m >= 4 then "FY" & Text.From(y - 2000 + 1) else "FY" & Text.From(y - 2000)
    ),
    AddQuarter = Table.AddColumn(
        AddFY,
        "Quarter",
        each
            let m = [Month_Num]
            in if m >= 4 then "Q" & Text.From(RoundUp((m - 3) / 3)) & " " & [FY]
               else "Q" & Text.From(RoundUp(m / 3)) & " " & [FY]
    )
in
    AddQuarter
```

### 5. Null Census (Data Quality Check in Load)

```m
let
    Source = your_table,
    Unpivot = Table.Unpivot(Source, List.Select(Table.ColumnNames(Source), each not Text.StartsWith(_, "Key")), "Column", "Value"),
    NullCount = Table.Group(
        Table.SelectRows(Unpivot, each [Value] = null or [Value] = "" or [Value] = "N/A"),
        {"Column"},
        {{"Count", each Table.RowCount(_)}}
    ),
    Filter = Table.SelectRows(NullCount, each [Count] > 0)
in
    if Table.RowCount(Filter) > 0 then
        error "Data quality issue: nulls detected in " & Text.Combine(Filter[Column], ", ")
    else
        Source
```

## Anti-Patterns (What NOT to Do)

| ❌ Anti-Pattern | ✓ Better Approach |
|-----------------|------------------|
| `=SUM([Column])` (implicit, unfiltered) | `CALCULATE(SUM(...), explicit filter)` |
| Hardcoded year `="FY" & 2027` | `="FY" & (YEAR(TODAY()) + 1)` (dynamic) |
| `ALL()` without exception | `ALLEXCEPT(Table, [Keep_These_Dims])` |
| `VAR` with no comment | `VAR varName = ... // Purpose: [explain]` |
| Complex nested IFs | Extract into separate measure + variable |
| Measure referencing other measures in M | All calculations in DAX; M loads only |
| No division guard `=A/B` | `DIVIDE(A, B, 0)` or `IFERROR(., 0)` |
| Circular relationships | Always one-to-many; use bridge for many-to-many |

## Testing DAX Measures

**Manual test checklist before publishing:**

1. **Blank filter:** Remove all filters; does measure show total as expected?
2. **Single filter:** Apply Chain filter; does measure show chain total only?
3. **Multiple filters:** Apply Chain + Month; does measure show intersection?
4. **Outlier data:** Test with extreme values (0, negative, very large); does error handling work?
5. **Prior period:** For YoY measure, does prior period show correct value?
6. **Historical consistency:** Does YTD measure for a closed month match archived report?

## Response Format
- Show complete DAX measure with COMMENT lines
- State expected filters and edge cases
- Provide M script example for data prep step
- Recommend test cases before deployment
- Flag any data model changes needed (new dimension, new relationship)
- Link to Power BI best practices doc for review
