# Monthly Offtake Refresh Procedure
## MT Dashboard v1.1.0

**Frequency:** Monthly (typically first week of the month)  
**Duration:** 15–30 minutes (including validation + deployment)  
**Owner:** Data Pipeline Operator  
**Last Updated:** 2026-09-04

---

## Overview

This procedure updates the MT Dashboard with the latest monthly store×article offtake data. The refresh:
- **Merges** new monthly CSV/XLSB files into the existing `data.js`
- **Recalculates** insights and RAG thresholds for the new month
- **Validates** data integrity (schema, ranges, baselines preserved)
- **Deploys** automatically via CI/CD (no manual steps after push)
- **Preserves** all FY25/FY26 historical data (idempotent, no double-counting)

**Key Property:** Fully idempotent — re-running with the same files produces identical results. Safe to retry on failure.

---

## PRE-FLIGHT CHECKLIST (Day 1 of Month)

- [ ] Confirm monthly offtake files have arrived in `PowerBI/RawDataFolders/offtake_monthly/`
  - Check with Data/BI team: "Are store×article offtake CSVs for [month] ready?"
  - Expected format: `.xlsb` or `.xlsx` (one file per month or one file per chain)
  - Count: typically 6–12 files (one per zone or chain grouping)
- [ ] Verify local git working tree is clean: `git status`
- [ ] Confirm you're on `main` branch: `git branch`
- [ ] Pull latest code: `git pull origin main`
- [ ] Check that CI/CD passed on the latest main commit
  - Visit: https://github.com/aswalsheshant-cell/mt-dashboard/actions
  - Look for **validate** and **deploy-pages** (both should show ✓ green)

---

## EXECUTION STEPS

### Step 1: Verify Source Files
```bash
# Count offtake files
ls -lh PowerBI/RawDataFolders/offtake_monthly/*.xlsb 2>/dev/null | wc -l

# If no .xlsb files, check for .xlsx
ls -lh PowerBI/RawDataFolders/offtake_monthly/*.xlsx 2>/dev/null | wc -l

# List all files (confirm they're recent)
ls -lht PowerBI/RawDataFolders/offtake_monthly/ | head -20
```

**Expected outcome:** 6+ files with today's or yesterday's timestamp.  
**If missing:** Stop. Contact Data team: "Offtake files not yet uploaded to offtake_monthly/"

---

### Step 2: Backup Current Data
```bash
# Create a timestamped backup of current data.js
cp dashboard/data.js dashboard/data.js.backup.$(date +%Y%m%d_%H%M%S)

# Verify backup was created
ls -lh dashboard/data.js.backup.*  | head -3
```

**Why:** Allows quick rollback if the rebuild has issues.

---

### Step 3: Run Offtake Patch
```bash
# Navigate to repo root (if not already there)
cd /home/user/mt-dashboard

# Run the idempotent offtake-patch rebuild
python3 scripts/build_dashboard_data.py \
  --offtake-patch \
  --src PowerBI/RawDataFolders/offtake_monthly \
  --out dashboard/data.js

# Expected output:
# ✓ Loading [month] data...
# ✓ Merged XXX rows
# ✓ Recalculated insights for FY27
# ✓ data.js regenerated (~9 MB)
```

**Success indicator:** Script completes with ✓ marks, no errors.  
**Common issues:**
- `FileNotFoundError`: Check file path in PowerBI/RawDataFolders/offtake_monthly/
- `KeyError: 'fy_tag'`: File format mismatch — confirm CSV has required columns
- `ValueError: duplicate rows`: Rare; usually means file was processed twice (use `--offtake-patch` to clean)

---

### Step 4: Validate Data Integrity
```bash
# Run schema + baseline validation
python3 tests/validate_data_integrity.py dashboard/data.js

# Expected output:
# ✓ FY25 baseline: ₹32,900.36L ± 0.1%
# ✓ FY26 baseline: ₹32,900.36L ± 0.1%
# ✓ 55 chains present
# ✓ 6 zones verified
# ✓ No NaN/null in required fields
# ✓ Offtake rows: [count] across [N] months
```

**Success criteria:**
- All ✓ marks present
- FY25/FY26 baselines within ±0.1%
- 55 chains, 6 zones confirmed
- Zero NaN/null warnings

