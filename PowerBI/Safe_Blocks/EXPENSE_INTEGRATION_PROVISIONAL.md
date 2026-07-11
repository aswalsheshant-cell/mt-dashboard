# Expense Integration — Provisional Model (v0 — Pending Finance Validation)

**Status:** ⚠️ **PROVISIONAL ONLY** — All CM2, Profitability, BA Withdrawal, Store Closure logic BLOCKED until Finance confirms formula & tax basis

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Date:** 2026-07-11  
**Scope:** Data standardization, mapping, QC findings, and safe provisional measures only

---

## 1. Expense-Sheet QC Findings

### Sheet 1: "claim" (Actually COGS+SC Teams, not claims)

| Finding | Severity | Issue | Impact |
|---------|----------|-------|--------|
| **NAME MISMATCH** | HIGH | Sheet named "claim" but contains COGS & SC Teams data | Requires clarification: is this COGS? SC Teams? Both? |
| **UNKNOWN UNITS** | CRITICAL | Decimal factors (0.1655, 0.1693, 0.1746, etc.) with NO unit label | ⚠️ **Assumption forbidden**: Do NOT assume 0.1655 = 16.55% until Finance confirms |
| **NO DOCUMENTATION** | HIGH | No labels explaining factor basis (per unit? %, ratio, rupees per 100,000?) | Cannot build measures until unit confirmed |
| **DUPLICATE SECTIONS** | MEDIUM | Two sections: "Cogs+SC Teams" (rows 2-16) and "Cogs" (rows 18-48) | Clarify: are these different cost types or same data twice? |
| **BRAND MAPPING** | MEDIUM | Brands: Mamaearth, TDC, AQ, BB, DRS — TDC appears to be a campaign/product, not a brand | Brand vs Product vs Campaign hierarchy unclear |
| **CHAIN MAPPING** | MEDIUM | Chains: Dmart, Reliance, Apollo, Others — matches offtake data but OTHERS is vague | Need actual chain names for Others category |
| **DATE FORMAT** | MEDIUM | Excel serial dates (46113 = Apr-26 correct, but some rows missing month labels) | Standardize: use YYYY-MM format |

**Data Sample (Raw):**
```
Row 5: [46113, 0.1656, 0.1654, 0.1793, 0.1749, | 46113, 0.1506, 0.1525, 0.1478, 0.1485, | ...5 brands × 4 chains]
⚠️ Interpretation: UNKNOWN. Do NOT multiply by NSV or MRP until confirmed.
```

---

### Sheet 2: "BA salary" (Actually Claims/Expense Summary, not BA salary)

| Finding | Severity | Issue | Impact |
|---------|----------|-------|--------|
| **NAME MISMATCH** | HIGH | Sheet named "BA salary" but contains claims summary (NPI listing, Off invoice, Promo offer, Rental, Visibility) | Rename to clarify: "Claims_Summary" or "Expense_Summary"? |
| **INCORRECT COMPANY MAPPING** | HIGH | 6 companies listed: Guardian Healthcare, Health & Glow, Metro Cash & Carry, Reliance, V-Mart, Walmart | These are NOT brands in offtake data. Are they vendors? Channels? Need mapping to chain/brand |
| **MISSING DATA** | HIGH | Rows show values only for some columns (e.g., Row 2 "NPI listing" = 82,600 for 1 company only, rest empty) | Sparse data matrix — clarify what empty cells mean (₹0? data not available? N/A?) |
| **UNIT CONFIRMED** | OK | Values in actual ₹ (82,600; 354,035.39; etc.) | OK to use directly as rupees |
| **INCOMPLETE MONTHS** | MEDIUM | Only Apr-26 and May-26 visible (2 months of 27 in offtake range) | Need full Apr'24–Jun'26 monthly breakdown |
| **EXPENSE TYPE MAPPING** | MEDIUM | 5 expense types: NPI listing, Off invoice, Promotion offer, Rental, Visibility | Need clarification: which are COGS? which are direct costs? which are overheads? |

**Data Sample (Raw):**
```
Month=Apr-26, Claim="NPI listing", Guardian=82,600, Others=empty
Month=Apr-26, Claim="Off invoice", Guardian=354,035, Metro=482,920, Others=empty
⚠️ Interpretation: Guardian and Metro incurred specific expense types; others did not or data missing.
```

---

### Sheet 3: "BA Supervisor" (ISR/PSR Payroll Data)

| Finding | Severity | Issue | Impact |
|---------|----------|-------|--------|
| **DESIGNATION UNCLEAR** | HIGH | ISR, PSR, MIS-EXECUTIVE — acronyms undefined | Need mapping: ISR = Inside Sales Rep? Supervisor? PSR = Product Sale Rep? |
| **ZONE MAPPING** | MEDIUM | Zones in this sheet: CENTRAL, NORTH-1, NORTH-2, WEST-1, WEST-2, SOUTH-1, SOUTH-2, EAST | Good alignment with P6 zones but need to verify one-to-one mapping |
| **NO CHAIN MAPPING** | HIGH | No chain/store field; only location name (LUCKNOW, PARBHANI, PUNE, etc.) | Cannot allocate costs to chain/store without location master |
| **CTC VS EXPENSE COLUMNS** | MEDIUM | 4 columns: CTC, Expense, Incentive, NET_PAY — logic unclear | CTC is base salary? Is "Expense" = benefits deducted? Need definition |
| **ACTIVE/INACTIVE STATUS** | LOW | Status column shows "Active" / "Inactive" | OK for filtering but need definition of Inactive (on leave? separated?) |
| **UNIT CONFIRMED** | OK | CTC, Expense, Incentive in actual ₹ | OK |
| **DATA COMPLETENESS** | OK | 750 rows, consistent structure, clear headers | Data appears clean |

