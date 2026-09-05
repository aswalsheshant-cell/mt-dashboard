# Production-Ready DAX Measures for GAP-01 & GAP-02

**Version:** 1.0  
**Status:** Ready for PBIP Integration  
**Validation:** Tested against baseline via `tests/test_business_validation_dax.py`  

---

## Overview

Below are the production-ready DAX measures structured for direct insertion into your semantic model definition folder (typically `tables/_Measures.tmdl` or inside your dedicated measure table).

---

## GAP-01: L3M Allocation Weighting Measures

These measures calculate the trailing 3-month weight (March–May 2026) for each Chain and Category slice and apply it to the unallocated June 2026 enterprise total.

### 1. Trailing 3-Month Actuals (Context Anchor)

```dax
NSV_L3M_Actuals = 
CALCULATE(
    [NSV_Actual_INR],
    DATESBETWEEN(
        'Dim_Date'[Date],
        DATE(2026, 3, 1),
        DATE(2026, 5, 31)
    ),
    'Fact_Financials'[Scenario] = "Actual"
)
```

**Purpose:** Sum NSV for the current dimension context (chain/category slice) for Mar–May 2026.  
**Example:** Chain A × Haircare: ₹330 Cr (sum of Mar ₹100 + Apr ₹110 + May ₹120)

---

### 2. Trailing 3-Month Total Channel Baseline (Denominator)

```dax
NSV_L3M_AllChannel_Total = 
CALCULATE(
    [NSV_L3M_Actuals],
    ALLSELECTED('Dim_Chain'),
    ALLSELECTED('Dim_Category')
)
```

**Purpose:** Total across ALL chains/categories for Mar–May 2026 (used as denominator for weight calculation).  
**Example:** ₹770 Cr (sum of Chain A ₹330 + Chain B ₹170 + Chain C ₹270)

---

### 3. Allocation Weight

```dax
Allocation_Weight_L3M = 
DIVIDE(
    [NSV_L3M_Actuals],
    [NSV_L3M_AllChannel_Total],
    0
)
```

**Purpose:** Slice-level share of L3M total.  
**Example:** Chain A weight = ₹330 ÷ ₹770 = 42.86%

---

### 4. Final Allocated June 2026 NSV

```dax
NSV_Jun26_Allocated = 
VAR Unallocated_Jun26_Pool = 
    CALCULATE(
        [NSV_Pool_INR],
        'Dim_Date'[YearMonth] = 202606,
        'Fact_Financials'[Scenario] = "Forecast_Unallocated",
        ALL('Dim_Chain'),
        ALL('Dim_Category')
    )
VAR CurrentRowActual = 
    CALCULATE(
        [NSV_Actual_INR],
        'Dim_Date'[YearMonth] = 202606
    )
RETURN
    IF(
        ISBLANK(CurrentRowActual) || CurrentRowActual = 0,
        Unallocated_Jun26_Pool * [Allocation_Weight_L3M],
        CurrentRowActual
    )
```

**Logic:**
- If Jun'26 actual NSV exists for the slice: use actual
- If blank/zero: apply L3M weight to enterprise pool
- Example: Chain A = ₹400 Cr (pool) × 42.86% = ₹171.4 Cr

**Validation:** Sum of all slices' allocated NSV = enterprise pool (±0.5% tolerance)

---

## GAP-02: Unclamped Cont% & Conditional Formatting Flags

These measures preserve true negative margins across all rollups and expose numeric threshold status codes and hex colors for front-end conditional formatting.

### 5. Net Contribution Margin Value

```dax
Contribution_Margin_INR = 
[NSV_Actual_INR] - [COGS_INR] - [Variable_Trade_Spend_INR] - [Freight_Logistics_INR]
```

**Purpose:** Dollar contribution available after all variable costs.  
**Example:** NSV ₹65 - COGS ₹45.5 - Trade ₹23.4 - Freight ₹6.5 = **-₹8.0 Cr (loss-making)**

---

### 6. Unclamped Contribution Margin %

```dax
Cont_Margin_Pct = 
DIVIDE(
    [Contribution_Margin_INR],
    [NSV_Actual_INR],
    BLANK()
)
```

**Purpose:** Contribution as % of NSV (NOT clamped to 0%).  
**Example:** -₹8 ÷ ₹65 = **-12.3%** (displayed as-is, not hidden)

---

### 7. Margin Status Flag (Categorical & Filterable)

