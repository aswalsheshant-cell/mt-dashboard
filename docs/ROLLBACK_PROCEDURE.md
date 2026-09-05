# Release Rollback Procedure

**Document Version:** 1.0  
**Last Updated:** 2026-09-05  
**Audience:** DevOps, Analytics Engineers, On-Call Team  
**Purpose:** Rapid incident response to revert broken releases

---

## Executive Summary

This document outlines the step-by-step procedure to roll back a broken release of:
1. **Dashboard** (`data.js` in `dashboard/index.html`)
2. **Power BI Dataset** (PBIP published to Power BI Service)

**Rollback SLA:** 15 minutes to restored service (target)

---

## Pre-Rollback Checklist

Before initiating rollback, confirm:

- [ ] Is production impacted? (check dashboard uptime, user reports, service monitoring)
- [ ] Is the issue real, or intermittent? (test 2–3 times before rolling back)
- [ ] What's the last known good version? (check git log or PowerBI Service history)
- [ ] Who approved this rollback? (Product Manager, Analytics Lead)

---

## Dashboard Rollback (data.js)

### Scenario 1: NaN/Undefined in Production Dashboard

**Symptoms:**
- Dashboard tabs show "undefined" or "NaN" in metric cards
- Browser console shows JS errors: "Cannot read property 'offtake' of undefined"
- Specific tabs broken (e.g., Primary tab loads, Offtake tab blank)

**Diagnosis (2 minutes):**
```bash
# Check current version
git log --oneline -5

# Last good commit (example):
# abc1234 Validate FY26 baseline: NSV 2,347 Cr reconciled
# def5678 Refresh offtake patch: FY27 Q1 monthly data merged
# ghi9012 [BROKEN] Add new forecast block: NaN in some chains  ← Problem here

# Confirm the break
python -m json.tool dashboard/data.js | head -100
# If JSON is invalid, data.js is corrupted
```

### Rollback (5 minutes):

**Option A: Revert to Last Good Commit**
```bash
# Identify last good commit (check git log or ask team)
# Example: def5678 (Refresh offtake patch)

# Revert to that commit
git revert def5678 --no-edit
# OR (more aggressive, if time is critical)
git reset --hard def5678

# Force push to main (WARNING: only with permission)
git push --force-with-lease origin main

# Verify:
# - Go to GitHub Pages dashboard URL
# - Refresh (Ctrl+Shift+R, hard refresh to clear cache)
# - Check: metrics show numbers, no NaN, no JS errors
# - Timestamp in footer shows old date (expected)
```

**Option B: Restore from Backup**
```bash
# If git history is unavailable (rare):
# Restore data.js from previous night's backup

# On-call team has backup: /backup/data.js-[YYYYMMDD-HHMMSS]
cp /backup/data.js-20260904-000000 dashboard/data.js
git add dashboard/data.js
git commit -m "Emergency rollback: data.js restored from backup

Incident: Dashboard showed NaN in Primary tab after [broken commit hash]
Action: Restored from previous day's backup (20260904 00:00)

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

git push origin main
```

### Post-Rollback (5 minutes):

1. **Verify dashboard is live**
   - Open dashboard URL
   - Test all 12 tabs, all 4 FY filters
   - No NaN, undefined, JS errors

2. **Notify stakeholders**
   ```
   Subject: Dashboard Incident - RESOLVED
   
   Dashboard experienced NaN errors from 14:00-14:15 UTC due to broken data.js.
   Status: Rolled back to working version. All metrics restored.
   Impact: None (internal use only; no user-facing impact)
   RCA: [Broken commit] introduced NaN in Primary calculations
   Fix: Will validate data.js QC checks before next release
   ```

3. **Start RCA (Root Cause Analysis)**
   - What change introduced the NaN?
   - Did build script validate JSON before pushing?
   - Why did it pass local testing but fail in production?
   - Update QC validation script to catch this in future

---

## Power BI Service Rollback (PBIP Dataset)

### Scenario 2: Dataset Refresh Fails / Measures Return Wrong Values

