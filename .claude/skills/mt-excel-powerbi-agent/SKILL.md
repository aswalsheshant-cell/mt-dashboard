# MT Excel + Power BI Agent — Deep Knowledge Base

Integrated knowledge across four learning domains, auto-applied whenever the agent encounters
challenges in this project. Covers: PL-300 Power BI, Prompt Engineering, Deep Learning
pattern-recognition, and Excel data analysis — all mapped to MT Offtake/Primary analytics.

---

## DOMAIN 1 — Excel Data Analysis (IBM Formulas + PL-300 Prep)

### Core Formula Arsenal for MT Offtake

Every formula below is **anti-heavy**: it reads from a named table, not from raw cell ranges,
so the worksheet stays thin. Heavy aggregation lives in Power Pivot (Domain 2).

#### 1a. Zone / State / Store Offtake — SUMIFS Pattern
```excel
// Zone total (single month)
=SUMIFS(tblOfftake[Offtake NSV],
        tblOfftake[Zone],      B2,
        tblOfftake[Month],     $B$1)

// State total within Zone
=SUMIFS(tblOfftake[Offtake NSV],
        tblOfftake[Zone],      B2,
        tblOfftake[State],     C2,
        tblOfftake[Month],     $B$1)

// Store total within State (Qty + NSV side-by-side)
=SUMIFS(tblOfftake[Offtake Qty],
        tblOfftake[State],     D2,
        tblOfftake[Store Code],E2,
        tblOfftake[Month],     $B$1)
```

**Rule:** Never write `SUMIFS` on raw unlocked ranges. Always convert source to
`Table` (Ctrl+T) → named `tblOfftake`. This auto-expands when rows are added.

#### 1b. Division-Safe Share & Margin Formulas
```excel
// Zone % of National
=IFERROR(F5/SUM($F$5:$F$9), 0)

// Gross Margin % (MRP–NSV gap approach)
=IFERROR((G5-F5)/G5, 0)       // (MRP Sales - Offtake NSV) / MRP Sales

// MoM Growth
=IFERROR((F5-H5)/ABS(H5), "N/A")   // H5 = prior month value
```

#### 1c. XLOOKUP for Zone/State Master Enrichment
```excel
// Enrich Store Code with Zone and State from master table
=XLOOKUP(A2, tblStoreMaster[Store Code], tblStoreMaster[Zone], "Not Found", 0)
=XLOOKUP(A2, tblStoreMaster[Store Code], tblStoreMaster[State], "Not Found", 0)

// Fallback with IFERROR for old Excel versions (no XLOOKUP)
=IFERROR(VLOOKUP(A2, StoreMaster, 3, 0), "Not Found")
```

#### 1d. Pivot Table–Ready Data Cleaning Formulas
```excel
// Trim + normalize text (chain names, store names)
=TRIM(PROPER(A2))

// FY derivation from Month-Year text "Apr'26"
// Extract month number: LEFT 3 chars → MATCH in month array
=MATCH(LEFT(A2,3), {"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"}, 0)

// FY tag: if month >= 4 (Apr) → FY = year+1, else FY = year
=IF(MATCH(LEFT(A2,3),{"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"},0)>=4,
   "FY"&(RIGHT(A2,2)+1),
   "FY"&RIGHT(A2,2))

// Month sequence number within FY (Apr=1, Mar=12)
=MOD(MATCH(LEFT(A2,3),{"Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"},0)+8,12)+1
```

#### 1e. Dynamic Array Formulas (Excel 365 — Zone Summary)
```excel
// Unique zones list (spill)
=UNIQUE(tblOfftake[Zone])

// Zone totals without pivot (spill)
=SUMIF(tblOfftake[Zone], A2#, tblOfftake[Offtake NSV])

// Top 10 stores by offtake (spill)
=TAKE(SORT(HSTACK(tblOfftake[Store Name], tblOfftake[Offtake NSV]), 2, -1), 10)
```