```dax
Cont_Margin_Status = 
VAR Pct = [Cont_Margin_Pct]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(Pct), "No Data",
        Pct < 0, "Loss-Making (< 0%)",
        Pct < 0.10, "At-Risk (0-10%)",
        Pct < 0.20, "Target (10-20%)",
        "High Margin (> 20%)"
    )
```

**Purpose:** Categorical label for reporting and filtering.  
**Values:**
- "No Data" → BLANK() (missing NSV or cost data)
- "Loss-Making (< 0%)" → Negative margin (needs immediate action)
- "At-Risk (0-10%)" → Compressed, vulnerable to cost spikes
- "Target (10-20%)" → Healthy, aligned with corporate targets
- "High Margin (> 20%)" → Premium segment (scale or test pricing)

---

### 8. Conditional Formatting Hex Color (Data-Bound Styling)

```dax
Cont_Margin_Color = 
VAR Pct = [Cont_Margin_Pct]
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(Pct), "#9E9E9E",    -- Gray (Neutral / No Data)
        Pct < 0, "#D32F2F",         -- Crimson Red (Negative Alert)
        Pct < 0.10, "#F57C00",      -- Amber (Margin Compression)
        Pct < 0.20, "#388E3C",      -- Standard Green (Healthy)
        "#1B5E20"                   -- Dark Green (Over-performing)
    )
```

**Purpose:** Hex color code for Power BI conditional formatting rules.  
**Binding in PBIX:**
1. Select visual (Matrix/Table)
2. Right-click → Format
3. Cell Elements → Formatting → Select `[Cont_Margin_Color]`

---

### 9. Data Card / Tooltip Display Badge

```dax
Cont_Margin_Badge = 
VAR Pct = [Cont_Margin_Pct]
VAR FormattedPct = FORMAT(Pct, "0.0%")
RETURN
    SWITCH(
        TRUE(),
        ISBLANK(Pct), "—",
        Pct < 0, "⚠️ " & FormattedPct & " [LOSS]",
        Pct < 0.10, "⚡ " & FormattedPct & " [COMPRESSED]",
        FormattedPct
    )
```

**Purpose:** User-friendly display for tooltips and data cards.  
**Examples:**
- -12.3% → "⚠️ -12.3% [LOSS]"
- 5.2% → "⚡ 5.2% [COMPRESSED]"
- 28.0% → "28.0%"

---

## TMDL Integration

Insert the following into your semantic model's `tables/_Measures.tmdl` (or equivalent measure table definition):

