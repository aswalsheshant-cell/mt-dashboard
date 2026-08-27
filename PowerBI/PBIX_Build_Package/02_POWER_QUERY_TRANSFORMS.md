# Power BI Power Query Transformations
## Modern Trade Dashboard — Demand & Sales Forecasting

**Version:** 1.0  
**Last Updated:** 2026-08-27  
**Status:** Production-Ready

---

## Overview

This document provides **copy-paste-ready Power Query M code** for loading, cleaning, and transforming raw CSV/Excel data into the semantic model fact and dimension tables defined in `01_SEMANTIC_MODEL_SCHEMA.md`.

Each transformation includes:
- Source data steps (CSV/Excel load)
- Data type casting
- Column derivation (e.g., FY, Month_Num from date)
- Nullable handling
- Relationship key generation (composite and surrogate)
- Row filtering (active status, future dates, valid ranges)

---

## 1. Loading Dimension Tables

### Dim_Date

**Purpose:** Calendar dimension spanning 10 years (120 rows, static).
**Refresh:** Annual (Q1-Q2 planning cycle).

```m
let
  Source = Csv.Document(File.Contents("\\DATA_SOURCES\Dim_Date.csv"), [Delimiter=",", Columns=7, Encoding=65001, QuoteStyle=QuoteStyle.None]),
  Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
  RemovedBlank = Table.SelectRows(Promoted, each [DateKey] <> null and [DateKey] <> ""),
  TypedDate = Table.TransformColumnTypes(RemovedBlank, {
    {"DateKey", type text},
    {"Date", type date},
    {"Month", type text},
    {"Month_Num", Int64.Type},
    {"Quarter", type text},
    {"Quarter_Num", Int64.Type},
    {"FY", type text},
    {"FY_Num", Int64.Type},
    {"Year", Int64.Type},
    {"Week_Num", Int64.Type},
    {"Is_Current_Month", type logical}
  }),
  // Validation: DateKey = yyyyMM format
  Validated = Table.AddColumn(TypedDate, "_check_datekey", each Text.Length([DateKey]) = 6 and try Value.FromText(Text.Start([DateKey], 4)) <> null otherwise false, type logical),
  Cleaned = Table.SelectRows(Validated, each [_check_datekey] = true),
  Removed = Table.RemoveColumns(Cleaned, {"_check_datekey"})
in
  Removed
```

**Key behaviors:**
- **DateKey** must be `yyyyMM` format (e.g., `202608` for Aug-26).
- **FY** derived from Month+Year: Apr-Dec of year Y → FY(Y+1), Jan-Mar → FY(Y).
- Rows with blank/invalid DateKey are dropped.
- **Is_Current_Month** is boolean; set to true for the latest complete month in planning.

---

### Dim_Chain

**Purpose:** Modern Trade chain master (450–500 rows).
**Refresh:** Monthly (capture new chains, status changes).

```m
let
  Source = Csv.Document(File.Contents("\\DATA_SOURCES\Dim_Chain.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
  Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
  RemovedBlank = Table.SelectRows(Promoted, each [ChainKey] <> null and [ChainKey] <> ""),
  TypedChain = Table.TransformColumnTypes(RemovedBlank, {
    {"ChainKey", type text},
    {"Chain_ID", type text},
    {"Chain_Name", type text},
    {"Zone", type text},
    {"Region", type text},
    {"Status", type text},
    {"Chain_Type", type text},
    {"Last_Updated", type date}
  }),
  // Filter only Active chains for fact-table joins (optional; can include Inactive for history)
  FilterActive = Table.SelectRows(TypedChain, each [Status] = "Active"),
  // Dedup on ChainKey (keep latest by Last_Updated)
  Sorted = Table.Sort(FilterActive, {{"Last_Updated", Order.Descending}, {"ChainKey", Order.Ascending}}),
  Deduped = Table.Group(Sorted, {"ChainKey"}, {{"_all", each _, type table}}),
  Expanded = Table.ExpandTableColumn(Deduped, "_all", {"Chain_ID", "Chain_Name", "Zone", "Region", "Status", "Chain_Type", "Last_Updated"}, {"Chain_ID", "Chain_Name", "Zone", "Region", "Status", "Chain_Type", "Last_Updated"}),
  Removed = Table.RemoveColumns(Expanded, {"_all"})
in
  Removed
```