#### 1f. CUBEVALUE — Pull from Power Pivot into Cell (Anti-Heavy)
```excel
// Single cell: Zone = "West", Month = "Apr'26", Measure = Total Offtake NSV
=CUBEVALUE("ThisWorkbookDataModel",
    CUBEMEMBER("ThisWorkbookDataModel","[Fact Offtake Sales].[Zone].&[West]"),
    CUBEMEMBER("ThisWorkbookDataModel","[Date Table].[Month].&[Apr'26]"),
    "[Measures].[Total Offtake NSV]")

// Dynamic (B2 = Zone selector, C1 = Month selector)
=CUBEVALUE("ThisWorkbookDataModel",
    CUBEMEMBER("ThisWorkbookDataModel","[Fact Offtake Sales].[Zone].&["&B2&"]"),
    CUBEMEMBER("ThisWorkbookDataModel","[Date Table].[Month].&["&C1&"]"),
    "[Measures].[Total Offtake NSV]")

// State within Zone
=CUBEVALUE("ThisWorkbookDataModel",
    CUBEMEMBER("ThisWorkbookDataModel","[Fact Offtake Sales].[Zone].&["&B2&"]"),
    CUBEMEMBER("ThisWorkbookDataModel","[Fact Offtake Sales].[State].&["&C2&"]"),
    CUBEMEMBER("ThisWorkbookDataModel","[Date Table].[Month].&["&D1&"]"),
    "[Measures].[Total Offtake NSV]")
```

**CUBEVALUE is the key to a light worksheet:** no SUMIFS on 100K+ rows — the
Power Pivot engine calculates; the sheet just retrieves.

---

## DOMAIN 2 — Power BI / Power Pivot Architecture

### The Anti-Heavy Pattern (Keep Sheets Thin)

```
Raw CSV files
    ↓  Power Query (M)  — loads into Data Model, NOT to worksheet
Data Model (Power Pivot)
    ↓  DAX Measures  — all aggregation happens here
Worksheet
    ↓  CUBEVALUE() / PivotTable  — thin retrieval layer only
```

**Never:** `=SUMIFS(A:A, B:B, "West", ...)` on 100K+ rows in a worksheet.
**Always:** DAX measure → CUBEVALUE() or PivotTable connected to the data model.

### Star Schema for MT Offtake (Excel Data Model)

```
Fact Offtake Sales (grain: Month × Store × Article)
    ├── → Dim Date      [MonthStart]
    ├── → Dim Store     [Store Code]
    ├── → Dim Article   [Article Code]
    └── → Dim Geography [Zone + State + City] (derived or from master)

Fact Primary Sales (grain: Month × ShipTo × Brand)
    ├── → Dim Date
    ├── → Dim Chain     [Chain]
    └── → Dim Geography
```

### Power Pivot DAX — Zone / State / Store Measures

```dax
// Zone-level offtake (respects slicer context)
OFFTAKE_NSV_ZONE =
CALCULATE(
    SUM('Fact Offtake Sales'[Offtake NSV]),
    ALLEXCEPT('Fact Offtake Sales', 'Fact Offtake Sales'[Zone])
)

// State share within Zone
OFFTAKE_STATE_SHARE =
DIVIDE(
    SUM('Fact Offtake Sales'[Offtake NSV]),
    CALCULATE(SUM('Fact Offtake Sales'[Offtake NSV]),
        ALLEXCEPT('Fact Offtake Sales', 'Fact Offtake Sales'[Zone]))
)

// Store rank by Offtake NSV (within selected State)
STORE_RANK_IN_STATE =
RANKX(
    ALLSELECTED('Dim Store'[Store Name]),
    SUM('Fact Offtake Sales'[Offtake NSV]),
    , DESC
)

// YoY growth — requires Date table with FY column
OFFTAKE_YOY =
VAR cur = SUM('Fact Offtake Sales'[Offtake NSV])
VAR py  = CALCULATE(
    SUM('Fact Offtake Sales'[Offtake NSV]),
    DATEADD('Dim Date'[Date], -12, MONTH))
RETURN DIVIDE(cur - py, py)

// Running FY total (Apr–Mar)
OFFTAKE_YTD =
CALCULATE(
    SUM('Fact Offtake Sales'[Offtake NSV]),
    FILTER(
        ALL('Dim Date'),
        'Dim Date'[FY] = MAX('Dim Date'[FY]) &&
        'Dim Date'[FY_Month_Seq] <= MAX('Dim Date'[FY_Month_Seq])
    )
)

// Margin % with division guard
MARGIN_PCT =
DIVIDE(
    SUM('Fact Offtake Sales'[Offtake NSV]) - SUM('Fact Offtake Sales'[MRP Sales]),
    SUM('Fact Offtake Sales'[MRP Sales])
)
```

