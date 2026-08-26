# CI/CD Incident History — mt-dashboard

Append new incidents at the bottom. One row per distinct root cause.
Full RCA for major incidents goes in a separate `deployment-fix-report-YYYY-MM-DD.md`.

---

## Incident Log

| Date | Category | Symptom | Root Cause | Fix | Status | PR |
|---|---|---|---|---|---|---|
| 2026-08-23 | A | Development deployment red — `conclusion: failure` on every run | `.github/workflows/main.yml` was empty (single blank line); YAML parse error before runner started | Replaced with valid `health-check` workflow targeting `environment: Development` | RESOLVED | #49 |
| 2026-08-23 | C | `startup_failure` across ALL workflows | "ChatGPT Codex Connector" GitHub App suspended — suspended app installation blocks runner token generation for the entire repo | Unsuspend the app: GitHub → Settings → Applications → Installed GitHub Apps → ChatGPT Codex Connector → Danger zone → Unsuspend | RESOLVED — pending workflow re-run confirmation | #49 #51 |
| 2026-08-23 | B | Labeler workflow crashes with "labeler.yml not found" | `.github/labeler.yml` config file missing from repo | Created `.github/labeler.yml` with path-based label rules | RESOLVED | #49 |
| 2026-08-23 | B | Conda workflow `build-linux` fails with "environment.yml not found" | `environment.yml` missing from repo root | Created `environment.yml` with Python 3.11 + pip dependencies | RESOLVED | #49 |
| 2026-08-23 | J | `NameError: name 'sys' is not defined` in `test_dashboard_disclosures.py` | Missing `import sys` at module level | Added `import sys` | RESOLVED | #49 |
| 2026-08-23 | J | `NameError: name 'true' is not defined` in `release_gate.py` | JSON boolean `true` used in Python context | Changed to Python `True` | RESOLVED | #49 |
| 2026-08-23 | J | `_check_governance_gate` TypeError: unexpected keyword argument | Function signature used `gate_pct` but caller passed `pct` | Renamed parameter to `gate_pct` | RESOLVED | #49 |
| 2026-08-23 | J | `reliance_bc` FY27 double-count in `data.js` (by_zone diff=86.26) | `_merge_dim` added old FY data on top of new source instead of only carrying FYs not in new source | Fixed `_merge_dim` to use `safe_kept_fy_tags`; corrected 7 fy27-only `by_state` entries | RESOLVED | #49 |

---

## Category Reference

| Cat | Name |
|---|---|
| A | Workflow Syntax |
| B | Repository Configuration |
| C | Actions Permissions |
| D | Billing / Usage Limits |
| E | Environment Configuration |
| F | Secrets Configuration |
| G | Runner Availability |
| H | GitHub Platform Incident |
| I | Deployment Failure |
| J | Code Failure |

See `docs/runner-failure-runbook.md` for the full diagnosis decision tree.

---

## Incident — Runner Provisioning Blocked (2026-08-23, RESOLVED PENDING CONFIRMATION)

**Root cause identified:** "ChatGPT Codex Connector" GitHub App was **suspended** in the account's installed apps. A suspended app installation blocks GitHub from generating runner tokens for workflows in the repo, causing immediate `startup_failure` before any runner is allocated.

**Fix:** Unsuspend the app at: GitHub → Settings → Applications → Installed GitHub Apps → ChatGPT Codex Connector → Danger zone → **Unsuspend**

**Closure criteria:** At least one workflow run shows `conclusion: success` after unsuspension.
