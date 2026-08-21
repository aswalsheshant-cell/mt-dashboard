# On-Call Guide — Production Support Procedure

**Issued:** 2026-08-08  
**Authority:** Release Manager + Analytics Engineering  
**Scope:** Emergency support for MT Dashboard production incidents  
**Target SLA:** Initial response < 15 min; resolution target < 4 hours  
**Escalation chain:** On-Call → Team Lead → Director  

---

## Overview

This guide defines how the on-call team responds to production incidents affecting the Modern Trade Analytics Dashboard. Use this guide when:

- Dashboard is inaccessible (GitHub Pages / Vercel down)
- Data is corrupt or stale (Release Gate FAIL; NaN values)
- Business KPIs don't match expected (divergence > 5%)
- Release Gate blocking data publication
- Power BI refresh failing (after PBIP deployed)

**Do NOT use this guide for:** non-urgent bugs, feature requests, documentation updates (handle via GitHub issues, not pages-down).

---

## Incident Severity Matrix

| Severity | Impact | Examples | Response Target | Escalation |
|----------|--------|----------|-----------------|------------|
| **CRITICAL** | Data corrupted; Dashboard offline for > 10 min | KPI showing NaN; Dashboard returns 404; Release Gate FAIL blocking build | Investigate in < 5 min; Rollback/Fix in < 30 min | Immediate (engage Team Lead + Director) |
| **HIGH** | Partial data missing; KPI error > 5% | FY27 missing; offtake 0; CM2 unexpectedly low | Investigate in < 15 min; Fix in < 2 hours | Within 30 min (engage Team Lead) |
| **MEDIUM** | Advisory warnings; cosmetic issues | TOT% fallback > threshold; drill missing for one dimension | Investigate within 1 hour; Fix in < 4 hours | Next business day (Team Lead aware) |
| **LOW** | Non-functional minor feature | Download feature broken for one format; dashboard loads slowly | Investigate next business day | Backlog ticket |

---

## Step 1: Triage (< 5 minutes)

### 1.1 Receive Alert

**Possible channels:**
- GitHub Actions CI failure notification
- Business user report (via Slack, email, phone)
- Automated monitoring alert (if configured)
- Manual discovery (user opens dashboard, sees error)

**Log the incident:**
- Timestamp of detection
- Who reported it + contact info
- Description of symptom
- Affected FY / tab (if known)
- Your name + start time

### 1.2 Confirm the Issue

**Quick checks (do all three):**

```bash
# A. Check if GitHub Pages is serving
curl -I https://mt-dashboard.github.io 2>&1 | grep "HTTP"
# Should see "HTTP 200" (OK) or "HTTP 301" (redirect)
# If "HTTP 503" or "Connection refused": GitHub Pages issue (escalate to IT)

# B. Check if Vercel is serving (if using Vercel mirror)
curl -I https://mt-dashboard.vercel.app 2>&1 | grep "HTTP"

# C. Open dashboard in browser (test both domains)
# Look for: Does page load? Are charts rendering? Any browser console errors?
```

**Assess severity:**

```
Issue confirmed?
  ├─ NO → False alarm. Log as "Not Reproducible" and close.
  └─ YES →
      ├─ Dashboard completely offline (404 / 503)?
      │  └─ CRITICAL: Proceed to Step 2 (Rollback)
      │
      ├─ Dashboard loads but shows NaN / Undefined / 0 totals?
      │  └─ CRITICAL: Proceed to Step 2 (Investigate Data)
      │
      └─ Dashboard loads with advisory warnings (yellow, not red)?
         └─ HIGH: Proceed to Step 3 (Diagnosis)
```

### 1.3 Notify Stakeholders (Immediate)

If CRITICAL or HIGH:

```bash
# Message template to send via Slack / email to Finance + Business leads:
"""
🚨 INCIDENT: MT Dashboard [SEVERITY]

Status: [INVESTIGATING / DEGRADED / OFFLINE]
Start Time: [TIMESTAMP]
Estimated Impact: [Business description, not technical]

Example (CRITICAL): "Primary NSV totals showing as NaN; Data appears corrupted"
Example (HIGH): "FY27 Offtake data missing from dashboard; still loading FY26"

We are investigating and will provide updates every 15 minutes.
"""
```

---

