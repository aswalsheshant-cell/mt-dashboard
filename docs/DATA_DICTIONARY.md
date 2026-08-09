# Data Dictionary & Schema Specification

## Purpose

This file defines the canonical column names, data types, grain, and business rules for every
table in the MT Analytics data model. Any script or DAX measure that references a column must
use the exact names defined here.

---

## Naming Conventions

| Layer | Table prefix | Column naming | Example |
|---|---|---|---|
| Staging | `stg_` | snake_case, source-close names | `stg_primary_sales` |
| Intermediate | `int_` | snake_case, conformed names | `int_sales_conformed` |
| Mart / Reporting | `fact_`, `dim_` | snake_case, business-readable | `fact_primary_monthly` |
| Derived columns | none | descriptive alias, no abbreviations | `scheme_deduction_pct` |

---

## Fact Tables

### `Fact_Sales` / `fact_primary_monthly`

**Grain:** One row per `month_label` × `chain_name` × `brand_name` × `sku_code`

| Column | Type | PK/FK | Description | Business Rules |
|---|---|---|---|---|
| `transaction_id` | String | PK | Unique invoice line identifier | Format: `{chain_code}-{YYYYMM}-{seq}` |
| `month_label` | String | — | "Apr-26", "May-26" etc. | Always derive FY from this — never from position |
| `date_key` | Integer | FK → dim_calendar | Format `YYYYMMDD` | Must exist in dim_calendar |
| `chain_name` | String | FK → dim_chain | Retail chain name | Exact match required — no fuzzy matching |
| `store_id` | String | FK → dim_store | Unique account store code | Preserve leading zeros — store as string |
| `brand_name` | String | FK → dim_product | Brand (e.g. Mamaearth, Aqualogica) | Canonical form from product master |
| `sku_code` | String | FK → dim_product | Master article / EAN number | String — never cast to numeric |
| `gross_billing_lakhs` | Decimal | — | GSV before discounts (₹ Lakhs) | Always positive; ≥ nsv_lakhs |
| `scheme_deduction_lakhs` | Decimal | — | Off-invoice scheme deductions (₹ Lakhs) | Non-negative; ≤ 50% of gross_billing |
| `nsv_lakhs` | Decimal | — | Net Sales Value = gross_billing − scheme_deduction (₹ Lakhs) | May be negative if returns > billing |
| `cogs_lakhs` | Decimal | — | Cost of goods sold (₹ Lakhs) | Non-negative |
| `gm_lakhs` | Decimal | — | Gross Margin = NSV − COGS (₹ Lakhs) | Derived; never store separately |
| `gm_pct` | Decimal | — | GM% = gm_lakhs / nsv_lakhs | −20% to +85% valid range |
| `primary_qty_units` | Integer | — | Volume shipped in units | Non-negative |
| `mrn_lakhs` | Decimal | — | Material Return Note value (₹ Lakhs) | Non-negative; traced separately |
| `fy_tag` | String | — | "FY25", "FY26", "FY27" | Derived from month_label — never hardcoded |
| `data_source` | String | — | Source file / pipeline that populated this row | Audit trail field |
| `ingested_at` | Timestamp | — | When this row was last written | UTC; set by pipeline |

### `fact_offtake_monthly`

**Grain:** One row per `month_label` × `chain_name` × `sku_code` (store-level offtake aggregated to chain)

| Column | Type | PK/FK | Description | Business Rules |
|---|---|---|---|---|
| `month_label` | String | — | "Apr-26", "May-26" etc. | Must match primary fact month labels |
| `chain_name` | String | FK → dim_chain | Retail chain | Same canonical names as Fact_Sales |
| `sku_code` | String | FK → dim_product | Article / EAN | String |
| `offtake_value_lakhs` | Decimal | — | Consumer sell-through value (₹ Lakhs) | Source of truth for consumer demand |
| `offtake_units` | Integer | — | Units sold to consumers | Non-negative |
| `dos_days` | Decimal | — | Days of Supply = (Primary − Offtake) / Daily Offtake | 0–90 valid; >90 = data suspect |
| `fy_tag` | String | — | Financial year tag | Derived from month_label |

---

## Dimension Tables

### `dim_chain` / `Dim_Store`

**Grain:** One row per `chain_name` (chain-level; store-level is `dim_store`)

| Column | Type | Description | Business Rules |
|---|---|---|---|
| `chain_name` | String | Retail chain name (PK in chain dim) | Canonical names: BigBasket, DMart, Reliance Smart, Nykaa, Blinkit, Zepto, JioMart, More Retail |
| `chain_code` | String | Short code (e.g. "BB", "DM", "RL") | Uppercase 2-3 chars |
| `channel_type` | String | "Grocery", "Pharmacy", "Beauty", "Quick Commerce" | Controlled vocabulary |
| `is_key_account` | Boolean | Whether a dedicated NKAM is assigned | True for top-10 chains by NSV |
| `reliance_brand_counter` | Boolean | Brand counter classification | EXACT match on source field — never infer |

### `dim_store`

**Grain:** One row per `store_id` (physical store / dark store / DC)

