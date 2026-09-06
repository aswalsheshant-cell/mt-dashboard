# TOT% and MRP Corrected Rate: Excel Native Implementation Guide

## Overview

Three implementation paths for deriving TOT% and MRP Corrected Rate:

1. **Native Excel Formulas** (Immediate, Dynamic, Interactive)
2. **Excel VBA Macro** (One-Click Automation, 19k rows in <2 seconds)
3. **Power Query M Code** (Power BI Integrated, Refreshes Automatically)

Choose based on your workflow and frequency of use.

---

## Implementation Path 1: Native Excel Formulas (Quickest)

**Best for:** Ad-hoc analysis, one-time monthly updates, interactive exploration

### Step 1: Identify Your Source Columns

Open `MTEB2BMTDPrimaryAug26._3.xlsx` and verify:

| Data | Column Letter | Example Cell |
|------|----------------|--------------|
| MRP Rate | M | M2 |
| Invoice Quantity (Inv Qty) | N | N2 |
| Invoice Net Value (Inv. Net value) | P | P2 |

**If your file differs**, adjust the column letters accordingly.

### Step 2: Insert TOT% Formula (Column U / 21)

1. Click on cell `U1` and type the header: `TOT%`
2. Click on cell `U2` and paste:

```excel
=IF(OR(M2=0, N2=0, ISBLANK(M2), ISBLANK(N2)), 0, ((M2 * N2) - P2) / (M2 * N2))
```

