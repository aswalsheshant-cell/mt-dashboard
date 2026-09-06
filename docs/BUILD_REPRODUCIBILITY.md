# Local Build Reproducibility Guide

**Document Version:** 1.0  
**Last Updated:** 2026-09-05  
**Audience:** Analytics Engineers, Data Engineers, DevOps  
**Purpose:** Enable any developer to rebuild `data.js` from source on their local machine

---

## Quick Start (5 minutes)

```bash
# Clone the repository
git clone https://github.com/aswalsheshant-cell/mt-dashboard.git
cd mt-dashboard

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify Python installation
python -m py_compile scripts/build_dashboard_data.py
echo "✓ Build script validated"
```

---

## Full Build Process

### Prerequisites

**System Requirements:**
- Python 3.8+
- 4 GB RAM minimum
- 2 GB disk space (for dependencies + source files)
- ~10 seconds per full build

**Required Files (not in repo):**

The build requires four source Excel files. These are NOT committed to the repo for security/size 
reasons. You must obtain these from the data owner:

| File | Purpose | Size | Owner |
|------|---------|------|-------|
| `Primary FY-2024-26.xlsx` | Primary sell-in (NSV, articles, zones) | ~50 MB | Finance |
| `Chain Offtake Master MONTHLY.xlsx` | Chain & zone sell-out | ~30 MB | Channel |
| `Universe MT.xlsx` | Store distribution footprint (426 stores) | ~2 MB | Channel |
| `Promo Master -MT.xlsx` | Trade spend & promotional calendar | ~5 MB | Trade |

**Contact:** Reach out to the Modern Trade analytics team for access to these files.

### Step 1: Set Up Environment

```bash
# Navigate to project root
cd /path/to/mt-dashboard

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install exact dependency versions
pip install -r requirements.txt

# Verify all packages installed
pip list | grep -E "pandas|openpyxl|lxml|python-pptx|pytest"
```

### Step 2: Prepare Source Data

```bash
# Create a source directory
mkdir -p ~/mt-dashboard-sources

# Copy the 4 Excel files to this directory
cp /path/to/sources/*.xlsx ~/mt-dashboard-sources/

# Verify all 4 files are present
ls ~/mt-dashboard-sources/
# Expected output:
# - Chain Offtake Master MONTHLY.xlsx
# - Primary FY-2024-26.xlsx
# - Promo Master -MT.xlsx
# - Universe MT.xlsx
```

### Step 3: Run Full Build

```bash
# Full rebuild (takes ~10 seconds)
python scripts/build_dashboard_data.py \
  --src ~/mt-dashboard-sources/ \
  --out dashboard/data.js

# If successful, you'll see:
# ✓ Parsed Primary workbook: 12,345 rows
# ✓ Parsed Offtake workbook: 8,234 rows
# ✓ Built universe: 426 active stores
# ✓ data.js generated: 9.2 MB
```

### Step 4: Validate Build Output

```bash
# Check file size (should be ~8-10 MB)
ls -lh dashboard/data.js

# Validate JSON syntax
python -m json.tool dashboard/data.js > /dev/null && echo "✓ JSON valid"

# Check that key data blocks exist
grep -c '"primary":' dashboard/data.js  # Should output: 1
grep -c '"offtake":' dashboard/data.js  # Should output: 1
grep -c '"by_chain":' dashboard/data.js # Should output: 1
```

### Step 5: Test in Browser

```bash
# Start a local HTTP server
cd dashboard
python -m http.server 8000

# Open browser: http://localhost:8000
# Verify:
# - Dashboard loads without JS errors
# - Data Explorer tab shows metrics
# - All 12 tabs render without NaN/undefined
# - FY25, FY26 data visible (FY27 if patched)
```

---

## Partial Rebuilds (Faster)

When you only need to update one data block, use partial-refresh modes:

### Refresh Detail Block Only
```bash
# Updates File 2 detail metrics + FY27 primary (if present)
python scripts/build_dashboard_data.py \
  --detail-only \
  --src ~/mt-dashboard-sources/ \
  --out dashboard/data.js
# Time: ~3 seconds
```

### Refresh Primary Block Only
```bash
# Updates primary/P&L/insights blocks
python scripts/build_dashboard_data.py \
  --primary-only \
  --src ~/mt-dashboard-sources/ \
  --out dashboard/data.js
# Time: ~2 seconds
```

