# Release Rollback Procedure

**Issued:** 2026-08-08  
**Authority:** Release Manager + Analytics Engineering  
**Scope:** Emergency recovery of corrupt `data.js` after publication  
**Target Recovery SLA:** < 30 minutes from detection to user visibility  

---

## Overview

If a `data.js` build fails validation **after** publication to GitHub Pages or Vercel (e.g., NaN values detected, Release Gate errors missed, data corruption), this procedure enables rapid rollback to the last known-good build.

**Trigger conditions** for rollback:
1. Release Gate report shows FAIL items (not just BLOCKED)
2. QC dashboard detects NaN/undefined in published data
3. Business reports material KPI divergence from expected (>5%)
4. Git commit or publication failure needs revert

---

## Detection & Diagnosis

### Step 1: Identify the Corrupted Build

**In GitHub CI logs:**
```bash
# Check latest QC run
# Go to: https://github.com/aswalsheshant-cell/mt-dashboard/actions/workflows/qc.yml
# Look for "✗ FAIL" or "⊘ BLOCKED" items in run output
# Record commit hash of the broken build: abc123def456...
```

**In published dashboard:**
```bash
# Open https://mt-dashboard.github.io (or Vercel domain)
# Run browser DevTools console:
Object.keys(window.DASH).forEach(k => {
  if (JSON.stringify(window.DASH[k]).includes("NaN")) {
    console.error(`NaN detected in block: ${k}`);
  }
});
```

**Severity assessment:**
- **CRITICAL:** KPI totals are 0, NaN, or undefined; Release Gate FAIL items present
- **HIGH:** Some drill dimensions broken but totals correct; advisory gate warnings only
- **MEDIUM:** Cosmetic data issues (formatting, missing drill options)

---

## Rollback Decision Tree

```
┌─────────────────────────────────┐
│  Detect corruption in data.js   │
└──────────────┬──────────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
   CRITICAL?      HIGH/MEDIUM?
       │                │
       │                └─→ 2. Try Quick Fix
       │                    (re-run QC tests, fix validation)
       │                    │
       ▼                    ├─→ Fix succeeds → Fast rebuild (30 min)
   1. Rollback            └─→ Fix fails → Proceed to Rollback
      (< 30 min)
       │
       ├─→ Rollback to previous build
       ├─→ Verify Release Gate passes
       ├─→ Publish to production
       ├─→ Notify stakeholders
       └─→ Post-mortem
```

---

## Rollback Procedure (Full Steps)

### Phase 1: Prepare Rollback (5 minutes)

**1.1 Identify last known-good commit**

```bash
# View recent Git tags (releases)
git tag -l --sort=-version:refname | head -5

# Example output:
# release/data.js.FY27.M08.2026
# release/data.js.FY27.M07.2026
# release/data.js.FY26.M03.2026

# Last good build is typically the most recent tag before the failure
LAST_GOOD_TAG="release/data.js.FY27.M07.2026"
LAST_GOOD_COMMIT=$(git rev-list -n 1 $LAST_GOOD_TAG)
echo "Rolling back to: $LAST_GOOD_COMMIT"
```

**1.2 Verify the backup data.js is intact**

```bash
# Check Git history of data.js
git log --oneline dashboard/data.js | head -10

# Verify file size is reasonable (should be ~10-15 MB, not 0 or > 20 MB)
git show $LAST_GOOD_COMMIT:dashboard/data.js | wc -c
# Should output ~10000000 (roughly 10 MB)
```

### Phase 2: Perform Rollback (10 minutes)

**2.1 Revert data.js to last good build**

```bash
# Check out the good version of data.js only (don't revert other files)
git checkout $LAST_GOOD_COMMIT -- dashboard/data.js

# Verify the file was restored
ls -lh dashboard/data.js
git status  # Should show "modified: dashboard/data.js"
```

**2.2 Create rollback commit**

```bash
git add dashboard/data.js

git commit -m "ROLLBACK: Revert data.js to last-good build

Reason: [SPECIFY CORRUPTION REASON]
- Example: 'Release Gate FAIL: Reconciliation variance exceeded'
- Example: 'NaN detected in Primary NSV totals'
- Example: 'Dataset publish failed to Power BI Service'

Last good build: $LAST_GOOD_TAG (commit: $LAST_GOOD_COMMIT)
Rollback timestamp: $(date -u +'%Y-%m-%d %H:%M:%S UTC')

Post-incident review ticket: [LINK TO INCIDENT TRACKING]

Co-Authored-By: Release Manager <noreply@company.com>
Claude-Session: [SESSION LINK IF AI-ASSISTED]"
```

**2.3 Push rollback to main**

```bash
git push origin HEAD:main

# Verify push succeeded
git log --oneline origin/main | head -3
```

### Phase 3: Verify Rollback (5 minutes)

**3.1 Re-run QC on restored data.js**

```bash
# Trigger CI pipeline manually (or wait for webhook)
python scripts/qc_dashboard.py --data dashboard/data.js

# Output should show:
# ✓ PASS for all mandatory checks
# Optionally: ⊘ BLOCKED or ⚠ ADVISORY for non-critical items
```

**3.2 Spot-check dashboard in production**

```bash
# GitHub Pages refreshes in ~1-2 minutes
# Open: https://mt-dashboard.github.io
# Verify:
# - Dashboard loads without errors
# - Primary NSV totals match expected values
# - No NaN/undefined in console
# - Release Gate report shows no FAIL items
```

**3.3 Confirm data integrity**

