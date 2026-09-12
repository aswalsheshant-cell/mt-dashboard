# Disaster Recovery Plan

**Issued:** 2026-08-08  
**Authority:** IT + Release Manager  
**Scope:** Recovery procedures if Git repo or source data is lost  
**RTO (Recovery Time Objective):** < 4 hours  
**RPO (Recovery Point Objective):** < 1 day (latest Git commit + daily backup)  

---

## Overview

This plan addresses scenarios where the primary Git repository or source data files become unavailable:

1. **Git repo corruption or deletion** (GitHub platform issue)
2. **Source data lost** (all four workbooks unavailable)
3. **Dashboard publication blocked** (GitHub Pages / Vercel offline for > 2 hours)

---

## Disaster Matrix

| Scenario | Impact | Detection | RTO | Action |
|----------|--------|-----------|-----|--------|
| **Git repo deleted on GitHub** | Cannot push; cannot clone; CI blocked | Inability to push or clone; HTTP 404 on GitHub | < 4 hours | Restore from GitHub backup or mirror |
| **Git repo data corruption** | Commits may be lost; history may be incomplete | `git fsck` errors; CI failure; push rejection | < 4 hours | Restore from GitHub backup; rebase local branches |
| **Source data files lost** | Cannot rebuild `data.js` from scratch | Build fails; missing Primary/Offtake/Universe files | < 4 hours | Restore from Google Drive backup or archive |
| **GitHub Pages offline** | Dashboard not accessible (404 / 503 for > 2 hours) | HTTP 503 on `mt-dashboard.github.io` | < 30 min | Failover to Vercel or alternate hosting |
| **Data.js corrupted** | Dashboard loads but shows NaN/undefined | QC gate detects FAIL; business reports errors | < 30 min | Rollback to last-good build (see ROLLBACK.md) |

---

## Prevention Strategy (First Line of Defense)

**Inherent redundancy (no action needed):**

- GitHub automatically mirrors all commits to multiple data centers
- GitHub Enterprise backup (if enabled)
- Git clone on local developer machines acts as incremental backup

**Recommended** (to strengthen resilience):

1. **GitHub Mirror (Optional):**
   ```bash
   # Mirror repo to GitLab or Gitea (backup hosting)
   git mirror clone --mirror https://github.com/aswalsheshant-cell/mt-dashboard.git \
     https://gitlab.company.com/backups/mt-dashboard.git
   ```

2. **Daily Source File Archive:**
   ```bash
   # Weekly sync of Google Drive sources to S3 / team backup
   # (automation TBD)
   ```

3. **Tagged Releases:**
   ```bash
   # Every production release is tagged (e.g., release/data.js.FY27.M08.2026)
   # Tags are immutable; cannot be deleted without explicit action
   git tag -a release/data.js.FY27.M08.2026 -m "Production snapshot"
   git push origin release/data.js.FY27.M08.2026
   ```

---

## Disaster Recovery Procedures

### Scenario 1: GitHub Repo Deleted or Corrupted

**Detection:**
```bash
# Push fails with: "Repository not found"
git push origin main
# Error: The repository does not exist

# OR: Git integrity check fails
cd /path/to/mt-dashboard
git fsck --full
# error: object is corrupted ...
```

**Recovery Procedure (< 4 hours):**

**Step 1.1: Restore from GitHub Backup (if GitHub Enterprise backup exists)**

Contact GitHub Support:
- Provide repo name: `aswalsheshant-cell/mt-dashboard`
- Request: "Restore deleted repo from backup"
- ETA: 1–4 hours

**Step 1.2: Restore from Local Git Clone**

If you have a recent local clone on your machine:

```bash
# On a machine with a healthy clone:
cd /path/to/mt-dashboard
git remote -v
# Should show origin pointing to GitHub

# If GitHub is unreachable, you can push to a mirror
git remote add mirror https://gitlab.company.com/backups/mt-dashboard.git
git push mirror --all
git push mirror --tags

# Then notify team that mirror is new source
# Until GitHub recovers
```

**Step 1.3: Restore from Developers' Local Clones**

If no centralized backup exists:

```bash
# Coordinate with team members who have recent local clones
# Each clone contains the full Git history

# On a team member's machine with full history:
git remote add restored https://github.com/aswalsheshant-cell/mt-dashboard.git
git push -u restored --all
git push -u restored --tags

# Re-establish main branch protection and CI webhooks
```