### Power Query M — Loading Offtake CSVs into Data Model (Not to Sheet)

```m
// In Excel Power Query: set Load To → "Only Create Connection" + "Add this
// data to the Data Model". Never "Table" for large fact tables.
let
    Source = Folder.Files("C:\MT_Data\Offtake_Monthly"),
    FilterCSV = Table.SelectRows(Source, each [Extension] = ".csv"),
    Combined = Table.Combine(List.Transform(FilterCSV[Content], each
        let
            Raw = Csv.Document(_, [Delimiter=",", Encoding=65001]),
            H   = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),
            Sel = Table.SelectColumns(H, {
                "Month","Year","Zone","State","Chain Name","Site Code",
                "Site Name","Brand","Category","Sales Qty","NSV","MRP Sales Value",
                "MRP","Margin"}, MissingField.UseNull)
        in Sel
    )),
    Typed = Table.TransformColumnTypes(Combined, {
        {"Sales Qty", type number}, {"NSV", type number},
        {"MRP Sales Value", type number}, {"MRP", type number}
    }),
    AddFY = Table.AddColumn(Typed, "FY", each
        let m = [Month]
        in if m = null then null
           else
             let mn = Record.FieldOrDefault(
                  [Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12,
                   Jan=1,Feb=2,Mar=3], Text.Start(m,3), null),
                 yr = Number.FromText(Text.AfterDelimiter(m,"'"))
             in if mn = null then null
                else if mn >= 4 then "FY" & Text.From(yr+1) else "FY" & Text.From(yr))
in
    Combined
```

---

## DOMAIN 3 — Prompt Engineering for Data Analysis Tasks

These patterns guide how to frame analytical questions for AI (Claude, Copilot, ChatGPT)
within this project. Apply them whenever stuck on a data/DAX challenge.

### Pattern 1 — Persona + Constraint Prompt
```
"Act as a Power BI DAX expert for a fast-moving consumer goods company.
 Context: Star-schema model. Fact: Offtake Sales (grain: Month × Store × Article).
 Dims: Date, Store (with Zone/State), Article.
 Problem: [your specific issue]
 Constraint: Must handle BLANK months gracefully. Must not use ALL() without ALLEXCEPT."
```

### Pattern 2 — Data Storytelling Prompt for Offtake Insights
```
"Analyze this offtake summary table (Zone × Month × NSV).
 Identify: (1) top-performing zone trend, (2) zone losing share MoM,
 (3) seasonal pattern in the last 3 months.
 Output format: 3 bullet executive insights + 1 recommended action per insight."
```

### Pattern 3 — Formula Debugging Prompt
```
"This Excel formula returns wrong values: [paste formula].
 Data: column A = Store Name, B = Zone, C = NSV (₹), D = Month text like 'Apr'26'.
 Expected: sum all NSV for Zone=West in Apr'26. Actual result: [observed].
 Show the corrected formula and explain what was wrong."
```

### Pattern 4 — Verification / Trustworthy AI Pattern
```
"Before I use this result, verify it:
 (1) Does the formula cover all months Apr–Mar, not just Jan–Dec?
 (2) Does it handle stores appearing in multiple zones?
 (3) Is it consistent with the SUMIFS baseline check [expected total]?"
```

