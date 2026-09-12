# Parameterized CM2 Model & Executive Theme
## Modern Trade Dashboard — Dynamic Cost Structure Governance

**Version:** 1.0  
**Last Updated:** 2026-08-27  
**Status:** Production-Ready

---

## Overview

This document provides:
1. **Disconnected parameter table** for dynamic CM2 calculation switching
2. **Parameterized DAX measures** (Provisional vs. Finance-approved baseline)
3. **Executive theme JSON** (modern dark-blue palette with drop shadows)
4. **Integration guide** for parameter slicer on report pages

---

## 1. Parameterized CM2 Logic

### 1.1 Parameter Table Definition

Create this as a new table in Power BI (not connected to fact/dimension tables).

**Method 1: DAX Table (Recommended)**

```dax
Param_CM2_Logic = 
DATATABLE(
    "Option", STRING,
    "OptionID", INTEGER,
    "Description", STRING,
    {
        {"Provisional (Base COGS Only)", 1, "CM2 = Revenue - Base_COGS (expense data EXAMPLE only)"},
        {"Finance Baseline (COGS + Logistics + Scheme)", 2, "CM2 = Revenue - Base_COGS - Logistics_Cost - Scheme_Adjustment (approved by Finance D1)"}
    }
)
```

**Method 2: CSV Load (Alternative)**

Create `Param_CM2_Logic.csv`:
```
Option,OptionID,Description
"Provisional (Base COGS Only)",1,"CM2 = Revenue - Base_COGS (expense data EXAMPLE only)"
"Finance Baseline (COGS + Logistics + Scheme)",2,"CM2 = Revenue - Base_COGS - Logistics_Cost - Scheme_Adjustment (approved by Finance D1)"
```

Then load via Power Query:
```m
Source = Csv.Document(File.Contents("...Param_CM2_Logic.csv"), [Delimiter=",", Encoding=65001]),
Promoted = Table.PromoteHeaders(Source)
```

**Note:** Do NOT create relationships from `Param_CM2_Logic` to any fact/dimension table. This is a **disconnected slicer table**.

### 1.2 Parameterized CM2 Measures

Paste these measures into the `_Measures` table:

#### Total Provisional Cost (Base COGS Only)

```dax
Total Provisional Cost =
SUMX(Fact_Sales, Fact_Sales[Base_COGS])
```

**Usage:** Baseline cost structure (no additional allocations).

#### Total Baseline Cost (COGS + Logistics + Scheme)

```dax
Total Baseline Cost =
VAR TotalCOGS = SUMX(Fact_Sales, Fact_Sales[Base_COGS])
VAR TotalLogistics = SUMX(Fact_Sales, Fact_Sales[Logistics_Cost])
VAR TotalScheme = SUMX(Fact_Sales, Fact_Sales[Scheme_Adjustment])
RETURN
    TotalCOGS + TotalLogistics + TotalScheme
```

**Usage:** Finance-approved cost model including all allocations.

#### CM2 Amount (Parameterized)

```dax
CM2 Amount =
VAR SelectedOption = SELECTEDVALUE(Param_CM2_Logic[OptionID], 1)
VAR ProvisionalCM2 = [Total Actual Revenue] - [Total Provisional Cost]
VAR BaselineCM2 = [Total Actual Revenue] - [Total Baseline Cost]
RETURN
    SWITCH(
        SelectedOption,
        1, ProvisionalCM2,
        2, BaselineCM2,
        ProvisionalCM2  -- Default to Provisional if no selection
    )
```

**Interpretation:**
- **Option 1 (Provisional):** Revenue - Base_COGS only (higher CM2, reflects example expense data)
- **Option 2 (Finance Baseline):** Revenue - all costs (true profitability, after Finance approval)
- **Toggle:** User selects via slicer; all dependent measures recalculate instantly

#### CM2 % (Parameterized)

```dax
CM2 % =
DIVIDE(
    [CM2 Amount],
    [Total Actual Revenue],
    0
)
```

**Format:** Percentage (0.0%)

**Interpretation:**
- Shows contribution margin as % of revenue
- Changes dynamically based on parameter selection
- **Green:** >20% (healthy margin) | **Yellow:** 15-20% | **Red:** <15% (pressure)