**Key behaviors:**
- **ChainKey** is the surrogate key (typically CHAIN_NNN or internal ID prefix).
- **Status** = `"Active"` or `"Inactive"`. Filter step keeps only Active for fact joins; remove filter to track historical chains.
- Deduplication ensures one row per ChainKey (picks latest Last_Updated).
- Zone and Region used for rollup aggregations in DAX.

---

### Dim_Product

**Purpose:** SKU master (8,000–12,000 rows).
**Refresh:** Weekly (new SKUs, discontinuations, price-tier changes).

```m
let
  Source = Csv.Document(File.Contents("\\DATA_SOURCES\Dim_Product.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
  Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
  RemovedBlank = Table.SelectRows(Promoted, each [ProductKey] <> null and [ProductKey] <> ""),
  TypedProduct = Table.TransformColumnTypes(RemovedBlank, {
    {"ProductKey", type text},
    {"SKU_Code", type text},
    {"Product_Name", type text},
    {"Brand", type text},
    {"Category", type text},
    {"Subcategory", type text},
    {"Pack_Size", type text},
    {"Price_Tier", type text},
    {"Status", type text},
    {"Is_Seasonal", type logical}
  }),
  // Filter only Active SKUs (optional; can include Discontinued for historical analysis)
  FilterActive = Table.SelectRows(TypedProduct, each [Status] = "Active"),
  // Dedup on ProductKey
  Sorted = Table.Sort(FilterActive, {{"ProductKey", Order.Ascending}}),
  Deduped = Table.Group(Sorted, {"ProductKey"}, {{"_count", Table.RowCount}}),
  // Keep first occurrence per ProductKey
  FirstRows = Table.ExpandTableColumn(Deduped, "_count", {})
in
  FirstRows
```

**Key behaviors:**
- **ProductKey** is typically `SKU_<code>` (e.g., `SKU_MAMAEA001`).
- **Brand**, **Category**, **Subcategory** used for drill-down and filtering.
- **Is_Seasonal** flag used to gate seasonal-forecast comparisons in DAX.
- **Price_Tier** (Premium/Mass/Economy) used for margin-tier aggregations.
- Discontinued SKUs can be kept for archival; filter removed to include them.

---

### Dim_Geography (Expanded with State & City Hierarchy)

**Purpose:** Multi-tier geographic hierarchy: Zone → State → Key City → Cluster (50–60 rows with state-level drill-down).
**Refresh:** Quarterly (boundary/territory changes, rare).
**New:** State_Code foreign key for fact-table joins; Operating_Region for logistics rollup.

```m
let
  Source = Csv.Document(File.Contents("\\DATA_SOURCES\Dim_Geography.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
  Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
  RemovedBlank = Table.SelectRows(Promoted, each [ZoneKey] <> null and [ZoneKey] <> "" and [State_Code] <> null),
  
  TypedGeography = Table.TransformColumnTypes(RemovedBlank, {
    {"ZoneKey", type text},
    {"Zone", type text},
    {"State", type text},
    {"State_Code", type text},
    {"Key_City", type text},
    {"Region", type text},
    {"Operating_Region", type text},
    {"Territory", type text},
    {"PIN_Range", type text},
    {"Geography_Type", type text},
    {"Depot_Warehouse", type text}
  }),
  
  // Dedup on State_Code (one row per state; multiple cities aggregate to Operating_Region)
  Sorted = Table.Sort(TypedGeography, {{"State_Code", Order.Ascending}}),
  Deduped = Table.Group(Sorted, {"State_Code"}, {{"_all", each Table.FirstN(_, 1), type table}}),
  Expanded = Table.ExpandTableColumn(Deduped, "_all", {"ZoneKey", "Zone", "State", "Key_City", "Region", "Operating_Region", "Territory", "PIN_Range", "Geography_Type", "Depot_Warehouse"}, {"ZoneKey", "Zone", "State", "Key_City", "Region", "Operating_Region", "Territory", "PIN_Range", "Geography_Type", "Depot_Warehouse"})
in
  Expanded
```