| Column | Type | Description | Business Rules |
|---|---|---|---|
| `store_id` | String | Unique store identifier (PK) | Preserve leading zeros |
| `chain_name` | String | Parent chain (FK → dim_chain) | Must match dim_chain exactly |
| `store_name` | String | Display name | No truncation |
| `format_type` | String | Hypermarket / Supermarket / Dark Store / Express / Pharma | Controlled vocabulary |
| `zone` | String | North / South / East / West | Used for regional allocation |
| `dc_code` | String | Distribution centre link | Maps to distributor hierarchy |
| `is_active` | Boolean | Store currently operational | False = exclude from distribution denominator |
| `listing_start_date` | Date | When Honasa products were first listed | Used for NPI allocation rules |

### `dim_product`

**Grain:** One row per `sku_code` (EAN / article code)

| Column | Type | Description | Business Rules |
|---|---|---|---|
| `sku_code` | String | EAN / Article code (PK) | Never cast to numeric — leading zeros preserved |
| `product_name` | String | Full product name | Canonical form from product master |
| `brand_name` | String | Brand (Mamaearth, The Derma Co, Aqualogica, Dr Sheth's, BBlunt, Staze) | Canonical brand name |
| `category` | String | Hair Care / Skin Care / Baby Care / Face Care / Body Care | L1 category |
| `sub_category` | String | L2 category | e.g. "Shampoo", "Sunscreen", "Face Wash" |
| `pack_size_ml` | Decimal | Pack volume in ml or g | Used for price-per-ml calculations |
| `mrp_inr` | Decimal | Maximum Retail Price (₹) | Latest valid MRP; versioned for RSP analysis |
| `is_active` | Boolean | SKU currently in market | False = exclude from new listing targets |
| `launch_date` | Date | First market availability date | NPI flag: < 3 months history from this date |

### `dim_calendar`

**Grain:** One row per calendar date

| Column | Type | Description | Business Rules |
|---|---|---|---|
| `date_key` | Integer | YYYYMMDD (PK) | — |
| `full_date` | Date | Calendar date | — |
| `month_label` | String | "Apr-26" format | Derives FY; must match fact table month_label |
| `fy_tag` | String | "FY25"/"FY26"/"FY27" | Apr–Dec of Y → FY(Y+1); Jan–Mar of Y → FY(Y) |
| `quarter_label` | String | "Q1 FY27" | Q1=Apr–Jun, Q2=Jul–Sep, Q3=Oct–Dec, Q4=Jan–Mar |
| `month_number` | Integer | 1=April, 12=March (FY-aligned) | — |
| `is_month_end` | Boolean | Last day of calendar month | Used for snapshot joins |

---

## Derived / Calculated Fields

Never store these in fact tables — compute them at query time:

| Metric | Formula | Notes |
|---|---|---|
| `gm_pct` | `gm_lakhs / NULLIF(nsv_lakhs, 0)` | Guard divide-by-zero |
| `scheme_pct` | `scheme_deduction_lakhs / NULLIF(gross_billing_lakhs, 0)` | Always use gross_billing as denominator |
| `trade_spend_pct` | `total_btl_lakhs / NULLIF(nsv_lakhs, 0)` | BTL includes schemes + activation + visibility |
| `dos_days` | `(primary_nsv_lakhs - offtake_value_lakhs) / (offtake_value_lakhs / days_in_month)` | Guard: if offtake = 0, return NULL not 0 |
| `scheme_roi` | `offtake_value_lakhs / NULLIF(scheme_deduction_lakhs, 0)` | See BUSINESS_RULES.md thresholds |

---

## Data Quality Rules

| Rule | Check | Severity |
|---|---|---|
| NSV cannot exceed gross billing | `nsv_lakhs ≤ gross_billing_lakhs` | FAIL |
| GM% within valid range | `-0.20 ≤ gm_pct ≤ 0.85` | FAIL |
| Trade Spend% within valid range | `0 ≤ trade_spend_pct ≤ 0.50` | FAIL (>0.25 = Warning) |
| DOS within valid range | `0 ≤ dos_days ≤ 90` | Warning (>90 = FAIL) |
| month_label must parse to a valid date | Regex `[A-Z][a-z]{2}-\d{2}` | FAIL |
| store_id must exist in dim_store | LEFT JOIN returns non-null | Warning (log orphan count) |
| Reliance Brand Counter: exact match only | `data_status == "brand counter"` | FAIL if str.contains() used |
| No NaN in NSV or offtake output | `nsv_lakhs IS NOT NULL` in final output | FAIL |
| FY27 allocations reconcile to zero residual | ∑SKU targets = chain target ±0.001% | FAIL |

---

## Reference

- `docs/BUSINESS_RULES.md` — canonical business logic for each metric
- `docs/ALLOCATION_RULES.md` — target allocation formulas and hierarchy
- `docs/KPI_DICTIONARY.md` — DAX measures for Power BI
- `docs/QC_FRAMEWORK.md` — automated QC gates that enforce these rules
- `scripts/build_dashboard_data.py` — Python implementation of Primary/Offtake pipeline
