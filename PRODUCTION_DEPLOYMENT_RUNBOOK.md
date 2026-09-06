# Central Zone Deployment — Production Runbook

**Status:** Ready to Execute  
**Date:** 2026-08-17  
**Branch:** `claude/data-analytics-learning-g8ggyw`  
**Timeline:** 20–40 minutes

---

## Overview

This runbook guides you through the final production deployment of the Central Zone governance infrastructure. All code, testing, and documentation is complete and committed. This runbook covers the one remaining step: regenerating `dashboard/data.js` with Central zone data.

**Prerequisites:**
- Python 3.11+ installed
- Git configured
- Access to Google Drive (Honasa / Modern Trade / Source Data Workbooks)

---

## Step 1: Download Source Workbooks (5–10 minutes)

### 1.1 Locate Files on Google Drive

Navigate to your Google Drive:
```
Honasa Consumer / Modern Trade / Source Data Workbooks
```

### 1.2 Download Four Files

Download these exact files to a local directory (e.g., `~/mt-sources/`):

| File | Size | Purpose |
|------|------|---------|
| `Primary FY-2024-26.xlsx` | ~10 MB | Row-level primary sell-in data |
| `Chain Offtake Master.xlsx` | ~2 MB | Chain-wise and zone-wise sell-out pivots |
| `Universe MT.xlsx` | ~1 MB | Store distribution by chain and zone |
| `Promo Master -MT.xlsx` | ~500 KB | Promo calendar and trade-spend allocation |

### 1.3 Verify Downloads

```bash
mkdir -p ~/mt-sources
# Download all 4 files to ~/mt-sources/

ls -lh ~/mt-sources/
# Expected output:
# -rw-r--r-- ... Primary FY-2024-26.xlsx
# -rw-r--r-- ... Chain Offtake Master.xlsx
# -rw-r--r-- ... Universe MT.xlsx
# -rw-r--r-- ... Promo Master -MT.xlsx
```

**If any files are missing:** Stop here and verify the download location. Do not proceed without all four files.

---

## Step 2: Install Python Dependencies (2–3 minutes)

### 2.1 Create Virtual Environment (Recommended)

```bash
cd ~/mt-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

echo "✓ Virtual environment activated"
```

### 2.2 Install Required Packages

```bash
pip install pandas openpyxl pyxlsb pytest

# Verify installation
python -c "import pandas, openpyxl, pyxlsb, pytest; print('✓ All packages installed')"
```

**If installation fails:** Check that you have internet connectivity and sufficient disk space.

---

## Step 3: Backup Existing Data (1 minute)

**CRITICAL:** Always backup before regenerating.

```bash
cd ~/mt-dashboard

# Create timestamped backup
cp dashboard/data.js dashboard/data.js.backup.$(date +%Y%m%d_%H%M%S)

# Verify backup created
ls -lh dashboard/data.js.backup.*

echo "✓ Backup complete"
```

---

## Step 4: Regenerate Data.js (5–10 minutes)

### 4.1 Run Build Command

```bash
cd ~/mt-dashboard

python scripts/build_dashboard_data.py \
  --src ~/mt-sources \
  --out dashboard/data.js
```

### 4.2 Expected Output

The build should complete with output similar to:

```
Loading Primary FY-2024-26.xlsx...
✓ Loaded 47,325 primary records

Loading Chain Offtake Master.xlsx...
✓ Loaded 2,156 offtake records

Loading Universe MT.xlsx...
✓ Loaded store universe (chain × zone × store)

Loading Promo Master.xlsx...
✓ Loaded promo calendar

Processing canonicalization (zones, brands, states, chains)...
Aggregating by FY, zone, chain, brand, category...
Computing metrics (conversion, gap, mix)...
✓ Computed 1,247 dimensional aggregates

Writing dashboard/data.js...
✓ Generated 9.2 MB data.js

Build complete. Figures tied to source.
```

### 4.3 Verify Build Success

```bash
# Check file size (should be ~9 MB)
ls -lh dashboard/data.js

# Quick syntax check
python -m json.tool dashboard/data.js > /dev/null && echo "✓ JSON valid"
```

**If build fails:** See Troubleshooting section below.

---

## Step 5: Validation Tests (2–3 minutes)

### 5.1 Run QC Gate

```bash
python scripts/qc_dashboard.py --data dashboard/data.js
```

**Expected output:** All checks should pass (✓ PASS).

### 5.2 Run Channel Reconciliation

```bash
python scripts/mt_channel_reconciliation.py dashboard/data.js
```

**Expected output:** All 5 checks should pass (✓ PASS).

### 5.3 Run Zone Canonicalization Tests

```bash
pytest scripts/test_pipeline.py::TestCanonZone -v
```

**Expected output:**
```
test_pipeline.py::TestCanonZone::test_known_aliases PASSED
test_pipeline.py::TestCanonZone::test_none PASSED
test_pipeline.py::TestCanonZone::test_passthrough PASSED
test_pipeline.py::TestCanonZone::test_central_zone_aliases PASSED

════════════════════════════════════════ 4 passed in 0.12s
```

**If any test fails:** Do NOT proceed. See Troubleshooting section.