**Data Sample (Raw):**
```
Month=Apr, Name=MANISH KUMAR NIGAM, Zone=CENTRAL, Location=LUCKNOW, Designation=ISR, DOJ=10/02/2024, CTC=1953, Expense=26569, Incentive=22644, Status=Active
⚠️ Question: Is CTC actually ₹1,953 (seems very low) or ₹19,53,000? Need unit confirmation.
⚠️ Question: Does "Expense" mean bonus/incentive spent, or cost to company?
```

---

### Sheet 4: "Dmart BA-Merchandiser" (BA & Merchandiser Payroll by Chain)

| Finding | Severity | Issue | Impact |
|---------|----------|-------|--------|
| **EXCELLENT CHAIN MAPPING** | OK | Chain_Name field maps employees to actual chains: RELIANCE, H&G, POTHYS, GT, BKD, NESTO, Balaji Grand Bazar, etc. | Good — can link to Dim_Chain_Raw |
| **DIVISION FIELD** | MEDIUM | Division = "BA" only in sample rows (row 2-25) | Need to confirm if all rows are BA or if some are Merchandiser (column says "BA-Merchandiser" but data shows only BA) |
| **CHANNEL FIELD** | MEDIUM | Channel values: MT, GT, others? | MT = Mamaearth Trade? GT = GT Retail? Need mapping |
| **DESIGNATION CONSISTENCY** | LOW | All sampled rows show "BEAUTY ADVISOR" | Assumed; need to verify if Merchandiser designation also appears |
| **DOJ FIELD** | MEDIUM | Date of Joining in YYYY-MM-DD format (e.g., 13/03/2024) | OK, but some DOJ dates are March 2024 while data is Apr 2026 (2 year tenure) |
| **CTC LOGIC UNCLEAR** | MEDIUM | Same columns as Sheet 3 (CTC, Expense, Incentive, NET_PAY) | Same definition issue as Sheet 3 |
| **UNIT CONFIRMED** | OK | CTC, Expense, Incentive in actual ₹ | OK |
| **DATA COMPLETENESS** | OK | 1,473 rows, strong structure, chain mapping present | Data appears clean |

**Data Sample (Raw):**
```
Month=Apr, Name=YASMEEN, Zone=CENTRAL, Location=ALLAHABAD, Designation=BEAUTY_ADVISOR, Chain=RELIANCE, Channel=MT, CTC=21073, Expense=21073, Incentive=16810, Status=Active
⚠️ Question: Why is CTC = Expense in this row? Should Incentive be added?
```

---

### Sheet 5: "other employ" (Other Staff — Merchandisers, Promoters, Team Leaders)

| Finding | Severity | Issue | Impact |
|---------|----------|-------|--------|
| **DESIGNATION VARIETY** | MEDIUM | Designations: MERCHANDISER, PROMOTER, TEAM LEADER | These are different roles than BA/PSR — separate cost pool needed |
| **ZONE MAPPING INCONSISTENT** | MEDIUM | Zone values: North, South, East, West (no numbers like NORTH-1) | Mismatch with other sheets — need standardization |
| **NO CHAIN MAPPING** | HIGH | No chain/store field; only location names | Cannot allocate to chains without location master |
| **CTC LOGIC** | MEDIUM | Same issue as Sheets 3–4 | Need definition |
| **UNIT CONFIRMED** | OK | CTC, Expense, Incentive in actual ₹ | OK |
| **DATA COMPLETENESS** | OK | 562 rows, consistent structure | Data appears clean |

**Data Sample (Raw):**
```
Month=Apr, Name=MOHD ADIL, Zone=North, Location=LUCKNOW, Designation=MERCHANDISER, CTC=23901, Expense=23901, Incentive=19976, Status=Active
⚠️ Same CTC=Expense pattern as Sheet 4.
```

---

### Sheet 6: "visibility or Rental" (Allowance/Expense Detail by Employee)

| Finding | Severity | Issue | Impact |
|---------|----------|-------|--------|
| **HEADER MISMATCH** | MEDIUM | Row 1 = "Apr'26 Expense" but row 2 headers include DOJ/DOL fields (typically hire/leave dates) | Clarify: is this employee travel/allowance for Apr 2026 or payroll record? |
| **DATE CONFUSION** | HIGH | DOJ column shows Excel serial dates (45839 = ~Jul 2025, 45586 = ~Jun 2025, 45352 = May 2025?) but header says "Apr'26 Expense" | Dates don't align with expense month; unclear if this is allowance or new hire data |
| **DOL FIELD (Date of Leave?)** | MEDIUM | Some rows have DOL values (46130 for one Inactive employee) | If this is payroll, DOL might be Date of Leaving. Inactive employees in Apr 2026? |
| **ALLOWANCE BREAKDOWN** | OK | Columns: Total, DA (Dearness Allowance), TA (Travel Allowance), Hotel, Misc | OK — actual ₹ amounts for employee-level allowances |
| **UNIT CONFIRMED** | OK | Values in actual ₹ | OK |
| **SPARSE DATA** | MEDIUM | Only ~25 employees visible in Apr'26 spend (sheet has 92 rows, many empty cells) | Either few employees claimed allowance in Apr 2026 or data incomplete |

**Data Sample (Raw):**
```
Month="Apr'26", Name=BOGI SANDEEP, Designation=MERCHANDISER, Zone=South, DOJ=45839 (serial date), Status=Active, Total_Allowance=5200, DA=5200, TA=0, Hotel=0, Misc=0
⚠️ Question: Is DOJ a typo for DOE (Date of Expense)? Or is this tracking new hires?
⚠️ Question: If this is Apr 2026 allowance, why are DOJ dates from 2025?
```

---

### Sheet 7: "COGS" (Actual Visibility & Rental Spend by Store/Campaign)

