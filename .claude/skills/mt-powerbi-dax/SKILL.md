---
name: mt-powerbi-dax
description: |
  Power BI DAX measures, semantic model design, and Power Query M patterns for Modern Trade
  MT reporting at Honasa/Mamaearth. Use this skill when the user asks to: write a DAX measure,
  fix a DAX formula, build a Power BI data model, write Power Query M code, design a star
  schema for MT, create a calculated column, write a time-intelligence measure, build a
  KPI card, fix a CALCULATE/FILTER issue, design the semantic layer, or says: "DAX for this",
  "Power BI measure", "why is my DAX wrong", "write M code", "Power Query transform",
  "calculated table", "SUMX measure", "RANKX for stores", "time intelligence in Power BI",
  "SAMEPERIODLASTYEAR", "what table relationships", "star schema for MT", "how to model this",
  "DAX for YoY", "MTD/YTD measure".
  Do NOT use for Python scripts (use mt-python-pipeline), SQL queries (use mt-sql-analytics),
  or Excel formulas (use excel-automation).
---

# MT Power BI / DAX

Build production-grade DAX measures and Power Query transformations for the Honasa MT
semantic model — clean, performant, and aligned to the Apr–Mar Indian FY.

## Semantic Model Architecture (Star Schema)

```
Fact Tables:
  Fact_Primary      → month_key, chain_key, brand_key, pack_key | nsv_lakhs, qty_cases
  Fact_Offtake      → month_key, chain_key, store_key, ean_key  | qty_sold, value_sold_lakhs
  Fact_PL           → month_key, chain_key                      | gm_lakhs, trade_spend_lakhs
  Fact_Distribution → month_key, chain_key, ean_key             | numeric_dist, weighted_dist

Dimension Tables:
  Dim_Date    → date, month_label, month_num, fy_tag, quarter_tag, is_current_month
  Dim_Chain   → chain_key, chain_name, channel_type, region, tier
  Dim_Store   → store_key, site_code, site_name, chain_key, city, pincode
  Dim_Brand   → brand_key, brand_name, category, sub_category
  Dim_EAN     → ean_key, ean, product_name, pack_size, brand_key, gm_pct_std
```

## FY Logic in DAX (Indian FY, Apr–Mar)

```dax
-- Calculated column in Dim_Date
FY Tag =
VAR mon = MONTH(Dim_Date[Date])
VAR yr  = YEAR(Dim_Date[Date])
RETURN
    IF(mon >= 4,
        "FY" & FORMAT(yr + 1 - 2000, "00"),
        "FY" & FORMAT(yr - 2000, "00")
    )

-- Current FY (dynamic)
Current FY = CALCULATE(MAX(Dim_Date[FY Tag]), Dim_Date[Is Current Month] = TRUE)
```

## Core MT Measures

### NSV and Volume

```dax
[Primary NSV (₹L)] =
SUMX(Fact_Primary, Fact_Primary[nsv_lakhs])

[Primary NSV vs Prior FY] =
VAR cur = [Primary NSV (₹L)]
VAR pri =
    CALCULATE(
        [Primary NSV (₹L)],
        SAMEPERIODLASTYEAR(Dim_Date[Date])
    )
RETURN cur - pri

[Primary NSV vs Prior FY %] =
DIVIDE(
    [Primary NSV vs Prior FY],
    ABS(CALCULATE([Primary NSV (₹L)], SAMEPERIODLASTYEAR(Dim_Date[Date]))),
    BLANK()
)
```

### Offtake

```dax
[Offtake Value (₹L)] =
SUMX(Fact_Offtake, Fact_Offtake[value_sold_lakhs])

[Primary-Offtake Gap (₹L)] =
[Primary NSV (₹L)] - [Offtake Value (₹L)]

[Primary-Offtake Gap %] =
DIVIDE([Primary-Offtake Gap (₹L)], [Primary NSV (₹L)], BLANK())
```

### Gross Margin

```dax
[Gross Margin (₹L)] =
SUM(Fact_PL[gm_lakhs])

[GM %] =
DIVIDE([Gross Margin (₹L)], [Primary NSV (₹L)], BLANK())

[GM % vs Prior Period (pp)] =
VAR cur_gm = [GM %]
VAR pri_gm =
    CALCULATE(
        [GM %],
        DATEADD(Dim_Date[Date], -1, MONTH)
    )
RETURN cur_gm - pri_gm
```

### Store Ranking