### Pattern 5 — ChatGPT Advanced Data Analysis (Code Interpreter)
```
"Here is the offtake CSV (attached). Do the following:
 1. Clean the Month column (standardize to 'MMM'YY' format).
 2. Derive FY column (Apr–Mar rule).
 3. Pivot: rows = Zone, columns = Month, values = sum(NSV).
 4. Highlight in Excel: top-3 Zone-Month cells by NSV.
 5. Export as formatted Excel file."
```

---

## DOMAIN 4 — Deep Learning Patterns Applied to Sales Data

These techniques apply when the agent needs to detect trends, anomalies, or
forecast gaps in Offtake/Primary data — beyond simple SUMIFS.

### 4a. Anomaly Detection (Z-Score) for Store Offtake Drops
```python
# Flag stores with NSV drop > 2 standard deviations from their own 3-month mean
import pandas as pd, numpy as np

def flag_anomalies(df: pd.DataFrame, metric: str = "Offtake NSV", window: int = 3) -> pd.DataFrame:
    df = df.sort_values(["Store Code", "MonthStart"])
    df["rolling_mean"] = df.groupby("Store Code")[metric].transform(
        lambda x: x.shift(1).rolling(window, min_periods=1).mean())
    df["rolling_std"] = df.groupby("Store Code")[metric].transform(
        lambda x: x.shift(1).rolling(window, min_periods=1).std().fillna(1))
    df["z_score"] = (df[metric] - df["rolling_mean"]) / df["rolling_std"]
    df["anomaly"] = df["z_score"].abs() > 2.0
    return df
```

### 4b. RNN / LSTM Mental Model for Offtake Forecasting
Key insight: Offtake is a time series with seasonal patterns (Diwali bump, summer
skin-care peak). Even without training an LSTM, use this reasoning:
- **Lookback window:** L3M average is your "hidden state"
- **Seasonality:** compare to same month prior year (YoY) — this is the "attention" mechanism
- **Gradient clipping analogy:** cap outlier months (promo spikes) before using as baseline

Apply in DAX:
```dax
// Seasonal-adjusted L3M (clip months above 95th percentile)
OFFTAKE_ADJ_L3M =
VAR _dates = DATESINPERIOD('Dim Date'[Date], MAX('Dim Date'[Date]), -3, MONTH)
VAR _vals = CALCULATETABLE(
    ADDCOLUMNS(VALUES('Dim Date'[MonthStart]),
        "M", CALCULATE(SUM('Fact Offtake Sales'[Offtake NSV]))), _dates)
VAR _p95 = PERCENTILE.EXC(SELECTCOLUMNS(_vals, "M", [M]), 0.95)
RETURN AVERAGEX(FILTER(_vals, [M] <= _p95), [M])
```

### 4c. Transfer Learning Mental Model — Reuse Zone Patterns Across Brands
When a new brand launches in a zone, bootstrap its forecast from the existing
brand's zone trajectory (transfer the pattern, scale by launch ratio):
```excel
// Bootstrap formula: new brand estimate = existing brand × launch ratio × zone index
=E5 * $B$1 * IFERROR(VLOOKUP(B5, ZoneIndex, 2, 0), 1)
// E5 = same-zone same-month existing brand NSV
// $B$1 = launch ratio (e.g. 0.30 for 30% of baseline)
// ZoneIndex = zone-level demand multiplier from master
```

### 4d. Gradient Descent Intuition — DAX Iterative Targeting
The concept of "converging on a value through iteration" maps directly to
What-If parameter sliders in Power BI / Excel:
```excel
// Target back-solve: what NSV per store achieves ₹10 Cr zone target?
=target_zone / COUNTIFS(tblOfftake[Zone], B2, tblOfftake[Month], $B$1)
// Use Excel's Goal Seek (Data → What-If → Goal Seek) to find break-even store count
```

---

## CHALLENGE-RESOLUTION LOOKUP TABLE

When the agent hits a wall, look up the challenge category here first.