## Step 2: Incident Response (< 30 minutes to Resolution)

### Path A: Dashboard Offline (HTTP 503 / 404)

**2A.1 Check Git/CI Status**

```bash
# Is the repo healthy?
cd /path/to/mt-dashboard
git status

# Did CI just fail?
# Go to: https://github.com/aswalsheshant-cell/mt-dashboard/actions
# Look at latest "Dashboard QC" run: PASSED or FAILED?

# If CI FAILED: Check the failure reason
# - Syntax error in build_dashboard_data.py?
# - Release Gate mandatory check failed?
# - QC gate detected NaN in data?
```

**2A.2 Check GitHub Pages / Vercel Status**

```bash
# GitHub Pages status
curl -s https://www.githubstatus.com/api/v2/status.json | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(d['status']['indicator'])"
# Output: "green" = OK, "yellow" = degraded, "red" = down

# Vercel status (if using Vercel)
curl -s https://www.vercel-status.com/api/v2/status.json | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(d['status']['indicator'])"
```

**2A.3 Recover: Force Rebuild**

If CI is passing but dashboard is stale:

```bash
# Trigger a manual rebuild (if you have contributor access)
# Go to: https://github.com/aswalsheshant-cell/mt-dashboard/actions
# Click "Dashboard QC" workflow
# Click "Run workflow" (on the desired branch)

# OR: Push a trivial commit to trigger CI
git commit --allow-empty -m "Trigger CI rebuild"
git push
```

**2A.4 Escalate if Unresolved**

If dashboard still offline after 15 min:
```
Escalate to: IT (GitHub Pages/Vercel) + Team Lead
Provide: CI logs, git status, curl output above
```

---

### Path B: Data Corrupted (NaN / Undefined / FAIL Gate)

**2B.1 Identify the Corruption Type**

```bash
# Check CI logs
# Go to: https://github.com/aswalsheshant-cell/mt-dashboard/actions
# Find latest "Dashboard QC" run
# Expand "Run QC gate" step

# Look for:
if grep -q "✗ FAIL" ; then
  echo "Release Gate FAILED — Mandatory check broken. Likely data error."
  echo "Action: See ROLLBACK.md; proceed to Step 2B.4"
elif grep -q "⊘ BLOCKED" ; then
  echo "Release Gate BLOCKED — Data dependency (expected). Proceed to Step 2B.3"
else
  echo "Release Gate PASSED — Likely a JS/UI error, not data."
  echo "Action: Check browser console; contact Analytics Engineering"
fi
```

**2B.2 Check Recent Changes**

```bash
# What changed in the last build?
git log --oneline -10 dashboard/data.js

# Who pushed to main in the last 30 minutes?
git log --oneline --since="30 minutes ago" main

# Any recent Finance decisions that would have changed gate config?
git log --oneline scripts/release_gate.py -5
```

**2B.3 If Corruption Confirmed (FAIL Gate)**

→ **See `docs/ROLLBACK.md` for detailed recovery steps.**

Quick summary:
```bash
# Find last good build
LAST_GOOD=$(git tag -l "release/*" --sort=-version:refname | head -1)
LAST_GOOD_COMMIT=$(git rev-list -n 1 $LAST_GOOD)

# Rollback data.js
git checkout $LAST_GOOD_COMMIT -- dashboard/data.js
git commit -m "ROLLBACK: Data corruption; reverting to $LAST_GOOD"
git push origin HEAD:main

# Notify stakeholders (update Slack message)
# "Data has been rolled back to 2026-08-07 build. Issue under investigation."
```

**2B.4 If BLOCKED Gate (Data Dependency)**

If gate shows `⊘ BLOCKED` but not `✗ FAIL`:
```bash
# BLOCKED = expected (Finance decision pending, etc.)
# Data.js was NOT published; deployment blocked at gate

# Check which gate is blocking
grep "⊘ BLOCKED:" <CI_LOG> | head -5

# Examples:
# "⊘ BLOCKED: Jun'26 Distributor allocation status = PROVISIONAL (awaiting Finance Decision 1)"
# "⊘ BLOCKED: Nielsen data absent (FY27)"

# Action:
# 1. Confirm this is expected (check Finance_Approval_Decision_Log.md)
# 2. If expected → Wait for data or Finance decision
# 3. If unexpected → Investigate why gate thinks data is missing
```