```dax
[Store Rank by Offtake] =
RANKX(
    ALLSELECTED(Dim_Store[site_name]),
    CALCULATE([Offtake Value (₹L)]),
    ,
    DESC,
    DENSE
)
```

### Running Totals (YTD)

```dax
[Primary NSV YTD] =
CALCULATE(
    [Primary NSV (₹L)],
    DATESYTD(Dim_Date[Date], "31-3")   -- Indian FY ends 31 March
)

[Offtake YTD] =
CALCULATE(
    [Offtake Value (₹L)],
    DATESYTD(Dim_Date[Date], "31-3")
)
```

### Trade Spend

```dax
[Trade Spend (₹L)] =
SUM(Fact_PL[trade_spend_lakhs])

[Trade Spend % of NSV] =
DIVIDE([Trade Spend (₹L)], [Primary NSV (₹L)], BLANK())

[Trade Spend ROI] =
DIVIDE([Offtake Value (₹L)], [Trade Spend (₹L)], BLANK())
-- Target > 1.5 = positive incremental ROI
```

### Distribution

```dax
[Numeric Distribution %] =
AVERAGEX(Fact_Distribution, Fact_Distribution[numeric_dist])

[Weighted Distribution %] =
AVERAGEX(Fact_Distribution, Fact_Distribution[weighted_dist])
```

## Power Query M — Key MT Patterns

### XLSB File Loading

```m
let
    Source = Excel.Workbook(File.Contents("C:\MT\Primary_FY27.xlsb"), null, true),
    Sheet  = Source{[Item="Sheet1",Kind="Sheet"]}[Data],
    Headers = Table.PromoteHeaders(Sheet, [PromoteAllScalars=true]),
    // Preserve identifiers as text
    Typed  = Table.TransformColumnTypes(Headers, {
        {"Site Code",    type text},
        {"EAN",          type text},
        {"Article Code", type text}
    })
in
    Typed
```

### FY Tag Column (Power Query)

```m
// Add FY Tag column based on Month Label (e.g. "Apr-26" → "FY27")
AddFYTag = Table.AddColumn(PrevStep, "FY Tag", each
    let
        parts = Text.Split([Month Label], "-"),
        mon   = parts{0},
        yr    = Number.FromText("20" & parts{1}),
        monNum = Date.Month(Date.FromText("1 " & mon & " " & Text.From(yr))),
        fyNum  = if monNum >= 4 then yr + 1 - 2000 else yr - 2000
    in
        "FY" & Text.PadStart(Text.From(fyNum), 2, "0"),
    type text
)
```

### Unpivot Monthly Columns to Rows

```m
// Convert wide monthly format (Jan-26, Feb-26 ...) to tall format
Unpivoted = Table.UnpivotOtherColumns(
    WithFY,
    {"Chain Name", "Brand Name", "Pack Size"},  // keep these as-is
    "Month Label",                               // new column name for headers
    "NSV Lakhs"                                  // new column name for values
)
```

### Reliance Brand Counter Filter

```m
// Must use exact text comparison — 'non brand counter' must NOT be removed
FilteredBC = Table.SelectRows(
    PrevStep,
    each not (
        Text.Contains(Text.Lower([Chain Name]), "reliance") and
        Text.Lower([Data Status]) = "brand counter"  // exact match
    )
)
```

## Model Relationship Rules

1. All fact tables connect to Dim_Date on date/month_key — always a MANY-to-ONE
2. Dim_Store connects to Dim_Chain — cascade chain filter through store
3. Dim_EAN connects to Dim_Brand — filter products by brand/category
4. Cross-filter direction: always single (Fact → Dim) unless explicitly justified
5. Never create bidirectional relationships without documenting why

## DAX Anti-Patterns to Avoid

| Bad pattern | Fix |
|---|---|
| `CALCULATE([M], ALL(Dim_Date))` losing chain filter | Use `KEEPFILTERS` or `REMOVEFILTERS(Dim_Date)` specifically |
| `SUMX(table, [measure])` where measure aggregates further | Use `SUM(table[column])` inside SUMX |
| Hardcoded FY ("FY26") in measures | Use `[Current FY]` calculated measure |
| RANKX without ALLSELECTED | Store rank changes with every slicer — usually wrong |
| Implicit BLANK() in DIVIDE ignored | Always test: does BLANK() propagate correctly in your visual? |

## Output Format for DAX Help

1. Show the complete DAX measure with proper indentation
2. State what context it expects (filter, slicer dependency)
3. Note any performance consideration (SUMX on large fact tables)
4. Provide the test case: "With Month = Jun-26 and Chain = Reliance, this should return X"