**If validation fails:**
- Read the error message carefully
- If it's a baseline drift (e.g., FY26 ±0.5%): likely data source issue, contact Data team
- If it's a schema error (missing column): file format issue, verify with source
- **Rollback:** `mv dashboard/data.js.backup.[timestamp] dashboard/data.js` and report the issue

---

### Step 5: Commit and Push
```bash
# Check diff to confirm changes are reasonable
git diff dashboard/data.js | head -50

# Stage the updated data.js
git add dashboard/data.js

# Commit with month identifier (e.g., Sep-26, Oct-26)
git commit -m "data(offtake): refresh monthly patch Sep-26

Merged 8 monthly offtake files covering 426 stores, 3,800+ articles.
RAG thresholds recalculated. Insights updated for FY27.
Baselines (FY25/FY26) preserved, no breaking changes.

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

# Push to main (CI/CD will validate + deploy automatically)
git push origin main
```

**Expected:** Push succeeds with no auth errors.  
**If push fails:** See Troubleshooting section below.

---

### Step 6: Monitor CI/CD Deployment

**Automated:** CI/CD workflows run automatically after push. You don't need to trigger anything.

**Monitor progress:**
```bash
# Option A: Watch in terminal
watch -n 10 'git log main -1 --format="%h %ai %s" && \
  echo "---" && \
  curl -s "https://github.com/aswalsheshant-cell/mt-dashboard/actions" | grep -o "validate\|deploy-pages" | head -2'

# Option B: Manual check every 2 minutes
# Visit: https://github.com/aswalsheshant-cell/mt-dashboard/actions
# Look for the latest workflow run matching your commit message
# Expected status: validate ✓ → ui-smoke ✓ → deploy-pages ✓
```

**Timeline:**
- T+0s: Push completes
- T+10s: GitHub detects main push, triggers workflows
- T+30s: validate.yml starts (Python syntax, JSON schema checks)
- T+60s: ui-smoke.yml starts (Playwright 52-state test matrix)
- T+120s: deploy-pages.yml starts (copy to gh-pages branch)
- T+150s: All complete, dashboard updated on GitHub Pages

---

### Step 7: Verify Live Dashboard Update

```bash
# Wait ~2 minutes for CI to complete, then:

# Option A: Check GitHub Pages files
git log origin/gh-pages -1 --format="%h %ai %s"
# Expected: Should match your commit timestamp (within ~2 min)

# Option B: Check file size (data.js should be ~9 MB)
curl -sI https://aswalsheshant-cell.github.io/mt-dashboard/data.js 2>/dev/null | grep Content-Length

# Option C: Manual verification (in a browser)
# 1. Open: https://aswalsheshant-cell.github.io/mt-dashboard/
# 2. Check FY dropdown: should show FY27 if applicable
# 3. Navigate Insights & Way Forward → check Alert Center for latest month
# 4. Verify no red NaN/undefined values on any tab
```

**Success:** Dashboard loads, shows new month data, no JS errors in console.

---

## POST-DEPLOYMENT CHECKLIST

- [ ] CI workflows all passed (validate, ui-smoke, deploy-pages) — check Actions tab
- [ ] Live dashboard loads without errors
- [ ] FY dropdown includes latest FY if new (e.g., FY27 for Apr-26+ months)
- [ ] Insights & Way Forward tab shows new month insights + RAG alerts
- [ ] At least one chart updated (e.g., Primary Sales shows new month)
- [ ] No NaN/undefined visible in rendered output
- [ ] FY25/FY26 numbers unchanged from prior refresh (baseline preserved)

---

## CLEAN UP

```bash
# Delete old backup files after 7 days
find dashboard/data.js.backup.* -mtime +7 -delete

# Verify cleanup
ls -lh dashboard/data.js.backup.* 2>/dev/null || echo "No backups older than 7 days"
```

---

## TROUBLESHOOTING

### Push fails with "403 Forbidden"
**Cause:** Network/proxy policy blocking GitHub push.  
**Action:**
1. Wait 5 minutes (may be temporary policy sync)
2. Try again: `git push origin main`
3. If still blocked, contact your network/proxy admin
4. **Do not attempt to bypass** (e.g., unset HTTPS_PROXY) — this is a policy issue