| Finding | Severity | Issue | Impact |
|---------|----------|-------|--------|
| **UNIT CONFIRMED** | OK | Row 1 explicitly states "In Lakhs" | ✓ Data is ₹ Lakhs (multiply by 100,000 for rupees or ÷100 for Crores) |
| **EXCELLENT STORE MAPPING** | OK | Store names are actual retail outlets: TRENT Hypermarket, MORE Retail, Lulu, Spencer, V-Mart, Apollo, Guardian, Frankross, H&G | Can link to store master |
| **CAMPAIGN MAPPING** | MEDIUM | Program/campaign names provided: "Ladder Rack", "MBEC - AMJ plan", "Visibility+Rental", "Shelf in Shelf", etc. | Need to map to actual campaigns/schemes |
| **BRAND TRACKING** | OK | Brands: TDC, ME (Mamaearth?) | Need to confirm ME = Mamaearth |
| **MONTHLY BREAKDOWN** | OK | Months: April, May, June, plus Q1 total | Good for monthly allocation |
| **STORE-LEVEL AGGREGATION** | MEDIUM | Data is by store+campaign+brand (not by chain); e.g., Apollo has 5 rows (Shelf in Shelf City, Airport, FSU, Baby Parasites, Summer Shelf) | Need to aggregate to chain level for offtake model |
| **Q1 TOTALS** | MEDIUM | Q1 total provided but some rows sum correctly (6+6+6=18) while others don't (e.g., row 19: 0+missing+5=5, not 5 implied) | Data quality issue — verify totals before using |

**Data Sample (Raw):**
```
Store="TRENT Hypermarket", Campaign="Ladder Rack - MJJ plan", Brand="TDC", April=0, May=1, June=1, Q1=2 (Lakhs)
Store="MORE Retail", Campaign="MBEC - AMJ plan", Brand="TDC", April=6, May=6, June=6, Q1=18 (Lakhs)
Store="Lulu", Campaign="Visibility+Rental", Brand="ME", April=9.8, May=9.8, June=9.8, Q1=29.5 (Lakhs)
⚠️ Interpretation: OK to use directly as ₹ Lakhs (no unit conversion needed).
```

---

## 2. Proposed Data Model

### Master Tables (Dimension-like, no direct fact linkage)

#### Cost_Master (Cleaned & Standardized)
```
Cost_ID (PK)                 — Unique identifier (auto-generated)
Cost_Type                    — { 'COGS', 'BA_Salary', 'BA_Supervisor', 'Merchandiser', 'Promoter', 'Visibility_Rental', 'Other_Allowance' }
Sheet_Source                 — { 'claim (COGS)', 'BA Salary (Claims)', 'BA Supervisor', 'Dmart BA-Merchandiser', 'Other Employ', 'Visibility Rental', 'COGS (Store)' }
Cost_Description             — Free text (e.g., "COGS+SC Teams for Mamaearth at Dmart")
Cost_Unit                    — { '₹', '₹_Lakh', 'Factor_Unknown', 'Percentage_Unknown', 'Ratio_Unknown', 'Per_Unit_Unknown' }
Cost_Basis                   — { 'Monthly', 'Per_Employee', 'Per_Store', 'Per_Campaign', 'Quarterly' }
Data_Quality_Flag            — { 'Verified', 'Pending_Unit_Confirmation', 'Sparse_Data', 'Incomplete_Months' }
Finance_Validation_Status    — { 'Pending', 'Rejected', 'Approved_As_Is', 'Approved_With_Adjustments' }
Tax_Treatment                — { 'Excl_Tax', 'Incl_Tax', 'Unknown' }  [CRITICAL: Do NOT assume]
Notes                        — Free text for issues/clarifications
```

#### Employee_Master (Standardized from Sheets 3–6)
```
Employee_ID (PK)            — MASTER ID from payroll sheets (e.g., GS10127229)
Employee_Name               — Name (standardized for duplicates)
Zone_Standardized           — P6 zone (North-1, North-2, West-1, West-2, South-1, South-2, Central, East)
State                       — State (standardized)
Location_City               — City (standardized for duplicates)
Designation                 — { 'ISR', 'PSR', 'MIS-EXECUTIVE', 'BEAUTY_ADVISOR', 'MERCHANDISER', 'PROMOTER', 'TEAM_LEADER' }
Designation_Category        — { 'BA', 'Supervisor', 'Merchandiser', 'Support_Staff' }
Chain_Assignment            — Chain name (for sheets with chain mapping) OR NULL (for sheets without)
Date_of_Joining             — Date (YYYY-MM-DD format)
Date_of_Leaving             — Date OR NULL (if active)
Status_Current              — { 'Active', 'Inactive', 'On_Leave' }
CTC_Monthly                 — ₹ (actual rupees, needs confirmation if low values)
Primary_Sheet_Source        — { 'BA Supervisor', 'Dmart BA-Merchandiser', 'Other Employ' }
```

#### Store_Campaign_Master (From Sheet 7)
```
Store_Campaign_ID (PK)      — Unique (e.g., "TRENT_Hypermarket_Ladder_Rack_TDC")
Store_Name                  — Retail outlet name (TRENT, MORE Retail, Lulu, Apollo, etc.)
Campaign_Name               — Campaign/program (Ladder Rack, Shelf in Shelf, etc.)
Brand                       — { 'TDC', 'ME' (Mamaearth?), 'AQ', 'BB', 'DRS' }
Cost_Lakhs_April            — ₹ Lakhs (value from sheet)
Cost_Lakhs_May              — ₹ Lakhs (value from sheet)
Cost_Lakhs_June             — ₹ Lakhs (value from sheet)
Cost_Lakhs_Q1_Total         — ₹ Lakhs (Q1 = Apr+May+Jun)
Store_Category              — { 'Hypermarket', 'Multi-Retail', 'Pharmacy', 'Modern Trade', 'General Trade' }
Data_Quality_Flag           — { 'Verified', 'Sums_Correct', 'Sums_Incorrect', 'Missing_Values' }
```

