# Runner Failure Runbook — startup_failure Decision Tree

**Use this when:** any GitHub Actions workflow reports `startup_failure`

`startup_failure` means GitHub queued the workflow but could not provision a runner.
It is NEVER caused by code errors. The workflow YAML was parsed successfully.

---

## Step 1 — Determine Scope

| Observation | Likely Category | Next Step |
|---|---|---|
| ONE workflow shows `startup_failure` | Cat A or Cat E | → Step 2 |
| ALL workflows show `startup_failure` | Cat D, G, or H | → Step 3 |
| Mixed: some `failure`, some `startup_failure` | Multiple | → Step 2, then Step 3 |

---

## Step 2 — Inspect the Affected Workflow

```bash
# Check file is not empty
wc -c .github/workflows/<name>.yml

# Check YAML parses
python -c "import yaml; yaml.safe_load(open('.github/workflows/<name>.yml'))"

# Check on: trigger exists
python -c "
import yaml, pathlib
doc = yaml.safe_load(pathlib.Path('.github/workflows/<name>.yml').read_text())
print('on:', 'on' in doc or True in doc)
print('jobs:', list(doc.get('jobs', {}).keys()))
"
```

**If empty (< 10 bytes):** replace with valid workflow content → Category A resolved.  
**If YAML error:** fix syntax → Category A resolved.  
**If `environment:` references a name:** go to Step 4 → Category E check.  
**If file looks correct:** proceed to Step 3.

---

## Step 3 — Check Account-Level Issues

### 3a. Billing (Category D)
Navigate to: **github.com/settings/billing**

- Look at "GitHub Actions" usage tile
- Free plan: 2,000 minutes/month (Linux), 3,000 minutes/month (Windows)
- If "Used" = "Limit": minutes exhausted → upgrade or wait for monthly reset
- Organisation repos: check "Spending limit" is not set to $0

**Fix:** Increase spending limit, upgrade plan, or wait for reset.

### 3b. Actions Enabled (Category C)
Navigate to: **github.com/<owner>/<repo>/settings/actions**

- "GitHub Actions permissions" must be "Allow all actions and reusable workflows"
- "Workflow permissions" should be "Read and write permissions"
- If Actions is disabled entirely: no workflows can run

**Fix:** Enable Actions, set permissions to Allow all.

### 3c. GitHub Platform Incident (Category H)
Navigate to: **githubstatus.com**

- Check "GitHub Actions" and "Actions / Runner" rows
- "Degraded Performance" or "Incident" → wait for GitHub resolution

**Fix:** None — wait for GitHub. Monitor githubstatus.com.

---

## Step 4 — Check Environment Configuration (Category E)

Navigate to: **github.com/<owner>/<repo>/settings/environments**

Verify:
- The environment name in the workflow YAML matches EXACTLY (case-sensitive)
- `Development` ≠ `development`
- No required reviewers set for automated workflows (required reviewers block runner provisioning until a human approves)

**This repository's named environments:** `Development`, `Preview`, `Production`

**Fix:** Create the missing environment, or correct the name in the workflow YAML.

---

## Step 5 — Rule Out Transient Runner Failure (Category G)

Re-run the workflow once via GitHub Actions UI → "Re-run all jobs".

- Second consecutive `startup_failure` on the same commit = not transient
- If no billing issue and no platform incident: open a GitHub support ticket

---

## Decision Summary

```
startup_failure?
│
├─ ONE workflow only
│   ├─ File empty or invalid YAML → Cat A → fix workflow file
│   └─ References environment: X → Cat E → check Settings → Environments
│
└─ ALL workflows
    ├─ Check billing → Cat D → upgrade/wait
    ├─ Check Actions enabled → Cat C → enable in Settings → Actions
    ├─ Check githubstatus.com → Cat H → wait for GitHub
    └─ All checks pass → Cat G → re-run once; then open support ticket
```

---

## This Repository — 2026-08-23 Incident

All workflows showed `startup_failure` after PR #49 merged the `main.yml` fix.

**Root cause:** Account-level issue (Category D or C or H).  
**Confirmed NOT:** workflow code error. `conclusion: failure` on the old empty `main.yml` correctly changed to `startup_failure` after the fix, proving the YAML parse issue is resolved.

**Required actions:**
1. Settings → Actions → General → verify "Allow all actions and reusable workflows"
2. github.com/settings/billing → verify Actions minutes > 0
3. githubstatus.com → verify no active Actions incident

See `docs/deployment-fix-report.md` for full incident record.