| Challenge | Domain | Pattern to Apply |
|-----------|--------|-----------------|
| SUMIFS too slow / worksheet freezes | Excel | Convert to Power Pivot CUBEVALUE (Domain 2) |
| DAX measure returns wrong total | Power BI | Add ALLEXCEPT, check filter context (Domain 2 Anti-Patterns) |
| Month column not parsing (Apr'26 format) | Excel / M | Use `LEFT(A,3)` + MATCH array formula (Domain 1d) or M pattern (Domain 2 PQ) |
| FY derivation wrong (Jan misclassified) | Any | Apply THE ONE FY RULE: month>=4 → FY(year+1), else FY(year) |
| Store data has Zone mismatches | Excel | XLOOKUP from tblStoreMaster, fallback IFERROR (Domain 1c) |
| Need Zone vs State breakdown fast | Excel | UNIQUE+SUMIF spill pattern (Domain 1e), or CUBEVALUE grid (Domain 1f) |
| Offtake trend anomaly in a store | Python | Z-score anomaly flagging (Domain 4a) |
| New brand / new zone forecast | Excel | Transfer learning bootstrap formula (Domain 4c) |
| Slow Excel workbook with large data | All | Move aggregation to Power Pivot data model; worksheet = CUBEVALUE only |
| AI / ChatGPT giving wrong formula | Prompt Eng | Use Verification Pattern 4 (Domain 3) |
| Report is hard to read / no insight | Prompt Eng | Use Data Storytelling Prompt Pattern 2 (Domain 3) |
| Need seasonal adjustment | Deep Learning | LSTM mental model → ADJ_L3M DAX measure (Domain 4b) |
| Division by zero errors | Any | IFERROR(,0) in Excel; DIVIDE(,,0) or DIVIDE(,,BLANK()) in DAX |
| Large CSV crashes Power Query | Power BI | Set load = "Only Create Connection" + "Add to Data Model" (Domain 2 PQ) |

---

## EXCEL ARCHITECTURE RULES FOR THIS PROJECT

These rules apply every time an Excel deliverable is built for MT Offtake/Primary:

### Rule 1 — Worksheet Layer (Light)
- Max 3 sheets: `Control` (slicers/selectors), `Summary` (CUBEVALUE formulas), `Checks` (QA)
- No raw data on worksheet sheets. Data lives in the model.
- All numbers from CUBEVALUE() or PivotTable connected to Power Pivot.

### Rule 2 — Data Model Layer (Heavy)
- Fact tables loaded via Power Query → "Only Create Connection" + "Add to Data Model"
- Dim tables same approach
- Date table: explicit (generated in M, not Excel auto-calendar)
- All relationships: one-to-many only

### Rule 3 — Formula Layer (Smart)
- Named ranges for all dimension lists: `rng_Zones`, `rng_States`, `rng_Months`
- Data validation dropdowns pull from named ranges (dynamic OFFSET or spill)
- Summary formulas = CUBEVALUE pattern (Domain 1f)

### Rule 4 — Quality Layer (Disciplined)
- `Checks` sheet: SUMIFS on small seed tables vs CUBEVALUE totals must reconcile
- Flag any >0.1% discrepancy in a red conditional format cell
- Track last-refresh date in cell, updated by Power Query refresh metadata

---

## COURSE LEARNING MAP → PROJECT APPLICATION

| Course | Core Skill | Applied Here |
|--------|-----------|--------------|
| PL-300 Power BI (Microsoft, 8 courses) | DAX, Power Query, Star Schema, PivotTables, Row-level security | `PowerBI/DAX/*.dax`, `PowerBI/PowerQuery/*.pq`, data model design, this skill |
| Prompt Engineering (Vanderbilt, 3 courses) | Persona prompts, Chain-of-thought, Verification, ChatGPT Code Interpreter | Domain 3 patterns above; use when debugging formulas or generating insights |
| Deep Learning (DeepLearning.AI, 5 courses) | RNN/LSTM for time series, anomaly detection, transfer learning | Domain 4 patterns; apply when analyzing store offtake trends or forecasting |
| Excel Basics for Data Analysis (IBM, 1 course) | SUMIFS, VLOOKUP/XLOOKUP, Pivot Tables, data cleaning, IFERROR | Domain 1 formulas; every MT Excel worksheet follows IBM best practices |