### Fact Tables (Linked to Fact_Offtake_Safe)

#### Cost_Allocation_Monthly (Normalized for Fact_Offtake_Safe join)
```
Allocation_ID (PK)         — Unique
Month                       — From Dim_Month
Cost_Type                   — From Cost_Master
Cost_Subtotal               — ₹ (actual rupees, summed/allocated from raw sheet)
Allocation_Basis            — { 'Chain', 'Zone', 'Category', 'Employee_Count', 'Store_Count', 'Per_Unit_Sales', 'Flat' }
Allocation_Rule             — Free text (e.g., "Allocate by MRP sales proportion", "Equal per employee", "By store count")
Fact_Offtake_Link           — Link to Fact_Offtake_Safe by (Month, Chain?) [TBD based on allocation rule]
Provisional_Status          — ⚠️ "Pending Finance Validation" (ALL rows)
```

#### Employee_Cost_Monthly (For BA & Merchandise workforce)
```
Payroll_ID (PK)            — Unique (e.g., Employee_ID + Month)
Employee_ID (FK)           — Link to Employee_Master
Month                       — From Dim_Month
Cost_Type                   — { 'Salary', 'Incentive', 'Allowance' }
Cost_Amount                 — ₹ (actual rupees)
Cost_Component              — { 'Base_CTC', 'Bonus', 'Travel_Allowance', 'Dearness_Allowance', 'Hotel' }
Designation_Category        — From Employee_Master
Chain_Assignment            — Chain (if applicable) OR NULL
Zone                        — P6 zone
Provisional_Status          — ⚠️ "Pending Finance Validation"
```

---

## 3. Cost Allocation Logic by Sheet

### Sheet 1: "claim" (COGS+SC Teams Factors)

**⚠️ BLOCKER: Unit unknown — Cannot allocate without Finance confirmation**

| Component | Mapping | Allocation Rule | Status |
|-----------|---------|-----------------|--------|
| **Decimal Factors** | Brands (Mamaearth, TDC, AQ, BB, DRS) × Chains (Dmart, Reliance, Apollo, Others) | TBD: Apply as % reduction? Per-unit cost? Ratio? | 🔴 BLOCKED |
| **Month** | Excel serial dates 46113 (Apr-26), 46143 (May-26), etc. | Map to Dim_Month | ✓ OK |
| **Chain** | Dmart, Reliance, Apollo, Others | Join to Dim_Chain_Raw (handle "Others" separately) | ✓ OK (for structure; not yet in data pipeline) |
| **Brand** | Mamaearth, TDC, AQ, BB, DRS | Not in offtake fact table; create lookup? | ⚠️ Needs clarification |

**Provisional Measure (Safe to Build):**
```dax
[COGS_Factor_Raw_TBD] =
SELECTEDVALUE( 'Fact_COGS_Factors'[Factor_Value], BLANK() )
// Label: ⚠️ "Pending Unit Confirmation - Do NOT use for calculations"
```

---

### Sheet 2: "BA salary" (Claims/Expense Summary)

**⚠️ BLOCKER: Company-to-chain mapping unknown — Cannot allocate without business rules**

| Component | Mapping | Allocation Rule | Status |
|-----------|---------|-----------------|--------|
| **Companies** | Guardian Healthcare, Health & Glow, Metro Cash & Carry, Reliance, V-Mart, Walmart | Map to chains in Dim_Chain_Raw? Or are these vendors/suppliers? | 🔴 BLOCKED |
| **Expense Type** | NPI Listing, Off Invoice, Promotion, Rental, Visibility | Which are COGS? Direct costs? Overheads? Need Finance mapping | 🔴 BLOCKED |
| **Month** | Apr-26, May-26 (2 months only) | Map to Dim_Month | ✓ OK |
| **Amount** | Actual ₹ values | Sum by month + expense type? | ✓ OK (structure) |

**Provisional Measure (Safe to Build — Summary Only):**
```dax
[Total_Claims_By_Month_TBD] =
SUM( 'Fact_Claims_Summary'[Amount_Rupees] )
// Label: ⚠️ "Expense Claims Summary (Unallocated) - Pending Company/Expense Type Mapping"
// WARNING: Do NOT use in CM2 or profitability until Finance confirms allocation rules
```

---

### Sheet 3: "BA Supervisor" (Payroll — ISR/PSR)

**Allocation Rule: By employee count, allocated to Zone (not chain)**

| Component | Mapping | Allocation Rule | Status |
|-----------|---------|-----------------|--------|
| **Employee** | MASTER ID → Employee_Master | Employee count by zone, month, designation | ✓ OK |
| **Zone** | CENTRAL, NORTH-1, NORTH-2, WEST-1, WEST-2, SOUTH-1, SOUTH-2, EAST | P6 zone (verify 1:1 mapping) | ✓ OK |
| **CTC/Expense** | ₹ values; definition unclear (is CTC base salary or total?) | Sum by zone + month | ⚠️ Needs CTC definition |
| **Chain** | NO chain field; only location (LUCKNOW, PUNE, etc.) | Cannot allocate to chain without location→store→chain master | 🔴 NEEDS MASTER |
| **Month** | "Apr" (text); need to map to Dim_Month | Convert to date format | ✓ OK |

**Provisional Measures (Safe to Build — Zone-level only):**
```dax
[BA_Supervisor_Headcount_By_Zone_Month] =
COUNTROWS( 'Employee_Master' )
FILTER( [Designation_Category] = "Supervisor", [Primary_Sheet_Source] = "BA Supervisor" )
// Label: "BA Supervisor Headcount (Apr-Jun 2026)"

[BA_Supervisor_Cost_Total_By_Zone_Month] =
SUM( 'Employee_Cost_Monthly'[Cost_Amount] )
FILTER( [Designation_Category] = "Supervisor" )
// Label: ⚠️ "BA Supervisor Total Cost (Pending CTC Definition Validation)"
// WARNING: Do NOT allocate to chain until location→store→chain master available
```