#### CM2 Forecast Variance

```dax
CM2 Forecast Variance ₹ =
VAR ForecastCM2Value = SUMX(Fact_Forecast, Fact_Forecast[Forecast_CM2_Value])
RETURN
    [CM2 Amount] - ForecastCM2Value
```

**Interpretation:**
- Positive = Actual CM2 > Forecast CM2 (upside)
- Negative = Actual CM2 < Forecast CM2 (downside)
- Shows margin realization quality

#### CM2 Forecast Variance %

```dax
CM2 Forecast Variance % =
VAR ForecastCM2Value = SUMX(Fact_Forecast, Fact_Forecast[Forecast_CM2_Value])
RETURN
    DIVIDE(
        [CM2 Amount] - ForecastCM2Value,
        ForecastCM2Value,
        0
    )
```

**Format:** Percentage (0.0%)

#### CM2 Realization % (vs. Target)

```dax
CM2 Realization % =
DIVIDE(
    [CM2 Amount],
    SUMX(Fact_Forecast, Fact_Forecast[Forecast_CM2_Value]),
    0
)
```

**Interpretation:**
- 100% = Actual CM2 equals forecast
- >100% = Beat margin forecast (upside)
- <100% = Missed margin forecast

#### CM2 Provisional Flag (Text)

```dax
CM2 Provisional Status =
VAR SelectedOption = SELECTEDVALUE(Param_CM2_Logic[OptionID], 1)
RETURN
    IF(
        SelectedOption = 1,
        "⚠️ PROVISIONAL (Example Expense Data)",
        "✓ APPROVED (Finance D1 Finalized)"
    )
```

**Usage:** Display on P&L page; warns users when using preliminary cost allocation.

---

## 2. Executive Theme JSON Palette

Save the following as `modern_trade_theme.json` and import into Power BI:
**File → Options and Settings → Options → Preview Features → (enable Custom Themes if needed)**
**File → Export Current Theme (for reference)**
Then upload via **View → Themes → Browse for Themes** → Select `modern_trade_theme.json`

### 2.1 Complete Theme Definition

```json
{
  "name": "ModernTradeExecutiveDarkBlue",
  "dataColors": [
    "#0F4C81",
    "#2E86AB",
    "#F6AE2D",
    "#F26419",
    "#33658A",
    "#55D6BE",
    "#7D82B8",
    "#D90429",
    "#1B3A6B",
    "#429EA6"
  ],
  "background": "#F8F9FA",
  "foreground": "#1A202C",
  "tableAccent": "#0F4C81",
  "visualStyles": {
    "*": {
      "*": {
        "background": [
          {
            "show": true,
            "color": { "solid": { "color": "#FFFFFF" } },
            "transparency": 0
          }
        ],
        "border": [
          {
            "show": true,
            "color": { "solid": { "color": "#E2E8F0" } },
            "radius": 4,
            "width": 1
          }
        ],
        "dropShadow": [
          {
            "show": true,
            "color": { "solid": { "color": "#00000014" } },
            "position": "Outer",
            "preset": "Custom",
            "shadowBlur": 6,
            "angle": 90,
            "shadowDistance": 2
          }
        ],
        "title": [
          {
            "show": true,
            "fontColor": { "solid": { "color": "#1A202C" } },
            "fontSize": 12,
            "fontFamily": "Segoe UI Semibold"
          }
        ]
      }
    },
    "card": {
      "*": {
        "background": [
          {
            "show": true,
            "color": { "solid": { "color": "#FFFFFF" } },
            "transparency": 0
          }
        ],
        "border": [
          {
            "show": true,
            "color": { "solid": { "color": "#0F4C81" } },
            "radius": 6,
            "width": 2
          }
        ],
        "dropShadow": [
          {
            "show": true,
            "color": { "solid": { "color": "#0F4C8126" } },
            "position": "Outer",
            "shadowBlur": 8,
            "angle": 90,
            "shadowDistance": 3
          }
        ],
        "labels": [
          {
            "show": true,
            "color": { "solid": { "color": "#0F4C81" } },
            "fontSize": 20,
            "fontFamily": "Segoe UI Bold"
          }
        ],
        "categoryLabels": [
          {
            "show": true,
            "color": { "solid": { "color": "#718096" } },
            "fontSize": 10,
            "fontFamily": "Segoe UI"
          }
        ]
      }
    },
    "columnChart": {
      "*": {
        "dataLabels": [
          {
            "show": true,
            "color": { "solid": { "color": "#1A202C" } },
            "fontSize": 9,
            "fontFamily": "Segoe UI"
          }
        ]
      }
    },
    "lineChart": {
      "*": {
        "dataLabels": [
          {
            "show": false
          }
        ]
      }
    },
    "table": {
      "*": {
        "grid": [
          {
            "outlineColor": { "solid": { "color": "#E2E8F0" } },
            "outlineWeight": 1
          }
        ],
        "header": [
          {
            "background": { "solid": { "color": "#0F4C81" } },
            "fontColor": { "solid": { "color": "#FFFFFF" } },
            "fontSize": 11,
            "fontFamily": "Segoe UI Semibold"
          }
        ],
        "total": [
          {
            "background": { "solid": { "color": "#F8F9FA" } },
            "fontColor": { "solid": { "color": "#0F4C81" } },
            "fontSize": 11,
            "fontFamily": "Segoe UI Bold"
          }
        ]
      }
    },
    "slicer": {
      "*": {
        "background": [
          {
            "show": true,
            "color": { "solid": { "color": "#F8F9FA" } }
          }
        ],
        "border": [
          {
            "show": true,
            "color": { "solid": { "color": "#CBD5E0" } },
            "radius": 4,
            "width": 1
          }
        ]
      }
    },
    "waterfall": {
      "*": {
        "dataLabels": [
          {
            "show": true,
            "color": { "solid": { "color": "#1A202C" } },
            "fontSize": 9
          }
        ]
      }
    }
  }
}
```

