# Power BI Data Model — Star Schema Diagram

**Branch:** claude/safe-powerbi-dashboard-rulings  
**Status:** v1 — Production-ready schema  
**Generated:** 2026-07-11

---

## Star Schema Overview

```
                            Date_Table
                                 │
                                 │ (Date relationship)
                                 │
                    ┌────────────┴────────────┐
                    │                         │
              Dim_Month                 Fact_Offtake_Safe
              (27 rows)                 (4.21M rows)
                    │                 /      │      \      \
                    └────────────────/       │       \      \
                                    │        │        │       │
                    ┌───────────────┤        │        │       │
                    │               │        │        │       │
              Dim_Chain_Raw    Dim_Zone   Dim_      (BA_Available,
              (34 chains)     (37 zones) Category   Is_Negative,
                                         (50-150)   Is_June26)


                        Expense_Assumptions_Input
                        (32 columns, refreshable)
                               │
                               │ (SUMX relationships in measures)
                               │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
         Cost_Master      BA_Master         Store_Master
         (10 cost        (BA employees)    (store codes)
          types)              │                 │
                              │                 │
                          (placeholder,     (pending from
                           HR data)         Operations)
```

---

## Fact Table: Fact_Offtake_Safe

**Purpose:** Core sales fact table (4.21M rows, Apr'24–Jun'26)

**Grain:** (Month, Chain, Zone, Category, Format, Brand, SKU) — one row per article-store-month

**Columns (18 total):**

| Column | Data Type | Purpose | Sample |
|--------|-----------|---------|--------|
| FY | Text | Fiscal year (Apr-Mar) | FY25, FY26 |
| Month | Text | Month code (Apr-24, May-24, ..., Jun-26) | Apr-24 |
| Month_Num | Number | Month number in FY | 1 (Apr) – 12 (Mar) |
| Month_Label | Text | Display month | "Apr-24", "May-24" |
| Chain_Name | Text | Retail chain (raw names) | Reliance, Walmart, Amazon |
| Zone | Text | Zone (P6 canonical) | NORTH-1, SOUTH-2, WEST-1 |
| Category | Text | Product category | Facewash, Shampoo, Serum |
| Format | Text | Packaging format | 50ml, 100ml, 500ml |
| Source_NSV_Lacs | Number | NSV in Lakhs (EXCLUDING tax) | 1500.50 |
| MRP_Sales_Value | Number | MRP in rupees (INCLUDING tax) | 150050000 |
| Sales_Qty | Number | Units sold | 50000 |
| BA_Available | Text | Brand Ambassador flag | "Yes" or "No" |
| Is_Negative_Return | Logical | Returns/credit note flag (MRP) | TRUE / FALSE |
| Is_Negative_NSV | Logical | Returns/credit note flag (NSV) | TRUE / FALSE |
| Is_June26_Partial | Logical | June'26 partial data flag | TRUE / FALSE |
| NSV_Cr | Number | NSV in Crores (Source_NSV_Lacs ÷ 100) | 15.00 (calculated) |
| NSV_Actual_Value | Number | NSV in rupees (Source_NSV_Lacs × 100,000) | 150050000 (calculated) |
| MRP_Sales_Value_Cr | Number | MRP in Crores (MRP ÷ 10,000,000) | 15.00 (calculated) |

**Key Flags:**
- `BA_Available`: Filter for BA analysis (BA vs Non-BA)
- `Is_June26_Partial`: 78,111 rows flagged (16 chains only)
- `Is_Negative_Return`: 12,705 rows flagged (valid returns)

---

## Dimension Tables

### Dim_Month (27 rows)

**Purpose:** Time dimension with Indian FY logic (Apr-Mar)

| Column | Data Type | Purpose |
|--------|-----------|---------|
| Date | Date | First day of month (2024-04-01, ..., 2026-06-01) |
| Month_Label | Text | Display format ("Apr-24", "May-24", ..., "Jun-26") |
| Month_Num | Number | 1 (Apr) – 12 (Mar) |
| Quarter | Text | "Q1", "Q2", "Q3", "Q4" |
| FY | Text | Fiscal year ("FY25", "FY26") |
| Month_Sort | Number | Sort order (1–27) |
| Is_June26_Partial | Logical | TRUE for Jun-26 only |
| Is_Partial | Logical | TRUE for Jun-26 only |

**Relationship:** Fact_Offtake_Safe[Month] ←→ Dim_Month[Month_Label]

---

### Dim_Chain_Raw (34 rows)

**Purpose:** Chain dimension (raw names, variants preserved)

| Column | Data Type | Purpose |
|--------|-----------|---------|
| Chain_Name | Text | Retail chain name (raw, includes variants) |
| Chain_Name_Canonical | Text | Standardized name (for future consolidation) |
| Chain_Type | Text | Type ("Modern Trade", "Pharmacy", "E-commerce") |
| Region | Text | Region served |

