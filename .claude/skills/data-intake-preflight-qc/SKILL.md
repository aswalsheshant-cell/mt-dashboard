---
name: data-intake-preflight-qc
description: Perform fail-closed quality control on incoming CSV, Excel, XLSB and analytical data before repository ingestion. Use whenever data is received, converted, refreshed, mapped, allocated or prepared for a dashboard. Detect schema drift, period errors, duplicates, invalid identities, incorrect units, reconciliation failures, mapping gaps and historical anomalies before production files are changed.
---

# Data Intake Preflight QC

**CORE RULE: Never place a newly received data file directly into a production repository folder.**

Treat every incoming file as untrusted until it passes a documented preflight.

---

## Intake Workflow

```
Received file
    ↓
Quarantine (staging folder, original preserved)
    ↓
File/schema checks (headers, types, encoding)
    ↓
Period checks (FY, Month, fiscal ordering)
    ↓
Row-level quality checks (duplicates, nulls, ranges)
    ↓
Financial reconciliation (NSV, MRP, tax, totals)
    ↓
Business-rule checks (chains, brands, direct/distributor)
    ↓
Historical comparison (prior months, anomaly detection)
    ↓
Master-data mapping simulation (chain, EAN, customer)
    ↓
Allocation preflight (distributor weights, joins, cardinality)
    ↓
NPI classification review (historical first-sale, not current-file-only)
    ↓
Acceptance report generation
    ↓
[PASS] → Repository placement
[WARN] → Approval gate (documented exception)
[FAIL] → Quarantine (cannot proceed)
[BLOCKED] → Missing source definition
```

---

## Stage 1: File & Schema Checks

**Always record first:**

- Source filename
- Received timestamp
- File size (bytes)
- SHA-256 checksum
- Workbook sheets (if applicable)
- Row count
- Column count
- Source owner
- Intended reporting period
- Intended destination folder

**Validate:**

- Correct file type (CSV, XLSX, XLSB)
- Readable workbook/CSV
- Expected sheets present
- **Exact required headers match** (order, spelling, case)
- No duplicate headers
- No hidden/blank columns
- No unexpected columns
- No merged header rows
- No empty sheets
- File not truncated
- Encoding (UTF-8, UTF-8-BOM, Latin-1?)
- CSV delimiter (comma, semicolon, tab?)
- Formulas versus cached values (XLSB)
- Material file-size change from prior month

**Schema Delta Report:**

Compare with the last accepted file:

```
Column Name | Prior | Current | Change | Action
-----------|-------|---------|--------|--------
```

Status: **PASS** (no changes) / **WARN** (documented expected changes) / **FAIL** (undocumented drift)

---

## Stage 2: Period Checks

**Mandatory fields for any record with a month:**

```
MonthStart     (first calendar day of month, e.g., 2026-06-01)
MonthKey       (YYYY-MM format, e.g., 2026-06)
MonthLabel     (MMM-YY format, e.g., Jun-26)
FY             (Fiscal year, e.g., FY27)
FiscalMonthNumber (1–12, where Apr=1, May=2, ..., Mar=12)
```

**Fiscal Year Mapping (April–March):**

```
Mar-26 → FY26
Apr-26 → FY27
May-26 → FY27
Jun-26 → FY27
Jul-26 → FY27
Dec-26 → FY27
Jan-27 → FY27
Feb-27 → FY27
Mar-27 → FY27
Apr-27 → FY28
```

**Reject (FAIL):**

- Ambiguous month names without a year (e.g., "June" alone)
- Dates outside the intended month
- Multiple unexpected months in a single file
- Incorrect FY mapping
- Missing FY column
- Future dates (beyond today)
- Invalid fiscal-month ordering within FY
- Duplicate delivery of an already-accepted period

**Report:**

```
Period Check
Intended Month: Jun-26
Intended FY: FY27
Records with month: 23,192
Unique months found: [Jun-26]
Unique FYs found: [FY27]
Date range: 2026-06-01 to 2026-06-30
Out-of-range dates: 0
Duplicate dates: 0
Status: PASS
```

---

## Stage 3: Row-Level Quality Checks

**Validate every row:**

- Not blank
- Complete invoice number
- Complete customer / Ship-To name
- Complete EAN or Article code
- Complete brand
- Complete category
- Complete chain (for Direct rows only)
- Quantity ≥ 0
- Primary NSV ≥ 0
- MRP > 0
- Tax ≥ 0 and mathematically consistent with NSV/MRP
- Not a cancelled invoice
- Not a pure MRN/credit note (handle separately if present)
- Not marked FOC/Tester (handle separately if present)
- Brand not in excluded list
- Channel valid (MT, EB2B, SIS)
- State/Zone from approved master
- No unexpected whitespace, case drift, or non-printing characters