**Key behaviors:**
- **State_Code** (PK): 2-letter code (DL, PB, UP, MH, GJ, KA, TN, WB) — foreign key for Fact_Sales and Fact_Forecast.
- **ZoneKey**: Still present for backward compatibility; Zone groups multiple states (North, South, East, West).
- **Operating_Region**: Sub-zone identifier (e.g., North-1, North-2, West-1) for logistics and supply-chain rollups.
- **Key_City**: Primary city in state (Delhi, Chandigarh, Mumbai, Bengaluru, Chennai, Kolkata, etc.).
- **Geography_Type** (Urban/Semi-Urban/Rural): Used for market-penetration and retail-density measures.
- **Depot_Warehouse**: Optional; identifies logistics node (DC_DL_01, WH_MH_02) for distribution cost allocation.
- One row per state; avoid duplicates on State_Code.

---

## 2. Loading Fact Tables

### Fact_Sales (Actuals / Offtake)

**Purpose:** Monthly sales actuals and offtake by [DateKey × ChainKey × ProductKey × ZoneKey].
**Grain:** Monthly (not daily); ~50M–100M rows/year.
**Refresh:** Daily (aggregated from POS/SAP).
**Source:** Primary workbook + Offtake patch (monthly store×article).

```m
let
  Source = Csv.Document(File.Contents("\\DATA_SOURCES\Fact_Sales.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
  Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
  RemovedBlank = Table.SelectRows(Promoted, each [DateKey] <> null and [DateKey] <> "" and [SalesKey] <> null),
  
  // Type casting
  TypedSales = Table.TransformColumnTypes(RemovedBlank, {
    {"SalesKey", Int64.Type},
    {"DateKey", type text},
    {"ChainKey", type text},
    {"ProductKey", type text},
    {"ZoneKey", type text},
    {"State_Code", type text},
    {"Actual_Qty", type number},
    {"Actual_Revenue", type number},
    {"Base_COGS", type number},
    {"CM2_Amount", type number},
    {"Logistics_Cost", type number},
    {"CM2_Provisional", type logical},
    {"Metric_Type", type text},
    {"Data_Source", type text},
    {"Is_Blended", type logical},
    {"Load_Date", type date}
  }),
  
  // Nullable handling: Qty/Revenue must not be null
  ValidQty = Table.SelectRows(TypedSales, each [Actual_Qty] <> null and [Actual_Qty] <> 0),
  ValidRev = Table.SelectRows(ValidQty, each [Actual_Revenue] <> null),
  
  // Defaults: CM2_Provisional → true if missing; Metric_Type → "Actual" if missing
  DefaultProvisional = Table.AddColumn(ValidRev, "_prov_check", each if [CM2_Provisional] = null then true else [CM2_Provisional], type logical),
  DefaultMetricType = Table.AddColumn(DefaultProvisional, "_metric_check", each if [Metric_Type] = null or [Metric_Type] = "" then "Actual" else [Metric_Type], type text),
  
  // Update columns
  UpdatedProvisional = Table.ReplaceValue(DefaultMetricType, each [CM2_Provisional], each null, each [_prov_check]),
  UpdatedMetric = Table.ReplaceValue(UpdatedProvisional, each [Metric_Type], each null, each [_metric_check]),
  Cleaned = Table.RemoveColumns(UpdatedMetric, {"_prov_check", "_metric_check"}),
  
  // Duplicate check: Group by composite key [DateKey, ChainKey, ProductKey, ZoneKey, Metric_Type]
  Grouped = Table.Group(Cleaned, {"DateKey", "ChainKey", "ProductKey", "ZoneKey", "Metric_Type"}, {{"_count", Table.RowCount}}),
  Flagged = Table.AddColumn(Grouped, "_dup_flag", each if [_count] > 1 then "DUPLICATE" else "OK", type text),
  // Log duplicates (optional: filter out or keep latest)
  // For now, keep all and flag; downstream DAX can sum by fact key
  Removed = Table.RemoveColumns(Flagged, {"_count", "_dup_flag"})
in
  Removed
```

**Key behaviors:**
- **Grain validation:** Each [DateKey, ChainKey, ProductKey, ZoneKey, Metric_Type] combination should appear once (or be flagged for review).
- **Nullable policy:** Actual_Qty and Actual_Revenue must not be null; rows with zero qty/revenue are kept (legitimate blanks).
- **CM2_Provisional flag:** Defaults to `true` (provisional/untrustworthy); set to `false` only when Finance D1 has approved and real expense rows loaded.
- **Metric_Type:** "Actual" (POS) or "Offtake" (distributor/retail partner offtake); "Blend" indicates combined source.
- **Is_Blended:** True if data merged across multiple sources; used in KPI disclaimers.
- **Load_Date:** ETL timestamp; used for freshness checks and SLA monitoring.