**Verification:**
```bash
# All commits restored?
git log --oneline | wc -l
# Should match recent clone count

# All tags restored?
git tag -l | wc -l
# Should include release/data.js.* tags

# CI working again?
# Check: https://github.com/aswalsheshant-cell/mt-dashboard/actions
```

---

### Scenario 2: Source Data Files Lost (Google Drive)

**Detection:**
```bash
# Build fails when trying to read source files
python scripts/build_dashboard_data.py --src ~/MT-Sources --out dashboard/data.js
# Error: Primary_ShipTo_FY25-26_to_May26.xlsb: No such file or directory
```

**Recovery Procedure (< 4 hours, depends on file size):**

**Step 2.1: Restore from Google Drive Revision History**

Google Drive retains version history for 30 days:

```bash
# In Google Drive web interface:
# 1. Navigate to /MT-Analytics/Sources/
# 2. Right-click file → "Version history"
# 3. Select previous version (last-known-good)
# 4. Click "Restore this version"
# 5. Download to ~/MT-Sources/
```

**Step 2.2: Restore from Archived data.js**

If source file is truly lost, recover from last-good `data.js` (see ROLLBACK.md):

```bash
# Get last-good commit hash
LAST_GOOD=$(git tag -l "release/*" --sort=-version:refname | head -1)
LAST_GOOD_COMMIT=$(git rev-list -n 1 $LAST_GOOD)

# Restore last-good data.js
git show $LAST_GOOD_COMMIT:dashboard/data.js > dashboard/data.js
git add dashboard/data.js
git commit -m "Disaster Recovery: restored last-good data.js (source files unavailable)"
git push origin HEAD:main

# Dashboard will serve restored data until source files are recovered
```

**Step 2.3: Request Source File from Data Owner**

Contact the file owner and request a recent backup:

```bash
# Email to Finance (for Primary workbook):
# "Primary_ShipTo_FY25-26_to_May26.xlsb was lost from Google Drive.
#  Can you provide a recent backup from your local drive or email?"

# Email to Supply Chain (for Offtake files):
# "Offtake monthly files were lost. Please re-upload latest months."

# Email to Product (for Universe):
# "Universe_Master_FY25-26.xlsb was lost. Can you provide backup?"

# Email to Trade Marketing (for Promo files):
# "Promo_Trade_Spend_Input was lost. Please re-upload."
```

**Step 2.4: Rebuild from Recovered Source**

Once source file is recovered:

```bash
# Place recovered file in ~/MT-Sources/
python scripts/build_dashboard_data.py --src ~/MT-Sources --out dashboard/data.js
python scripts/qc_dashboard.py --data dashboard/data.js
git add dashboard/data.js
git commit -m "Recovered data.js from restored source files"
git push origin HEAD:main
```

---

### Scenario 3: GitHub Pages / Vercel Offline (> 2 hours)

**Detection:**
```bash
curl -I https://mt-dashboard.github.io
# HTTP/1.1 503 Service Unavailable

# OR: Dashboard doesn't load; browser shows error
```

**Recovery Procedure (< 30 minutes, depending on root cause):**

**Step 3.1: Check Service Status**

```bash
# GitHub Pages status
curl -s https://www.githubstatus.com/api/v2/status.json | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(d['status']['indicator'])"
# Output: "green" (OK), "yellow" (degraded), "red" (down)

# If GitHub is down → Wait for GitHub to recover
# ETA usually < 1 hour; check https://status.github.com
```

**Step 3.2: Check Repo Permissions**

```bash
# Is GitHub Pages still enabled?
# Go to: https://github.com/aswalsheshant-cell/mt-dashboard/settings/pages
# Verify: "Build and deployment" is set to "Deploy from a branch" (main)

# If disabled → Re-enable:
# 1. Go to Settings → Pages
# 2. Source: "Deploy from a branch"
# 3. Branch: "main"
# 4. Save
```

**Step 3.3: Failover to Vercel Mirror**

If GitHub Pages is down for > 30 min, failover to Vercel:

