# Power BI Model Specification — Safe Offtake Blocks

**Branch:** claude/safe-powerbi-blocks  
**Generated:** 2026-07-11  
**Status:** Draft (ready for implementation in Power BI Desktop)

---

## 1. Fact Table: Fact_Offtake_Safe

**Purpose:** Core fact table containing all transactional offtake data (MRP basis, June'26 partial, no NSV scaling)

**Source:** Power Query query `Offtake_Safe` (loads monthly CSV files)

**Record Count:** 4,211,571 rows (Apr'24–Jun'26, 582 files, 27 months)

**Grain:** One row per transaction (Site × Chain × Category × Month)

### Columns

| Column Name | Data Type | Format | Purpose | Notes |
|---|---|---|---|---|
| Site_Code | Text | - | Store identifier (raw, cleaned) | Preserved from source |
| Site_Name | Text | - | Store name (raw, cleaned) | Not canonicalized yet |
| Chain_Name | Text | - | Chain identifier (RAW, NOT CANONICALIZED) | Preserve variants (Vmm/VMM, etc.); pending decision |
| Zone | Text | - | Geographic zone (P6 canonicalized) | Proper case; variants normalized |
| Category | Text | - | Product category | Cleaned, trimmed |
| PPT_Category | Text | - | Planning / PowerPoint category | Cleaned, trimmed |
| Format | Text | - | Store format (e.g., standalone, mall, kiosk) | Cleaned, trimmed |
| Classification | Text | - | Store classification | Cleaned, trimmed |
| Month | Text | - | Month label (e.g., "Apr-24") | Format: Mon-YY |
| FY | Text | - | Financial year (e.g., "FY26") | Calculated from Month |
| Month_Num | Number | - | Month number (1–12) | Extracted from Month label |
| Month_Sort | Number | - | Month sort order within FY (1–12) | 1=Apr, 2=May, ..., 12=Mar; for ordering |
| Calendar_Year | Number | - | Calendar year (2024, 2025, 2026) | Extracted from Month label |
| Is_Month_Partial | Boolean | Yes/No | TRUE if this month is incomplete | Currently: June'26 = TRUE; others = FALSE |
| Is_June26_Partial | Boolean | Yes/No | TRUE if this row is from June'26 | Specifically flags June'26 partial data |
| Sales_Qty | Number | Standard | Sales quantity (units) | Verified basis |
| MRP_Sales_Value | Number | Currency (₹) | MRP Sales Value (rupees) | **SAFE VALUE BASIS (verified)** |
| Safe_Value_Basis | Number | Currency (₹) | Safe value for reports (= MRP_Sales_Value) | Alias for clarity; always = MRP_Sales_Value |
| Is_Safe_For_Reporting | Boolean | Yes/No | TRUE = can be used in reports | All rows = TRUE for MRP-basis reporting |
| Is_Negative_Return | Boolean | Yes/No | TRUE if sales value is negative | Valid returns/credit notes (12,705 rows) |

### Relationships

- **Fact_Offtake_Safe → Dim_Month** (via `Month_Sort`, `FY`)  
  Cardinality: Many-to-One  
  Cross-filter: Both directions

- **Fact_Offtake_Safe → Dim_Chain_Raw** (via `Chain_Name`)  
  Cardinality: Many-to-One  
  Cross-filter: Both directions

- **Fact_Offtake_Safe → Dim_Zone** (via `Zone`)  
  Cardinality: Many-to-One  
  Cross-filter: Both directions

- **Fact_Offtake_Safe → Dim_Category** (via `Category`)  
  Cardinality: Many-to-One  
  Cross-filter: Both directions

---

## 2. Dimension: Dim_Month

**Purpose:** Time dimension for month-level analysis

**Source:** Derived from Fact_Offtake_Safe; one row per month

**Record Count:** 27 rows (Apr'24–Jun'26)

### Columns

| Column Name | Data Type | Format | Purpose |
|---|---|---|---|
| Month_Sort | Number | - | Sort key (1–12) |
| Month | Text | - | Month label (e.g., "Apr-24") |
| FY | Text | - | Financial year (e.g., "FY26") |
| Calendar_Year | Number | - | Calendar year (2024, 2025, 2026) |
| Month_Num | Number | - | Month number (1–12) |
| Date | Date | - | First day of month (e.g., 2024-04-01) [FOR PREVIOUSMONTH() FUNCTION] |
| Is_Partial | Boolean | Yes/No | TRUE if month is incomplete (currently June'26) |
| Fiscal_Quarter | Text | - | Fiscal quarter (Q1–Q4) + FY (e.g., "Q1-26") |

### Relationships

- **Dim_Month ← Fact_Offtake_Safe** (Many-to-One, as above)

---

## 3. Dimension: Dim_Chain_Raw

**Purpose:** Chain (retail chain) dimension with raw names (awaiting canonicalization)

**Source:** DISTINCTCOUNT of Fact_Offtake_Safe[Chain_Name]

**Record Count:** 34 rows

**Note:** Chains are NOT canonicalized yet. Variants (Vmm/VMM, Fsn/FSN, etc.) appear as separate entries. This is intentional — pending business canonicalization decision.

### Columns

| Column Name | Data Type | Format | Purpose |
|---|---|---|---|
| Chain_Name | Text | - | Raw chain name (from source, cleaned) |
| Row_Count | Number | - | Total rows for this chain (metadata) |
| MRP_Total | Number | Currency (₹) | Total MRP for this chain (metadata) |
| Chain_Type_Flag | Text | - | [FUTURE] Will be "Chain", "BA Channel", "Store Type", or "Review" once decided |
| Note | Text | - | [FUTURE] Notes on issues (e.g., "Variant: also spelled Vmm") |

### Relationships

- **Dim_Chain_Raw ← Fact_Offtake_Safe** (Many-to-One, as above)

---

## 4. Dimension: Dim_Zone

**Purpose:** Geographic zone dimension (P6 canonicalized)

**Source:** DISTINCTCOUNT of Fact_Offtake_Safe[Zone]

**Record Count:** 37 rows (includes variants that are properly cased)

### Columns

| Column Name | Data Type | Format | Purpose |
|---|---|---|---|
| Zone | Text | - | Zone name (P6 canonicalized) |
| Row_Count | Number | - | Total rows for this zone (metadata) |
| MRP_Total | Number | Currency (₹) | Total MRP for this zone (metadata) |

### Relationships

- **Dim_Zone ← Fact_Offtake_Safe** (Many-to-One, as above)

---

## 5. Dimension: Dim_Category

**Purpose:** Product category dimension

**Source:** DISTINCTCOUNT of Fact_Offtake_Safe[Category]

**Record Count:** TBD (typically 50–150 categories in beauty/personal care)

### Columns

| Column Name | Data Type | Format | Purpose |
|---|---|---|---|
| Category | Text | - | Category name |
| Row_Count | Number | - | Total rows for this category (metadata) |
| MRP_Total | Number | Currency (₹) | Total MRP for this category (metadata) |

### Relationships

- **Dim_Category ← Fact_Offtake_Safe** (Many-to-One, as above)

---

## 6. QC Table: QC_Monthly_Reconciliation

**Purpose:** QC & validation table; monthly aggregates (row count, MRP, Qty, negative-value rows)

**Source:** Power Query query `QC_Monthly_Reconciliation`

**Record Count:** 27 rows (one per month)

### Columns

| Column Name | Data Type | Purpose |
|---|---|---|
| Month | Text | Month label (e.g., "Apr-24") |
| FY | Text | Financial year |
| Is_Month_Partial | Boolean | TRUE if month is incomplete |
| Row_Count | Number | Total rows in this month |
| MRP_Sales_Value | Number | Total MRP for this month |
| Sales_Qty | Number | Total quantity for this month |
| Negative_Value_Row_Count | Number | Count of return/credit-note rows (NSV < 0) |

### Relationships

None (reference table; not linked to fact table)

---

## 7. QC Table: QC_Duplicate_Report

**Purpose:** QC table; identifies exact-duplicate rows in More Retail chain

**Source:** Power Query query `QC_Duplicate_Report`

**Record Count:** TBD (dozens of duplicate patterns)

### Columns

| Column Name | Data Type | Purpose |
|---|---|---|
| Row_Hash | Text | Hash of Site/Chain/Category/Month/MRP (for duplicate detection) |
| Count | Number | Number of times this exact row appears |
| MRP_Total | Number | Total MRP for all occurrences of this duplicate |
| Sample_Month | Text | Example month where this duplicate appears |

### Relationships

None (reference table)

---

## 8. QC Table: QC_Chain_Variant_Check

**Purpose:** QC table; lists all distinct chain names and their coverage

**Source:** Power Query query `QC_Chain_Variant_Check`

**Record Count:** 34 rows

### Columns

| Column Name | Data Type | Purpose |
|---|---|---|
| Chain_Name | Text | Raw chain name (as it appears in source) |
| Row_Count | Number | Total rows for this chain |
| MRP_Total | Number | Total MRP for this chain |

### Relationships

None (reference table)

---

## 9. QC Table: QC_Blocked_Measures

**Purpose:** QC table; documents measures that are blocked and awaiting business decisions

**Source:** Power Query query `QC_Blocked_Measures` (static list)

**Record Count:** 11 rows

### Columns

| Column Name | Data Type | Purpose |
|---|---|---|
| Seq | Number | Sequence |
| Measure | Text | Name of blocked measure |
| Reason | Text | Why it is blocked |

### Relationships

None (reference table)

---

## 10. QC Table: QC_Pending_Decisions

**Purpose:** QC table; documents 6 blocking business decisions

**Source:** Power Query query `QC_Pending_Decisions` (static list)

**Record Count:** 6 rows

### Columns

| Column Name | Data Type | Purpose |
|---|---|---|
| Seq | Number | Sequence (1–6) |
| Decision | Text | Name of decision (e.g., "NSV Unit Validation") |
| Action | Text | Action required |
| Impact | Text | Impact if not decided |
| Timeline | Text | Estimated timeline |

### Relationships

None (reference table)

---

## Model Diagram (Conceptual)

```
Fact_Offtake_Safe (4.21M rows)
├─ PK: [Month_Sort, FY, Chain_Name, Zone, Category, Site_Code, ...] [implied]
├─ FK → Dim_Month (via Month_Sort, FY)
├─ FK → Dim_Chain_Raw (via Chain_Name)
├─ FK → Dim_Zone (via Zone)
└─ FK → Dim_Category (via Category)

Dim_Month (27 rows)
├─ PK: [Month_Sort, FY]
└─ Date (for PREVIOUSMONTH calculations)

Dim_Chain_Raw (34 rows)
├─ PK: [Chain_Name]
└─ Metadata: Row_Count, MRP_Total

Dim_Zone (37 rows)
├─ PK: [Zone]
└─ Metadata: Row_Count, MRP_Total

Dim_Category (50–150 rows)
├─ PK: [Category]
└─ Metadata: Row_Count, MRP_Total

QC_Monthly_Reconciliation (27 rows) [reference]
├─ Month, FY, Is_Month_Partial
├─ Row_Count, MRP_Sales_Value, Sales_Qty, Negative_Value_Row_Count
└─ No relationships

QC_Duplicate_Report (N rows) [reference]
├─ Row_Hash, Count, MRP_Total, Sample_Month
└─ No relationships

QC_Chain_Variant_Check (34 rows) [reference]
├─ Chain_Name, Row_Count, MRP_Total
└─ No relationships

QC_Blocked_Measures (11 rows) [reference]
├─ Seq, Measure, Reason
└─ No relationships

QC_Pending_Decisions (6 rows) [reference]
├─ Seq, Decision, Action, Impact, Timeline
└─ No relationships
```

---

## Notes on Design

### Safe Measures Only
- All DAX measures are MRP-basis only
- NSV is NOT calculated or exposed in any measure
- All profitability, state-level, and BA measures are blocked and NOT implemented

### June'26 Partial Flagging
- Dim_Month[Is_Partial] = TRUE for June'26
- Fact_Offtake_Safe[Is_June26_Partial] = TRUE for June'26 rows
- Watermarks on every report page alert users to partial data

### Preserved Raw Data
- Chain_Name is kept RAW (not canonicalized)
- Site_Code and Site_Name are preserved as-is
- No deduplication applied to More Retail
- Negative-value rows (returns) are preserved and flagged, not removed

### Future Extensions (After Business Decisions)
1. Add Dim_Chain_Canonical (once business approves canonicalization)
2. Add Dim_State_Canonical (once City-State mapping approved)
3. Add Dim_BA_Store (once Brand Counter classified and BA Headcount provided)
4. Implement NSV measures (once finance confirms unit)
5. Implement P&L measures (once NSV unit confirmed + margin assumptions approved)
6. Implement de-duped More Retail totals (once duplication decision finalized)

---

## Implementation Checklist

- [ ] Create Fact_Offtake_Safe table from Power Query
- [ ] Create Dim_Month dimension
- [ ] Create Dim_Chain_Raw dimension
- [ ] Create Dim_Zone dimension
- [ ] Create Dim_Category dimension
- [ ] Create QC_Monthly_Reconciliation reference table
- [ ] Create QC_Duplicate_Report reference table
- [ ] Create QC_Chain_Variant_Check reference table
- [ ] Create QC_Blocked_Measures reference table
- [ ] Create QC_Pending_Decisions reference table
- [ ] Define relationships (see diagram above)
- [ ] Create all DAX measures (copy from DAX_Safe_Measures.dax)
- [ ] Verify no NSV measures are active
- [ ] Verify no State dimension exists
- [ ] Verify no BA profitability measures exist
- [ ] Add June'26 Partial flag to every report page
- [ ] Test all safe measures on sample visuals

---

**Status:** Ready for implementation in Power BI Desktop.