---

### Sheet 4: "Dmart BA-Merchandiser" (Payroll — BA by Chain)

**Allocation Rule: Direct by Chain (best chain mapping in dataset)**

| Component | Mapping | Allocation Rule | Status |
|-----------|---------|-----------------|--------|
| **Employee** | MASTER ID → Employee_Master | Employee count by chain, month, designation | ✓ OK |
| **Chain_Name** | RELIANCE, H&G, POTHYS, GT, BKD, NESTO, Balaji Grand Bazar, etc. | Join to Dim_Chain_Raw (handle naming variants) | ✓ OK (requires chain master match) |
| **Zone** | P6 zones (same as Sheet 3) | Verify zone consistency with Sheet 3 | ✓ OK |
| **Designation** | BEAUTY_ADVISOR (sampled); possibly MERCHANDISER (not in sample) | Separate BA costs from Merchandiser (if both present) | ⚠️ Verify designation values |
| **CTC/Incentive** | ₹ values; definition unclear | Sum by chain + month | ⚠️ Needs CTC definition |
| **Month** | "Apr" (text) | Convert to date format | ✓ OK |

**Provisional Measures (Safe to Build — Chain-level):**
```dax
[BA_Store_Headcount_By_Chain_Month] =
COUNTROWS( 'Employee_Master' )
FILTER( [Designation] = "BEAUTY_ADVISOR", [Primary_Sheet_Source] = "Dmart BA-Merchandiser" )
// Label: "BA Headcount by Chain (Apr-Jun 2026)"

[BA_Store_Cost_By_Chain_Month] =
SUM( 'Employee_Cost_Monthly'[Cost_Amount] )
FILTER( [Designation] = "BEAUTY_ADVISOR" )
// Label: ⚠️ "BA Cost by Chain (Pending CTC Definition & Allocation Rule)"
// WARNING: Do NOT use in CM2 or profitability until Finance confirms exact allocation logic
```

---

### Sheet 5: "other employ" (Payroll — Merchandisers, Promoters, Team Leaders)

**Allocation Rule: By designation category + zone; cannot allocate to chain without location master**

| Component | Mapping | Allocation Rule | Status |
|-----------|---------|-----------------|--------|
| **Employee** | MASTER ID → Employee_Master | Employee count by designation, zone, month | ✓ OK |
| **Designation** | MERCHANDISER, PROMOTER, TEAM_LEADER | Separate cost pools by designation | ✓ OK |
| **Zone** | North, South, East, West (NOT P6 format; inconsistent with Sheets 3–4) | Standardize to P6 zones; may require mapping table | ⚠️ Needs standardization |
| **Location** | City names (LUCKNOW, HYDERABAD, etc.) | Cannot allocate to chain/store without location master | 🔴 NEEDS MASTER |
| **CTC/Expense** | ₹ values; definition unclear | Sum by zone + designation + month | ⚠️ Needs CTC definition |

**Provisional Measures (Safe to Build — Zone + Designation level):**
```dax
[Other_Staff_Headcount_By_Zone_Designation] =
COUNTROWS( 'Employee_Master' )
FILTER( [Designation_Category] = "Merchandiser" or "Support_Staff" )
// Label: "Other Staff Headcount by Zone & Designation"

[Other_Staff_Cost_By_Zone_Designation] =
SUM( 'Employee_Cost_Monthly'[Cost_Amount] )
FILTER( [Designation_Category] IN { "Merchandiser", "Support_Staff" } )
// Label: ⚠️ "Other Staff Cost by Zone & Designation (Pending Location→Chain Mapping)"
```

---

### Sheet 6: "visibility or Rental" (Allowance Detail)

**⚠️ BLOCKER: Date interpretation unclear; possibly Apr 2025 data, not Apr 2026**

| Component | Mapping | Allocation Rule | Status |
|-----------|---------|-----------------|--------|
| **Month** | "Apr'26" in header but DOJ dates from 2025 | Clarify: is this April 2026 expense or 2025 hire data? | 🔴 BLOCKED |
| **Employee** | Link to Employee_Master via MASTER ID | Per-employee allowance allocation | ✓ OK (structure) |
| **Allowance Type** | DA, TA, Hotel, Misc | Sum by type + month | ✓ OK (structure) |
| **Amount** | Actual ₹ values | Allocate to employee's assigned chain/zone | ⚠️ Depends on chain master |

**Provisional Measures (Safe to Build — Deferred until date clarity):**
```dax
[Employee_Allowance_Total_By_Month] =
SUM( 'Fact_Employee_Allowance'[Total_Amount_Rupees] )
// Label: ⚠️ "Employee Allowance Total (Date Range Pending Clarification)"
```

---

### Sheet 7: "COGS" (Store-level Visibility & Rental, in Lakhs)

**Allocation Rule: By store + campaign + brand; aggregate to chain for join to offtake**

| Component | Mapping | Allocation Rule | Status |
|-----------|---------|-----------------|--------|
| **Store** | TRENT, MORE Retail, Lulu, Spencer, V-Mart, Apollo, Guardian, Frankross, H&G | Join to store master, then aggregate to chain | ⚠️ Needs store→chain master |
| **Campaign** | Ladder Rack, MBEC, Shelf in Shelf, Visibility+Rental, etc. | Optional: categorize as "Visibility", "Rental", "Promotion" | ⚠️ Needs campaign categorization |
| **Brand** | TDC, ME (Mamaearth?) | Map to brand master | ⚠️ Needs confirmation |
| **Amount (Lakhs)** | Actual ₹ Lakhs | Convert to rupees (×100,000) or Crores (÷100) | ✓ OK |
| **Month** | April, May, June | Map to Dim_Month | ✓ OK |