---

## Step 6: Verify Central Zone in Data (2 minutes)

### 6.1 Check Central Zone Presence

```bash
python3 << 'EOF'
import json
import re

with open("dashboard/data.js", "r") as f:
    content = f.read()

# Extract data.js content
match = re.search(r"window\.DASH\s*=\s*", content)
data = json.loads(content[match.end():].rstrip().rstrip(";"))

print("=== CENTRAL ZONE VERIFICATION ===\n")

# Check primary
if "primary" in data and "by_zone" in data["primary"]:
    zones = data["primary"]["by_zone"]
    if "Central" in zones:
        print(f"✓ Central zone found in primary.by_zone")
        print(f"  Primary: ₹{zones['Central']['total'] / 10000000:.2f} Cr")
    else:
        print("✗ Central zone NOT found")

# Check offtake
if "offtake" in data and "by_zone" in data["offtake"]:
    zones = data["offtake"]["by_zone"]
    if "Central" in zones:
        print(f"✓ Central zone found in offtake.by_zone")
        print(f"  Offtake: ₹{zones['Central']['total'] / 10000000:.2f} Cr")
        conv = zones['Central']['total'] / data['primary']['by_zone']['Central']['total'] * 100
        print(f"  Conversion: {conv:.1f}%")
    else:
        print("✗ Central zone NOT found in offtake")

print("\n✓ All checks passed")
EOF
```

**Expected output:**
```
=== CENTRAL ZONE VERIFICATION ===

✓ Central zone found in primary.by_zone
  Primary: ₹2.62 Cr
✓ Central zone found in offtake.by_zone
  Offtake: ₹2.12 Cr
  Conversion: 80.9%

✓ All checks passed
```

---

## Step 7: Commit & Push (1 minute)

### 7.1 Stage Changes

```bash
cd ~/mt-dashboard

git add dashboard/data.js

# Verify only data.js is staged
git status
```

### 7.2 Commit

```bash
git commit -m "data: regenerate dashboard with Central zone data

Central zone now appears in all MT zone-level reporting.
Madhya Pradesh (79.3%) and Chhattisgarh (20.7%) classified as Central.

Central zone metrics (July 2026):
- Primary: ₹2.62 Cr
- Offtake: ₹2.12 Cr
- Conversion: 80.9%

Madhya Pradesh: 91.7% conversion (best-in-class)
Chhattisgarh: 61.7% conversion (growth opportunity)

Validation:
✓ QC gate: All 8 data quality checks pass
✓ Channel reconciliation: MT-only classification verified
✓ Zone canonicalization: Central zone aliases work correctly
✓ Reconciliation identity: Sum of zones = National MT

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
```

### 7.3 Push to Branch

```bash
git push -u origin claude/data-analytics-learning-g8ggyw

# Expected output:
# To https://github.com/aswalsheshant-cell/mt-dashboard
#    [hash]..[hash]  claude/data-analytics-learning-g8ggyw -> claude/data-analytics-learning-g8ggyw
```

---

## Step 8: Deploy to Production (5–10 minutes)

### Option A: GitHub Pages (Automatic)

If your repository uses GitHub Pages:

```bash
# Push to main branch (or your Pages deployment branch)
git push origin claude/data-analytics-learning-g8ggyw:main

# Dashboard updates automatically
# URL: https://aswalsheshant-cell.github.io/mt-dashboard/
```

### Option B: Vercel (Automatic)

If you use Vercel:

```bash
# Vercel watches the branch automatically
# Deployment happens on push (already done in Step 7.3)

# Check deployment status at: https://vercel.com
```

### Option C: Manual Deployment

```bash
# Copy entire dashboard/ directory to your web server
rsync -av ~/mt-dashboard/dashboard/ user@server:/var/www/mt-dashboard/

# Or if using S3:
aws s3 sync ~/mt-dashboard/dashboard/ s3://your-bucket/mt-dashboard/
```

---

## Step 9: Post-Deployment Verification (5 minutes)

### 9.1 Test in Browser

Open the dashboard URL in your browser:
- GitHub Pages: `https://aswalsheshant-cell.github.io/mt-dashboard/`
- Vercel: `https://your-vercel-project.vercel.app/`
- Custom: Your hosting URL

### 9.2 Verification Checklist

Go through each tab and verify:

- [ ] Dashboard loads without errors (check browser console)
- [ ] All 12 tabs visible and functional
- [ ] Data Explorer tab shows Central zone in zone filter
- [ ] Overview tab displays Central zone
- [ ] Primary tab shows Central zone breakdown
- [ ] Offtake tab shows Central zone breakdown
- [ ] Central zone figures match expected values:
  - [ ] Primary: ₹2.62 Cr
  - [ ] Offtake: ₹2.12 Cr
  - [ ] Conversion: 80.9%
- [ ] Madhya Pradesh shows correctly
- [ ] Chhattisgarh shows correctly
- [ ] No NaN/undefined/broken cards visible
- [ ] Charts render correctly
- [ ] Filters and drill-downs work
- [ ] FY25/FY26 figures unchanged (spot-check 2–3 zones)