**Examples:** Reliance, Walmart, Amazon, Apollo Pharmacy, More, Lulu, Metro

**Relationship:** Fact_Offtake_Safe[Chain_Name] ←→ Dim_Chain_Raw[Chain_Name]

**Note:** Chain variants (Vmm/VMM, Fsn/FSN, Walmart Cnc/CNC) preserved as separate rows until canonicalization approved.

---

### Dim_Zone (37 rows)

**Purpose:** Zone dimension (P6 canonical geography)

| Column | Data Type | Purpose |
|--------|-----------|---------|
| Zone_Name | Text | Zone identifier (P6 format) |
| Zone_Code | Text | Code (e.g., "W1" for WEST-1) |
| Region | Text | Super-region (North, South, East, West) |
| Super_Region | Text | Broader grouping |

**Examples:** NORTH-1, NORTH-2, SOUTH-1, SOUTH-2, EAST-1, WEST-1, WEST-2

**Relationship:** Fact_Offtake_Safe[Zone] ←→ Dim_Zone[Zone_Name]

---

### Dim_Category (50–150 rows)

**Purpose:** Product category dimension

| Column | Data Type | Purpose |
|--------|-----------|---------|
| Category | Text | Category name |
| Sub_Category | Text | Sub-category |
| Brand | Text | Brand name |
| Format | Text | Packaging format |

**Examples:** Facewash, Shampoo, Body Lotion, Serum, Sun Care, Deodorant, etc.

**Relationship:** Fact_Offtake_Safe[Category] ←→ Dim_Category[Category]

---

### Date_Table (730+ rows)

**Purpose:** Calendar table for time-based filtering (optional, enhances slicing)

| Column | Data Type | Purpose |
|--------|-----------|---------|
| Date | Date | Calendar date (2024-04-01 to 2026-06-30) |
| Year | Number | Calendar year |
| Month | Number | Month number (1–12) |
| Day | Number | Day of month |
| Quarter | Text | "Q1", "Q2", "Q3", "Q4" |
| Month_Name | Text | Month name ("April", "May", ...) |
| Year_Month | Text | "2024-04", "2024-05", ... |
| FY | Text | Fiscal year ("FY25", "FY26") |

**Relationship:** Date_Table[Date] ←→ Dim_Month[Date] (optional, enables date slicing)

---

## Master Tables (Dimension-like, for reference)

### Store_Master (Placeholder — pending Operations data)

**Purpose:** Map store_code → chain → zone → location (for drill-down)

| Column | Data Type | Status | Notes |
|--------|-----------|--------|-------|
| Store_Code | Text | **Pending** | Unique identifier (REL-001, WAL-042, etc.) |
| Store_Name | Text | **Pending** | Display name |
| Chain | Text | **Pending** | Chain assignment |
| Zone | Text | **Pending** | Zone (P6 canonical) |
| Region | Text | **Pending** | Region (North, South, East, West) |
| BA_Deployment_Date | Date | **Pending** | When BA was deployed at store |
| BA_Status | Text | **Pending** | "BA" or "Non-BA" |
| City | Text | **Pending** | City (optional, for state mapping) |
| State | Text | **Pending** | State (optional, for geo-analysis) |

**Future Relationship:** Expense_Assumptions_Input[Store_Code] ←→ Store_Master[Store_Code]

---

### BA_Master (Placeholder — pending HR data)

**Purpose:** Brand Ambassador employee master (for cost allocation)

| Column | Data Type | Status | Notes |
|--------|-----------|--------|-------|
| BA_ID | Text | **Pending** | Unique BA identifier |
| BA_Name | Text | **Pending** | Full name |
| Chain | Text | **Pending** | Assignment chain |
| Zone | Text | **Pending** | Assignment zone |
| Monthly_CTC | Number | **Pending** | Monthly salary (₹) |
| Deployment_Date | Date | **Pending** | When deployed |
| Separation_Date | Date | **Pending** | When left (if applicable) |
| Status | Text | **Pending** | "Active", "Inactive", "Separated" |

**Future Relationship:** Expense_Assumptions_Input → BA_Master (for headcount-based allocation)

---

### Cost_Master (Reference dimension)

**Purpose:** Cost type catalog + allocation rules

| Column | Data Type | Content |
|--------|-----------|---------|
| Cost_Type | Text | COGS, BA_SALARY, BA_SUPERVISOR, BA_MERCHANDISER, OTHER_EMPLOY, NPI_LISTING, TOT, PROMOTIONAL, VISIBILITY, RENTAL, CLAIMS |
| Cost_Description | Text | Human-readable description |
| Cost_Category | Text | "Fixed" or "Variable" |
| Default_Allocation | Text | "Direct", "By_Headcount", "By_MRP_Share", "By_Store_Count", "Equal_Split" |
| Tax_Basis | Text | "Excl_Tax", "Incl_Tax", "Unknown" |
| Validation_Status | Text | "Confirmed", "Awaiting", "Pending", "Rejected" |