### CI workflow fails (validate or ui-smoke)
**Action:**
1. Open the failed workflow in GitHub Actions
2. Read the error message in the job logs
3. Common causes:
   - **Schema error:** Offtake file missing required column (e.g., `store_id`, `article_code`, `quantity`)
   - **Duplicate rows:** Same store×article×month appears twice — use `--offtake-patch` to clean
   - **Baseline drift >0.1%:** Data source issue; contact Data team
4. **Recovery:**
   - Rollback: `git revert HEAD --no-edit && git push origin main`
   - Fix the issue with Data team (e.g., re-export file with correct columns)
   - Retry the monthly refresh

### Baseline (FY25/FY26) drifted after refresh
**Cause:** Offtake patch may have affected prior FYs (should not happen, but worth investigating).  
**Action:**
1. Check the drift percentage: `python tests/validate_data_integrity.py dashboard/data.js`
2. If drift >0.1%, compare the data.js blocks:
   ```bash
   git show HEAD~1:dashboard/data.js | grep -A5 '"FY26":' > /tmp/old_fy26.txt
   cat dashboard/data.js | grep -A5 '"FY26":' > /tmp/new_fy26.txt
   diff /tmp/old_fy26.txt /tmp/new_fy26.txt | head -20
   ```
3. If there are changes to FY25/FY26, rollback and investigate:
   ```bash
   git revert HEAD --no-edit && git push origin main
   ```
4. Report to Data team: "Offtake patch inadvertently modified FY25/FY26 block"

### data.js file is much larger than expected (>15 MB)
**Cause:** May have accidentally included duplicate FYs or extra data.  
**Action:**
1. Rollback: `git revert HEAD && git push origin main`
2. Delete the backup and start fresh:
   ```bash
   rm dashboard/data.js.backup.*
   ```
3. Verify source files are in the correct directory:
   ```bash
   ls PowerBI/RawDataFolders/offtake_monthly/ | wc -l
   ```
4. Retry the monthly refresh

### Dashboard shows old data even after deployment
**Cause:** Browser cache.  
**Action:**
1. Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. Clear browser cache (DevTools → Application → Storage → Clear site data)
3. Wait 60 seconds for CloudFront cache invalidation (GitHub Pages uses CDN)

---

## MONTHLY CADENCE CHECKLIST

Use this checklist to track monthly refreshes:

| Month | Files Received | Refresh Date | CI Status | Insights Updated | Owner | Notes |
|-------|--------|--------------|-----------|------------------|-------|-------|
| Sep-26 | ✓ 8 files | 2026-09-04 | ✓ Pass | ✓ FY27 | [Name] | Initial Phase 4 deploy |
| Oct-26 | [ ] | [ ] | [ ] | [ ] | [ ] | |
| Nov-26 | [ ] | [ ] | [ ] | [ ] | [ ] | |
| Dec-26 | [ ] | [ ] | [ ] | [ ] | [ ] | |

---

## ESCALATION & SUPPORT

**Data Quality Issues** (duplicates, missing columns, baseline drift)  
→ Contact Data/BI Team  
→ Share error message + data.js diff

**CI/CD Failures** (validate or deploy steps failing)  
→ Check GitHub Actions logs: https://github.com/aswalsheshant-cell/mt-dashboard/actions  
→ If unresolved, share error + commit SHA

**Network/Push Issues** (403 Forbidden, connection reset)  
→ Not a blocker — likely temporary network policy  
→ Retry in 5 minutes  
→ If persistent, report to infrastructure team

**Dashboard Display Issues** (NaN, undefined, missing data)  
→ Hard refresh browser (`Ctrl+Shift+R`)  
→ Clear cache and retry  
→ If still broken, verify step 7 (CI/CD) completed successfully

**Questions or Improvements**  
→ Review the RUNBOOK.md section 3 for additional details  
→ Consult PHASE_4_COMPLETION.txt for architectural context

---

## TIME LOG TEMPLATE

When running this procedure, record timing for operational insights:

```
Monthly Refresh Log — [Month] [Year]

Start Time: [HH:MM UTC]
Step 1 (Verify files): __ min
Step 2 (Backup): __ min
Step 3 (Offtake patch): __ min
Step 4 (Validate): __ min
Step 5 (Commit+Push): __ min
Step 6 (Monitor CI): __ min
Step 7 (Verify live): __ min

Total Duration: __ min
End Time: [HH:MM UTC]
Issues Encountered: [None / describe]
Owner: [Name]
```

---

**Ready for monthly operations. Dashboard is production-ready and fully automated.**