**Report (exception CSV):**

```
Row | Invoice | EAN | Issue | Quantity | NSV | Action
----|---------|-----|-------|----------|-----|--------
```

**Count:**

```
Total rows: 23,192
Valid rows: 23,192
Rows with exceptions: 0
Blank rows: 0
Duplicate invoices: 0
Negative quantity: 0
Negative NSV: 0
FOC/Tester records: [count and separate]
Cancelled invoices: [count and separate]
Status: PASS
```

---

## Stage 4: Financial Reconciliation

**Calculate independently from source data (do NOT trust summary cells):**

```python
source_qty = SUM(Inv Qty)
source_nsv = SUM(Inv. Net value (LOC)) / 1e5  # → Lakh
source_mrp = SUM(Total MRP sales) / 1e5       # → Lakh
source_tax = SUM(Inv. Tax Amount) / 1e5       # → Lakh
```

**Reconcile against:**

- Workbook summary totals (if provided)
- Sheet-level grand totals
- Month-over-month prior period
- FY-to-date totals (sum of all months in FY)

**Report:**

```
Metric          Source Total    Calculated     Variance    Variance %   Tolerance   Status
Quantity        [X]             [Y]             [D]         [%]          ±0.01%      PASS
Primary NSV     [X] Lakh        [Y] Lakh        [D] Lakh    [%]          ±0.02 L     PASS
Primary MRP     [X] Lakh        [Y] Lakh        [D] Lakh    [%]          ±0.02 L     PASS
Tax             [X] Lakh        [Y] Lakh        [D] Lakh    [%]          ±0.02 L     PASS
```

Status: **PASS** (within tolerance) / **WARN** (minor variance, investigate) / **FAIL** (material gap)

---

## Stage 5: Business-Rule Checks

**Direct rows (Chain explicitly provided):**

- Chain must be from approved Chain Master
- Chain must NOT equal Ship-To name or Customer name (use Chain Master ID)
- Chain must be a retail outlet, not a distributor

**Distributor rows (blank or source convention chain):**

- Blank raw reporting chain OR explicit "DISTRIBUTOR" marker
- Customer must be from approved Distributor/Customer master
- Do NOT automatically trust source chain value
- Flag rows where Chain = Customer name (likely mislabeled)

**Report:**

```
Direct rows: 15,000
  - Chain in master: 15,000 ✓
  - Chain = Ship-To: 0 ✓
  - Chain = Customer: 0 ✓

Distributor rows: 8,192
  - Customer in master: 8,192 ✓
  - Blank chain: 8,192 ✓
  - Unmatched customers: 0 ✓
```

Status: **PASS**

---

## Stage 6: Historical Comparison

**Compare with at least the previous two accepted periods:**

```
Metric              Prior Month    Current Month    Variance    Variance %   Alert?
Row count           19,399         23,192           +3,793      +19.5%       🔍
Quantity            1,289,000      1,456,000        +167,000    +13.0%       ✓
Primary NSV         4,416 L         4,167 L         -249 L      -5.6%        ✓
Chain count         34             51               +17         +50%         🔍
Article count       ~800           ~950             +150        +18.8%       ✓
New brands          0              2                +2          New          ✓
Excluded brands     0              0                —           —            ✓
```

**Investigate flags:**

- Row count increase of 19.5% — expected given June arrival? ✓
- Chain count increase of 50% — 17 new chains in June? ✓

Status: **PASS** (anomalies explained) / **WARN** (investigate) / **FAIL** (unexplained major change)

---

## Stage 7: Master-Data Mapping Simulation

**For every unique value in Chain, Brand, Category, Customer, State, Zone:**

- Look up in approved master
- Record:
  - Value from source
  - Match in master (exact, fuzzy, alias)
  - Master ID
  - Master canonical name
  - Unmatched rows / NSV affected

**Report (mapping_exceptions.csv):**

```
Dimension  | Source Value              | Master Match | Master ID | NSV Affected | Action
-----------|---------------------------|--------------|-----------|--------------|--------
Chain      | D-Mart-Store-E-Com       | D-Mart-Offline | 45       | 1,200 L     | REMAP
Chain      | JUST MARK-Dmart          | D-Mart-Offline | 45       | 850 L       | REMAP
Brand      | Mamaearth                | Mamaearth      | 1        | 2,500 L     | ✓
Chain      | [blank]                  | Unassigned     | 999      | 180 L       | FLAG
```