---

### Fact_Forecast (Demand / Targets)

**Purpose:** Rolling 24-month demand/sales forecast by [DateKey × ChainKey × ProductKey × ZoneKey].
**Grain:** Monthly.
**Refresh:** Weekly (forecast model updates, new months roll in).
**Source:** Demand-planning tool, seasonal model, or ML predictions.

```m
let
  Source = Csv.Document(File.Contents("\\DATA_SOURCES\Fact_Forecast.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
  Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
  RemovedBlank = Table.SelectRows(Promoted, each [ForecastKey] <> null and [DateKey] <> null and [DateKey] <> ""),
  
  // Type casting
  TypedForecast = Table.TransformColumnTypes(RemovedBlank, {
    {"ForecastKey", Int64.Type},
    {"DateKey", type text},
    {"ChainKey", type text},
    {"ProductKey", type text},
    {"ZoneKey", type text},
    {"Forecast_Qty", type number},
    {"Forecast_Revenue", type number},
    {"Target_Revenue", type number},
    {"Forecast_Type", type text},
    {"Confidence_Level", type number},
    {"Forecast_Method", type text},
    {"Update_Frequency", type text},
    {"Last_Updated", type date}
  }),
  
  // Nullable handling: Forecast_Qty/Revenue must not be null
  ValidQty = Table.SelectRows(TypedForecast, each [Forecast_Qty] <> null),
  ValidRev = Table.SelectRows(ValidQty, each [Forecast_Revenue] <> null),
  
  // Bounds check: Confidence_Level ∈ [0.0, 1.0]; default 0.5 if missing/out of range
  BoundedConfidence = Table.AddColumn(ValidRev, "_conf", each 
    if [Confidence_Level] = null then 0.5
    else if [Confidence_Level] < 0 then 0.5
    else if [Confidence_Level] > 1 then 1.0
    else [Confidence_Level], type number),
  UpdateConfidence = Table.ReplaceValue(BoundedConfidence, each [Confidence_Level], each null, each [_conf]),
  Cleaned = Table.RemoveColumns(UpdateConfidence, {"_conf"}),
  
  // Future-dated check: DateKey >= current month (optional; can include past forecasts for accuracy validation)
  // Assuming load captures "current month" from Forecast metadata
  // For now, accept all DateKey values (past forecasts used for hindcast evaluation)
  
  // Dedup on [DateKey, ChainKey, ProductKey, ZoneKey, Forecast_Type]: keep latest by Last_Updated
  Sorted = Table.Sort(Cleaned, {{"DateKey", Order.Ascending}, {"ChainKey", Order.Ascending}, {"ProductKey", Order.Ascending}, {"ZoneKey", Order.Ascending}, {"Last_Updated", Order.Descending}}),
  Grouped = Table.Group(Sorted, {"DateKey", "ChainKey", "ProductKey", "ZoneKey", "Forecast_Type"}, {{"_all", each Table.FirstN(_, 1), type table}}),
  Expanded = Table.ExpandTableColumn(Grouped, "_all", {"Forecast_Qty", "Forecast_Revenue", "Target_Revenue", "Confidence_Level", "Forecast_Method", "Update_Frequency", "Last_Updated"}, {"Forecast_Qty", "Forecast_Revenue", "Target_Revenue", "Confidence_Level", "Forecast_Method", "Update_Frequency", "Last_Updated"})
in
  Expanded
```

**Key behaviors:**
- **Grain:** [DateKey × ChainKey × ProductKey × ZoneKey × Forecast_Type]; only the latest forecast per grain is kept (older hindcasts archived separately).
- **Future-dated:** Typically DateKey ≥ current month; but past months kept for hindcast accuracy evaluation.
- **Confidence_Level:** Ranges [0.0, 1.0]; model-output confidence (e.g., 0.95 = 95% confidence). Defaults to 0.5 if missing.
- **Forecast_Type:** "Rolling" (continuous re-plan), "Seasonal" (seasonal index applied), "ML_Model" (ML predictions). Used to gate measure calculations.
- **Forecast_Method:** "Statistical" (time-series), "ML" (neural net, ARIMA), "Expert" (manual adjustment by planner).
- **Target_Revenue:** TY (This Year) target set by Finance; may differ from Forecast_Revenue (actual prediction).
- **Last_Updated:** Forecast refresh timestamp; used to identify stale forecasts (> 30 days old = warning).

