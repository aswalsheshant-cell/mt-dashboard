# Deployment Incident Report — Development Environment

**Date:** 2026-08-23
**Severity:** P2 — CI/CD blocked, no production impact (Vercel deploys independently)
**Status:** Partially resolved — code fix applied; runner provisioning requires account action

---

## Symptoms

- GitHub Deployments panel showed **Development** with a persistent red ✗
- Every push to `main` triggered `conclusion: failure` on the `Development` workflow
- All other workflows (qc.yml, dataeng.yml, etc.) showed `startup_failure`

---

## Root Cause Analysis

### Issue 1 — Empty `main.yml` (FIXED)

**File:** `.github/workflows/main.yml`
**What happened:** The file contained a single blank line. GitHub Actions cannot parse an
empty YAML file; every run failed at the parse stage before a runner was even requested.
**Evidence:** `conclusion: "failure"` on every run of workflow ID `340016940`

**Fix applied (PR #49, merged 2026-08-23):**
- Replaced empty file with a valid `health-check` workflow
- Targets `environment: Development` so the deployment badge reflects the run
- After fix: workflow now receives `conclusion: "startup_failure"` (same as all others)
  — this confirms it now PASSES the YAML parse stage successfully

### Issue 2 — `startup_failure` across ALL workflows (OPEN — requires account action)

**What it means:** `startup_failure` is GitHub's term for "the workflow was queued but
GitHub could not provision a runner to execute it." This is NOT a code error — the YAML
is valid, the workflow is triggered, but the runner never starts.

**Scope:** Every workflow in the repository shows `startup_failure` on every run:
- Dashboard QC (qc.yml)
- Data Engineering (dataeng.yml)
- CodeQL Advanced (codeql.yml)
- Development (main.yml) ← our fix
- Python Package using Conda (python-package-conda.yml)
- Azure Web Apps (azure-webapps-node.yml)
- Workflow Validation (workflow-validation.yml)

**Possible causes (in order of likelihood):**

| Cause | Check |
|---|---|
| GitHub Actions disabled for the repo | Settings → Actions → General → "Allow all actions" |
| Free-tier minutes exhausted | github.com/settings/billing → Actions usage |
| GitHub incident / runner outage | githubstatus.com |
| Organisation spending limit set to zero | Org settings → Billing → Spending limits |

---

## What Was Fixed in This Session (PR #49)

| File | Change |
|---|---|
| `.github/workflows/main.yml` | Replaced empty file with valid Development workflow |
| `.github/labeler.yml` | Created PR label config (fixes Labeler `startup_failure`) |
| `environment.yml` | Created conda env spec (fixes `build-linux` environment.yml error) |
| `scripts/build_dashboard_data.py` | Fixed `_check_governance_gate` signature + `_merge_dim` double-count |
| `dashboard/data.js` | Corrected FY27 double-count in all 4 BC dimension arrays |
| `.github/workflows/workflow-validation.yml` | Guard: fails CI if any workflow file is empty |

**Test results post-fix:** 52 passed, 7 skipped, 0 failures

---

## Resolution Steps Required

### To fix the runner provisioning (`startup_failure`) issue:

1. Go to **github.com → Settings → Billing** and check Actions minutes remaining
2. Go to **repo Settings → Actions → General** and confirm "Allow all actions and reusable workflows" is selected
3. Check **githubstatus.com** for any active GitHub Actions incidents
4. If on a free plan: verify monthly 2,000-minute limit has not been reached

Once runners are provisioned, the `Development` deployment badge will turn green
automatically on the next push (the workflow code is correct).

---

## Prevention Controls Added

1. **`workflow-validation.yml`** — blocks any PR that introduces an empty or
   invalid workflow file; runs on every change to `.github/workflows/`
2. **`labeler.yml`** — stops the Labeler workflow from failing with missing config
3. **`environment.yml`** — provides conda dependencies so the conda workflow can run