---

## Step 3: Diagnosis (< 2 hours to Root Cause)

If dashboard is online and data looks reasonable, but something is off:

### 3.1 Spot-Check KPIs

**Manual validation (compare to expected ranges or Finance control totals):**

```bash
# Example: Check Primary NSV for FY26
curl -s https://mt-dashboard.github.io/dashboard/data.js 2>/dev/null | \
  python3 << 'EOF'
import json, sys
data_str = sys.stdin.read().replace('window.DASH = ', '').rstrip(';')
data = json.loads(data_str)
fy26_nsv = data['primary'].get('FY26', {}).get('total_nsv', 'N/A')
print(f'Primary NSV (FY26): ₹{fy26_nsv} L')
# Compare to Finance's expected value
# If off by > 0.5%: investigate
EOF
```

**KPI ranges (from Business Logic Registry):**

| KPI | FY26 Expected | Tolerance | Notes |
|-----|---------------|-----------|-------|
| Primary NSV | ₹15,776 L | ±₹79 L (0.5%) | From Finance close |
| Offtake Qty | 4.2M units | ±2% | Supply Chain KPI |
| Distribution (TDP) | 8,420 stores | TBD | Pending TDP data |
| Market Share (Nielsen) | TBD | TBD | Pending Nielsen data |

If actual diverges > 5%: Log as HIGH incident.

### 3.2 Check Recent Data Ingestion

```bash
# Did any source data change recently?
# (Primary, Offtake, Universe, Promo workbooks)

# Check git log for build-related commits
git log --oneline --since="24 hours ago" -- dashboard/data.js

# Check release tags (when was the last build?)
git log -1 --format=%ad --date=short $(git tag -l "release/*" --sort=-version:refname | head -1)
# Compare to current time. Is data > 1 month old? (unlikely if system is working)
```

### 3.3 Check Release Gate Thresholds

```bash
# Are any thresholds recently changed?
git log -p scripts/release_gate.py | grep -A2 -B2 "tolerance\|min_pct\|max_pct" | head -30

# Are Finance decisions affecting gate behavior?
grep -E "jun26_allocation_status|negative_frac_treatment_status" scripts/release_gate.py

# If thresholds look wrong:
# 1. Confirm with Finance (via BUSINESS_LOGIC_REGISTRY.md)
# 2. If incorrect: Create GitHub issue; assign to Analytics Engineering
# 3. Fix; re-run build; publish corrected data.js
```

### 3.4 Check Browser Console for Client-Side Errors

```bash
# Open https://mt-dashboard.github.io in browser
# Press F12 (DevTools)
# Go to Console tab
# Look for red error messages

# Common errors:
# - "data.js:1 SyntaxError: Unexpected token '<'" → File not found (404)
# - "Cannot read property 'X' of undefined" → Missing data block
# - "NaN" in computed totals → Allocation or calculation error
```

### 3.5 Escalate for Deep Dive

If still unresolved:
```
→ Escalate to Analytics Engineering + Team Lead
Provide:
  - KPI spot-check results
  - Git log (recent commits)
  - Release Gate threshold review
  - Browser console errors (if any)
  - Incident ticket number
```

---

## Step 4: Implement Fix (< 4 hours)

Once root cause is identified, coordinate with owner:

### If Data Error (Release Gate FAIL / NaN)

**Owner:** Analytics Engineering  
**Action:** Run diagnostics; fix source data or allocation logic; rebuild data.js; publish

### If Finance Decision Pending

**Owner:** Finance  
**Action:** Provide decision approval (Decision 1 or 2); Analytics team updates config; rebuild

### If Source Data Missing (Nielsen / TDP)

**Owner:** Finance / Supply Chain  
**Action:** Supply missing source file; Analytics team ingests; rebuild

### If Environment Issue (GitHub Pages / Vercel)

**Owner:** IT  
**Action:** Restore service; clear CDN cache; re-publish

---

## Step 5: Post-Incident (< 24 hours)

### 5.1 Complete Incident Ticket

Document:
- Incident start time
- Root cause (data, config, external, infrastructure)
- Time to detect / investigate / resolve
- Preventive action to avoid recurrence
- Owner assigned for preventive action

### 5.2 Notify Stakeholders (Final)