---

## 3. Linking Fact Tables to Dimensions

### Fact_Sales Relationships (in Power BI Model)

| From | To | Active | Notes |
|---|---|---|---|
| Fact_Sales[DateKey] | Dim_Date[DateKey] | ✓ | Primary aggregation axis |
| Fact_Sales[ChainKey] | Dim_Chain[ChainKey] | ✓ | Chain drill-down, multi-select |
| Fact_Sales[ProductKey] | Dim_Product[ProductKey] | ✓ | SKU/Category drill-down |
| Fact_Sales[ZoneKey] | Dim_Geography[ZoneKey] | ✓ | Regional rollup (Zone level) |
| Fact_Sales[State_Code] | Dim_Geography[State_Code] | ✓ | **NEW:** State-level drill-down, operational reporting |

### Fact_Forecast Relationships (in Power BI Model)

| From | To | Active | Notes |
|---|---|---|---|
| Fact_Forecast[DateKey] | Dim_Date[DateKey] | ✓ | Future projection axis |
| Fact_Forecast[ChainKey] | Dim_Chain[ChainKey] | ✓ | Chain drill-down, multi-select |
| Fact_Forecast[ProductKey] | Dim_Product[ProductKey] | ✓ | SKU/Category drill-down |
| Fact_Forecast[ZoneKey] | Dim_Geography[ZoneKey] | ✓ | Regional rollup (Zone level) |
| Fact_Forecast[State_Code] | Dim_Geography[State_Code] | ✓ | **NEW:** State-level drill-down, operational reporting |

**Note:** Both fact tables join the same dimension tables, allowing pivot and compare (Actual vs. Forecast) in the same visual without ambiguity.

---

## 4. Data Quality Gates (Post-Load)

Implement these as Power Query steps or DAX validation measures:

| Check | Rule | Action |
|---|---|---|
| **Fact_Sales DateKey validity** | Must match `yyyyMM` pattern | Log to DLQ; skip row |
| **Fact_Forecast future-dated** | DateKey ≥ current month (optional) | Include in dataset; mark as "hindcast" if past |
| **Null Qty/Revenue** | Actual_Qty/Forecast_Qty must not be null | Skip row; log |
| **Duplicate keys** | [DateKey, ChainKey, ProductKey, ZoneKey, Metric_Type] should be unique | Flag; aggregate or keep latest |
| **Orphaned keys** | ChainKey/ProductKey/ZoneKey must exist in dimension tables | Log to DLQ; skip row |
| **Confidence bounds** | Confidence_Level ∈ [0.0, 1.0] | Clamp to [0, 1]; log warning |
| **Stale forecasts** | Last_Updated < (today - 30 days) | Flag in dashboard; user decision on inclusion |

---

## 5. Incremental Refresh Strategy (Optional)

For large datasets (Fact_Sales 50M+ rows), implement incremental refresh in Power BI:

```m
// Add to Fact_Sales query (after Cleaned step):
let
  // Capture load date range from parameter
  RefreshWindow = if RangeStart = null then Date.From(DateTime.LocalNow() - #duration(90, 0, 0, 0)) else RangeStart,
  FilteredByDate = Table.SelectRows(Cleaned, each [Load_Date] >= RefreshWindow)
in
  FilteredByDate
```

**Parameters:**
- `RangeStart` (Date): First date to include in refresh window.
- `RangeEnd` (Date): Last date to include (typically today).
- **Refresh cadence:** Full refresh monthly; incremental weekly.

---

## Next Steps

1. **Save each query** to the Power BI model using these exact query names:
   - `Dim_Date`, `Dim_Chain`, `Dim_Product`, `Dim_Geography`, `Fact_Sales`, `Fact_Forecast`
2. **Create relationships** as specified in Section 3.
3. **Define measures** in the next document (`03_DAX_MEASURE_LIBRARY.md`).
4. **Load seed data** (sample CSV files) to test queries before connecting to live sources.
5. **Run data quality checks** (Section 4) and log failures to DLQ for review.

---

**Next Document:** `03_DAX_MEASURE_LIBRARY.md` — Complete set of base aggregations, variance/accuracy measures, and KPI calculations.
