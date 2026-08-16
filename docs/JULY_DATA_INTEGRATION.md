# July 2026 Data Integration Guide

## Status

**Current:** Dashboard data current through June 2026 (FY27 Apr-Jun)  
**Ready for:** July 2026 integration  
**Target:** Extend FY27 coverage to Apr-Jul (4-month rolling window)

## Available Source Files

Located in uploads and scratchpad:

1. **MTEB2BMTDPrimaryJuly26._2.xlsx** (11 MB)
   - 31,356 transaction-level rows from "MTD-Primary-July'26." sheet
   - Columns: Inv No, Invoice Date, Ship-To, Bill-to, Division, Category, EAN, Description, MRP, Qty, NSV value
   - Format: Raw transaction-level data (requires transformation)

2. **Chain_Wise_Primary_Sale...xlsx** (2.9 MB)
   - Chain-wise summary breakdown
   - Format: Pivot/summary format

3. **July26_primary_and_distributor_secondary.xlsb** (2.2 MB)
   - Monthly store × article offtake extract
   - Format: Monthly snapshot (ready for --offtake-patch mode)

## Integration Pipeline

### Step 1: Transform Raw July Primary Data

```bash
python scripts/transform_july_data.py \
  --input <path-to-MTEB2BMTDPrimaryJuly26._2.xlsx> \
  --output dashboard/cleaned_july_primary.xlsx
```

**Output:** `cleaned_july_primary.xlsx` with schema:
- Month, FY, Brand, Zone, Channel, NSV, MRP, Qty, Category, EAN, Chain

### Step 2: Merge into Primary Build

Once transformation produces cleaned data, two options:

**Option A: Create combined Primary_FY202426_10.xlsx**
```bash
# Combine existing FY24-26 + transformed July into single Primary file
# Then run full pipeline:
python scripts/build_dashboard_data.py \
  --src <dir-with-Primary_FY202426_10.xlsx> \
  --out dashboard/data.js
```

**Option B: Incremental FY27 Patch (Recommended)**
```bash
# Use --primary-only to add July to existing FY27 primary block
python scripts/build_dashboard_data.py \
  --primary-only \
  --src <dir-with-cleaned_july_primary.xlsx> \
  --out dashboard/data.js
```

### Step 3: Integrate Offtake Data

For the `.xlsb` monthly offtake extract:

```bash
python scripts/build_dashboard_data.py \
  --offtake-patch \
  --src <dir-with-july-offtake.xlsb> \
  --out dashboard/data.js
```

### Step 4: Validate

```bash
# Run full regression tests
python -m pytest scripts/test_*.py -v

# Run QC gate
python scripts/qc_dashboard.py --data dashboard/data.js
```

Expected results:
- 144 tests PASS
- 26 QC checks PASS (3-4 may shift to BLOCKED for July data gaps)
- FY27 coverage expands: Apr-Jun → Apr-Jul
- Primary FY27 value increases by July NSV

## Known Challenges

1. **Large Excel File**: MTEB2B file (31K rows) has performance issues with openpyxl/pandas
   - **Workaround**: Use `pd.read_excel(..., sheet_name="MTD-Primary-July'26.", chunksize=5000)` for streaming
   - **Alt**: Convert .xlsx to .csv first, then process

2. **Column Mapping**: Raw file columns ≠ dashboard schema
   - Transformation script handles mapping
   - Requires manual review for:
     - Zone assignment (currently heuristic-based on state)
     - Chain classification (Bill-to may not align with dashboard chains)
     - Brand canonicalization (verify Division Desc. → Brand)

3. **Missing Masters**:
   - Sub-category, Range, Net-content not in raw file
   - Would need product master or Category→Range mapping
   - Currently filled as empty placeholders

## Next Steps

1. **Immediate**: Test transformation script on sample/reduced July file
2. **Data QA**: Validate zone, brand, chain mappings against business rules
3. **Build**: Run --primary-only or --offtake-patch mode
4. **Test**: Confirm 144 tests pass and QC gate green
5. **Release**: Commit updated data.js to branch

## Automation for Future Months

The transformation pipeline is idempotent:
- Place new monthly .xlsx files in `--src` directory
- Script auto-discovers and processes any new months
- Re-run build with `--primary-only` or `--offtake-patch`
- Pre-commit hook validates before each commit

This keeps the dashboard fresh as new month-end data arrives.