**Symptoms:**
- Power BI Service shows refresh failed
- Dataset measures show NaN or 0
- Report pages show "No data available"
- Refresh log shows error: "Illegal argument" or "Connection failed"

**Diagnosis (5 minutes):**
```powershell
# Power BI Service → Datasets → [Your Dataset] → Refresh History
# Check:
# - Last refresh status: Failed / Success
# - Error message: (e.g., "Cannot connect to data source")
# - Refresh duration: (longer than usual = potential issue)

# If error is data source related:
# → Check shared drive connectivity
# → Verify data source credentials

# If error is DAX related:
# → Check recent measure edits
# → Run Desktop validation (see below)
```

### Rollback (10 minutes):

**Option A: Republish Previous Desktop Version**

```powershell
# On Windows machine with Power BI Desktop:

# 1. Open previous good .pbix version
# File → Open → PBIP_Assembled_20260904.pbix
# (Verify: File modified date is before broken deployment)

# 2. Validate locally
# Home → Refresh (Ctrl+R)
# Expected: All queries load, no errors, measures calculate correctly

# 3. Republish to Service
# File → Publish → [Workspace] → Select dataset: 
#   "Overwrite existing 'PBIP_Assembled' dataset" → Yes

# 4. Wait for publish to complete (2–5 minutes)

# 5. Verify in Service
# Power BI Service → Datasets → [Dataset] → Refresh
# Check: Refresh succeeds, refresh duration normal

# 6. Check reports
# Power BI Service → Reports → [Report] → view
# Verify: Metrics show numbers, no errors
```

**Option B: Delete Broken Dataset & Republish**
```powershell
# If overwrite doesn't work (rare):

# 1. Delete broken dataset
# Power BI Service → Datasets → [Broken Dataset] → Delete
# (Warning: Deletes all reports built on this dataset)

# 2. Republish from Desktop
# File → Publish → [Workspace] → (new dataset name)

# 3. Recreate reports (or restore from template if available)
# File → Save As → PBIP_Restored_[Date].pbit
```

### Post-Rollback (5 minutes):

1. **Verify dataset is functional**
   - Refresh succeeds without errors
   - Test report shows correct metrics
   - Refresh schedule is still active (verify Settings)

2. **Notify BI users**
   ```
   Subject: Power BI Service — Incident Resolved
   
   Dataset refresh failed from 14:00-14:15 UTC due to measure validation error.
   Status: Rolled back to previous version (20260904 08:00 UTC).
   Action: All reports restored, refresh resumed on normal schedule.
   Impact: 15 minutes of stale data (last refresh before incident)
   RCA: [Measure name] had incorrect DAX syntax after recent edit
   ```

3. **Start RCA**
   - What measure change caused the failure?
   - Was the change tested in Desktop before publishing?
   - Add measure validation step to pre-publication checklist

---

## GitHub Pages Rollback (If Dashboard Not in Git)

**Scenario 3: GitHub Pages Dashboard is Live but Git History is Lost**

If `dashboard/index.html` is published directly to GitHub Pages but the git history is corrupted:

```bash
# 1. Check GitHub Pages history (in Settings)
# GitHub → Settings → Pages → View last deployment
# (GitHub keeps deployment history for ~6 months)

# 2. Find previous working version
# GitHub → Actions → Deployments → find last successful deployment

# 3. Re-download artifact from deployment
# (Or manually restore index.html from GitHub's revision history)

# 4. Commit restored version
git add dashboard/index.html
git commit -m "Emergency rollback: GitHub Pages restored from previous deployment"
git push origin main
```

---

## Checklist: Was Rollback Successful?

After rollback (any system), verify:

**Dashboard:**
- [ ] Dashboard loads (no 404)
- [ ] Data renders (no blank/error page)
- [ ] All 12 tabs accessible
- [ ] Metric cards show numbers (no NaN/undefined)
- [ ] Browser console clean (no JS errors)
- [ ] FY filter works (All / FY25 / FY26 / FY27)
- [ ] Data Explorer tab shows correct metrics