**Provisional Measures (Safe to Build — Store-level; chain aggregation pending master):**
```dax
[Visibility_Rental_Cost_Lakhs_By_Month] =
SUM( 'Fact_Store_Campaign'[Cost_Lakhs] )
// Label: "Visibility & Rental Cost ₹ Lakhs (By Store/Campaign)"

[Visibility_Rental_Cost_Rupees] =
[Visibility_Rental_Cost_Lakhs_By_Month] * 100000
// Label: "Visibility & Rental Cost ₹ (Actual Rupees)"

[Visibility_Rental_Cost_Crore] =
[Visibility_Rental_Cost_Rupees] / 10000000
// Label: "Visibility & Rental Cost ₹ Crore"
```

---

## 4. Unmapped and Blocked Items

### CRITICAL BLOCKERS (Must resolve before CM2)

| Item | Issue | Data Source | Required From | Impact |
|------|-------|-------------|----------------|--------|
| **COGS Factor Units** | Are 0.1655 values %, ratios, per-unit costs, or something else? | Sheet 1 "claim" | Finance | Cannot build COGS measure without unit confirmation |
| **CM2 Formula (Exact)** | What is the exact CM2 = f(NSV, MRP, COGS, ...)? Which tax base (NSV excl. or MRP incl.)? | N/A — needs Finance definition | Finance | Cannot implement profitability without formula |
| **Tax-Basis in CM2** | Should CM2 use NSV (excl. tax) or MRP (incl. tax) as revenue base? How to handle tax components? | N/A — needs Finance clarification | Finance | Cannot allocate cost components correctly |
| **CTC Definition** | Is CTC base salary, gross salary, or total compensation? Why some values appear very low (e.g., ₹1,953)? | Sheets 3–6 (payroll) | Finance / HR | Cannot validate employee cost accuracy |
| **Company-to-Chain Mapping** | Are Guardian Healthcare, Health & Glow, Metro Cash & Carry companies, vendors, or something else? How do they map to chains? | Sheet 2 "BA salary" | Business / Commercial | Cannot allocate claims to chains |
| **Expense-Type Categorization** | Which claims (NPI, Off Invoice, Promotion, Rental, Visibility) are COGS, direct costs, or overheads? | Sheet 2 "BA salary" | Finance | Cannot allocate to correct GL accounts or CM2 components |

### HIGH-PRIORITY MAPPINGS (Needed for data integration)

| Item | Issue | Data Source | Required From | Impact |
|------|-------|-------------|----------------|--------|
| **Location → Store → Chain Master** | Sheets 3, 5, 6 have location names (LUCKNOW, PUNE, etc.) but no chain/store mapping | Sheets 3, 5, 6 | Operations / Store Master | Cannot allocate employee costs to chains |
| **Zone Standardization** | Sheet 5 uses North, South, East, West; Sheets 3–4 use North-1, North-2, etc.; need unified mapping | Sheets 3–6 | Operations / Zone Master | Cannot consolidate zone-level costs |
| **Store → Chain Master (Sheet 7)** | Sheet 7 has store names (TRENT, Lulu, Apollo) but not chain assignments; need mapping | Sheet 7 | Store Operations Master | Cannot aggregate visibility/rental to chain level for offtake join |
| **Brand Mapping** | TDC, AQ, BB, DRS, ME (Mamaearth?) — need to confirm brand IDs | Sheets 1, 7 | Product / Brand Master | Cannot link to offtake by brand dimension |
| **Designation-to-Role Mapping** | ISR, PSR, MIS-EXECUTIVE, BA, MERCHANDISER, PROMOTER, TEAM_LEADER — need business definitions | Sheets 3–6 | HR | Cannot categorize correctly for cost allocation |
| **Chain Name Normalization** | Dmart vs Dmart, Reliance vs Reliance Retail, POTHYS vs Pothys, etc. — handle variants | Sheets 1, 4, 7 | Store Master | Cannot join to Dim_Chain_Raw consistently |

### MEDIUM-PRIORITY CLARIFICATIONS

| Item | Issue | Status |
|------|-------|--------|
| **Sheet 2 Month Coverage** | Only Apr-26 and May-26 data; need full Apr'24–Jun'26 history | Sparse data; ask for archive |
| **Sheet 1 Duplicate Sections** | Two "COGS" sections (rows 2–16 and 18–48); are they different cost types or duplicates? | Clarify: different categories? |
| **Sheet 6 Date Interpretation** | DOJ dates from 2025 but header says "Apr'26 Expense" | Is this 2025 data mislabeled as 2026? Or are these hire dates? |
| **Sheet 4 Division Field** | All sampled rows = "BA"; do any rows contain "Merchandiser" in this sheet? | Verify dataset scope |
| **Sheet 7 Campaign Categorization** | Programs like "Ladder Rack", "Shelf in Shelf", "Visibility+Rental" — how to categorize for CM2? | Need business mapping |

---

## 5. Provisional Measures (Safe to Build — No CM2)

**⚠️ ALL measures below must be labeled: "Pending Finance Validation — For QC Only, Do NOT use in Profitability Reporting"**

### Employee Workforce Metrics (Safe)