```bash
# Prerequisites (manual setup once):
# 1. Login to Vercel (https://vercel.com)
# 2. Import mt-dashboard repo
# 3. Deploy
# 4. DNS: Add CNAME mt-dashboard-mirror.vercel.app

# When GitHub Pages fails:
# 1. Update DNS or announce alternate URL: https://mt-dashboard-mirror.vercel.app
# 2. Notify stakeholders: "Dashboard temporarily at vercel.app due to GitHub Pages downtime"
# 3. Monitor GitHub Pages for recovery
# 4. Update DNS back when GitHub recovers
```

**Step 3.4: Force GitHub Pages Rebuild**

```bash
# Sometimes a rebuild can fix transient issues
# Go to: https://github.com/aswalsheshant-cell/mt-dashboard/actions
# Click "Pages" workflow (if exists)
# Run workflow (or)

# Trigger rebuild by committing empty commit
git commit --allow-empty -m "Trigger GitHub Pages rebuild"
git push origin main

# Wait 2-5 minutes for GitHub Pages to rebuild
# Check: https://mt-dashboard.github.io
```

---

## Backup & Archival Strategy

### Automated Backups (Current State)

- **Git commits:** GitHub maintains 6 copies of every commit (default GitHub redundancy)
- **Release tags:** Immutable; cannot be lost without explicit action

### Recommended Enhanced Backups (Future)

| Target | Frequency | Destination | Retention | Effort |
|--------|-----------|-------------|-----------|--------|
| **Git repo mirror** | Daily (auto) | GitHub Enterprise or mirror.example.com | 30 days rolling | 0.25 days setup |
| **Source file backups** | Weekly (manual) | S3 or on-prem NAS | 13 weeks (quarterly) | Ongoing |
| **data.js snapshots** | Every release (tagged) | Git tags (immutable) | Indefinite | Already done |
| **PBIP backup** | After each Power BI change | Power BI Service version history | 30 days (Service default) | N/A |

### Testing Disaster Recovery (Recommended Quarterly)

To ensure procedures are accurate and feasible:

**Quarterly Drill (Q4 2026, Q1 2027, ...):**

1. **Simulate Git repo deletion:**
   ```bash
   # DO NOT actually delete GitHub repo
   # Instead: Clone fresh copy to new machine
   git clone https://github.com/aswalsheshant-cell/mt-dashboard.git /tmp/dr-test
   cd /tmp/dr-test
   # Verify: All commits, all tags present
   git log --oneline | wc -l  # Should match expected count
   git tag -l | wc -l         # Should match expected count
   ```

2. **Simulate source file recovery:**
   ```bash
   # Delete local source files
   rm ~/MT-Sources/*
   
   # Attempt rebuild from last-good data.js
   python scripts/build_dashboard_data.py --primary-only \
     --src ~/MT-Sources --out /tmp/test-data.js
   # Should fail with "file not found" (expected)
   
   # Restore from Git archive
   git show main:dashboard/data.js > /tmp/test-data.js
   # Should succeed
   ```

3. **Document findings:**
   - Did procedures work?
   - Were any steps unclear?
   - Update this document if procedures changed

---

## Contacts & Escalation

| Role | Contact | When | Escalation Path |
|------|---------|------|-----------------|
| **GitHub Support** | support@github.com | Repo deletion / major outage | Critical: open ticket |
| **Google Drive Admin** | [TBD] | Drive data loss / permissions issue | Critical: request recovery |
| **AWS / Cloud Admin** | [TBD] | Storage / backup infrastructure | Critical: request restore |
| **Release Manager** | [TBD] | Coordinate all recovery efforts | Within 15 min of detection |
| **On-Call** | [TBD] | 24/7 incident response | Immediate (see ON_CALL_GUIDE.md) |

---

## Post-Disaster Review

After any disaster event:

1. **Root Cause Analysis:**
   - What caused the failure?
   - Why wasn't it detected earlier?
   - Could it have been prevented?

2. **Update This Document:**
   - What procedures didn't work?
   - What new insights did we gain?
   - Revise steps based on lessons learned

3. **Implement Prevention:**
   - Add monitoring / alerting to catch early
   - Strengthen backup strategy if needed
   - Update team training

---

**This plan is tested quarterly via disaster recovery drill.**  
**Last drill: [Date TBD]**  
**Next scheduled drill: [Q4 2026]**
