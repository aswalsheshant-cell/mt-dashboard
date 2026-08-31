# FY24-25 Data Restoration Workflow

## Executive Summary

This guide walks you through restoring **FY24-25 (Apr 2024 - Mar 2025) data** to the MT Dashboard. The source XLSB files exist on Google Drive but must be downloaded locally and split into monthly CSVs using production-ready scripts.

**Expected Outcome:** FY25 will appear as a selectable filter on all 12 dashboard tabs, with complete Apr'24-Mar'25 historical coverage.

---

## STEP 1: Download Source Files

You must download these 2 files from Google Drive to your local machine. The scripts cannot fetch them directly (cloud proxy blocks Drive).

### Files to Download

| File | Size | Location | File ID |
|------|------|----------|---------|
| **Primary_Article XLSB** | 174.7 MB | `pRIMARY/` folder | `1R8sg2YONPcPUWb-Qky7eIUdiFXAwweMt` |
| **Offtake_Store_Article XLSB** | 184.7 MB | `oFFTAKE/` folder | `1cl2eR8nDwip7IUVYbLEU2b_26iy---EO` |

**Google Drive Folder:** https://drive.google.com/drive/folders/1BetIwPuQZmJ5Ouwd65CA5eDErmlT8zcv?usp=sharing

### Download Instructions

1. Open the Google Drive folder link above
2. Navigate to **pRIMARY** → Right-click **"MT, Eb2B & SIS primary April_23 to May_26.xlsb"** → Download
3. Navigate to **oFFTAKE** → Right-click **"FY-24-26 Chain offtake Store Wise File till May.xlsb"** → Download
4. Save both files to a local folder (e.g., `~/Downloads/MT-Sources/`)

---

## STEP 2: Run Split Scripts

Once files are downloaded, run the split scripts to extract monthly CSVs.

### Environment Check

Verify pyxlsb is installed:
```bash
python3 -c "import pyxlsb; print('✓ pyxlsb installed')"
```

If NOT installed:
```bash
pip install pyxlsb
```

### Option A: Headers-Only Verification (Recommended First)

Before splitting, verify the file structure by printing headers:

#### Primary Headers:
```bash
python scripts/split_primary_article_xlsb.py \
    "~/Downloads/MT-Sources/MT, Eb2B & SIS primary April_23 to May_26.xlsb" \
    --headers-only
```

**Expected Output:** Column list including Month, Primary_NSV, Zone, State, Brand, Chain Name, etc.

#### Offtake Headers:
```bash
python scripts/split_offtake_store_article_xlsb.py \
    "~/Downloads/MT-Sources/FY-24-26 Chain offtake Store Wise File till May.xlsb" \
    --headers-only
```

**Expected Output:** Column list including Month, Store, Article, Offtake_NSV, etc.

### Option B: Execute Full Split

Once headers are verified, run the full split to generate monthly CSVs:

#### Primary Split (generates: primary_article_Apr_24.csv through primary_article_May_26.csv)
```bash
python scripts/split_primary_article_xlsb.py \
    "~/Downloads/MT-Sources/MT, Eb2B & SIS primary April_23 to May_26.xlsb" \
    "PowerBI/RawDataFolders/Primary_Article_Monthly"
```

**Expected:** 14 CSV files created (Apr'25 - May'26 existing, Apr'24 - Mar'25 new)

#### Offtake Split (generates: offtake_store_article_Apr_24.csv through offtake_store_article_May_26.csv)
```bash
python scripts/split_offtake_store_article_xlsb.py \
    "~/Downloads/MT-Sources/FY-24-26 Chain offtake Store Wise File till May.xlsb" \
    "PowerBI/RawDataFolders/Offtake_Monthly"
```