```dax
// Sheet 3: BA Supervisors
[BA_Supervisor_Headcount_Apr_Jun] =
COUNTROWS( 'Employee_Master' )
FILTER( [Designation_Category] = "Supervisor", [Primary_Sheet_Source] = "BA Supervisor" )

[BA_Supervisor_Headcount_By_Zone] =
SUMMARIZE(
  'Employee_Master',
  'Employee_Master'[Zone_Standardized],
  "Headcount", COUNTROWS( 'Employee_Master' )
)

// Sheet 4: Store BAs
[BA_Store_Headcount_Apr_Jun] =
COUNTROWS( 'Employee_Master' )
FILTER( [Designation] = "BEAUTY_ADVISOR", [Primary_Sheet_Source] = "Dmart BA-Merchandiser" )

[BA_Store_Headcount_By_Chain] =
SUMMARIZE(
  'Employee_Master',
  'Employee_Master'[Chain_Assignment],
  "Headcount", COUNTROWS( 'Employee_Master' )
)

// Sheet 5: Other Staff
[Other_Staff_Headcount_Apr_Jun] =
COUNTROWS( 'Employee_Master' )
FILTER( [Designation_Category] IN { "Merchandiser", "Support_Staff" } )

[Other_Staff_Headcount_By_Designation] =
SUMMARIZE(
  'Employee_Master',
  'Employee_Master'[Designation],
  "Headcount", COUNTROWS( 'Employee_Master' )
)
```

### Cost Summary Metrics (Safe — no allocation logic assumed)

```dax
// Sheet 7: Visibility & Rental (store-level)
[Visibility_Rental_Cost_Lakhs] =
SUM( 'Fact_Store_Campaign'[Cost_Lakhs] )
// Label: "Visibility & Rental Cost ₹ Lakhs (Apr-Jun 2026, Store-Level)"

[Visibility_Rental_Cost_Crore] =
[Visibility_Rental_Cost_Lakhs] / 100
// Label: "Visibility & Rental Cost ₹ Crore"

// Sheet 2: Claims Summary (unallocated)
[Total_Claims_Apr_May] =
SUM( 'Fact_Claims_Summary'[Amount_Rupees] )
// Label: "Total Expense Claims (Apr-May 2026, Unallocated) — Pending Company Mapping"

[Total_Claims_By_Type] =
SUMMARIZE(
  'Fact_Claims_Summary',
  'Fact_Claims_Summary'[Expense_Type],
  "Total", SUM( 'Fact_Claims_Summary'[Amount_Rupees] )
)
// Label: "Expense Claims by Type (NPI, Off-Invoice, etc.) — Pending GL Mapping"
```

### BA Store Performance Measures (Provisional — No Profitability Assumed)

```dax
// SAFE: Ratio of BA headcount to MRP sales (indicator only, not profitability)
[BA_Store_Coverage_Ratio] =
DIVIDE(
  [BA_Store_Headcount_Apr_Jun],
  [MRP Sales Value Cr],
  BLANK()
)
// Label: ⚠️ "BA Coverage Ratio (BAs per ₹ Cr MRP) — Pending Finance Validation — Indicator Only, Do NOT use in profitability"

[Offtake_Per_BA_Store_Headcount] =
DIVIDE(
  [MRP Sales Value Cr],
  [BA_Store_Headcount_Apr_Jun],
  BLANK()
)
// Label: ⚠️ "Offtake per BA (₹ Cr per BA FTE) — Pending Finance Validation — For Workforce Planning Only"

[BA_Store_MRP_Contribution_Pct] =
DIVIDE(
  CALCULATE(
    [MRP Sales Value Cr],
    FILTER( 'Fact_Offtake_Safe', [BA_Available] = "Yes" )
  ),
  [MRP Sales Value Cr],
  BLANK()
) * 100
// Label: ⚠️ "MRP from BA-Available Stores (%) — Pending Finance Validation — Indicator Only"
```

### Cost-to-Sales Indicators (For QC Only — Do NOT use for CM2)

```dax
[Visibility_Rental_Cost_As_Pct_MRP] =
DIVIDE(
  [Visibility_Rental_Cost_Crore],
  [MRP Sales Value Cr],
  BLANK()
) * 100
// Label: ⚠️ "Visibility/Rental Cost as % of MRP (Apr-Jun 2026) — Pending Unit Confirmation & Allocation Rule — QC Metric Only"

[Total_Payroll_Cost_As_Pct_MRP] =
DIVIDE(
  SUM( 'Employee_Cost_Monthly'[Cost_Amount] ) / 10000000,  // Convert to Crore
  [MRP Sales Value Cr],
  BLANK()
) * 100
// Label: ⚠️ "Total Payroll Cost as % of MRP — Pending CTC Definition & Allocation Rule — QC Metric Only"
```

---

## 6. Questions Requiring Finance or HR Confirmation

### CRITICAL — Must answer before CM2 implementation

**Q1. COGS Factors (Sheet 1):**
- What do the decimal values (0.1655, 0.1693, 0.1746, etc.) represent?
  - Are they percentages (16.55% of NSV? Of MRP?)
  - Are they ratios or cost factors (apply multiplicatively)?
  - Are they per-unit costs (₹ per unit of Qty)?
  - Are they something else?
- Provide: Exact formula to convert a factor to CM2 component

**Q2. CM2 Formula & Tax Basis:**
- What is the exact Contribution Margin 2 (CM2) formula?
  - Is CM2 = NSV (excl. tax) - COGS - Direct Costs?
  - Or CM2 = MRP (incl. tax) - COGS - Tax - Direct Costs?
  - Or something else?
- Which cost sheets are included in each CM2 component?
  - COGS: From Sheet 1 factors (once unit confirmed)?
  - Direct Costs: From Sheets 3–4 (BA), Sheet 5 (Merchandisers), Sheet 7 (Visibility)?
- How are tax components (GST/VAT) handled in the formula?
  - Are cost inputs tax-inclusive or tax-exclusive?
  - Is tax a separate line item or embedded?

**Q3. CTC Definition (Sheets 3–6):**
- What do the "CTC", "Expense", "Incentive", "NET_PAY" columns represent?
  - Is CTC base salary, gross salary, or total cost to company?
  - Why do some rows show CTC = Expense (e.g., Sheet 4, row 2: CTC=21073, Expense=21073, Incentive=16810)?
  - Is NET_PAY = CTC - Deductions? Or CTC + Incentive - Deductions?