**Power BI:**
- [ ] Dataset refresh succeeds
- [ ] Refresh log shows no errors
- [ ] Test report loads
- [ ] Metric values match baseline (FY26 NSV = 2,347 Cr, etc.)
- [ ] Refresh schedule still active

---

## Post-Rollback: Next Steps

### 1. Incident Report (Due within 4 hours)

Template:
```
INCIDENT REPORT: [Release Date] Dashboard Rollback

Incident ID: INC-[YYYYMMDD-001]
Date/Time: 2026-09-05 14:00–14:15 UTC
Duration: 15 minutes
Status: RESOLVED

TIMELINE:
- 14:00 UTC: User reports NaN in Primary tab
- 14:02 UTC: Confirmed issue (data.js corrupted)
- 14:03 UTC: Initiated rollback to commit [abc1234]
- 14:08 UTC: Rollback complete, dashboard restored
- 14:10 UTC: All-clear verified

ROOT CAUSE:
[Describe the problem that caused the outage]

IMPACT:
- Systems: Dashboard, Power BI Service
- Users: 15 analysts affected
- Data exposure: None (internal tool)
- Duration: 15 minutes
- Business impact: Minimal (daily reporting, not critical path)

PREVENTATIVE ACTION:
[What will prevent this in the future?]
- Add QC validation step before pushing data.js
- Test Power Query connections before republishing PBIP
- etc.

OWNER: [Name]
```

### 2. Root Cause Analysis (RCA) — Due within 24 hours

Identify:
- What change introduced the bug?
- Why did it pass local testing?
- Why didn't CI/CD catch it?
- What process gap exists?

### 3. Update QC Validation

If the issue should have been caught by automated testing:
```bash
# Add a test to scripts/validate_dashboard_qc.py
# to catch this type of error in future

# Example:
def test_no_nan_in_chains_metrics():
    """Catch NaN in chain-level metrics before release"""
    for fy in FY_ALL:
        for chain in data['by_chain']:
            for metric in ['total', 'avg_price']:
                assert not isnan(data['by_chain'][chain][metric])
```

---

## Escalation Path

| Scenario | Action | Owner | SLA |
|----------|--------|-------|-----|
| Dashboard NaN | Rollback data.js | Analytics Engineer | 15 min |
| Power BI refresh fails | Republish PBIP | Analytics Engineer | 30 min |
| Multiple systems down | All-hands incident | VP Analytics | 10 min |
| Data loss concern | Restore from backup | IT / DBA | 1 hour |
| RCA update | Prevent future | Product/Analytics Lead | 24 hours |

---

## On-Call Contact (24/7)

```
On-Call Rotation: mt-analytics-oncall@honasa.com
Escalation: vp-analytics@honasa.com
Emergency: +91-XXXXXX [On-call phone, if available]
```

---

## Backup & Recovery Details

**Automated Backups:**
- `dashboard/data.js` backed up nightly to `/backup/data.js-[YYYYMMDD-HHMMSS]`
- Retention: 30 days (can restore any release from last 30 days)
- Location: `/backup/` or cloud storage (TBD with IT)

**Manual Backup (Before Any Release):**
```bash
# Before pushing new data.js
cp dashboard/data.js dashboard/data.js.backup-[commit-hash]
git add dashboard/data.js.backup-*
git commit -m "Backup before release [commit]"
```

**Git History (Permanent):**
- All commits backed up to GitHub
- Can restore any commit ever made: `git reset --hard [commit-hash]`
- GitHub keeps full history indefinitely

---

## Definitions of Done

✓ Rollback procedure documented  
✓ Backup process in place (automated or manual)  
✓ Pre-rollback checklist defined  
✓ Rollback verification checklist defined  
✓ Post-rollback RCA process defined  
✓ On-call team trained on rollback steps  
✓ Contact list for escalation established  

---

**Last Updated:** 2026-09-05  
**Next Review:** After first real-world rollback  
**Owner:** DevOps / Analytics Engineering Lead
