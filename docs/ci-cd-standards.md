# CI/CD Standards — mt-dashboard

## Workflow inventory

| File | Purpose | Trigger |
|---|---|---|
| `qc.yml` | Dashboard QC: compileall, ruff, pytest, Playwright sweep | push all branches, PR → main |
| `dataeng.yml` | Data engineering: script syntax, Node build, pytest, QC gate | push scripts/data, PR → main |
| `main.yml` | Development environment health-check | push all branches |
| `workflow-validation.yml` | Guard: blocks empty/invalid workflow files | push/PR to .github/workflows/ |
| `label.yml` | Auto-label PRs by changed file path | pull_request_target |
| `python-package-conda.yml` | Conda environment build + flake8 + pytest | push |
| `azure-webapps-node.yml` | Azure Web Apps Node deployment | push |
| `codeql.yml` | CodeQL security scanning | push, PR, schedule |
| `monthly-central-zone-ppt.yml` | Generate Central Zone leadership PPT | schedule / manual |
| `stale.yml` | Mark stale issues and PRs | schedule |
| `summary.yml` | Summarise new issues | issues.opened |
| `npm-publish-github-packages.yml` | Publish Node package to GitHub Packages | release |

## Key rules

1. **Never commit an empty workflow file.** An empty `.yml` in `.github/workflows/`
   causes `conclusion: failure` on every run — indistinguishable from a real test failure.
   The `workflow-validation.yml` guard enforces this automatically.

2. **`startup_failure` ≠ code error.** If every workflow shows `startup_failure`, the
   issue is account-level (billing limit, Actions disabled, GitHub outage). Check
   `githubstatus.com` and `Settings → Billing` before debugging YAML.

3. **`failure` on `main.yml`** historically meant the file was empty (parse error).
   After the fix, a real code failure in the health-check steps would show `failure`
   with actual log output — check Actions → Development → latest run logs.

4. **Deployment environments:**
   - `Development` — driven by `main.yml`, runs on every push to any branch
   - `Preview` and `Production` — driven by Vercel, independent of GitHub Actions runners

5. **QC gate (qc.yml) is the authoritative pass/fail gate.** All 12 dashboard tabs ×
   4 FY states must pass before a PR touches `dashboard/data.js`.

## Incident history

| Date | Incident | Fix |
|---|---|---|
| 2026-08-23 | Development deployment red — empty `main.yml` | Replaced with valid health-check workflow (PR #49) |
| 2026-08-23 | `startup_failure` across all workflows | Account-level issue — see deployment-fix-report.md |
| 2026-08-23 | `NameError: sys` in test_dashboard_disclosures.py | Added `import sys` |
| 2026-08-23 | `NameError: true` in release_gate.py | Changed JSON `true` → Python `True` |
| 2026-08-23 | Labeler workflow: labeler.yml not found | Created `.github/labeler.yml` |
| 2026-08-23 | Conda workflow: environment.yml not found | Created `environment.yml` |
| 2026-08-23 | `_check_governance_gate` wrong parameter name | Renamed to `gate_pct` |
| 2026-08-23 | `reliance_bc` FY27 double-count in data.js | Fixed `_merge_dim` + corrected data.js |
