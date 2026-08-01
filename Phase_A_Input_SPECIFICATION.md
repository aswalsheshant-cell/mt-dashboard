# Phase A Input Folder Specification

**Date**: 2026-08-01  
**Status**: Ready for data preparation  
**Location**: `Phase_A_Input/` directory (git-ignored, local only)

---

## Folder Structure

```
Phase_A_Input/
├── primary_history.csv          Historical primary sales data (Apr 2025–Jun 2026)
├── offtake_history.csv           Historical retail offtake (Apr 2025–Jun 2026)
├── fact_margin.csv               Margin, pricing, GST, CM2 by article/chain/month
├── article_master.csv            Article (SKU) dimension table
├── chain_master.csv              Chain and geographic dimensions
├── warehouse_mapping.csv         Chain-to-warehouse allocation logic
├── monthly_targets.csv           Business targets/budget by chain/brand/month
├── business_events.csv           Planned promotions, new listings, festivals
└── assumptions_register.xlsx     Business assumption decisions (for sign-off)
```

All files are **CSV format** except `assumptions_register.xlsx` (Excel).

---

## File Specifications

### 1. primary_history.csv

**Purpose**: Monthly primary sales to distributors (supply-chain view)

**Historical Period**: April 2025 through June 2026 (15 months minimum)

**Required Columns**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| month | YYYY-MM | 2025-04 | Fiscal month (Apr-Dec = Y, Jan-Mar = Y+1) |
| chain_name | String | Reliance | Retail chain identifier |
| zone | String | East | Geographic zone (East, West, North, South) |
| state | String | Maharashtra | State within zone |
| brand | String | Mamaearth | Product brand |
| category | String | Personal Care | Product category |
| article | String | Shampoo_250ML | Article/SKU name |
| ean | String | 8901050001111 | European Article Number (unique product ID) |
| primary_qty | Numeric | 12500 | Quantity sold to distributor (units) |
| primary_nsv | Numeric | 250000 | Net selling value to distributor (₹) |
| distributor | String | Apollo Pharmacies | Specific distributor (optional reference) |
| warehouse | String | Gurgaon | Dispatch warehouse |

**Quality Checks**:
- ✓ No blank values in required columns
- ✓ EAN values are unique-ish per article (same EAN across multiple chains/states allowed)
- ✓ Quantities are positive integers (no negative primary)
- ✓ Months are consecutive Apr 2025–Jun 2026
- ✓ NSV ≥ quantity × 10 (rough sanity check for pricing)
- ✓ No excluded brands (Pure Origin, Lumineve, Staze)

**Data Quality Filters**:
- Remove rows with quantity = 0 for 3+ consecutive months (likely delisted)
- Flag rows with primary > 100K for 1 month (potential data entry error; review with Data Owner)

---

### 2. offtake_history.csv

**Purpose**: Monthly retail sales (end-demand view); acts as forecast target

**Historical Period**: April 2025 through June 2026 (15 months minimum)

**Required Columns**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| month | YYYY-MM | 2025-04 | Fiscal month |
| chain_name | String | Reliance | Retail chain |
| zone | String | East | Zone |
| state | String | Maharashtra | State |
| brand | String | Mamaearth | Brand |
| category | String | Personal Care | Category |
| article | String | Shampoo_250ML | Article |
| ean | String | 8901050001111 | Product ID |
| offtake_qty | Numeric | 8500 | Retail offtake (units) |
| offtake_nsv | Numeric | 170000 | Retail NSV (₹) |
| store_count | Numeric | 450 | Number of stores selling this article |