**Purpose:** Reference only (not joined in measures, used for documentation)

---

## Data Flow (Input Table)

### Expense_Assumptions_Input (Excel-based, refreshable)

**Purpose:** Centralized, auditable expense assumptions (Finance-editable)

**32 Columns:**
- Dimensions: Month, Chain, Store_Code, Store_Name, Brand
- Cost values: BA_Salary, Supervisor_Cost, Visibility, Rental, NPI_Listing, TOT, Promo, COGS, Claims, Other
- Metadata: Tax_Basis, Allocation_Method, Data_Status, Missing_Cost_Flag, Provisional_Cost_Flag
- Audit trail: Last_Updated_Date, Updated_By, Source_File, Remarks

**Relationship:** Referenced in DAX measures via SUMX (not a joined relationship)

**Refresh:** Via Power Query external connection to Excel file

---

## Relationship Diagram (Text Format)

```
┌─────────────────────────────────────────────────────────────────┐
│                        STAR SCHEMA                               │
│                                                                   │
│                         Dim_Month (27)                           │
│                              │                                   │
│                              │ (Date)                            │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐              │
│         │                    │                    │              │
│    Dim_Chain_Raw        Fact_Offtake_Safe     Dim_Zone          │
│    (34 chains)          (4.21M rows)          (37 zones)        │
│         │                    │                    │              │
│         └────────────────────┼────────────────────┘              │
│                              │                                   │
│                         Dim_Category                             │
│                         (50-150 categories)                      │
│                                                                   │
│  REFERENCE (No direct joins):                                   │
│  ├─ Expense_Assumptions_Input (32 columns, Excel-based)         │
│  ├─ Store_Master (pending Operations)                           │
│  ├─ BA_Master (pending HR)                                      │
│  └─ Cost_Master (reference only)                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Properties

| Property | Value | Notes |
|----------|-------|-------|
| **Fact Table** | Fact_Offtake_Safe | 4.21M rows, 18 columns (incl. calculated) |
| **Dimensions** | 4 (Month, Chain, Zone, Category) | Star schema with single fact table |
| **Grain** | (Month, Chain, Zone, Category, Format, Brand) | Article-store-month level |
| **Time Coverage** | Apr'24–Jun'26 (27 months) | Including FY25, FY26 |
| **External Input** | Expense_Assumptions_Input | Excel-based, 32 columns, refreshable |
| **Relationships** | 4 (all from fact → dimensions) | No many-to-many |
| **Calculated Columns** | 3 in Fact table | NSV_Cr, NSV_Actual_Value, MRP_Sales_Value_Cr |
| **Measures** | 84 (organized in 15 sections) | Sales, Growth, Contribution, Expenses, Profitability (provisional), ROI, QC flags |
| **Flags** | 3 key flags | BA_Available, Is_June26_Partial, Is_Negative_Return/NSV |

---

## Build Checklist

**In Power BI Desktop:**

- [ ] Import Fact_Offtake_Safe
- [ ] Import Dim_Month, Dim_Chain_Raw, Dim_Zone, Dim_Category
- [ ] Create Date_Table (if needed for slicing)
- [ ] Load Expense_Assumptions_Input via Power Query (external Excel)
- [ ] Create relationships:
  - [ ] Fact[Month] ←→ Dim_Month[Month_Label]
  - [ ] Fact[Chain_Name] ←→ Dim_Chain_Raw[Chain_Name]
  - [ ] Fact[Zone] ←→ Dim_Zone[Zone_Name]
  - [ ] Fact[Category] ←→ Dim_Category[Category]
- [ ] Verify data model (no red errors)
- [ ] Create all 84 DAX measures
- [ ] Test refresh: Update Expense_Assumptions_Input.xlsx → Refresh → Verify measures update
- [ ] Build 10 report pages (see PowerBI_10Page_DetailedSpec.md)

---

## Notes

**Tax-Basis Awareness:**
- NSV (Lakhs, EXCLUDING tax) → shown in Crores (÷100) or rupees (×100,000)
- MRP (rupees, INCLUDING tax) → shown in Crores (÷10,000,000)
- Never mix directly in calculations without tax context

**Data Quality:**
- June'26 partial: 78,111 rows from 16 chains (flagged)
- Negative values: 12,705 rows (returns/credit notes, flagged)
- More Retail duplicates: 13,661 rows (reported, retained per business approval)

**External Dependencies (Pending):**
- Store_Master (operations, store_code → chain → zone)
- BA_Master (HR, employee details)
- Store-to-chain mapping (for COGS allocation)
- BA deployment dates (for Pre-BA vs Post-BA analysis)

---

**Status:** v1 — Production-ready schema  
**Branch:** claude/safe-powerbi-dashboard-rulings  
**Next:** Build 10 pages using this schema (see PowerBI_10Page_DetailedSpec.md)