```tmdl
table _Measures

	measure NSV_L3M_Actuals = ```
		CALCULATE(
		    [NSV_Actual_INR],
		    DATESBETWEEN(
		        'Dim_Date'[Date],
		        DATE(2026, 3, 1),
		        DATE(2026, 5, 31)
		    ),
		    'Fact_Financials'[Scenario] = "Actual"
		)
		```
		formatString: #,##0.00
		displayFolder: GAP-01 Allocation
		dataType: decimal

	measure NSV_L3M_AllChannel_Total = ```
		CALCULATE(
		    [NSV_L3M_Actuals],
		    ALLSELECTED('Dim_Chain'),
		    ALLSELECTED('Dim_Category')
		)
		```
		formatString: #,##0.00
		displayFolder: GAP-01 Allocation
		dataType: decimal

	measure Allocation_Weight_L3M = ```
		DIVIDE(
		    [NSV_L3M_Actuals],
		    [NSV_L3M_AllChannel_Total],
		    0
		)
		```
		formatString: 0.0000%
		displayFolder: GAP-01 Allocation
		dataType: decimal

	measure NSV_Jun26_Allocated = ```
		VAR Unallocated_Jun26_Pool = 
		    CALCULATE(
		        [NSV_Pool_INR],
		        'Dim_Date'[YearMonth] = 202606,
		        'Fact_Financials'[Scenario] = "Forecast_Unallocated",
		        ALL('Dim_Chain'),
		        ALL('Dim_Category')
		    )
		VAR CurrentRowActual = 
		    CALCULATE(
		        [NSV_Actual_INR],
		        'Dim_Date'[YearMonth] = 202606
		    )
		RETURN
		    IF(
		        ISBLANK(CurrentRowActual) || CurrentRowActual = 0,
		        Unallocated_Jun26_Pool * [Allocation_Weight_L3M],
		        CurrentRowActual
		    )
		```
		formatString: #,##0.00
		displayFolder: GAP-01 Allocation
		dataType: decimal

	measure Contribution_Margin_INR = ```
		[NSV_Actual_INR] - [COGS_INR] - [Variable_Trade_Spend_INR] - [Freight_Logistics_INR]
		```
		formatString: #,##0.00
		displayFolder: GAP-02 Contribution Margin
		dataType: decimal

	measure Cont_Margin_Pct = ```
		DIVIDE(
		    [Contribution_Margin_INR],
		    [NSV_Actual_INR],
		    BLANK()
		)
		```
		formatString: 0.0%
		displayFolder: GAP-02 Contribution Margin
		dataType: decimal

	measure Cont_Margin_Status = ```
		VAR Pct = [Cont_Margin_Pct]
		RETURN
		    SWITCH(
		        TRUE(),
		        ISBLANK(Pct), "No Data",
		        Pct < 0, "Loss-Making (< 0%)",
		        Pct < 0.10, "At-Risk (0-10%)",
		        Pct < 0.20, "Target (10-20%)",
		        "High Margin (> 20%)"
		    )
		```
		displayFolder: GAP-02 Contribution Margin\Formatting
		dataType: string

	measure Cont_Margin_Color = ```
		VAR Pct = [Cont_Margin_Pct]
		RETURN
		    SWITCH(
		        TRUE(),
		        ISBLANK(Pct), "#9E9E9E",
		        Pct < 0, "#D32F2F",
		        Pct < 0.10, "#F57C00",
		        Pct < 0.20, "#388E3C",
		        "#1B5E20"
		    )
		```
		displayFolder: GAP-02 Contribution Margin\Formatting
		dataType: string

	measure Cont_Margin_Badge = ```
		VAR Pct = [Cont_Margin_Pct]
		VAR FormattedPct = FORMAT(Pct, "0.0%")
		RETURN
		    SWITCH(
		        TRUE(),
		        ISBLANK(Pct), "—",
		        Pct < 0, "⚠️ " & FormattedPct & " [LOSS]",
		        Pct < 0.10, "⚡ " & FormattedPct & " [COMPRESSED]",
		        FormattedPct
		    )
		```
		displayFolder: GAP-02 Contribution Margin\Formatting
		dataType: string
```

---

## Matrix Visual Configuration Guide

### Binding in Power BI Desktop

1. **Select Matrix/Table visual**
2. **Fields Pane:**
   - Rows: `Dim_Chain`, `Dim_Category`, `Dim_SKU`
   - Values: `NSV_Jun26_Allocated`, `Cont_Margin_Pct`, `Contribution_Margin_INR`

3. **Format (Matrix)**
   - Cell Elements → Formatting
   - Select `[Cont_Margin_Color]` → Field value
   - Background fill → bound to hex color

4. **Tooltips**
   - Add: `[Cont_Margin_Badge]`, `[Contribution_Margin_INR]`, `[Cont_Margin_Status]`
   - Display: "⚠️ -12.3% [LOSS] | -₹8 Cr | Loss-Making (< 0%)"

---

## Validation & Testing

All measures are validated by `tests/test_business_validation_dax.py`:

```bash
pytest tests/test_business_validation_dax.py -v
```

**Expected Results:**
- ✓ Allocation weights sum to 100%
- ✓ Jun'26 allocated NSV matches enterprise pool (±0.5%)
- ✓ Negative margins preserved (not clamped)
- ✓ Status/Color badges align with margin buckets
- ✓ Reconciliation variance < 0.5% vs baseline

---

## Deployment Checklist

- [ ] Copy all 9 measures into `_Measures.tmdl`
- [ ] Verify syntax (no red wavy underlines in Power Query Editor)
- [ ] Refresh Data Model (Home → Refresh)
- [ ] Create test card visual: drag `[Cont_Margin_Pct]` → verify negative values display
- [ ] Create test matrix: rows = Chain/Category, value = `[Cont_Margin_Badge]` → verify "⚠️ -X.X% [LOSS]" appears
- [ ] Bind conditional formatting: select matrix → Format → cell elements → font color = `[Cont_Margin_Color]`
- [ ] Publish to Power BI Service
- [ ] Run validation test suite against published dataset

---

**Document Version:** 1.0  
**Status:** Ready for PBIP Assembly  
**Contact:** analytics-engineering@honasa.com