```bash
# Sample KPI check (manually or via API)
curl -s https://mt-dashboard.github.io/dashboard/data.js | \
  python3 -c "
import sys, json
data = json.loads(sys.stdin.read().replace('window.DASH = ', '').rstrip(';'))
print(f'Primary NSV (FY26): {data[\"primary\"][\"FY26\"][\"total_nsv\"]}')
print(f'Offtake Qty (FY26): {data[\"offtake\"][\"FY26\"][\"total_qty\"]}')
# If values are 0 or NaN, rollback failed
"
```

### Phase 4: Notify & Document (5 minutes)

**4.1 Notify stakeholders**

```bash
# Send message to:
# - Finance (data update notification)
# - Business users (if dashboards were already viewed)
# - On-call team (incident report)

# Example message:
# "Data.js publication from 2026-08-08T14:32:00Z has been ROLLED BACK
#  to 2026-08-07T18:00:00Z due to [CORRUPTION REASON].
#  Dashboard is now serving last-known-good data.
#  Incident ticket: [LINK]"
```

**4.2 Create incident ticket**

Document in your incident tracking system (Jira/Linear/GitHub Issues):
- Timestamp of detection
- Severity level
- Corruption evidence (error logs, screenshots)
- Rollback confirmation
- Root cause analysis (to be completed within 24 hours)
- Preventive action (to avoid recurrence)

**4.3 Post-Mortem (Within 24 hours)**

Schedule a brief post-incident review:
1. What broke? (data validation, Release Gate logic, CI/CD)
2. Why wasn't it caught? (QC gap, test gap, missing validation)
3. How to prevent? (add gate, add test, add monitoring)
4. Owner assigned for fix

---

## Common Corruption Scenarios & Quick Fixes

### Scenario 1: Release Gate FAIL (Reconciliation Variance Exceeded)

**Symptom:** QC output shows `✗ FAIL: Reconciliation variance 0.15% > 0.01% tolerance`

**Quick Fix (try before rollback):**
```bash
# Check if gate threshold is misconfigured
grep "reconciliation_variance_tolerance" scripts/release_gate.py

# If tolerance is too tight:
# 1. Review the actual variance (is it legit?)
# 2. Check if source data changed unexpectedly
# 3. Re-run with --verbose flag to see details

# If variance is documented & acceptable:
python scripts/build_dashboard_data.py --primary-only --src <dir> --out dashboard/data.js
python scripts/qc_dashboard.py --data dashboard/data.js
# If QC still fails, proceed to rollback
```

### Scenario 2: NaN in Primary NSV Totals

**Symptom:** Browser console shows `Primary NSV is NaN` for a specific FY

**Quick Fix:**
```bash
# Check if a distributor allocation failed
python scripts/qc_dashboard.py --data dashboard/data.js --verbose

# Look for warnings about "allocation mismatch" or "unmapped NSV"
# If > 2% unmapped NSV: likely allocation issue
# If allocation is recent (recent Decision 1/2 change):
#   1. Verify Finance decision was applied to release_gate.py
#   2. Re-run build with corrected config
#   3. Re-test

# If problem persists, proceed to rollback
```

### Scenario 3: Offtake Data Missing (All 0s)

**Symptom:** Offtake tab shows 0 volumes; Release Gate shows `allocation_coverage_min 0% < 95%`

**Quick Fix:**
```bash
# Check if offtake source files were included in build
ls -la PowerBI/RawDataFolders/Offtake/

# If empty: source file not supplied
# If present: verify build was run with --offtake-patch flag
python scripts/build_dashboard_data.py --offtake-patch --src <dir> --out dashboard/data.js

# Re-test; if still fails, rollback
```

---

## False Positive: When NOT to Rollback

**Do NOT rollback in these cases:**

| Signal | Reason | Action Instead |
|--------|--------|--------|
| Advisory gate warnings (⚠) | Design; doesn't block | Document in Release Notes |
| BLOCKED gate items (⊘) | Data dependencies; expected | Await data; proceed with caution |
| Release Notes link updated | Intentional change; documentation | Confirm Release Notes accuracy |
| FY27 data missing (pre-agg only) | Architectural; pre-agg ends Mar'26 | Confirm FY coverage in docs |

---

## Preventing Future Rollbacks

### Add to Release Checklist

Before **every** data.js publication:
```bash
☐ Run full pytest suite: pytest scripts/test_*.py -v
☐ Run Release Gate: python scripts/demo_release_gate_blocking.py
☐ Run QC: python scripts/qc_dashboard.py --data dashboard/data.js
☐ Spot-check dashboard in browser (all 12 tabs, all 4 FY contexts)
☐ Verify no new NaN/undefined in console
☐ If all clear → git tag && git push
```

### Monitoring & Alerting

1. **CI Integration:** Configure GitHub Actions to fail on `✗ FAIL` items
2. **Dashboard Health Check:** Add hourly Lighthouse audit to detect load time regression
3. **Data Quality Monitoring:** Add automated data validation in Power BI Service (if PBIP published)

---

## Contacts & Escalation

| Role | Contact | When |
|------|---------|------|
| **Release Manager** | [TBD] | Coordinate rollback; notify stakeholders |
| **Analytics Engineering** | [TBD] | Investigate root cause; implement fix |
| **Finance** | [TBD] | Data validation; control totals verification |
| **On-Call** | [TBD] | 24/7 escalation for critical issues |

---

## Appendix: Git Commands Reference

```bash
# List all release tags
git tag -l "release/*" --sort=-version:refname

# Show commit date of a tag
git log -1 --format=%ad <TAG_NAME>

# View data.js file at a specific commit
git show <COMMIT>:dashboard/data.js | head -100

# Revert just data.js (don't revert other files)
git checkout <COMMIT> -- dashboard/data.js

# Revert entire commit (if multiple files were corrupted)
git revert <COMMIT> -m "Reason: [describe]"

# Check diff before pushing
git diff origin/main
```

---

**This procedure is tested; a rollback drill should be conducted quarterly.**
