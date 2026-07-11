# Expense_Assumptions_Input — Editable Excel Table Structure

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** v0 — Provisional, Pending Finance Validation  
**Purpose:** Centralized, auditable expense assumptions linked to Power BI via external Excel file

---

## Overview

This table is **NOT** hard-coded in Power Query or DAX. Instead:
- **Managed in Excel** (separate workbook: `Expense_Assumptions_Input.xlsx`)
- **Read by Power BI** via Power Query (external connection)
- **Updated manually** or via API/script (not by Power BI itself)
- **Refreshed in Power BI** each time the workbook opens or user clicks Refresh

**Why this design?**
- All expense values remain **auditable** in their source file
- **No hidden calculations** in Power BI measures
- Changes to expenses **propagate immediately** to all dependent visuals
- **Version control**: Excel file tracked in repo (or linked to Finance's shared drive)
- **Non-technical users** (Finance) can update assumptions without touching Power BI

---

## Table Structure: Expense_Assumptions_Input

**Location:** `PowerBI/SeedData/Expense_Assumptions_Input.xlsx` (Sheet: "Assumptions")

**Primary Key:** (Month, Chain, Store_Code, Brand, Cost_Type, Effective_From)

| Column | Data Type | Editable | Required | Description | Example |
|--------|-----------|----------|----------|-------------|---------|
| **Month** | Date (or YYYY-MM) | ✓ | ✓ | Month of expense (Apr-26, May-26, etc.) | 2026-04-01 |
| **Chain** | Text | ✓ | ✓ | Chain name (raw from Fact_Offtake_Safe) | Reliance, Walmart, Amazon |
| **Store_Code** | Text | ✓ | ✓ | Store identifier (from store master, pending) | REL-001, WAL-042 |
| **Store_Name** | Text | | | Store name (reference, not editable) | Reliance Thane Store 1 |
| **Brand** | Text | ✓ | ✓ | Brand name (from Fact_Offtake_Safe) | Mamaearth, TDC, AQ, BB |
| **BA_Salary** | Currency | ✓ | | Monthly BA salary (₹, per employee) | 15000 |
| **BA_Supervisor_Cost** | Currency | ✓ | | Monthly supervisor/manager cost (₹) | 25000 |
| **Dmart_BA_Merchandiser_Cost** | Currency | ✓ | | D'Mart BA/merchandiser monthly cost (₹) | 12000 |
| **Other_Employee_Cost** | Currency | ✓ | | Other staff (operations, etc.) monthly (₹) | 8000 |
| **Visibility_Cost** | Currency | ✓ | | Visibility/fixture rental (₹ or ₹ Lakh) | 5000 |
| **Rental_Cost** | Currency | ✓ | | Space/counter rental (₹ or ₹ Lakh) | 10000 |
| **NPI_Listing_Cost** | Currency | ✓ | | New Product Introduction listing fee (₹) | 2500 |
| **TOT_Percentage** | Decimal (%) | ✓ | | Trade-off-Trade % of NSV (e.g., 2.5 = 2.5%) | 2.5 |
| **TOT_Value** | Currency | ✓ | | Trade-off-Trade fixed value (₹, if not %) | (leave blank if using %) |
| **Promotional_Offer_Percentage** | Decimal (%) | ✓ | | Promotional discount % of NSV | 3.0 |
| **Promotional_Offer_Value** | Currency | ✓ | | Promotional fixed value (₹, if not %) | (leave blank if using %) |
| **Claims_Reimbursements** | Currency | ✓ | | Ad-hoc claims/reimbursements (₹) | 1500 |
| **Other_Direct_Cost** | Currency | ✓ | | Miscellaneous direct costs (₹) | 500 |
| **COGS_Rate** | Decimal | ✓ | | COGS as % of NSV (e.g., 0.1655 = 16.55%, pending Finance confirmation) | 0.1655 |
| **COGS_Value** | Currency | ✓ | | COGS fixed value (₹, if not rate-based) | (leave blank if using rate) |
| **Tax_Basis** | Text | ✓ | | Tax treatment: "Excl_Tax" / "Incl_Tax" / "Unknown" | Excl_Tax |
| **Allocation_Method** | Text | ✓ | | How cost allocates: "Direct" / "By_Headcount" / "By_MRP_Share" / "By_Store_Count" / "Equal_Split" / "Unknown" | By_Headcount |
| **Effective_From** | Date | ✓ | ✓ | Start date for this cost assumption | 2026-04-01 |
| **Effective_To** | Date | ✓ | | End date (leave blank for ongoing) | 2026-06-30 |
| **Data_Status** | Text | | ✓ | "Actuals" / "Estimates" / "Pending" / "Provisional" / "Validated" | Provisional |
| **Missing_Cost_Flag** | Boolean (Y/N) | | | Mark TRUE if cost data is unavailable for this line | N |
| **Provisional_Cost_Flag** | Boolean (Y/N) | | | Mark TRUE if cost is not yet validated by Finance | Y |
| **Mapping_Status** | Text | | | "Mapped" / "Partial" / "Unmapped" / "Under_Review" | Mapped |
| **Finance_Validation_Status** | Text | | | "Awaiting" / "Confirmed" / "Rejected" / "Clarification_Needed" | Awaiting |
| **Last_Updated_Date** | Date | | | Auto-fill on save (or manual) | 2026-07-11 |
| **Updated_By** | Text | | | Name/ID of person who updated this row | Finance Team |
| **Source_File** | Text | | | Source workbook/sheet (audit trail) | All_Expenses_together.xlsx \| Sheet 2 "BA salary" |
| **Remarks** | Text | ✓ | | Free-form notes/flags (e.g., "awaiting Finance confirmation on COGS factor") | Pending Q2 answer |

---

## Key Design Rules

### 1. **Percentage vs. Value Inputs**

For fields where BOTH % and value columns exist (TOT, Promotional Offer, COGS):

**Rule:** Priority is **determined by `Allocation_Method` and user intent**, not automatic switching.

**Examples:**
- If `TOT_Percentage = 2.5` and `TOT_Value = blank`, calculate as: `TOT_Amount = NSV × 0.025`
- If `TOT_Percentage = blank` and `TOT_Value = 5000`, use fixed value: `TOT_Amount = 5000`
- If **both are filled**, raise a **validation warning** in Power BI: "⚠️ TOT: Both % and value provided. Clarify which takes priority in remarks."

**Power BI Measure Logic:**
```
TOT_Amount = 
  IF(
    NOT ISBLANK(Assumptions[TOT_Percentage]),
    [NSV Cr] × Assumptions[TOT_Percentage] / 100,
    IF(
      NOT ISBLANK(Assumptions[TOT_Value]),
      Assumptions[TOT_Value] / 10000000,  // Convert ₹ to Crore
      BLANK()
    )
  )
```

### 2. **Tax Basis Awareness**

All cost inputs must specify **tax treatment**:
- **"Excl_Tax"** — Cost is net of tax (e.g., BA salary, internal costs)
- **"Incl_Tax"** — Cost includes GST (e.g., vendor invoices, visibility rental)
- **"Unknown"** — Awaiting Finance clarification

**Rule:** Do NOT mix tax bases in CM2 calculation until Finance confirms the formula (Q2).

### 3. **Allocation Method Flexibility**

Different cost types allocate differently:

| Cost Type | Default Allocation | Alternatives |
|-----------|-------------------|---------------|
| BA Salary | By_Headcount (# BA per store) | By_Store_Count, Direct |
| Visibility/Rental | Direct (per store) | By_MRP_Share, Equal_Split |
| TOT | By_MRP_Share (% of store NSV) | Direct, By_Store_Count |
| Promotional | By_MRP_Share (% of store NSV) | Direct, By_Store_Count |
| COGS | By_MRP_Share (% of store NSV) | Rate-based (factor × NSV) |

**Power BI must support:** Users changing allocation method per row without breaking calculations.

### 4. **Missing Cost Handling**

If a cost is **not available** for a store/month/brand:

**Do NOT default to 0.** Instead:
- Set `Missing_Cost_Flag = Y`
- Leave the cost column BLANK
- Set `Data_Status = "Pending"`
- Power BI displays: ⚠️ Missing cost data (not 0, which would incorrectly reduce CM2)

**Example:**
```
Chain: Reliance, Store: REL-001, Month: Apr-26, Brand: Mamaearth
- BA_Salary: 15000 (✓ available)
- NPI_Listing_Cost: (blank, Missing_Cost_Flag = Y, reason: "Listing not yet charged")
- TOT_Percentage: (blank, Missing_Cost_Flag = Y, reason: "TOT % pending from Reliance")
```

**Power BI displays:** "Cost Data Pending" in store classification, visuals show `#N/A` or conditional formatting to highlight gaps.

### 5. **Audit Trail**

Every row must track:
- `Last_Updated_Date` — When this assumption was last changed
- `Updated_By` — Who changed it (Finance, Operations, etc.)
- `Source_File` — Where the data came from (audit trail)
- `Remarks` — Why the change was made

**Example:**
```
Updated_By: "Finance Team (Ankit)"
Last_Updated_Date: 2026-07-15
Source_File: "All_Expenses_together.xlsx | Sheet 2 BA salary"
Remarks: "Updated BA salary from Sheet 2 based on Jun'26 payroll. Pending confirmation of CTC definition (Q3)."
```

---

## Seed Data (Initial Sample)

**File:** `PowerBI/SeedData/Expense_Assumptions_Input.xlsx`

**Sheet:** "Assumptions"

| Month | Chain | Store_Code | Brand | BA_Salary | BA_Supervisor_Cost | Visibility_Cost | TOT_Percentage | Promotional_Offer_Percentage | NPI_Listing_Cost | Tax_Basis | Allocation_Method | Effective_From | Data_Status | Finance_Validation_Status | Remarks |
|-------|-------|-----------|-------|-----------|-------------------|-----------------|----------------|-------------------------------|------------------|-----------|-------------------|----------------|-----------|------------------------|---------|
| 2026-04 | Reliance | REL-001 | Mamaearth | 15000 | 25000 | 5000 |  | 3.0 | 2500 | Excl_Tax | By_Headcount | 2026-04-01 | Provisional | Awaiting | From Sheet 2 BA salary; TOT % pending from business |
| 2026-04 | Reliance | REL-001 | Mamaearth | (blank) | (blank) | (blank) | 2.5 | (blank) | (blank) | Unknown | Unknown | 2026-04-01 | Pending | Awaiting | COGS unit unknown; awaiting Q1 answer; TOT % waiting Q3 |
| 2026-05 | Walmart | WAL-042 | TDC | 12000 | 20000 | 4000 |  | 2.5 | (blank) | Excl_Tax | By_Headcount | 2026-05-01 | Provisional | Awaiting | From Sheet 4 Dmart BA-Merchandiser; Listing not charged yet |
| 2026-06 | Amazon | AMZ-015 | AQ | 10000 | (blank) | 6000 |  | 3.5 | 1500 | Excl_Tax | Direct | 2026-06-01 | Provisional | Awaiting | From Sheet 5 other employ; supervisor absent; TOT % pending |

---

## Power Query Script: Load from Excel

**File:** `PowerBI/Safe_Blocks/PowerQuery_Expense_Assumptions.pq`

```m
let
  Source = Excel.Workbook(
    File.Contents("C:\Users\[Your Path]\Expense_Assumptions_Input.xlsx"),
    null,
    true
  ),
  ExpenseAssumptions_Sheet = Source{[Item="Assumptions"]}[Data],
  #"Promoted Headers" = Table.PromoteHeaders(ExpenseAssumptions_Sheet, [PromoteAllScalars=true]),
  #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {
    {"Month", type date},
    {"Chain", type text},
    {"Store_Code", type text},
    {"Store_Name", type text},
    {"Brand", type text},
    {"BA_Salary", type number},
    {"BA_Supervisor_Cost", type number},
    {"Dmart_BA_Merchandiser_Cost", type number},
    {"Other_Employee_Cost", type number},
    {"Visibility_Cost", type number},
    {"Rental_Cost", type number},
    {"NPI_Listing_Cost", type number},
    {"TOT_Percentage", type number},
    {"TOT_Value", type number},
    {"Promotional_Offer_Percentage", type number},
    {"Promotional_Offer_Value", type number},
    {"Claims_Reimbursements", type number},
    {"Other_Direct_Cost", type number},
    {"COGS_Rate", type number},
    {"COGS_Value", type number},
    {"Tax_Basis", type text},
    {"Allocation_Method", type text},
    {"Effective_From", type date},
    {"Effective_To", type date},
    {"Data_Status", type text},
    {"Missing_Cost_Flag", type logical},
    {"Provisional_Cost_Flag", type logical},
    {"Mapping_Status", type text},
    {"Finance_Validation_Status", type text},
    {"Last_Updated_Date", type date},
    {"Updated_By", type text},
    {"Source_File", type text},
    {"Remarks", type text}
  }),
  #"Filtered Rows" = Table.SelectRows(#"Changed Type", each [Data_Status] <> null),
  #"Added Flag" = Table.AddColumn(#"Filtered Rows", "Is_Provisional", each [Finance_Validation_Status] <> "Confirmed", type logical)
in
  #"Added Flag"
```

**Notes:**
- Update file path to match your environment
- Filters out blank rows
- Adds `Is_Provisional` flag for conditional formatting in visuals
- Refreshes each time Power BI opens the workbook

---

## Validation Rules (Excel + Power BI)

### Excel-Side (Data Entry Validation)

**Columns to validate in Excel Data Validation:**

| Column | Type | Allowed Values |
|--------|------|----------------|
| **Data_Status** | List | Actuals, Estimates, Pending, Provisional, Validated |
| **Finance_Validation_Status** | List | Awaiting, Confirmed, Rejected, Clarification_Needed |
| **Mapping_Status** | List | Mapped, Partial, Unmapped, Under_Review |
| **Tax_Basis** | List | Excl_Tax, Incl_Tax, Unknown |
| **Allocation_Method** | List | Direct, By_Headcount, By_MRP_Share, By_Store_Count, Equal_Split, Unknown |
| **Missing_Cost_Flag** | Checkbox | Y / N |
| **Provisional_Cost_Flag** | Checkbox | Y / N |

### Power BI-Side (Warnings & Conditional Formatting)

**Visual alerts:**
1. ⚠️ **Missing Cost Warning** — Row with `Missing_Cost_Flag = Y` highlighted in yellow
2. ⚠️ **Both % and Value Filled** — TOT/Promotional/COGS rows with both % and value highlighted in red
3. ⚠️ **Provisional Flag** — Rows with `Provisional_Cost_Flag = Y` shown in italics or dashed border
4. ⚠️ **Awaiting Validation** — Rows with `Finance_Validation_Status = "Awaiting"` flagged with icon

---

## Items Blocked Until Finance/Operations Provide Data

### Critical (Q & A Required)

| Item | Question | Blocker | Timeline |
|------|----------|---------|----------|
| COGS Unit | Q1: What do 0.1655 values represent? % or ratio? | Cannot finalize COGS allocation | 1 week |
| CM2 Formula | Q2: Exact formula, tax-basis treatment | Cannot finalize CM2 measures | 1 week |
| CTC Definition | Q3: Base/gross/total? Why some values <₹2K? | Cannot allocate BA costs correctly | 1 week |
| TOT % | Q4: What % or value applies per chain/month? | TOT cost row will remain blank | 1 week |
| Promotional % | Q5: What % or fixed value per chain? | Promotional cost row will remain blank | 1 week |

### High-Priority (Mappings Required)

| Item | Needed From | Blocker | Timeline |
|------|-------------|---------|----------|
| Store Master | Operations/Reliance | Cannot map store_code → chain → zone | 2 weeks |
| BA Deployment List | Operations/Reliance/HR | Cannot filter BA vs Non-BA stores | 2 weeks |
| Zone Standardization | Operations | Cannot reconcile generic vs P6 zones | 1 week |

---

## Return Path: File Upload & Refresh

### Setup (One-Time)

1. **Create Excel file:** `Expense_Assumptions_Input.xlsx` (save to shared drive or repo)
2. **Power BI loads via Power Query:** External connection to Excel file
3. **Commit to repo:** `PowerBI/SeedData/Expense_Assumptions_Input.xlsx` (seed with sample data)

### Ongoing (Monthly Refresh)

**Finance updates assumptions in Excel:**
1. Add new row for current month + chain + store
2. Fill in available costs (BA salary from Sheet 2, visibility from Sheet 6, etc.)
3. Leave missing costs blank (set Missing_Cost_Flag = Y)
4. Save Excel file

**Power BI refreshes:**
1. User opens Power BI file
2. Automatically reads latest from Excel (Power Query external connection)
3. All dependent visuals update (no manual Power BI editing required)

---

## Example: How Expense Flow Works

**Scenario:** Finance has Apr-26 BA salary data (Sheet 2) but TOT % still pending.

**Excel (Expense_Assumptions_Input.xlsx):**
```
Month: 2026-04
Chain: Reliance
Store_Code: REL-001
Brand: Mamaearth
BA_Salary: 15000 (from Sheet 2 BA salary)
BA_Supervisor_Cost: 25000 (from Sheet 2)
TOT_Percentage: (blank) → Missing_Cost_Flag = Y, Remarks: "Awaiting TOT % from business"
```

**Power BI (BA Stores Profitability page):**
```
Store KPI: "REL-001 | Mamaearth | Apr-26"
- NSV: ₹1.5 Cr (from Fact_Offtake_Safe)
- BA Salary Cost: ₹0.15 Lakh (15000 ÷ 100)
- Supervisor Cost: ₹0.25 Lakh
- TOT Cost: ⚠️ (Missing_Cost_Flag shown; data pending)
- Total Support Cost: ₹0.40 Lakh (salary + supervisor; TOT excluded)
- Provisional CM2: ⚠️ (cannot finalize without TOT)
- Data Status: "Cost Data Pending" (not "Below Break-even" or "Strong Performer")
```

**Finance updates Excel with TOT % → Next refresh:**
```
TOT_Percentage: 2.5
Missing_Cost_Flag: N
Finance_Validation_Status: Confirmed
```

**Power BI recalculates automatically:**
```
- TOT Cost: ₹3.75 Lakh (1.5 Cr × 2.5%)
- Total Support Cost: ₹4.15 Lakh
- Provisional CM2: ₹1.35 Cr (1.5 - 0.15 - 0.25 - 3.75)
- Data Status: "Monitor" (or "Strong Performer", depending on classification threshold)
```

---

## Files to Create/Update

| File | Type | Status | Purpose |
|------|------|--------|---------|
| `PowerBI/SeedData/Expense_Assumptions_Input.xlsx` | Excel | Create | Seed data (sample Apr-May-Jun, 3-5 chains, 5-10 stores) |
| `PowerBI/Safe_Blocks/PowerQuery_Expense_Assumptions.pq` | Power Query | Create | Load Excel into Power BI |
| (This file) | Doc | Create | Table structure & design rules |

---

## Next Steps

1. **Finance provides answers to Q1-Q5** (COGS unit, CM2 formula, CTC definition, TOT %, Promotional %)
2. **Operations provides store master** (store_code → chain → zone mapping, BA deployment list)
3. **Power BI Build Phase (1-2 hours):**
   - Create Expense_Assumptions_Input table via Power Query
   - Build 12 Executive KPI measures
   - Build Store Profitability matrix visual
   - Add conditional formatting for store classification & warnings
4. **Validation:** Run through all stores, check that missing costs are flagged (not zero), confirm CM2 changes when expenses updated
5. **Archive:** Commit to `claude/safe-powerbi-dashboard-rulings` branch

---

**Status:** v0 — Provisional, awaiting Finance & Operations inputs  
**Branch:** claude/safe-powerbi-dashboard-rulings  
**PR:** #14 (do not merge until Finance confirms Q1-Q5)

