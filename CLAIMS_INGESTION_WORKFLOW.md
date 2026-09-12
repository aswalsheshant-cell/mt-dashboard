# Distributor Claims Ingestion & CM2 Reconciliation Workflow

**Status:** Pipeline Ready | **Branch:** `claude/power-bi-data-analysis-f1vggw`

---

## Overview

This workflow guides you through extracting distributor claim data from the Google Drive archive, validating column mappings for specific chains (Trent, Guardian, WH Smith, etc.), pre-aggregating at the CM2 hierarchy, and integrating into the authoritative `data_master.json`.

**File Size Optimization:**
- **Raw Input:** 200MB+ transaction-level claim files
- **Compressed Output:** <5 MB aggregated master (98% reduction)
- **Preserved Granularity:** Chain × Brand × Category × Subcategory × Article × Month

---

## Step 1: Download Raw Files from Google Drive

1. Navigate to: [Distributor Claims Google Drive Folder](https://drive.google.com/drive/folders/1Y0HVY5r_qv1UFGJFsqm7IIyRdFPZSk8j?usp=sharing)
2. Download all `.csv` and `.xlsx` files
3. Extract any `.zip` archives locally
4. Create the staging directory and place files:
   ```bash
   mkdir -p data_sources/raw_large_claims
   # Copy all downloaded claim files here
   ```

5. Add raw files to `.gitignore` (they are too large for Git):
   ```bash
   echo "data_sources/raw_large_claims/" >> .gitignore
   ```

---

## Step 2: Inspect Column Mappings & Chain Distribution

**Purpose:** Preview how specific distributors/chains are mapped before full aggregation.

### Command Syntax

```bash
# Inspect all files and show column mappings
python scripts/inspect_claims_columns.py

# Inspect a specific file
python scripts/inspect_claims_columns.py --file "credit_notes_jul26.csv"

# Show sample records for a specific chain
python scripts/inspect_claims_columns.py --chain "Trent"

# Show sample records for Guardian distributor
python scripts/inspect_claims_columns.py --chain "Guardian"

# Show all chains and claim distribution
python scripts/inspect_claims_columns.py --all-chains

# Show more sample rows (default: 5)
python scripts/inspect_claims_columns.py --sample-rows 20
```

### Example Output

```
================================================================================
🔍 DISTRIBUTOR CLAIMS COLUMN INSPECTION & MAPPING PREVIEW
================================================================================

✅ FILE: credit_notes_jul26.csv
  ✓ distributor_id    ← 'DIST_CODE'
  ✓ claim_id          ← 'CLAIM_NO'
  ✓ claim_date        ← 'DATE'
  ✓ claim_amount      ← 'SETTLED_AMT'
  ✓ chain             ← 'CHAIN_NAME'
  ✓ zone              ← 'REGION'
  ✓ brand             ← 'BRAND'
  ✓ category          ← 'CATEGORY'
  ✓ expense_type      ← 'SCHEME_TYPE'

CHAIN × DISTRIBUTOR DISTRIBUTION:
Chain               Distributor_ID  Total_Claim_Amount  Claim_Count
Trent               TRE001          ₹45,230,000         260
Guardian            GUA001          ₹38,450,000         485
WH Smith            WHS001          ₹22,100,000         180
...
```

### What to Look For

1. **Column Mapping Status:**
   - ✅ All required columns found? (distributor_id, claim_id, claim_amount, chain, brand)
   - ⚠️ Any missing fields? (Will show in output)

2. **Chain Totals:**
   - Verify Trent, Guardian, WH Smith claim values match your finance ledgers
   - Check for data entry errors (negative amounts, null chains, zero claims)

3. **Sample Records:**
   - Spot-check a few transactions for accuracy
   - Verify Brand × Category breakdown looks reasonable

---

## Step 3: Fix Column Mappings (if needed)

If the inspection shows column mismatches, edit the script:

**File:** `scripts/compress_and_aggregate_claims.py`

Locate the `COLUMN_ALIASES` dictionary and add your column names:

```python
COLUMN_ALIASES = {
    "claim_amount": ["claim_amount", "amount", "claim_val", "settled_value", 
                     "claim_amt", "val_inr", "settled_amt", "YOUR_COLUMN_NAME"],
    "chain": ["chain", "account", "customer_name", "retailer", "key_account", 
              "customer", "YOUR_CHAIN_COLUMN"],
    # ... etc
}
```

Re-run inspection to verify mappings are fixed.

---

## Step 4: Run Local Pre-Aggregation & Compression

**Purpose:** Aggregate raw transaction data to CM2 hierarchy (Chain × Brand × Category × Article × Month) and compress to Git-ready files.

### Run the Aggregation Script

```bash
python scripts/compress_and_aggregate_claims.py
```

### Output

The script produces two files in `data_sources/distributor_claims/`:

1. **`distributor_claims_aggregated_master.csv`** (~2-5 MB)
   - Aggregated grain-level data ready for data_master.json integration
   - Columns: fiscal_year, month, chain, zone, brand, category, subcategory, article_code, expense_type, total_claim_amount, transaction_count, unique_claim_ids
   - Sorted by total_claim_amount (descending)

2. **`distributor_claims_quarantine_audit.csv`** (~0.5-1 MB)
   - Records that failed validation (nulls, non-positive amounts, missing dimensions)
   - Flagged with quarantine_reason for manual review
   - Columns: [all original + quarantine_reason]

### Example Output Log

```
================================================================================
🚀 DISTRIBUTOR CLAIMS PRE-AGGREGATION & COMPRESSION
================================================================================
Input Directory: /path/to/data_sources/raw_large_claims
Output Directory: /path/to/data_sources/distributor_claims
Files to Process: 3

📂 Processing: credit_notes_jul26.csv
  ✓ Processed 100,000 rows...
  ✓ Processed 200,000 rows...
  ✅ Aggregated to 8,450 grain-level rows

📂 Processing: debit_notes_jul26.csv
  ✓ Processed 100,000 rows...
  ✅ Aggregated to 3,220 grain-level rows

========================================
✅ COMPRESSION COMPLETE
========================================

Raw Ingestion Summary:
  Total Valid Records: 343,691
  Total Quarantine Records: 5,230

Output Files:
  1. distributor_claims_aggregated_master.csv (4.2 MB) ← Use for data_master.json
  2. distributor_claims_quarantine_audit.csv (0.8 MB) ← Review manually
```

---

## Step 5: Review Quarantine & Reconcile Disputes

Open `data_sources/distributor_claims/distributor_claims_quarantine_audit.csv` and review:

1. **Null Claim Amounts:** May indicate data entry errors; escalate for correction
2. **Non-Positive Amounts:** Reversal/credit notes; flag for manual classification
3. **Missing Chain:** Unmapped retailers; add to master account list
4. **Missing Brand:** SKU mapping gaps; resolve with supply chain team

**Action Items:**
- ✅ Correct obvious data entry errors
- ✅ Reclassify reversals and credits
- ⚠️ Flag genuinely disputed records for finance review
- ❌ Do NOT delete quarantine records (maintain audit trail)

---

## Step 6: Commit & Push to Repository

Once you've validated the aggregated master and reviewed quarantine:

```bash
# Stage the compressed claim files
git add data_sources/distributor_claims/

# Commit with clear message
git commit -m "feat(claims): add pre-aggregated distributor claims FY25-FY27

- credit_notes_jul26.csv + debit_notes_jul26.csv compressed to master aggregates
- 343,691 raw transactions → 11,670 grain-level nodes (Chain×Brand×Category×Article×Month)
- Trent: ₹45.2 Cr | Guardian: ₹38.5 Cr | WH Smith: ₹22.1 Cr (Jul '26)
- Quarantine audit: 5,230 records flagged for manual review
- Ready for data_master.json integration"

# Push to feature branch
git push origin claude/power-bi-data-analysis-f1vggw
```

---

## Step 7: Integration & Reconciliation (Agent-Driven)

Once files are pushed, the **Claims Reconciliation Sub-Agent** will:

### Phase 1: Three-Way Matching
- ✅ Reconcile claim submissions against approved trade scheme grids
- ✅ Match against verified primary invoice volumes
- ✅ Cross-check with secondary off-take pull data
- ✅ Detect duplicate claim IDs (same invoice claimed twice)

### Phase 2: Root Cause Analysis (RCA)
- ✅ Trace why Trent/Guardian/WH Smith were omitted from legacy snapshots
- ✅ Document ₹5.30 Cr variance root cause (estimation vs. actuals)
- ✅ Enforce permanent CI/CD controls (pre-commit hook + GitHub Actions)

### Phase 3: CM2 & Trade Spend ROI Calculation
- ✅ Allocate verified claims across hierarchy
- ✅ Compute: Gross Revenue → CM1 → Direct Costs → CM2 (₹ & %)
- ✅ Calculate Trade Spend ROI = Incremental Margin / Total Trade Spend Claimed
- ✅ Generate Month-over-Month trend analysis

### Phase 4: Integration into data_master.json
- ✅ Merge reconciled claims under `distributor_claims_cm2_granular` collection
- ✅ Maintain LOCKED_MULTI_YEAR_V2 status with governance audit trail
- ✅ Run `scripts/sync_data_js.py` to regenerate `dashboard/data.js`
- ✅ Validate CI/CD pipeline (`.github/workflows/validate-data.yml`)

### Deliverables Generated

1. **RCA Briefing Document**
   - Historical error analysis (omissions, overstatements)
   - Permanent preventative controls

2. **Claim Reconciliation Ledger**
   - Matched vs. Quarantined vs. Disputed breakdown
   - Distributor recovery amounts (if any)

3. **CM2 & ROI Performance Matrix**
   - Multi-level hierarchy: Chain | Brand | Category | Subcategory | Article
   - Metrics: Gross Sales | Trade Spend | CM2 Value | CM2 % | Spend ROI
   - Month-over-Month trends with margin driver commentary

4. **Updated data_master.json**
   - Verified claims integrated under new collection
   - Full audit trail maintained in governance_audit_ledger.json
   - Production-ready for dashboard deployment

---

## Expected Column Schema (Reference)

### Input Raw Files (Example)

```
DIST_CODE, CLAIM_NO, DATE, SETTLED_AMT, CHAIN_NAME, REGION, BRAND, CATEGORY, SCHEME_TYPE, SUBCATEGORY, ARTICLE_ID
TRE001, CLM-000123, 2026-07-15, 250000, Trent, North, Mamaearth, Body Care, TPR_Summer, Lotion, MM-BC-LOT-001
```

### Output Aggregated Master

```
fiscal_year, month, chain, zone, brand, category, subcategory, article_code, expense_type, total_claim_amount, transaction_count, unique_claim_ids
FY27, Jul-26, Trent, North, Mamaearth, Body Care, Lotion, MM-BC-LOT-001, TPR_Summer, 2500000, 45, 12
```

### CM2 Hierarchy (Dashboard-Ready)

```
Chain | Brand | Category | Subcategory | Article | Month | Gross_Sales | Trade_Spend | CM1 | Direct_Costs | CM2_Value | CM2_% | Spend_ROI
Trent | Mamaearth | Body Care | Lotion | MM-BC-LOT-001 | Jul-26 | 50000000 | 2500000 | 47500000 | 5000000 | 42500000 | 85% | 1.7x
```

---

## Troubleshooting

### "No CSV or Excel files found in data_sources/raw_large_claims"
- ✓ Verify directory exists: `ls -la data_sources/raw_large_claims/`
- ✓ Check file extensions are `.csv`, `.xlsx`, or `.xls`
- ✓ Ensure files are not in a subdirectory (move to root of raw_large_claims/)

### "Missing mandatory fields: distributor_id, claim_id"
- ✓ Update `COLUMN_ALIASES` in `compress_and_aggregate_claims.py`
- ✓ Run `inspect_claims_columns.py` first to see actual column names
- ✓ Add your column name to the aliases list

### "Quarantine audit shows 50% of records flagged"
- ✓ Check for data quality issues in source export
- ✓ Verify finance team provided complete/finalized claim ledger
- ✓ Review quarantine_reason breakdown for patterns
- ✓ Escalate to finance if systematic issues found

### File sizes still >100 MB
- ✓ Ensure `compress_and_aggregate_claims.py` completed successfully
- ✓ Check that output file is `distributor_claims_aggregated_master.csv` (not raw input)
- ✓ If still large, may need additional filtering (contact agent)

---

## Key Metrics & Success Criteria

| Metric | Target | Status |
|--------|--------|--------|
| Raw transaction records processed | 300,000+ | ✅ Track during aggregation |
| Output file size | <5 MB | ✅ Check after compression |
| Trent Jul'26 value reconciliation | ±2% vs finance | ⏳ Validate post-aggregation |
| Guardian Jul'26 value reconciliation | ±2% vs finance | ⏳ Validate post-aggregation |
| WH Smith Jul'26 value reconciliation | ±2% vs finance | ⏳ Validate post-aggregation |
| Quarantine rate | <5% (data quality) | ⏳ Monitor during aggregation |
| CM2 Margin calculation variance | 0.00% | ✅ Validated in agent phase |

---

## Next Checkpoint

✅ **After Step 6 (Commit & Push):**

Message the agent: *"Distributor claim files pushed. Ready for RCA & CM2 reconciliation."*

The agent will spawn the Claims Reconciliation Sub-Agent to:
1. Perform three-way matching
2. Conduct root cause analysis
3. Calculate CM2 and Trade Spend ROI
4. Integrate into data_master.json
5. Generate executive deliverables

---

**Document Version:** 1.0  
**Last Updated:** 2026-08-25  
**Branch:** `claude/power-bi-data-analysis-f1vggw`  
**Status:** Pipeline Ready for Data Ingestion