**Reconcile mapped NSV to source NSV:**

```
Source NSV:       4,167.38 L
Mapped NSV:       4,167.38 L
Unmatched NSV:    0 L
Status:           PASS
```

Status: **PASS** / **WARN** (with documented remapping) / **FAIL** (unmatchable identities)

---

## Stage 8: Allocation Preflight (Distributor Rows)

**Simulate approved allocation logic:**

1. Load allocation weights (Distributor → Chain splits by month/brand)
2. For each Distributor row:
   - Extract: Customer code, Brand, Month
   - Look up allocation key: (Customer, Brand, MonthKey)
   - Apply weights (exact month) or (nearest month within FY)
   - Distribute NSV, MRP, Qty across chains
   - Validate weight sum = 1.0 ± 0.01%
   - Track allocation cardinality

**Report (allocation_qc.csv):**

```
Customer          | Brand     | Month  | Rows | Exact Alloc | Nearest Alloc | Unmapped | Action
-----------------|-----------|--------|------|------------|---------------|----------|--------
Dist Customer XYZ | Mamaearth | Jun-26 | 24   | 24         | 0             | 0        | ✓
Dist Customer ABC | MamaTea   | Jun-26 | 18   | 18         | 0             | 0        | ✓
Dist Customer DEF | Aqualogica| Jun-26 | 5    | 0          | 5             | 0        | NEAREST
Dist Customer GHI | Dr. Sheth | Jun-26 | 12   | 0          | 0             | 12       | FAIL
```

**Reconcile NSV pre/post allocation:**

```
Distributor NSV (source):  1,450 L
Allocated NSV (chains):    1,450 L
Rounding variance:         ±0.01 L
Status:                    PASS
```

Status: **PASS** / **WARN** (acceptable nearest-month substitution) / **FAIL** (unresolvable allocation)

---

## Stage 9: NPI Classification Review

**CRITICAL: Do NOT classify as NPI based on current file alone.**

For every article in the incoming file:

1. Query all available Primary history (all months ever loaded)
2. Query all available Offtake history
3. Find earliest verified commercial sale (non-FOC, non-Tester, non-cancelled)
4. Classify:
   - **Confirmed NPI**: First sale Mar-26 or later, with continuous history from first sale through current month
   - **Provisional NPI**: First sale Mar-26 or later, with gaps or incomplete history
   - **Existing Portfolio**: First verified sale before Mar-26
   - **Ambiguous**: Cannot determine due to data gaps

**Record per article:**

```
EAN        | Article Name                  | First Sale | First FY | Historical Coverage | Classification
-----------|-------------------------------|------------|----------|----------------------|------------------
8904417314298 | [Product A]                | Apr-26     | FY27     | Apr, May, Jun        | Confirmed NPI
8906087779032 | [Product B]                | Jun-26     | FY27     | Jun only             | Provisional NPI
8904417300512 | [Product C]                | Apr-25     | FY25     | [15 months]          | Existing Portfolio
```

**Reconcile:**

```
Articles in file:        950
  - Confirmed NPI:       368
  - Provisional NPI:     121
  - Existing Portfolio:  477
  - Ambiguous/Excluded:  -16
Total classified:        950
```

Status: **PASS** / **WARN** (ambiguous articles, document decision) / **FAIL** (cannot classify)

---

## Stage 10: Repository-Placement Gate

**All of the following must be true:**

- [x] Schema PASS
- [x] Period PASS (FY/Month/Fiscal ordering)
- [x] Row-quality PASS or approved WARN
- [x] Financial reconciliation PASS
- [x] Master-data coverage PASS or approved exceptions
- [x] Allocation simulation PASS (if distributor rows)
- [x] Historical anomaly review completed
- [x] NPI classification complete
- [x] Source checksum recorded
- [x] QC report generated
- [x] Destination path validated

**Filename Convention:**

```
primary_article_Jun_26.csv       (source, quarantine)
primary_article_Jun_26.qc.json   (QC metadata)
primary_article_Jun_26.qc.md     (human report)
primary_article_Jun_26.csv       (canonical copy after PASS)
```

**DO NOT overwrite** an existing accepted file without:
- Recording reason for replacement
- Keeping prior version as `.bak`
- Re-running full QC on the replacement

---

## Stage 11: Post-Placement Verification

**After copying into repository:**

1. Re-run all checks against the repository copy
2. Verify file checksum or documented conversion equivalence
3. Run ingestion in validation mode:
   ```bash
   python scripts/build_dashboard_data.py --detail-only --validate \
     --src ./PowerBI/RawDataFolders --out dashboard/data.js
   ```
