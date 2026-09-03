# TOT% and MRP Corrected Rate Derivation

## Overview

This module derives two critical columns from Primary sales data:
- **TOT%** (column 21): Trade Operating Total — distribution margin percentage
- **MRP Corrected Rate** (column 15): Adjusted MRP after accounting for distribution margins

## Data Location

**Input:** `MTEB2BMTDPrimaryAugXX._3.xlsx` (or similar monthly Primary file)
- Column 14: MRP Rate (source, pre-filled)
- Column 17: Inv Qty (source, pre-filled)
- Column 18: Inv. Net value(LOC) (source, pre-filled)
- Column 15: MRP corrected Rate (output, initially empty)
- Column 21: TOT% (output, initially empty)

## Formulas

### TOT% (Trade Operating Total)
```
TOT% = (MRP Rate × Inv Qty - Inv. Net value) / (MRP Rate × Inv Qty) × 100
```

This represents the distribution margin as a percentage of total MRP value.

**Example:**
```
MRP Rate = 549, Inv Qty = 168, Inv. Net value = 33219.15
MRP Extended = 549 × 168 = 92,232
TOT% = (92,232 - 33,219.15) / 92,232 × 100 = 63.98%
```

### MRP Corrected Rate
```
MRP Corrected = MRP Rate × (1 - TOT% / 100)
```

This adjusts the MRP by removing the distribution margin, resulting in an effective net MRP.

**Example:**
```
MRP Corrected = 549 × (1 - 63.98 / 100) = 549 × 0.3602 = 197.73
```

## Usage

### Method 1: Command Line (Recommended)

```bash
# Simple usage (saves as FILENAME_UPDATED.xlsx)
python scripts/derive_tot_and_mrp.py "MTEB2BMTDPrimaryAug26._3.xlsx"

# With custom output path
python scripts/derive_tot_and_mrp.py \
  "MTEB2BMTDPrimaryAug26._3.xlsx" \
  "MTEB2BMTDPrimaryAug26_FINAL.xlsx"
```

**Output:**
- New Excel file with columns 15 and 21 populated
- All 19,070 rows processed
- Summary report printed to console

### Method 2: Python Integration

```python
from scripts.derive_tot_and_mrp import derive_tot_and_mrp

# Process a file
stats = derive_tot_and_mrp("path/to/primary_file.xlsx")

# Check results
print(f"Calculated: {stats['rows_calculated']}")
print(f"Skipped: {stats['rows_skipped']}")
print(f"Errors: {stats['errors']}")
```

## Validation

Run the test suite to verify the derivation logic:

```bash
python scripts/test_tot_derivation.py
```

Expected output:
```
✓ PASS - All tests validated against sample data
```

## Data Quality Notes

1. **Skipped Rows:** Rows with missing MRP Rate, Inv Qty, or Inv. Net value are skipped
2. **Zero Division:** If MRP Extended = 0, TOT% is set to 0
3. **Formatting:** Output columns are formatted as decimal numbers with 2 decimal places
4. **No Overwrite:** Original file is never modified; output is always a new file

## Integration with Build Pipeline

To automatically derive TOT% and MRP Corrected for new monthly Primary files:

1. Drop the new Primary file in `PowerBI/RawDataFolders/Primary_Article_Monthly/`
2. Run the derivation script
3. Update `scripts/build_dashboard_data.py` to include these derived columns in the data pipeline

Example integration point (future work):
```python
# In build_dashboard_data.py, after loading primary data
derived_stats = derive_tot_and_mrp(primary_file_path)
# Merge derived columns back into primary_df
```

## Sample Results (19,070 rows)

| MRP Rate | Inv Qty | Inv. Net Value | TOT%  | MRP Corrected |
|----------|---------|----------------|-------|---------------|
| 549      | 168     | 33219.15       | 63.98 | 197.73        |
| 449      | 160     | 27396.61       | 61.86 | 171.23        |
| 449      | 120     | 20547.46       | 61.86 | 171.23        |

## Business Context

- **TOT%** indicates the discount/margin provided to distributors
- **MRP Corrected** represents the effective selling price after applying distribution margins
- These metrics are critical for:
  - Profitability analysis
  - Competitive pricing benchmarking
  - Distributor margin audits
  - Revenue reconciliation

## Support

For issues or questions:
1. Check that the input file has the expected column layout
2. Run `test_tot_derivation.py` to validate the logic
3. Verify the output file was created and contains populated columns 15 and 21