**Quality Checks**:
- ✓ offtake_qty ≤ primary_qty (retail can't exceed supply)
- ✓ offtake_nsv ≥ offtake_qty × 5 (rough pricing sanity check)
- ✓ store_count > 0 (at least 1 store)
- ✓ No excluded brands
- ✓ Months = Apr 2025–Jun 2026

**Data Quality Filters**:
- Flag zero-offtake months (out-of-stock? delisting?)
- Flag negative offtake (data entry error; investigate)

---

### 3. fact_margin.csv

**Purpose**: Pricing, margin, and profitability by article/chain/month

**Historical Period**: April 2025 through June 2026

**Required Columns**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| month | YYYY-MM | 2025-04 | Fiscal month |
| chain_name | String | Reliance | Retail chain |
| brand | String | Mamaearth | Brand |
| article | String | Shampoo_250ML | Article |
| ean | String | 8901050001111 | Product ID |
| mrp | Numeric | 299 | Maximum Retail Price (₹) |
| margin_pct | Numeric | 25.5 | Effective margin % (out of MRP) |
| tot_pct | Numeric | 12.0 | Trade margin + distribution % |
| gst_pct | Numeric | 5.0 | GST % (standard for cosmetics) |
| cm2_pct | Numeric | 18.0 | Company contribution margin after tax |
| quality_status | String | PUBLISHED | Data quality flag (PUBLISHED / DRAFT / AUDIT) |

**Quality Checks**:
- ✓ MRP > 0
- ✓ margin_pct between 0 and 100
- ✓ margin_pct + tot_pct + gst_pct ≤ 100 (sanity)
- ✓ All EANs in primary_history have margin records
- ✓ quality_status in (PUBLISHED, DRAFT, AUDIT); exclude DRAFT/AUDIT for production

**Notes**:
- One margin record per EAN per chain per month (no duplicates)
- If margin missing for EAN in given month, use prior month or annual average
- Margin from Margin Repository (export from Release_v1.0.0_RC1/04_Business_Outputs/)

---

### 4. article_master.csv

**Purpose**: Static dimension table for articles (enrichment only)

**Required Columns**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| ean | String | 8901050001111 | Unique product ID |
| article | String | Shampoo_250ML | Article name |
| brand | String | Mamaearth | Brand |
| category | String | Personal Care | Category |

**Quality Checks**:
- ✓ No blank values
- ✓ Unique EANs (one row per EAN)
- ✓ All EANs in primary_history present in master

---

### 5. chain_master.csv

**Purpose**: Static dimension table for retail chains (enrichment only)

**Required Columns**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| chain_name | String | Reliance | Unique chain identifier |
| zone | String | East | Geographic zone |
| state | String | Maharashtra | State within zone |

**Quality Checks**:
- ✓ No blank values
- ✓ Unique chain-state-zone combinations
- ✓ All chains in primary_history present in master
- ✓ States match standard Indian state names

---

### 6. warehouse_mapping.csv

**Purpose**: Maps chains to dispatching warehouses (used in allocation)

**Required Columns**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| chain_name | String | Reliance | Retail chain |
| zone | String | East | Zone |
| state | String | Maharashtra | State |
| warehouse | String | Gurgaon | Warehouse name |
| allocation_pct | Numeric | 60 | Allocation % for this chain-warehouse pair |

**Quality Checks**:
- ✓ allocation_pct sums to 100 for each chain
- ✓ Allocation percentages between 0 and 100
- ✓ All chains in primary_history have warehouse mapping
- ✓ Warehouses in (Gurgaon, Mumbai, Bangalore, Kolkata)

**Example**:
```
Reliance, East, Maharashtra, Gurgaon, 40
Reliance, East, Maharashtra, Mumbai, 30
Reliance, East, Maharashtra, Bangalore, 20
Reliance, East, Maharashtra, Kolkata, 10
```

---

### 7. monthly_targets.csv

**Purpose**: Business targets/budget for planning context (informational only)

**Optional Columns**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| month | YYYY-MM | 2025-04 | Fiscal month |
| chain_name | String | Reliance | Retail chain |
| brand | String | Mamaearth | Brand |
| target_qty | Numeric | 50000 | Target quantity |
| target_nsv | Numeric | 1000000 | Target NSV (₹) |

**Usage**:
- Compare forecast vs. target in Power BI
- Flag if forecast is significantly below target (risk indicator)
- Informational only; does not block forecast

---

### 8. business_events.csv

**Purpose**: Planned promotions, new listings, festivals, etc. (enrichment only)

**Optional Columns**:

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| month | YYYY-MM | 2025-04 | Month of event |
| chain_name | String | Reliance | Affected chain (or ALL) |
| brand | String | Mamaearth | Affected brand (or ALL) |
| event_type | String | PROMOTION | Type: PROMOTION, NEW_LISTING, FESTIVAL, PRICE_CHANGE, BOGO |
| event_name | String | Diwali Sale | Human-readable name |
| expected_uplift_pct | Numeric | 35 | Expected % uplift from baseline (optional) |
| notes | String | 20% discount on all products | Details |

**Usage**:
- KAM/Category uses this to add manual adjustments to forecast
- Not automatically applied; requires explicit approval + reason

---

### 9. assumptions_register.xlsx

**Purpose**: Formal decision register for Phase A business assumptions

**Sheets**:
1. **Assumptions** — A1–A5 assumptions with approvals
2. **Operational Decisions** — D1–D5 detail-level decisions
3. **Metrics & Gates** — Reference of acceptance criteria

**See**: `ASSUMPTIONS_REGISTER_TEMPLATE.md` for detailed structure

**Status**: Template ready for stakeholder sign-off (see separate guide)

---

## Data Preparation Checklist

### Before Running Audit

- [ ] All 9 files present in `Phase_A_Input/` directory
- [ ] All CSV files use UTF-8 encoding
- [ ] Column names lowercase, no spaces (use underscores)
- [ ] Numeric columns contain only numbers (no currency symbols, commas)
- [ ] No extra columns beyond those specified
- [ ] Files are not locked (available for read)

### After Audit

- [ ] Run: `python forecast_engine/data_readiness_audit.py Phase_A_Input audit_output`
- [ ] Review: `audit_output/audit_summary.json`
- [ ] Check: BLOCKED count must = 0
- [ ] Fix: Any FAIL or BLOCKED issues
- [ ] Verify: No excluded brands in data

### Data Reconciliation

- [ ] Primary quantities > offtake quantities (supply > demand)
- [ ] All offtake EANs present in margin master
- [ ] All chains in primary have warehouse allocation
- [ ] Month coverage: Apr 2025–Jun 2026 continuous
- [ ] No duplicate Chain×EAN×Month records

---

## Historical Period: Why Apr 2025–Jun 2026?

This 15-month window provides:

1. **Sufficient history** (12+ months minimum for trend calculation)
2. **Completed months only** (no partial-month bias)
3. **Four backtestable months** (Mar, Apr, May, Jun 2026 can use prior data)
4. **Seasonal coverage** (15 months spans 1+ full seasonal cycles)

**Exclude**:
- April 2024 and earlier (stale, pre-Margin Repo v1.0.0)
- July 2026 (incomplete; use only when fully reconciled)
- August 2026 onwards (not yet relevant for Phase A validation)

---

## File Sizes (Typical)

| File | Size | Rows | Notes |
|------|------|------|-------|
| primary_history.csv | 50–100 MB | 500K–1M | Monthly snapshots × articles |
| offtake_history.csv | 40–80 MB | 400K–800K | Monthly snapshots × stores |
| fact_margin.csv | 10–20 MB | 100K–200K | Monthly × articles × chains |
| article_master.csv | 2–5 MB | 20K–50K | 1 row per EAN |
| chain_master.csv | <1 MB | 100–500 | 1 row per chain-state |
| warehouse_mapping.csv | <1 MB | 50–200 | Chain × warehouse allocation |
| monthly_targets.csv | 1–2 MB | 10K–50K | Optional reference |
| business_events.csv | <1 MB | 100–1K | Planned events |

---

## Next Steps

1. **Create `Phase_A_Input/` directory** in project root
2. **Assemble 9 CSV files** from data sources (Margin Repo, Primary/Offtake history, masters)
3. **Run data audit**: `python forecast_engine/data_readiness_audit.py`
4. **Fix any BLOCKED issues** with Data Owner
5. **Proceed to backtesting** once audit passes

---

**Status**: Specification complete, ready for data preparation  
**Owner**: Data Ops  
**Timeline**: 2–5 days to assemble  
**Next Milestone**: Data readiness audit (BLOCKED = 0)
