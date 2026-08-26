# Central Zone Deployment Guide

## Status
Central Zone has been added as an official MT zone (sort order 7) with Madhya Pradesh and Chhattisgarh as constituent states. The zone is ready for production deployment.

## Pre-Deployment Checklist

### ✓ Completed
- [x] ZoneStateMaster.csv updated with Central zone entries (sort order 7)
- [x] Madhya Pradesh moved from West to Central
- [x] Chhattisgarh added to Central zone
- [x] Data pipeline canonicalization updated (build_dashboard_data.py)
- [x] DataDictionary.md and RefreshGuide.md updated with Central zone documentation
- [x] Central Zone Leadership Pack PowerPoint generator created (18 slides)
- [x] CI/CD pipeline configured to generate Central zone PPTX monthly
- [x] Zone canonicalization tests added and passing
- [x] MT channel reconciliation test integrated into workflow

### ⏳ Pending
- [ ] Source workbooks downloaded from Google Drive
- [ ] Full data.js regeneration (requires Primary FY-2024-26.xlsx, etc.)
- [ ] Dashboard deployed with Central zone data
- [ ] Monthly CI/CD runs to generate Central_Zone_Leadership_Pack_*.pptx
- [ ] Central zone reporting added to leadership review cadence

## Deployment Steps

### Step 1: Regenerate Dashboard Data (When Source Workbooks Available)

**Required files** (from Google Drive, not in repo):
- `Primary FY-2024-26.xlsx` — Row-level primary sell-in data
- `Chain Offtake Master.xlsx` — Chain & zone-wise sell-out pivots
- `Universe MT.xlsx` — Store universe and distribution footprint
- `Promo Master -MT.xlsx` — Promo and trade-spend calendar

**Run the build:**
```bash
# Download source workbooks to a local directory
mkdir -p ~/sources && cd ~/sources
# ... download files from Google Drive ...

# Generate updated data.js with Central zone
cd ~/mt-dashboard
python scripts/build_dashboard_data.py --src ~/sources --out dashboard/data.js

# Verify the build
python scripts/qc_dashboard.py --data dashboard/data.js
python scripts/mt_channel_reconciliation.py dashboard/data.js
```

**Expected results:**
- Central zone appears in all zone-level reporting
- Madhya Pradesh: ₹1.68 Cr primary, ₹1.54 Cr offtake, 91.7% conversion
- Chhattisgarh: ₹0.94 Cr primary, ₹0.58 Cr offtake, 61.7% conversion
- Zone total: ₹2.62 Cr primary, ₹2.12 Cr offtake, 80.9% conversion
- All FY25/FY26 figures unchanged (zone reassignment only)

### Step 2: Deploy Dashboard to GitHub Pages / Vercel

Once data.js is regenerated:

```bash
# Commit the regenerated data.js
git add dashboard/data.js
git commit -m "data: regenerate dashboard with Central zone data

Central zone now appears in all MT zone-level reporting.
Madhya Pradesh and Chhattisgarh are classified as Central zone.
All FY25/FY26 figures unchanged (zone reassignment only)."

# Push to main or your deployment branch
git push origin main
```

**Dashboard URL:** https://aswalsheshant-cell.github.io/mt-dashboard/  
(or your Vercel deployment)

**Verification:**
- Open dashboard in browser
- Navigate to each tab (Data Explorer, Overview, Primary, Offtake, etc.)
- Verify Central zone appears in zone filters, charts, and tables
- Spot-check a few zone-level figures against expected values

### Step 3: Configure Monthly CI/CD Generation

The Central Zone Leadership Pack PPTX is now generated automatically on every push to the `scripts/` or `PowerBI/SeedData/` directories.

**Monthly generation workflow:**
1. `dataeng.yml` runs on every push
2. Generates `Central_Zone_Leadership_Pack_Jul26.pptx` (or current month)
3. Uploads as artifact (90-day retention)
4. Artifact available in GitHub Actions UI

**To manually trigger:**
```bash
# Option 1: Generate locally
node scripts/build_central_zone_presentation.js
# Output: Central_Zone_Leadership_Pack_Jul26.pptx

# Option 2: Force CI run
git commit --allow-empty -m "chore: trigger Central zone generation"
git push origin main
# Then download artifact from GitHub Actions
```

### Step 4: Add Central Zone to Leadership Reporting Calendar

**Monthly deliverables:**
- Main MT Command Centre PowerPoint (existing)
- Central Zone Leadership Pack (new, 18 slides)
- Q1/Q2/Q3/Q4 zone deep-dives as needed

**Distribution:**
- Central Zone Leadership Pack → Central RKAM, Zone Head, NKAM stakeholders
- Send alongside main MT pack in weekly/monthly reviews
- Use Central zone data for exception reporting only (below ₹0.25 Cr materiality floor)

**Governance:**
- Report Central by exception only in weekly reviews (zone is healthy)
- Monthly pack generated automatically via CI/CD
- Quarterly governance review: verify zone classification, reconciliation, and data quality

## Data Validation

### Zone Canonicalization Tests
```bash
pytest scripts/test_pipeline.py::TestCanonZone -v
```

Expected passing tests:
- ✓ canon_zone("central") == "Central"
- ✓ canon_zone("CENTRAL") == "Central"
- ✓ canon_zone("pan india") == "Pan India"

### MT Channel Reconciliation
```bash
python scripts/mt_channel_reconciliation.py dashboard/data.js
```

Expected: All checks PASS
- Zone sales exclude eB2B and SIS channels
- National MT = sum of six MT zones + Central zone
- Channel separation verified at month-level

### QC Gate
```bash
python scripts/qc_dashboard.py --data dashboard/data.js
```

Expected: All checks ✓ PASS (or ⊘ BLOCKED with documented reason)

## Rollback Plan

If issues arise after deployment:

1. **Data issues:** Revert data.js to previous version
   ```bash
   git revert <commit-hash>
   git push
   ```

2. **Zone master issues:** Revert ZoneStateMaster.csv
   ```bash
   git revert <commit-hash>
   ```

3. **PowerPoint generator issues:** Disable in CI/CD workflow
   - Remove generation step from `.github/workflows/dataeng.yml`
   - Keep test/validation steps

## Success Criteria

✓ Central zone appears in dashboard (all tabs)  
✓ Central zone data matches expected figures (Q1 and July)  
✓ No regression in West, North, East, South-1, South-2 zone figures  
✓ Channel reconciliation passes (MT-only check)  
✓ Central Zone Leadership Pack generated monthly  
✓ Zone governance documented and in RefreshGuide.md  

## Support

**Questions?**
- Zone master issues: See `PowerBI/docs/RefreshGuide.md` § Zone Classification
- Dashboard issues: See `dashboard/README.md`
- PowerPoint generator: See `scripts/build_central_zone_presentation.js` (comments)
- Data pipeline: See `scripts/build_dashboard_data.py` (lines 125-137, zone canonicalization)

---
**Last Updated:** 2026-08-17  
**Prepared by:** Claude Code  
**Branch:** claude/data-analytics-learning-g8ggyw