```bash
# Message template (send to same distribution as alert):
"""
✅ INCIDENT RESOLVED: MT Dashboard [SEVERITY]

Issue: [Brief description of what broke]
Root Cause: [What caused it]
Resolution: [What we did]
Impact: [Business impact duration, KPI divergence]

Preventive Action: [What we're doing to prevent this]
Ticket: [GitHub issue link]
Owner: [Analytics Engineering / Finance / IT]
"""
```

### 5.3 Schedule Post-Mortem (if CRITICAL / HIGH)

```bash
# Within 24 hours of incident:
# 1. Call 15-min review with: On-Call, Analytics Engineering, Team Lead
# 2. Document: what broke, why it wasn't caught, how to prevent
# 3. Assign owner for preventive action
# 4. Target delivery: 1 week
# 5. Add test case to prevent regression
```

---

## Monitoring & Alerting Configuration

### GitHub Actions Notification

Currently: Push to `main` triggers QC workflow; results emailed.

**Desired (to implement):**
```yaml
# Add to .github/workflows/qc.yml:
- name: Notify on FAIL
  if: failure()
  run: |
    # Send Slack message to on-call channel
    curl -X POST -H 'Content-type: application/json' \
      --data '{"text":"🚨 MT Dashboard QC: FAIL. See actions."}' \
      $SLACK_WEBHOOK_URL
```

### Dashboard Health Check (Future)

When PBIP is deployed to Power BI Service:
```
- Schedule daily refresh validation
- Monitor: Refresh duration, error rate, data freshness
- Alert if: Refresh fails > 2x in a row, data > 24h stale
```

---

## On-Call Schedule

| Period | On-Call Engineer | Backup | Contact |
|--------|------------------|--------|---------|
| Mon–Fri 9–17 (IST) | [TBD] | [TBD] | [Phone + Slack] |
| Fri 17 – Mon 9 (Nights/Weekends) | [TBD] | [TBD] | [Phone + Slack] |

**Handoff procedure:** Every Monday 9 AM IST, outgoing on-call briefs incoming on-call on:
- Any open incidents
- Recent changes (Finance decisions, new data)
- Known issues in backlog

---

## Reference: Common Issues & Quick Fixes

### "Dashboard shows 0 for all KPIs"

**Likely cause:** Offtake data not ingested (or Primary × allocation mismatch)

```bash
# Fix:
python scripts/build_dashboard_data.py --offtake-patch --src <dir> --out dashboard/data.js
python scripts/qc_dashboard.py --data dashboard/data.js
# If QC passes: git push to publish
```

### "FY27 data missing; FY26 showing"

**Likely cause:** FY27 source files not supplied; system working as designed

```bash
# Verify:
ls -la PowerBI/RawDataFolders/Offtake/
# If empty: Supply Chain hasn't provided FY27 yet
# Action: Contact Supply Chain; update SOURCES.md with ETA
# Not an incident; document in Release Notes
```

### "Release Gate says BLOCKED; deployment stopped"

**Likely cause:** Awaiting Finance decision or missing data

```bash
# Check gate report:
grep "⊘ BLOCKED:" dashboard/release_gate_report.json

# If Decision 1 or 2 blocking:
# → Escalate to Finance (not an on-call fix)

# If Nielsen or TDP blocking:
# → Update SOURCES.md with ETA; not an incident
```

---

## Contacts & Resources

| Role | Name | Phone | Slack | Email |
|------|------|-------|-------|-------|
| **On-Call Lead** | [TBD] | [TBD] | @oncall | [TBD] |
| **Team Lead** | [TBD] | [TBD] | @[name] | [TBD] |
| **Finance POC** | [TBD] | [TBD] | @[name] | [TBD] |
| **IT/Infrastructure** | [TBD] | [TBD] | @[name] | [TBD] |

**Quick links:**
- Dashboard: https://mt-dashboard.github.io
- GitHub Repo: https://github.com/aswalsheshant-cell/mt-dashboard
- CI Workflow: https://github.com/aswalsheshant-cell/mt-dashboard/actions
- Release Gate Report: Latest CI run → "Upload Release Gate Report" artifact
- Finance Decision Log: `PowerBI/docs/Finance_Approval_Decision_Log.md`

---

**This guide is tested quarterly via incident drill. Last drill: [Date TBD]**