- Are the values annual, monthly, or hourly?
  - Example: Sheet 3, Row 2 shows CTC=1953 — is this ₹1,953/month or ₹19,53,000/month?

**Q4. Company & Expense Type Mapping (Sheet 2):**
- What are the 6 companies listed (Guardian Healthcare, Health & Glow, Metro Cash & Carry, Reliance, V-Mart, Walmart)?
  - Are they vendor companies, retail chains, or something else?
  - How do they map to the chains in Dim_Chain_Raw (Dmart, Reliance, Apollo, Vmm, Fsn, Walmart, Ratanadeep, etc.)?
- For each expense type (NPI Listing, Off Invoice, Promotion, Rental, Visibility):
  - Is this a COGS component, direct cost, or overhead?
  - Should it be included in CM2? If yes, which CM2 component?

**Q5. Sheet 6 Date Clarification (Visibility/Rental Allowance):**
- Is Sheet 6 "Apr'26 Expense" actual allowance paid in April 2026, or is it hire data from 2025?
  - Why do DOJ fields show serial dates from 2025 (45839 ≈ Jul 2025, 45586 ≈ Jun 2025)?
  - Should this data be treated as 2025 or 2026?

**Q6. Sheet 1 Duplicate Section (COGS):**
- Rows 2–16 show "Cogs+SC Teams" and rows 18–48 show "Cogs" — are these two different cost components or the same data?
  - If different: how should they be combined (sum, average, separate)?
  - If same: which section should we use?

### HIGH-PRIORITY — Needed for data integration

**Q7. Location → Chain Mapping (Sheets 3, 5, 6):**
- Provide a master table mapping:
  - Location name (city) → Store ID → Chain name
  - Example: LUCKNOW → [Store ID] → [Chain X]
- This is needed to allocate employee costs from Sheets 3, 5, 6 to chains for offtake join

**Q8. Store → Chain Master (Sheet 7):**
- Provide mapping: Store name → Chain
  - Example: TRENT Hypermarket → Trent? LULU → Lulu? RELIANCE → Reliance?
- Note: Some stores may belong to multiple chains; clarify allocation method

**Q9. Zone Standardization (Sheets 3–6):**
- Sheets 3–4 use P6 zones (North-1, North-2, West-1, West-2, Central, South-1, South-2, East)
- Sheet 5 uses generic zones (North, South, East, West)
- Provide mapping table: Generic Zone → P6 Zone

**Q10. Brand Master (Sheets 1, 7):**
- Provide list and definitions:
  - Mamaearth, TDC, AQ, BB, DRS, ME (Mamaearth?)
  - Which are actual brands vs. campaigns?

### MEDIUM-PRIORITY — For data quality

**Q11. Chain Name Variants (Sheet 4):**
- Confirm correct spelling/ID for chains in Sheet 4:
  - RELIANCE vs Reliance vs Reliance Retail
  - H&G vs H & Glow vs Health & Glow
  - POTHYS vs Pothys
  - Others?

**Q12. Sheet 2 Archive (Claims):**
- Provide full history of claims from Apr'24–Jun'26
- Currently only Apr-26 and May-26 visible

**Q13. Employee Status (Sheets 3–6):**
- Define "Inactive" status: On leave? Separated? Left company?
- Should Inactive employees' costs be included in Apr-Jun 2026 allocation?

**Q14. Campaign Categorization (Sheet 7):**
- How should programs (Ladder Rack, Shelf in Shelf, Visibility+Rental, MBEC, etc.) be categorized for CM2?
  - Are they "Brand Support"? "Trade Spend"? "Retail Activation"?

---

## Summary & Next Steps

### What's Ready to Implement (Safely)

✅ **Data Model:** Cost_Master, Employee_Master, Store_Campaign_Master, with provisional fact tables
✅ **Workforce Metrics:** Headcount by zone, chain, designation (no assumptions)
✅ **Cost Summary Metrics:** Total cost by type and month (raw data only, no allocation)
✅ **QC Indicators:** Ratios of cost-to-sales for monitoring (labeled as QC only)

### What's Blocked (Until Finance Confirms)

🔴 **COGS Allocation:** Factor units unknown
🔴 **CM2 Calculation:** Formula and tax-basis undefined
🔴 **Profitability Measures:** All blocked pending formula confirmation
🔴 **BA Profitability:** Blocked pending CTC definition and chain/store mapping
🔴 **Cost Allocation:** Cannot allocate employee costs to chains without location master

### Immediate Actions Required

1. **Finance:** Answer Q1–Q6 (COGS factors, CM2 formula, CTC definition, company mapping, date clarification, duplicate check)
2. **Operations/HR:** Answer Q7–Q9 (location → chain mapping, store master, zone standardization)
3. **Product/Brand:** Answer Q10 (brand master definitions)
4. **Data Team:** Provide missing masters; standardize zone and chain naming

### Timeline to Profitability Implementation

- **Week 1:** Receive answers to Q1–Q6 from Finance
- **Week 2:** Receive location/store/zone masters from Operations; validate data quality
- **Week 3:** Build provisional cost allocation logic; QA against business rules
- **Week 4:** Implement DAX measures for CM2, Margin %, BA Profitability
- **Week 5:** Validate against accounting records; remove "Pending Validation" label once approved

---

**STATUS:** ⚠️ All measures and allocations are PROVISIONAL and labeled "Pending Finance Validation". No CM2, Profitability, BA Withdrawal, or Store Closure decisions can be made until answers to Q1–Q14 are confirmed.

**Branch:** claude/safe-powerbi-dashboard-rulings (do not merge PR #14)

**Last Updated:** 2026-07-11