### 2.2 Color Palette Reference

| Role | Color | Use Case |
|------|-------|----------|
| **Primary Blue** | `#0F4C81` | KPI cards, table headers, primary series |
| **Secondary Blue** | `#2E86AB` | Secondary series, supporting elements |
| **Accent Gold** | `#F6AE2D` | Highlights, third series (attention-grabbing) |
| **Alert Red** | `#F26419` | Downside, risk, alert thresholds |
| **Status Green** | `#55D6BE` | Upside, achievement, positive variance |
| **Background** | `#F8F9FA` | Page/card background (light neutral) |
| **Text** | `#1A202C` | Primary text (dark neutral) |

---

## 3. Integrated Report Page Structure

### 3.1 Global Slicer Bar (Top of All Pages)

Add these slicers in sequence (left to right):

| Slicer | Table | Field | Type | Default | Notes |
|--------|-------|-------|------|---------|-------|
| **Date** | Dim_Date | DateKey | Dropdown | Current Month | Single-select |
| **Zone** | Dim_Geography | Zone | Buttons | All | Multi-select |
| **Chain** | Dim_Chain | Chain_Name | Dropdown | All | Multi-select with search |
| **CM2 Logic** | Param_CM2_Logic | Option | Dropdown | "Provisional (Base COGS Only)" | **NEW:** Parameterized toggle |

### 3.2 Page 1: Executive Summary (Enhanced)

**Layout:** KPI strip + dual trend + parameter info

#### Row 1: KPI Scorecard (5 cards)

| Card | Measure | Format | Conditional Color |
|------|---------|--------|-------------------|
| **Revenue** | [Total Actual Revenue] | ₹ 0.0 Cr | None |
| **Forecast Accuracy** | [Forecast Accuracy %] | 0.0% | Green ≥90%, Yellow 80-90%, Red <80% |
| **CM2 Amount** | [CM2 Amount] | ₹ 0.0 Cr | Varies by option (Prov./Baseline) |
| **CM2 %** | [CM2 %] | 0.0% | Green ≥20%, Yellow 15-20%, Red <15% |
| **CM2 Status** | [CM2 Provisional Status] | Text | Amber if Provisional, Green if Approved |

#### Row 2: Dual Trend (Left) + Status Info (Right)

**Left: Line + Clustered Column Combo**
- X-axis: Dim_Date[Month_Year]
- Column series 1: [Total Actual Revenue] (blue)
- Column series 2: [Total Forecast Revenue] (orange)
- Line series (secondary Y-axis): [CM2 %] (green line)
- Title: "Revenue & CM2 Margin Trend"

