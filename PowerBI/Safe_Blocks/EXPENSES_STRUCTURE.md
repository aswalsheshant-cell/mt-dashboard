# All_Expenses_together.xlsx — Cost Structure Data Analysis

## File Overview
- **Format:** Excel workbook with 7 cost-related sheets
- **Purpose:** Complete cost structure for CM2/profitability calculations
- **Status:** This is the critical input that was blocking profitability measures in v3.1

## Sheets Identified

### 1. COGS (Cost of Goods Sold)
- **Structure:** Monthly cost factors by chain and brand
- **Data:** 
  - Brands tracked: Mamaearth, TDC, AQ, BB, DRS
  - Chains: Dmart, Reliance, Apollo, Others
  - Format: Excel serial dates (46113 = Apr-26, etc.) + decimal cost factors
  - Example factors: 0.1655, 0.1654, 0.1793, 0.1749... (likely COGS % or ratios)
- **Rows:** 48 (includes headers and data)
- **Usage for CM2:** COGS values to subtract from NSV (excl. tax) or MRP (incl. tax)

### 2. Claim
- **Purpose:** Claims/reimbursement tracking
- **Structure:** TBD (need to parse)

### 3. BA Salary
- **Purpose:** Beauty Advisor salary costs
- **Structure:** TBD
- **Relevance:** Blocks BA profitability calculation (was pending BA Headcount & Cost)

### 4. BA Supervisor
- **Purpose:** BA Supervisor salary/cost allocation
- **Structure:** TBD
- **Relevance:** Components of BA cost structure

### 5. Dmart BA-Merchandiser
- **Purpose:** Dmart-specific BA and Merchandiser costs
- **Structure:** TBD
- **Relevance:** Chain-specific BA cost tracking

### 6. Other Employ (Other Employees)
- **Purpose:** Other staff costs (non-BA)
- **Structure:** TBD
- **Relevance:** Fixed/variable cost allocation

### 7. Visibility or Rental
- **Purpose:** Visibility/rental/activation spend
- **Structure:** TBD
- **Relevance:** Direct cost component for CM2

---

## Critical Information for CM2 Implementation

**What this file provides (blocking items from v3.1):**
1. ✓ **COGS Data** — by month, chain, brand (resolves COGS blocker)
2. ✓ **BA Cost Structure** — salary sheets (resolves BA cost blocker)
3. ✓ **Other Direct Costs** — visibility, rental, employee costs (resolves cost allocation blocker)
4. ? **Exact CM2 Formula** — NOT YET PROVIDED (still need this from Finance)
5. ? **Tax Handling Rules** — NOT YET PROVIDED (still need CM2 formula accounting for NSV excl. tax vs MRP incl. tax)

---

## Next Steps for Profitability Implementation

**To activate CM2/Margin%/Profitability measures:**

1. **Confirm CM2 Formula from Finance:**
   - Is CM2 calculated on NSV basis (excl. tax) or MRP basis (incl. tax)?
   - What is the exact formula? (e.g., NSV - COGS - Visibility - BA Cost - Allocation?)
   - How are tax components handled in the formula?
   - Which cost sheets are included/excluded from each component?

2. **Map Cost Data to Offtake Model:**
   - Match COGS by chain to Dim_Chain_Raw (handle chain name variants)
   - Match BA Salary by location/zone to Dim_Zone
   - Allocate "Other Employ" and "Visibility or Rental" across categories/chains
   - Determine monthly/quarterly/annual allocation basis

3. **Update Power BI Data Model:**
   - Create fact tables for COGS, BA Costs, Other Costs (linked by chain/zone/month)
   - Add relationships: Fact_Offtake_Safe ↔ Cost tables (many-to-one on Chain, Zone, Month)
   - Create calculated columns for per-unit costs

4. **Implement DAX Measures:**
   - [COGS] — total or per-unit COGS by filter context
   - [Direct Costs] — Visibility + BA + Other allocations
   - [Gross Profit] or [CM1] — NSV - COGS (if NSV-based) OR MRP - COGS - Tax (if MRP-based)
   - [CM2] — per exact formula confirmed by Finance
   - [Margin %] — CM2 ÷ NSV (or ÷ MRP)

5. **QC & Validation:**
   - Verify COGS totals align with accounting records
   - Validate BA headcount and salary amounts
   - Cross-check visibility/rental spend allocation
   - Confirm tax-basis treatment in CM2 calculation

---

## File Condition & Format Notes

**Current State:**
- Excel 2007+ format (.xlsx)
- 5,792 shared strings (large data volume)
- Multiple tabs with monthly cost data (Apr-Jun 2026 visible in COGS)
- Decimal cost factors (not yet converted to actual rupees)

**Data Quality Checks Needed:**
- [ ] Verify all costs are in consistent unit (₹, %, factors, rupees per unit?)
- [ ] Confirm date range matches offtake data (Apr'24–Jun'26)
- [ ] Validate chain name matching with Dim_Chain_Raw (handle variants)
- [ ] Cross-check BA salary total against HR records
- [ ] Reconcile visibility/rental spend with commercial records