**Why this formula:**
- Checks for zero or missing MRP Rate or Qty (returns 0 to avoid #DIV/0!)
- Calculates: (Gross MRP - Net Invoice) / Gross MRP
- Returns decimal (0.6398 for 63.98%)

3. **Format as Percentage:**
   - Select cell U2
   - Press `Ctrl + Shift + 5` (Windows) or `Cmd + Shift + 5` (Mac)
   - Or: Right-click → Format Cells → Number tab → Percentage → 2 decimals
   - Result: `63.98%`

### Step 3: Insert MRP Corrected Formula (Column O / 15)

1. Click on cell `O1` and type: `MRP Corrected Rate`
2. Click on cell `O2` and paste:

```excel
=IF(U2=0, M2, ROUND(M2 * (1 - U2), 2))
```

**Why this formula:**
- If TOT% is 0, keep original MRP Rate
- Otherwise: MRP Rate × (1 - TOT%)
- ROUND to 2 decimals to match currency precision

3. **Format as Currency:**
   - Select cell O2
   - Press `Ctrl + Shift + 4` (Windows) or `Cmd + Shift + 4` (Mac)
   - Or: Right-click → Format Cells → Currency → ₹ Indian Rupee → 2 decimals
   - Result: `₹197.73`

### Step 4: Copy Down to All Rows

**Method A: Double-Click Fill Handle (Fastest)**
1. Click on cell U2 (the TOT% formula)
2. Position cursor on the small square at the **bottom-right corner** of the cell (fill handle)
3. Double-click → Excel auto-fills down to the last row with data (~row 19070)
4. Repeat for column O (MRP Corrected Rate)

**Method B: Manual Drag**
1. Select cells U2:O2 (both formulas)
2. Copy: `Ctrl + C`
3. Select range U2:U19070 and O2:O19070
4. Paste: `Ctrl + V`

**Method C: Select and Fill Down**
1. Select U2:U19070 (or use Ctrl + Shift + End after clicking U2)
2. Press `Ctrl + D` (Fill Down)
3. Repeat for O2:O19070

**Expected Result:** All 19,070 rows populated in <5 seconds

---

## Implementation Path 2: Excel VBA Macro (Fully Automated)

**Best for:** Monthly recurring workflow, 19k-row batches, one-click execution

### Step 1: Open VBA Editor

1. Open your Primary Excel file
2. Press `Alt + F11` (Windows) or `Fn + Option + F11` (Mac)
3. The VBA Editor window opens

### Step 2: Insert a New Module

1. Click: Insert → Module
2. A blank code pane appears on the right

### Step 3: Paste the Macro Code

Copy and paste the entire code below into the module:

```vba
Sub DeriveTOTAndMRPCorrected()
    Dim ws As Worksheet
    Dim lastRow As Long
    
    Set ws = ActiveSheet
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    
    If lastRow < 2 Then
        MsgBox "No data found.", vbExclamation
        Exit Sub
    End If
    
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    
    ' Set Column Headers
    ws.Cells(1, 15).Value = "MRP Corrected Rate"
    ws.Cells(1, 21).Value = "TOT%"
    
    ' Enter vector formulas across the range
    ' M = MRP Rate (col 13), N = Inv Qty (col 14), P = Net Value (col 16)
    ws.Range(ws.Cells(2, 21), ws.Cells(lastRow, 21)).FormulaR1C1 = _
        "=IF(OR(RC13=0, RC14=0), 0, ((RC13*RC14) - RC16) / (RC13*RC14))"
        
    ws.Range(ws.Cells(2, 15), ws.Cells(lastRow, 15)).FormulaR1C1 = _
        "=ROUND(RC13 * (1 - RC21), 2)"
    
    ' Format Columns
    ws.Columns(21).NumberFormat = "0.00%"
    ws.Columns(15).NumberFormat = "#,##0.00"
    
    ' Convert Formulas to Hard Values (Prevents workbook bloat on 19k rows)
    ws.Range(ws.Cells(2, 21), ws.Cells(lastRow, 21)).Value = _
        ws.Range(ws.Cells(2, 21), ws.Cells(lastRow, 21)).Value
    ws.Range(ws.Cells(2, 15), ws.Cells(lastRow, 15)).Value = _
        ws.Range(ws.Cells(2, 15), ws.Cells(lastRow, 15)).Value
    
    Application.Calculation = xlCalculationAutomatic
    Application.ScreenUpdating = True
    
    MsgBox "✓ Derived TOT% and MRP Corrected Rate for " & (lastRow - 1) & " rows!", _
           vbInformation, "Derivation Complete"
End Sub
```

### Step 4: Run the Macro

1. Press `F5` or click the green Play button (▶)
2. Macro executes: ~2 seconds for 19,070 rows
3. Popup confirms: `✓ Derived TOT% and MRP Corrected Rate for 19069 rows!`
4. Close VBA Editor: Press `Alt + F4`
5. Your Primary file now has columns 15 and 21 populated

### Step 5: Save the Workbook (Enable Macros)

When prompted to save:
- Choose: **Save as** → **Excel Macro-Enabled Workbook (.xlsm)**
- File naming: `MTEB2BMTDPrimaryAug26._3_MacroEnabled.xlsm`

---

## Implementation Path 3: Power Query M Code (Power BI Integrated)

**Best for:** Power BI refresh workflows, no manual Excel file editing needed

### In Power BI Desktop:

1. Open Power Query Editor:
   - **Home** → **Transform Data**

2. Locate the Primary data query

3. Add a new custom step. Click **Add Step** and paste:

```m
// Define TOT% Calculation
#"Added TOT_Pct" = Table.AddColumn(
    #"PreviousStep", 
    "TOT%", 
    each 
        if [Inv Qty] = null or [Inv Qty] <= 0 or [MRP Rate] = null or [MRP Rate] <= 0 
        then 0 
        else (([MRP Rate] * [Inv Qty]) - [Inv. Net value]) / ([MRP Rate] * [Inv Qty]), 
    Percentage.Type
),

// Define MRP Corrected Calculation
#"Added MRP_Corrected" = Table.AddColumn(
    #"Added TOT_Pct", 
    "MRP Corrected Rate", 
    each Number.Round([MRP Rate] * (1 - [#"TOT%"]), 2), 
    type number
)

in
    #"Added MRP_Corrected"
```

4. Click **Close & Apply**

5. Power BI automatically calculates both columns on every refresh without touching the source Excel file

---

## Conditional Formatting: Highlight Anomalies

### Method 1: Simple Highlight (Recommended)

Target: Highlight rows where TOT% is negative or excessive (>80%)

#### Step 1: Select the TOT% Data Column

1. Click column header `U` (or your TOT% column)
2. Select all data: `U2:U19070`

#### Step 2: Apply Conditional Formatting Rules

**Rule 1 — Red for Negative TOT% (< 0%):**

1. Home → **Conditional Formatting** → **Highlight Cells Rules** → **Less Than...**
2. Enter value: `0` or `0%`
3. Format: Light Red Fill with Dark Red Text
4. Click OK

**Rule 2 — Amber for High TOT% (> 80%):**

1. Home → **Conditional Formatting** → **Highlight Cells Rules** → **Greater Than...**
2. Enter value: `0.8` (if formatted as percentage) or `80` (if formatted as 0–100)
3. Click **Custom Format** → **Fill** → Select Amber/Orange → Click OK

**Result:** All anomalous rows in column U are now highlighted for quick visual audit.

---

### Method 2: Full-Row Highlighting (Comprehensive Audit)

Highlight the **entire row** when TOT% is anomalous

#### Setup:

1. Select your full data range: `A2:U19070`
   - Ensure `A2` is the active cell in your selection
2. Home → **Conditional Formatting** → **New Rule...**
3. Choose: **Use a formula to determine which cells to format**

#### Rule 1: Negative TOT% (Red Fill)

Paste formula:
```excel
=AND(ISNUMBER($U2), $U2 < 0)
```

- Click **Format** → **Fill** tab → Select Soft Red (#F8D7DA)
- Click OK → OK

#### Rule 2: Excessive TOT% (Amber Fill)

1. **New Rule** → **Use a formula...**

Paste formula (if column U is stored as decimal 0.80):
```excel
=AND(ISNUMBER($U2), $U2 > 0.8)
```

Or (if stored as 0–100 integer):
```excel
=AND(ISNUMBER($U2), $U2 > 80)
```

- Click **Format** → **Fill** tab → Select Soft Orange (#FFF3CD)
- Click OK → OK

**Result:** Entire rows flagged when TOT% is anomalous. Use **Data** → **Filter** → **Filter by Color** to isolate exceptions.

---

### Method 3: VBA Automated Conditional Formatting

**One-click setup for both highlighting rules:**

1. Press `Alt + F11` to open VBA Editor
2. Click **Insert** → **Module**
3. Paste:

```vba
Sub ApplyTOTConditionalFormatting()
    Dim ws As Worksheet
    Dim lastRow As Long
    Dim dataRange As Range
    Dim ruleNeg As FormatCondition, ruleHigh As FormatCondition

    Set ws = ActiveSheet
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    If lastRow < 2 Then Exit Sub

    ' Range spanning from Column A to Column U
    Set dataRange = ws.Range("A2:U" & lastRow)
    
    ' Clear existing rules
    dataRange.FormatConditions.Delete

    ' Rule 1: Red for TOT% < 0
    Set ruleNeg = dataRange.FormatConditions.Add(xlExpression, , "=AND(ISNUMBER($U2), $U2<0)")
    With ruleNeg
        .Interior.Color = RGB(248, 215, 218) ' Soft Red
        .Font.Color = RGB(114, 28, 36)
    End With

    ' Rule 2: Amber for TOT% > 80% (0.8)
    Set ruleHigh = dataRange.FormatConditions.Add(xlExpression, , "=AND(ISNUMBER($U2), $U2>0.8)")
    With ruleHigh
        .Interior.Color = RGB(255, 243, 205) ' Soft Amber
        .Font.Color = RGB(133, 100, 4)
    End With
    
    MsgBox "Conditional formatting applied to " & dataRange.Address, vbInformation
End Sub
```

4. Press F5 to run
5. Both highlighting rules applied instantly

---

## Comparison: Which Method to Use?

| Method | Speed | Maintenance | Recalculation | Best For |
|--------|-------|-------------|----------------|----------|
| **Excel Formulas** | ~5 sec | Manual (copy/paste) | Dynamic (auto-recalc) | One-time, exploratory |
| **VBA Macro** | <2 sec | Auto (one button) | Convert to values | Monthly recurring drops |
| **Power Query** | Integrated | Auto (refresh) | Dynamic (query refresh) | Power BI workflow |

---

## Troubleshooting

### Issue: Formula Returns #DIV/0! Error
**Cause:** MRP Rate or Inv Qty is zero
**Solution:** Formulas already include `IF(OR(...))` guard; verify source data

### Issue: Values appear as decimals (0.6398) instead of percentages (63.98%)
**Solution:** Select column U → Right-click → Format Cells → Percentage → 2 decimals

### Issue: Macro won't run (greyed out)
**Solution:** 
1. Save file as Excel Macro-Enabled (.xlsm)
2. Trust the workbook: File → Options → Trust Center → Trust Center Settings → Macro Settings → Enable all macros

### Issue: Paste Special → Values doesn't work
**Solution:** The macro already converts formulas to values at the end; if you need to do it manually:
1. Select column with formulas
2. Copy: Ctrl + C
3. Right-click → Paste Special → Values only → OK

---

## Summary Table: Formula Syntax

| Component | Python Script | Excel Formula | Power Query M |
|-----------|---------------|---------------|--------------|
| **TOT%** | `(MRP × Qty - Net) / (MRP × Qty) × 100` | `=((M2*N2)-P2)/(M2*N2)` | `(([MRP Rate] * [Inv Qty]) - [Inv. Net value]) / ([MRP Rate] * [Inv Qty])` |
| **MRP Corrected** | `MRP × (1 - TOT% / 100)` | `=M2*(1-U2)` | `[MRP Rate] * (1 - [#"TOT%"])` |

---

## Next Steps After Implementation

1. **Validate 5-10 rows manually** against sample results
2. **Export to Power BI** or dashboard pipeline
3. **Apply conditional formatting** to flag anomalies
4. **Review exceptions** flagged with red/amber highlighting
5. **Archive** processed file and repeat monthly

---

## Files & References

| File | Purpose |
|------|---------|
| `scripts/derive_tot_and_mrp.py` | Python implementation (CLI) |
| `EXCEL_NATIVE_DERIVATION_GUIDE.md` | This guide (Excel native approaches) |
| `README_TOT_MRP_Derivation.md` | Original technical documentation |

---

*Last Updated: 2026-09-03*  
*Applicable to: MTEB2BMTDPrimaryAugXX._3.xlsx and similar Primary data files*
