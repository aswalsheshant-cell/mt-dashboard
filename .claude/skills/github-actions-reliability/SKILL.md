---
name: github-actions-reliability
description: |
  Automatically activate when any GitHub Actions topic appears.
  Triggers on: "startup_failure", "workflow failure", "deployment failure",
  "environment deployment", "Actions runner", "workflow yaml", "CI/CD",
  "GitHub deployment", "GitHub environment", "Actions enabled", "billing exhaustion",
  "runner provisioning", "branch protection", "secrets missing", "dispatch failed",
  "workflow dispatch", "workflow not running", "red deployment badge", "Development red",
  "workflow empty", "workflow invalid", "missing workflow", "actions disabled".
  Do NOT use for Python code bugs, data pipeline issues, or dashboard UI changes.
---

# GitHub Actions Reliability Guardian

Diagnose and permanently resolve GitHub Actions failures in this repository.
Do not speculate — classify the failure category, collect evidence, apply the fix, verify, commit, push, and document.

---

## Root Cause Classification Framework

Before touching any file, classify the failure into exactly one primary category:

| Category | Name | Symptoms | Evidence to collect |
|---|---|---|---|
| A | Workflow Syntax | `conclusion: failure` on every run before any step executes | `wc -c workflow.yml`; `python -c "import yaml; yaml.safe_load(open('file'))"` |
| B | Repository Configuration | Labeler/conda workflow crashes with "file not found" | Check `.github/labeler.yml`, `environment.yml`, `requirements.txt` exist |
| C | Actions Permissions | 403 errors in job logs; "Resource not accessible by integration" | Settings → Actions → General → Workflow permissions |
| D | Billing / Usage Limits | `startup_failure` across ALL workflows simultaneously | github.com/settings/billing; check Actions minutes |
| E | Environment Configuration | `startup_failure` only on workflows that reference `environment:` | Settings → Environments → verify named env exists |
| F | Secrets Configuration | Steps fail with "secret not found" or empty env vars | Settings → Secrets and Variables → Actions |
| G | Runner Availability | `startup_failure` without billing issue; intermittent | githubstatus.com; re-run to confirm not transient |
| H | GitHub Platform Incident | All repos affected; `startup_failure` unrelated to billing | githubstatus.com → GitHub Actions status |
| I | Deployment Failure | Badge red but workflow steps pass; environment approval gate | Settings → Environments → check reviewer rules |
| J | Code Failure | Specific test/lint step fails with log output | Read the job log; find the failing assertion |

**Triage rule:** `startup_failure` across ALL workflows = Category D or G or H (never J).  
`startup_failure` only on one workflow = Category A or E.  
`conclusion: failure` with step logs = Category J or C.

---

## Mandatory Health Checks (run before every merge to main)

### 1. Workflow Checks
```bash
# No empty workflow files
for f in .github/workflows/*.yml .github/workflows/*.yaml; do
  [ -f "$f" ] || continue
  size=$(wc -c < "$f")
  [ "$size" -lt 10 ] && echo "FAIL empty: $f ($size bytes)"
done

# YAML parses and has on: trigger
python - <<'EOF'
import glob, yaml, pathlib, sys
errors = []
for path in glob.glob(".github/workflows/*.yml"):
    try:
        doc = yaml.safe_load(pathlib.Path(path).read_text())
        if not isinstance(doc, dict) or ("on" not in doc and True not in doc):
            errors.append(f"{path}: missing 'on:' key")
    except yaml.YAMLError as e:
        errors.append(f"{path}: parse error — {e}")
[print(e) for e in errors] or print("✓ all workflows valid")
EOF
```

### 2. Repository Asset Checks
```bash
for f in dashboard/index.html dashboard/data.js requirements.txt .github/labeler.yml environment.yml; do
  [ -f "$f" ] && echo "✓ $f" || echo "MISSING: $f"
done
```

### 3. Environment Checks (via GitHub API through MCP tools)
- Verify `Development` environment exists in Settings → Environments
- Verify no required reviewer rules blocking automated deployments
- Verify environment has no secret references that are undefined

### 4. Infrastructure Checks (manual — cannot be automated via CLI)
- github.com/settings/billing → Actions minutes remaining > 0
- githubstatus.com → No active Actions/Runner incidents
- Repo Settings → Actions → General → "Allow all actions and reusable workflows"

---

## Startup Failure Runbook

When any workflow reports `startup_failure`:

### Step 1 — Inspect the workflow file
```bash
wc -c .github/workflows/<name>.yml          # < 10 bytes = empty = Category A
python -m py_compile .github/workflows/...  # syntax check
python -c "import yaml; yaml.safe_load(open('.github/workflows/<name>.yml'))"
```
- Empty file → fix: replace with valid content (Category A)
- Parse error → fix: correct the YAML (Category A)

### Step 2 — Check scope of failure
- ONE workflow: suspect Category A (syntax) or Category E (environment missing)
- ALL workflows simultaneously: suspect Category D (billing) or G/H (runner/platform)

### Step 3 — Check billing (Category D)
Navigate to: **github.com/settings/billing → Actions**
- Free plan: 2,000 minutes/month; check used vs. limit
- If limit reached: upgrade plan or wait for monthly reset
- Organisation: check spending limit not set to $0

### Step 4 — Check Actions settings (Category C)
Navigate to: **Repo Settings → Actions → General**
- "GitHub Actions permissions" = "Allow all actions and reusable workflows"
- "Workflow permissions" = "Read and write permissions"

### Step 5 — Check environments (Category E)
Navigate to: **Repo Settings → Environments**
- `Development` must exist with no required reviewers for automated runs
- `environment: Development` in a job without the named env = perpetual `startup_failure`

### Step 6 — Check GitHub status (Category H)
Navigate to: **githubstatus.com**
- If "GitHub Actions" shows "Degraded Performance" or "Incident": wait for resolution
- Not a code issue; no fix needed in this repo

### Step 7 — Re-run to rule out transient runner failure (Category G)
- Re-run the failed workflow once
- Two consecutive `startup_failure` = not transient
- Confirm with githubstatus.com

---

## Permanent Prevention Controls

Three guard workflows protect this repository. Never delete them.

### `workflow-validation.yml` (exists)
- Blocks empty workflow files (< 10 bytes)
- Validates YAML syntax and `on:` trigger
- Confirms `dashboard/index.html`, `dashboard/data.js`, `requirements.txt` exist

### `repo-health.yml` (added by this skill)
- Verifies all required repo assets on every push
- Checks `environment.yml`, `.github/labeler.yml`, `requirements.txt`
- Python syntax check on all scripts

### `deployment-readiness.yml` (added by this skill)
- Validates each workflow references a real environment name
- Checks workflow YAML completeness
- Runs on changes to `.github/workflows/`

---

## Required Documentation

The `docs/` directory must contain:
- `ci-cd-standards.md` — workflow inventory + key rules
- `deployment-fix-report.md` — incident reports with RCA
- `runner-failure-runbook.md` — step-by-step startup_failure diagnosis
- `workflow-governance.md` — governance policy for adding/changing workflows
- `github-actions-checklist.md` — pre-merge checklist
- `incident-history.md` — running log of all CI/CD incidents

---

## Diagnostic Output Template

Every investigation produces this structured output:

```
## Incident: <one-line description>

**Date:** YYYY-MM-DD
**Severity:** P1 (production blocked) / P2 (CI blocked) / P3 (warning)
**Category:** A–J (from classification table)

### Observed Symptoms
- <what the user saw>

### Evidence Collected
- <workflow run IDs, conclusions>
- <file sizes, parse results>
- <billing state>

### Root Cause
<one paragraph, no speculation>

### Fix Applied
| File | Change |
|---|---|
| ... | ... |

### Verification
- [ ] Tests pass: `python -m pytest scripts/ -v`
- [ ] Lint clean: `ruff check scripts/`
- [ ] Syntax clean: `python -m compileall scripts/ -q`
- [ ] Workflow YAML valid: passes workflow-validation.yml checks
- [ ] Required files present: dashboard/index.html, data.js, requirements.txt

### Prevention Measures Added
- <new workflow or doc added>

### Status
RESOLVED / OPEN (requires account action)
```

---

## This Repository's Known CI Context

Workflows (see `docs/ci-cd-standards.md` for full inventory):
- `qc.yml` — authoritative pass/fail gate; 12 tabs × 4 FY states
- `dataeng.yml` — data pipeline syntax + build
- `main.yml` — Development environment health-check
- `workflow-validation.yml` — guards against empty/invalid workflows
- `repo-health.yml` — required asset verification
- `deployment-readiness.yml` — deployment pre-flight

**`startup_failure` on this repo as of 2026-08-23:** account-level issue — runners not provisioning. All workflow code is correct. User must verify billing + Actions settings + githubstatus.com. See `docs/deployment-fix-report.md` Issue 2.