### Patch Offtake with FY27 Monthly Data
```bash
# Merges FY27 monthly offtake .xlsx files into existing data.js
python scripts/build_dashboard_data.py \
  --offtake-patch \
  --src ~/mt-dashboard-sources/ \
  --out dashboard/data.js
# Time: ~2 seconds
# Note: Idempotent — safe to re-run with all months at once
```

### Refresh Forecast Block
```bash
# Updates TY target & forecast block
python scripts/build_dashboard_data.py \
  --forecast-only \
  --src ~/mt-dashboard-sources/ \
  --out dashboard/data.js
# Time: ~1 second
```

---

## Troubleshooting

### Error: "Module not found: pandas"
```bash
# Activate virtual environment
source venv/bin/activate

# Reinstall
pip install --upgrade -r requirements.txt
```

### Error: "File not found: Primary FY-2024-26.xlsx"
```bash
# Verify source directory path is correct
ls ~/mt-dashboard-sources/

# If files aren't there, request them from Finance/Channel teams
# Expected file names (exact):
# - Primary FY-2024-26.xlsx
# - Chain Offtake Master MONTHLY.xlsx
# - Universe MT.xlsx
# - Promo Master -MT.xlsx
```

### Error: "Illegal argument exception" or "Zip file corrupt"
- Source Excel file may be corrupted or locked
- Try opening it in Excel first to validate
- Download a fresh copy from the shared drive

### data.js is smaller than expected (<5 MB)
- Check if all 4 source files were processed
- Run with `--src` pointing to directory with all 4 files
- Check console output for "Skipped" messages

### Browser shows "undefined" in metrics
- This indicates missing data in the source files
- Run QC validation: `python scripts/validate_dashboard_qc.py`
- Check which source block is incomplete

---

## QC Validation (Optional)

After building, optionally run comprehensive QC:

```bash
# Validate data integrity & schema
python scripts/validate_dashboard_qc.py \
  --input dashboard/data.js \
  --output qc_report.json

# Expected output:
# ✓ n_stores: 426 (baseline maintained)
# ✓ n_chains: 8 (baseline maintained)
# ✓ FY25 NSV: ₹2,105 Cr (verify with Finance)
# ✓ FY26 NSV: ₹2,347 Cr (verify with Finance)
# ✓ Zero NaN values in by_chain metrics
```

---

## Release Testing (Before Commit)

Before committing a new `data.js`, run the full 52-state test:

```bash
# Test all 13 tabs × 4 FY states (All/FY25/FY26/FY27)
pytest scripts/test_dashboard_ui_matrix.py --headless

# Expected: 52 tests pass, 0 failures
# Time: ~3 minutes

# On any failure, check:
# 1. Does the broken tab load at all?
# 2. Are there NaN/undefined values in metrics?
# 3. Is the broken state (No FY / FY25-only / FY26-only / FY27-only)?
```

---

## Checksum Validation (Optional)

To verify data consistency across builds:

```bash
# Generate baseline checksum
md5sum dashboard/data.js > data.js.baseline

# After rebuild, verify no unintended changes
md5sum -c data.js.baseline
# Output: "data.js: OK" (if identical)
# Output: "data.js: FAILED" (if any data changed)

# Useful for CI/CD: catch accidental overwrites
```

---

## Environment Variables (Optional)

For headless/automated builds:

```bash
export MT_DASHBOARD_SRC=/path/to/sources/
export MT_DASHBOARD_OUT=/path/to/dashboard/data.js
export MT_BUILD_VERBOSITY=DEBUG  # Or INFO, WARN, ERROR

python scripts/build_dashboard_data.py
```

---

## Support

**Issues?** Open an issue or contact:
- **Build failures:** mt-analytics-engineering@honasa.com
- **Missing source files:** finance-data-access@honasa.com
- **Dashboard logic bugs:** channel-analytics@honasa.com

---

## Definitions of Done

✓ Requirements.txt installed without errors  
✓ All 4 source files present and readable  
✓ `data.js` generated (8–10 MB)  
✓ JSON validation passes  
✓ Browser loads without JS errors  
✓ QC validation passes (n_stores, n_chains, baseline metrics)  
✓ 52-state test passes (all 13 tabs × 4 FY states)
