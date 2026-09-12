#!/bin/bash
# Distributor Claims Ingestion Quick Start Guide
# Copy-paste commands in order; uncomment as you complete each step

echo "======================================================================"
echo "DISTRIBUTOR CLAIMS INGESTION - QUICK START"
echo "======================================================================"
echo ""
echo "Prerequisites:"
echo "  1. Download raw claim files from Google Drive"
echo "  2. Extract any .zip archives"
echo "  3. Create data_sources/raw_large_claims/ and place files inside"
echo ""
echo "======================================================================"
echo ""

# Step 1: Create directories
echo "STEP 1: Create staging directory"
echo "$ mkdir -p data_sources/raw_large_claims"
# mkdir -p data_sources/raw_large_claims

echo ""
echo "STEP 2: Add raw_large_claims to .gitignore (prevent Git push of 200MB+ files)"
echo "$ echo 'data_sources/raw_large_claims/' >> .gitignore"
# echo "data_sources/raw_large_claims/" >> .gitignore

echo ""
echo "======================================================================"
echo "INSPECTION PHASE (Run these BEFORE full aggregation)"
echo "======================================================================"
echo ""

echo "STEP 3a: Inspect all files and show column mappings"
echo "$ python scripts/inspect_claims_columns.py"
# python scripts/inspect_claims_columns.py

echo ""
echo "STEP 3b: Preview specific chain - TRENT"
echo "$ python scripts/inspect_claims_columns.py --chain 'Trent'"
# python scripts/inspect_claims_columns.py --chain "Trent"

echo ""
echo "STEP 3c: Preview specific chain - GUARDIAN"
echo "$ python scripts/inspect_claims_columns.py --chain 'Guardian'"
# python scripts/inspect_claims_columns.py --chain "Guardian"

echo ""
echo "STEP 3d: Preview specific chain - WH SMITH"
echo "$ python scripts/inspect_claims_columns.py --chain 'WH Smith'"
# python scripts/inspect_claims_columns.py --chain "WH Smith"

echo ""
echo "STEP 3e: Show all chains and claim distribution"
echo "$ python scripts/inspect_claims_columns.py --all-chains"
# python scripts/inspect_claims_columns.py --all-chains

echo ""
echo "======================================================================"
echo "VALIDATION"
echo "======================================================================"
echo ""
echo "At this point, you should verify:"
echo "  ✓ All column mappings are correct (or update COLUMN_ALIASES in compress script)"
echo "  ✓ Trent, Guardian, WH Smith claim values match your finance ledgers (±5%)"
echo "  ✓ No suspicious null values or negative amounts in sample records"
echo ""
echo "If column mappings need fixing:"
echo "  1. Edit scripts/compress_and_aggregate_claims.py"
echo "  2. Update COLUMN_ALIASES dictionary with your actual column names"
echo "  3. Re-run inspection to verify"
echo ""

echo "======================================================================"
echo "AGGREGATION PHASE"
echo "======================================================================"
echo ""

echo "STEP 4: Run local pre-aggregation & compression"
echo "$ python scripts/compress_and_aggregate_claims.py"
# python scripts/compress_and_aggregate_claims.py

echo ""
echo "Expected outputs in data_sources/distributor_claims/:"
echo "  1. distributor_claims_aggregated_master.csv (~2-5 MB) ← Git-ready"
echo "  2. distributor_claims_quarantine_audit.csv (~0.5-1 MB) ← Review manually"
echo ""

echo "======================================================================"
echo "REVIEW & RECONCILIATION"
echo "======================================================================"
echo ""

echo "STEP 5: Review quarantine ledger"
echo "$ head -50 data_sources/distributor_claims/distributor_claims_quarantine_audit.csv"
# head -50 data_sources/distributor_claims/distributor_claims_quarantine_audit.csv

echo ""
echo "Fix any data quality issues found in quarantine audit:"
echo "  - Correct obvious data entry errors in source"
echo "  - Reclassify reversal/credit notes"
echo "  - Map unmapped chains to master account list"
echo "  - Flag genuinely disputed amounts for finance review"
echo ""

echo "STEP 6: Validate aggregated master against finance"
echo "$ wc -l data_sources/distributor_claims/distributor_claims_aggregated_master.csv"
# wc -l data_sources/distributor_claims/distributor_claims_aggregated_master.csv

echo "$ head -10 data_sources/distributor_claims/distributor_claims_aggregated_master.csv"
# head -10 data_sources/distributor_claims/distributor_claims_aggregated_master.csv

echo ""
echo "======================================================================"
echo "COMMIT & PUSH"
echo "======================================================================"
echo ""

echo "STEP 7: Stage validated claim files"
echo "$ git add data_sources/distributor_claims/"
# git add data_sources/distributor_claims/

echo ""
echo "$ git status"
# git status

echo ""
echo "STEP 8: Commit with descriptive message"
echo "$ git commit -m \"feat(claims): add pre-aggregated distributor claims FY25-FY27"
echo ""
echo "- Aggregated [N] raw transactions to [M] grain-level nodes (Chain×Brand×Category×Article×Month)"
echo "- Trent: ₹XX Cr | Guardian: ₹XX Cr | WH Smith: ₹XX Cr (Jul '26 baseline)"
echo "- Quarantine audit: [K] records flagged for manual review"
echo "- Ready for data_master.json integration\""

# git commit -m "feat(claims): add pre-aggregated distributor claims FY25-FY27"

echo ""
echo "STEP 9: Push to feature branch"
echo "$ git push origin claude/power-bi-data-analysis-f1vggw"
# git push origin claude/power-bi-data-analysis-f1vggw

echo ""
echo "======================================================================"
echo "✅ PHASE COMPLETE"
echo "======================================================================"
echo ""
echo "Next Steps:"
echo "1. Wait for CI/CD validation to pass (.github/workflows/validate-data.yml)"
echo "2. Message agent: 'Distributor claim files pushed. Ready for RCA & CM2.'"
echo "3. Agent will:"
echo "   - Perform three-way matching (scheme grids, invoice volumes, off-take)"
echo "   - Conduct root cause analysis (why omissions & overstatements occurred)"
echo "   - Calculate CM2 and Trade Spend ROI across hierarchy"
echo "   - Integrate into data_master.json"
echo "   - Regenerate dashboard/data.js"
echo "   - Generate executive RCA briefing & CM2 performance matrix"
echo ""
echo "======================================================================"
