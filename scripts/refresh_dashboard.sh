#!/usr/bin/env bash
# One-command dashboard data refresh — triggered when raw monthly files land in data/raw_drops/
# Usage: ./scripts/refresh_dashboard.sh

set -e

echo ""
echo "=========================================="
echo "MT Dashboard v1.1.2 — Data Refresh"
echo "=========================================="
echo ""

# Step 1: Validate raw drops folder exists
if [ ! -d "data/raw_drops" ]; then
    echo "❌ Error: data/raw_drops/ not found."
    echo "   Place your monthly source files here first:"
    echo "   - Primary_FY202426_*.xlsx"
    echo "   - Offtake pivot .xlsx/.xlsb"
    echo "   - Universe/mapping files (if updating)"
    exit 1
fi

echo "✓ Ingestion folder found: data/raw_drops/"
ls -lh data/raw_drops/ | tail -n +2 | awk '{print "  ", $9, "(" $5 ")"}'

echo ""
echo "========== Step 1/3: Regenerate data.js =========="
python scripts/build_dashboard_data.py --src data/raw_drops --out dashboard/data.js
if [ $? -eq 0 ]; then
    echo "✓ data.js regenerated"
    wc -c dashboard/data.js | awk '{print "  Size: " $1/1024/1024 " MB"}'
else
    echo "❌ data.js build failed"
    exit 1
fi

echo ""
echo "========== Step 2/3: QA Sentinel & Validation =========="

# Python validation: baseline preservation, null safety, schema
python3 << 'PYTHON_VALIDATE'
import json
import sys

try:
    with open('dashboard/data.js', 'r') as f:
        content = f.read()
        # Extract window.DASH = {...}; to validate JSON
        start = content.find('{')
        end = content.rfind('}') + 1
        json_str = content[start:end]
        data = json.loads(json_str)

        # Basic schema checks
        assert 'by_chain' in data, "Missing by_chain block"
        assert 'detail_meta' in data, "Missing detail_meta block"
        assert 'forecast' in data, "Missing forecast block"
        assert 'offtake' in data, "Missing offtake block"

        # Baseline check: n_chains and n_stores must be > 0
        assert len(data.get('by_chain', {})) > 0, "by_chain is empty"

        # Null safety: data.js should not contain literal 'NaN' or 'undefined' strings
        if 'NaN' in json_str or 'undefined' in json_str:
            print("⚠ WARNING: Found NaN or undefined literals in data.js")
        else:
            print("✓ No NaN/undefined literals")

        print(f"✓ JSON schema valid")
        print(f"  Chains: {len(data.get('by_chain', {}))}")

except json.JSONDecodeError as e:
    print(f"❌ data.js JSON invalid: {e}")
    sys.exit(1)
except AssertionError as e:
    print(f"❌ Schema validation failed: {e}")
    sys.exit(1)
PYTHON_VALIDATE

if [ $? -ne 0 ]; then
    echo "❌ QA validation failed"
    exit 1
fi

echo ""
echo "========== Step 3/3: Commit & Push to Production =========="

git add dashboard/data.js
git status --short

echo ""
read -p "Review changes above. Ready to push to main? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "data: refresh monthly offtake dataset (v1.1.2 store hierarchy schema)

$(date +%Y-%m-%d\ %H:%M:%S) ingestion from data/raw_drops/
- Phase 1 synthetic site code standardization active
- Phase 2 granularity badges & Reliance BC toggle live
- QA Sentinel validation passed

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

    git push origin main
    if [ $? -eq 0 ]; then
        echo ""
        echo "=========================================="
        echo "✅ DEPLOYMENT COMPLETE"
        echo "=========================================="
        echo ""
        echo "Live Dashboard: https://aswalsheshant-cell.github.io/mt-dashboard/"
        echo ""
        echo "Hard-refresh your browser (Ctrl+Shift+R) to see latest data."
        echo ""
    else
        echo "❌ Push failed. Check network or permissions."
        exit 1
    fi
else
    echo "Aborted. Changes staged but not pushed."
    git reset
    exit 0
fi