4. Confirm expected month/FY appears in generated detail_meta
5. Confirm totals reconcile in generated output
6. Confirm detail_records includes the new period
7. Confirm no regression in prior FY values

**Validation Report:**

```
File:                primary_article_Jun_26.csv
Checksum:            [SHA-256]
Build status:        ✓ PASS
Generated detail:    19,311 records (capped by value)
FY27 months covered: [Apr-26, May-26, Jun-26]
FY27 Primary NSV:    13,659.98 L
  - Apr-26:          5,076.86 L
  - May-26:          4,415.74 L
  - Jun-26:          4,167.38 L
FY25 Primary NSV:    23,331.97 L (unchanged) ✓
FY26 Primary NSV:    32,900.36 L (unchanged) ✓
Regression tests:    8/8 PASS ✓
Status:              PASS — ready for dashboard use
```

---

## Completion Rule

**Never claim "data integrated" merely because the file was copied.**

Integration is complete ONLY when ALL of the following are true:

1. ✓ Intake QC passes all stages (PASS on 11 gates)
2. ✓ Repository copy verified against original
3. ✓ Build script recognizes the new period
4. ✓ Generated detail includes the records
5. ✓ Totals reconcile within tolerance
6. ✓ Dimensions match master data
7. ✓ No regression in prior FY values
8. ✓ Downstream regression tests pass

If ANY contradiction appears, **stop before deployment** and escalate.

---

## Required Deliverables

For every ingested file, produce:

| File | Format | Purpose |
|------|--------|---------|
| `qc_summary.json` | JSON | Machine-readable pass/fail decisions for each stage |
| `qc_summary.md` | Markdown | Human-readable executive summary |
| `schema_diff.csv` | CSV | Column-by-column comparison to prior file |
| `row_exceptions.csv` | CSV | All rows flagged for quality issues |
| `reconciliation.csv` | CSV | Totals, variances, reconciliation proof |
| `mapping_exceptions.csv` | CSV | Unmatched chains, brands, customers |
| `allocation_qc.csv` | CSV | Distributor allocation cardinality and coverage |
| `npi_classification.csv` | CSV | Article-by-article NPI determination with justification |
| `accepted_file_manifest.json` | JSON | Checksum, source, destination, QC status |

Example `qc_summary.json`:

```json
{
  "file": "primary_article_Jun_26.csv",
  "received": "2026-07-25T14:30:00Z",
  "quarantine_path": "PowerBI/Quarantine/primary_article_Jun_26.csv",
  "sha256": "e43bea32...",
  "stages": {
    "file_schema": { "status": "PASS", "issues": 0 },
    "period": { "status": "PASS", "months": ["Jun-26"], "fys": ["FY27"] },
    "row_quality": { "status": "PASS", "exceptions": 0 },
    "reconciliation": { "status": "PASS", "nsv_variance_pct": 0.00 },
    "business_rules": { "status": "PASS", "unmatched_chains": 0 },
    "historical_comparison": { "status": "PASS", "anomalies_explained": true },
    "mapping": { "status": "PASS", "unmapped_nsv": 0 },
    "allocation": { "status": "PASS", "unmapped_rows": 0 },
    "npi": { "status": "PASS", "ambiguous": 0 }
  },
  "final_status": "PASS",
  "approved_for_repository": true,
  "approved_by": "[name]",
  "approved_timestamp": "2026-07-25T15:00:00Z",
  "destination": "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jun_26.csv",
  "post_placement_verified": true
}
```

---

## Invocation

Use this skill every time new data arrives:

```text
Use $data-intake-preflight-qc on this incoming file.

File: [filename]
Source: [source system]
Period: [intended month and FY]

Keep it quarantined until QC passes. Run all 11 stages. Compare with prior accepted files. Validate FY/month mapping, row counts, totals, identities, Direct/Distributor logic, allocation readiness and NPI classification (using full history, not current-file-only).

Do not copy into the repository until I see the complete PASS verdict and all deliverables.
```

---

**This skill would have caught:**

- ✗ June'26 missing from generated payload (test: confirm month appears in months_covered)
- ✗ 19,311 groups ≠ 23,192 rows (reconciliation: explain row-level to group-level reduction)
- ✗ Distributor names becoming chains (allocation simulation: validate all rows → chains before placement)
- ✗ Missing FY context (period checks: reject month-only records)
- ✗ NPI classified on current file only (NPI review: query full history before placement)
- ✗ Hardcoded "Apr-May" labels despite June data (post-placement: verify months_covered before deployment)