**Expected:** Monthly offtake CSVs for FY24-25 and FY25-26 (currently only Apr-Jul'26 exist)

---

## STEP 3: Verify CSV Output

Check that split was successful:

```bash
# Count Primary CSVs
ls PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_*.csv | wc -l

# Count Offtake CSVs
ls PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_*.csv | wc -l

# List all months to verify coverage
echo "=== PRIMARY MONTHS ===" && \
ls PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_*.csv | sed 's/.*primary_article_//' | sed 's/.csv//' | sort

echo "=== OFFTAKE MONTHS ===" && \
ls PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_*.csv | sed 's/.*offtake_store_article_//' | sed 's/.csv//' | sort
```

**Expected Primary Months:**
```
Apr_24, May_24, Jun_24, Jul_24, Aug_24, Sep_24, Oct_24, Nov_24, Dec_24, Jan_25, Feb_25, Mar_25, 
Apr_25, May_25, Jun_25, Jul_25, Aug_25, Sep_25, Oct_25, Nov_25, Dec_25, Jan_26, Feb_26, Mar_26, 
Apr_26, May_26
```

**Expected Offtake Months (at minimum):**
```
Apr_24, May_24, ..., Mar_25 (new), Apr_25, May_25, ..., Mar_26 (new), Apr_26, May_26, Jul_26
```

---

## STEP 4: Commit to Repository

Once CSVs are verified, commit them to the branch:

```bash
# Add new/updated CSVs
git add PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_*.csv
git add PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_*.csv

# Commit with descriptive message
git commit -m "Add FY24-25 monthly data splits from source XLSB files

- Primary: Apr'24-May'26 (26 months total)
- Offtake: Apr'24-Jul'26 (monthly store×article level)
- Enables complete 28-month dashboard coverage (Apr'24-Jul'26)
- Resolves FY25 missing data on Primary & Offtake tabs

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

# Push to remote
git push origin claude/ai-agent-powerbi-dashboard-issues-wpjuh6
```

---

## STEP 5: Rebuild Dashboard

With all CSVs in place, rebuild the dashboard data.js:

```bash
# Full rebuild (recommended for initial FY24-25 ingestion)
python scripts/build_dashboard_data.py \
    --src PowerBI/RawDataFolders \
    --out dashboard/data.js
```

**Build Progress:**
- Ingests Primary_Article_Monthly: Apr'24 onwards
- Ingests Offtake_Monthly: Apr'24 onwards  
- Merges universe/chain/brand masters
- Aggregates into 12-tab dashboard structure
- Generates 21 MB data.js with full history

**Typical Duration:** 2-5 minutes

---

## STEP 6: Verify Dashboard Coverage

After rebuild, verify FY25 appears on all tabs:

### Command-Line Verification

```bash
python3 << 'EOF'
import json

# Load rebuilt data.js
with open('dashboard/data.js', 'r') as f:
    content = f.read()
    json_start = content.find('{')
    data = json.loads(content[json_start:])

# Check FY coverage
print("=== FY COVERAGE IN REBUILT DASHBOARD ===\n")

if 'FY_ALL' in data:
    print(f"Available FYs: {data['FY_ALL']}")
else:
    print("⚠ FY_ALL not found")

if 'PREAGG_FYS' in data:
    print(f"Pre-aggregated FYs: {data['PREAGG_FYS']}")

if 'primary' in data:
    print(f"\nPrimary block keys: {list(data['primary'].keys())}")
    if 'by_zone' in data['primary']:
        print(f"Primary data present: ✓")
        # Check for FY25
        for zone in data['primary']['by_zone'][:1]:
            if 'fy25' in zone:
                print(f"  FY25 in primary: ✓ (e.g., {zone['zone']}: {zone['fy25']})")
            else:
                print(f"  FY25 in primary: ✗")
                break

if 'offtake' in data:
    if 'by_zone' in data['offtake']:
        print(f"\nOfftake data present: ✓")
        # Check for FY25
        has_fy25 = False
        for zone in data['offtake']['by_zone']:
            if 'fy25' in zone:
                has_fy25 = True
                print(f"  FY25 in offtake: ✓ (e.g., {zone['name']}: {zone['fy25']})")
                break
        if not has_fy25:
            print(f"  FY25 in offtake: ✗")

print("\n" + "="*60)
if data.get('FY_ALL') and 'FY25' in data['FY_ALL']:
    print("✓✓✓ FY25 SUCCESSFULLY ADDED TO DASHBOARD ✓✓✓")
else:
    print("✗ FY25 not yet available - rebuild may not have completed")
EOF
```

### Browser-Based Verification

1. Open `dashboard/index.html` in a browser (or serve via HTTP)
2. Check the **FY filter dropdown** (top-right) 
3. Verify **"FY25"** appears alongside FY26, FY27
4. Select **FY25** and verify data displays on all tabs:
   - **Primary Tab:** Apr'24-Mar'25 data with zones/chains/brands
   - **Offtake Tab:** Offtake data (if available in source)
   - **P&L Tab:** Derived from primary
   - **Other tabs:** All should show FY25 data without dashes

---

## Troubleshooting

### Issue: Split script fails with "pyxlsb.exception.WorkbookException"

**Cause:** XLSB file corrupted or in wrong format

**Solution:**
1. Verify file downloaded completely (check file size matches)
2. Try headers-only mode first: `--headers-only` flag
3. If headers work but split fails, run with `--header-row 1` flag (annotation row above real header)

### Issue: No CSVs generated after split

**Cause:** Month column not auto-detected

**Solution:**
1. Run `--headers-only` to identify month column name
2. Run split with explicit `--month-col "Column Name"` flag

### Issue: Dashboard rebuild fails or completes quickly

**Cause:** New CSVs not in correct directory

**Solution:**
```bash
# Verify CSV placement
ls PowerBI/RawDataFolders/Primary_Article_Monthly/ | head
ls PowerBI/RawDataFolders/Offtake_Monthly/ | head

# Run rebuild with explicit --src path
python scripts/build_dashboard_data.py \
    --src $(pwd)/PowerBI/RawDataFolders \
    --out $(pwd)/dashboard/data.js
```

### Issue: FY25 still doesn't appear after rebuild

**Cause:** data.js not loaded or browser cache

**Solution:**
1. Hard refresh browser: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
2. Clear browser cache for the dashboard URL
3. Verify new data.js was actually generated: `ls -lht dashboard/data.js`

---

## Success Criteria

✓ All checks passed:
- [ ] Both XLSB files downloaded successfully
- [ ] pyxlsb installed and headers verified
- [ ] Split scripts completed without errors
- [ ] Primary CSVs: Apr_24 through May_26 present (26 files)
- [ ] Offtake CSVs: Apr_24 through Jul_26 present
- [ ] CSVs committed and pushed to remote
- [ ] Dashboard rebuild completed (< 5 min)
- [ ] FY25 appears in dashboard FY filter dropdown
- [ ] FY25 data displays on Primary tab (no dashes)
- [ ] FY25 data displays on Offtake tab (if offtake split successful)

---

## Next Steps (After Completion)

1. **Automated Refresh:** Update PowerBI watch folder configuration to auto-detect monthly splits
2. **Monthly Handoff:** Establish cadence for XLSB source updates (current data ends Jul'26)
3. **Archive:** Once FY24-25 is confirmed stable, archive split XLSB files to Drive folder

---

## Questions or Issues?

If split fails or rebuild doesn't produce FY25 data:
1. Verify file paths are correct (no spaces, proper quotes)
2. Check CSV files exist and are not empty: `wc -l PowerBI/RawDataFolders/Primary_Article_Monthly/*.csv`
3. Run dashboard rebuild with explicit paths as shown above
4. Check browser console for JavaScript errors after opening dashboard