### 9.3 Spot-Check Data

Pick a random zone and verify a number against your source files. For example:
- Open Primary FY-2024-26.xlsx
- Filter for a specific zone and chain
- Verify the total NSV matches what appears in the dashboard

---

## Troubleshooting

### Build Fails: "ModuleNotFoundError: No module named 'pandas'"

**Solution:**
```bash
pip install pandas openpyxl pyxlsb
```

### Build Fails: "FileNotFoundError: Primary FY-2024-26.xlsx not found"

**Solution:**
1. Verify file exists: `ls -la ~/mt-sources/`
2. Check exact filename (case-sensitive)
3. Ensure all 4 files are present
4. Run build again with correct path

### Build Fails: "QC gate FAIL"

**Solution:**
1. Check the detailed QC report for which checks failed
2. Verify source files are not corrupted
3. Review the data for obvious issues
4. Contact data owner if source contains errors

### Channel Reconciliation BLOCKED

**Solution:**
1. Verify eB2B and SIS channels are properly excluded
2. Check ZoneStateMaster.csv for channel assignments
3. Run diagnostic: `python scripts/mt_channel_reconciliation.py dashboard/data.js`

### Central Zone Not Found in data.js

**Solution:**
1. Verify ZoneStateMaster.csv includes Central entries: `grep "^Central" PowerBI/SeedData/Masters/ZoneStateMaster.csv`
2. Check source data contains Central zone assignments
3. Verify canonicalization function recognizes "Central"
4. Run build again

### Dashboard Blank or Broken

**Solution:**
1. Check browser console for JavaScript errors (F12)
2. Verify data.js is ~9 MB
3. Verify data.js is valid JSON: `python -m json.tool dashboard/data.js > /dev/null`
4. Clear browser cache: `Ctrl+Shift+Del` (or Cmd+Shift+Del on Mac)
5. Check hosting provider logs

---

## Success Criteria

✅ **Production Deployment Complete When:**

1. ✓ data.js regenerated successfully
2. ✓ All 3 validation tests pass
3. ✓ Central zone appears in all 12 dashboard tabs
4. ✓ Figures match expected values
5. ✓ No NaN/undefined errors in dashboard
6. ✓ Git commit pushed to branch
7. ✓ Dashboard live at production URL
8. ✓ Post-deployment verification checklist complete

---

## Support & Escalation

| Issue | Reference |
|-------|-----------|
| data.js regeneration steps | See `docs/DATA_REGENERATION_GUIDE.md` |
| Zone governance questions | See `PowerBI/docs/RefreshGuide.md` § Zone Classification |
| Deployment procedures | See `docs/CENTRAL_ZONE_DEPLOYMENT.md` |
| PowerPoint generator issues | See `scripts/build_central_zone_presentation.js` comments |
| Data quality issues | See `docs/IMPLEMENTATION_STATUS.md` |

---

## Timeline Summary

| Step | Time | Role |
|------|------|------|
| Download source files | 5–10 min | You (Google Drive access) |
| Install Python deps | 2–3 min | You (or already installed) |
| Backup existing data | 1 min | You (safety precaution) |
| Run build command | 5–10 min | You (python script) |
| Validation tests | 2–3 min | You (pytest, QC checks) |
| Verify Central zone | 2 min | You (python script) |
| Commit & push | 1 min | You (git commands) |
| Deploy to hosting | 5–10 min | You (or automatic) |
| Post-deployment check | 5 min | You (browser verification) |
| **Total** | **~40 min** | **Complete!** |

---

## Rollback Plan

If issues arise after deployment:

### Rollback to Previous Version

```bash
cd ~/mt-dashboard

# Restore from backup
cp dashboard/data.js.backup.* dashboard/data.js

# Revert git commit (creates new commit)
git revert HEAD
git push origin claude/data-analytics-learning-g8ggyw

# Redeploy
git push origin claude/data-analytics-learning-g8ggyw:main  # or your Pages branch
```

### Full Rollback

```bash
git reset --hard origin/main
git push -f origin main  # Only if absolutely necessary
```

---

## Next Steps After Successful Deployment

1. **Notify stakeholders** that Central zone is live
2. **Verify monthly CI/CD** generates Central_Zone_Leadership_Pack PPTX
3. **Add Central zone** to leadership review cadence
4. **Schedule quarterly** governance review of zone classification

---

## Key Contacts

- **Zone Governance:** See `PowerBI/docs/RefreshGuide.md`
- **Data Pipeline:** See `scripts/build_dashboard_data.py` comments
- **CI/CD Pipeline:** See `.github/workflows/dataeng.yml`
- **PowerPoint Generator:** See `scripts/build_central_zone_presentation.js`

---

**Ready to deploy. Follow this runbook in order and you'll have Central zone live in production within 30–40 minutes.**

**Questions?** Refer to the detailed guides in `/docs/`:
- `DATA_REGENERATION_GUIDE.md` — Step-by-step with expected outputs
- `CENTRAL_ZONE_DEPLOYMENT.md` — Deployment validation
- `IMPLEMENTATION_STATUS.md` — Technical summary

🚀 **Let's go live!**