**Right: Parameter Selection Info Card**
```
┌─────────────────────────────────┐
│  CM2 Model: [SELECTEDVALUE]    │
│  Option: Provisional / Baseline │
│                                 │
│  Base_COGS:  ₹X Cr             │
│  + Logistics: ₹Y Cr (if Baseline)
│  + Scheme:    ₹Z Cr (if Baseline)
│  ──────────────────────────────  │
│  Total Cost:  ₹ABC Cr           │
└─────────────────────────────────┘
```

---

## 4. Implementation Checklist

- [ ] **Create Param_CM2_Logic table** (DAX or CSV)
  - [ ] Verify table appears in Data pane
  - [ ] Confirm NO relationships created (disconnected table)

- [ ] **Add all CM2 parameterized measures** (8 new measures)
  - [ ] [CM2 Amount] — main toggle measure
  - [ ] [CM2 %] — margin percentage
  - [ ] [CM2 Forecast Variance ₹] — actual vs. forecast variance
  - [ ] [CM2 Provisional Status] — text flag
  - [ ] Test: Select Option 1 → CM2 should update
  - [ ] Test: Select Option 2 → CM2 should update (larger value)

- [ ] **Apply theme**
  - [ ] Save `modern_trade_theme.json` to local folder
  - [ ] Power BI → View → Themes → Browse for Themes → Select file
  - [ ] Verify: All cards have blue borders + drop shadows
  - [ ] Verify: Table headers are dark blue with white text
  - [ ] Verify: Slicers have light gray background

- [ ] **Add CM2 Logic slicer to Page 1**
  - [ ] Insert → Slicer → Param_CM2_Logic[Option]
  - [ ] Position: Top-right of slicer bar
  - [ ] Style: Dropdown (not buttons)
  - [ ] Default: "Provisional (Base COGS Only)"
  - [ ] Test: Toggle between options → all CM2 measures update

- [ ] **Validate CM2 switching logic**
  - [ ] Select Option 1: CM2 = Revenue - Base_COGS only
  - [ ] Select Option 2: CM2 = Revenue - (Base_COGS + Logistics + Scheme)
  - [ ] Verify CM2 Amount in Option 2 is always ≤ Option 1
  - [ ] Verify [CM2 Status] flag shows ⚠️ or ✓ correctly

---

## 5. Formula Audit & Testing

| Scenario | Expected Behavior | Pass/Fail |
|----------|---|---|
| **No parameter selected** | Default to Option 1 (Provisional) | |
| **Option 1 selected** | [CM2 Amount] = Revenue - Base_COGS | |
| **Option 2 selected** | [CM2 Amount] = Revenue - (COGS + Logistics + Scheme) | |
| **Option 2 < Option 1** | Always true (baseline costs more than provisional) | |
| **Parameter + Date filter** | All CM2 measures respect date filter + parameter | |
| **Parameter + Chain filter** | Measures drill to chain level correctly | |
| **[CM2 %] on Option 1** | Typically 22-28% (higher, less allocations) | |
| **[CM2 %] on Option 2** | Typically 15-20% (lower, more allocations) | |

---

## 6. User Guidance

### For Finance Team
- **Use Option 1 (Provisional):** For internal forecasting before expense data approved
- **Use Option 2 (Finance Baseline):** For official P&L reporting after D1 approval
- **Toggle freely:** Slicer allows instant comparison without rebuild

### For Sales/Operations Team
- **Monitor both:** Understand the gap between provisional and baseline (cost allocation impact)
- **Track Variance:** [CM2 Forecast Variance %] shows margin realization quality
- **Accountability:** Flag states/chains with >10% margin variance

---

**Next Steps:**
1. Load `Param_CM2_Logic` table
2. Add 8 parameterized CM2 measures
3. Apply `modern_trade_theme.json`
4. Add CM2 Logic slicer to report page
5. Test all switching scenarios

---

**Related Documents:**
- `03_DAX_MEASURE_LIBRARY.md` — Base measures & helpers
- `04_REPORT_LAYOUT_SPECS.md` — Page design specs
- `README.md` — Implementation guide
