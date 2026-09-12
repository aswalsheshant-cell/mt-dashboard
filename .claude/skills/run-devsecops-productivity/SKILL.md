---
name: run-devsecops-productivity
description: |
  Unified DevSecOps and engineering-productivity skill for the Honasa / Mamaearth
  MT Analytics Platform. Use this skill for: CI/CD and GitHub Actions pipeline design,
  secure build and deployment, application-security testing, security-risk assessments
  and remediation, least-privilege workflow permissions, DORA-style engineering metrics,
  developer experience and IDE practices, responsible AI-assistant adoption in code
  workflows, and continuous feedback loops.
  Do NOT use for: generic CI/CD definitions, dependency CVE scanning (use
  secure-dependencies), agent execution controls (use run-evidence-grounded-agents),
  or Power BI / data-engineering quality checks (use their respective agents).
---

# Run DevSecOps & Productivity — Unified Engineering Operations

## Purpose

Embed security into every phase of the engineering lifecycle — from local dev to
production deployment — while measuring and improving team throughput, change
stability, and developer experience. Security is not a gate at the end; it is a
property of each step.

## Standing Rules

1. **Shift left.** Security checks run locally and in CI before code reaches review,
   not as a post-merge gate.
2. **Least privilege everywhere.** GitHub Actions tokens, deployment credentials, and
   developer access are scoped to the minimum required for each job.
3. **Every build is reproducible.** A given commit hash must produce byte-identical
   output on any runner, any time.
4. **Metrics are for system improvement, not individual ranking.** DORA and
   productivity metrics identify bottlenecks in the system; they are never used to
   evaluate or compare individual developers.
5. **AI assistants accelerate, not replace, human judgement.** Copilot and Claude
   Code suggestions are reviewed with the same rigour as human-authored code (see
   `run-evidence-grounded-agents` for AI code verification).
6. **Fail fast, recover faster.** Pipelines fail at the earliest possible check;
   rollback paths are defined before deployment, not after failure.

---

## CI/CD Pipeline Design

See `references/pipeline.md` for the full pipeline specification.

**Quick reference — required stages for this project:**

```
1. lint-and-compile     python -m py_compile + pylint/flake8
2. unit-tests           python -m unittest discover (177 tests; must all pass)
3. security-scan        bandit -r scripts/ + dependency audit
4. build-check          build_dashboard_data.py compile gate
5. determinism-check    two-run byte-identical output (FY-specific blocks)
6. deploy-preview       Vercel preview on PR branches
7. deploy-production    Vercel production on main (manual gate required)
```

No stage may be skipped. A failing stage blocks all subsequent stages.

---

## Application Security Testing

See `references/security-testing.md` for SAST, DAST, and secret-scanning protocols.

**Quick reference:**

- Static analysis: bandit (Python), eslint-security (JS) — run on every PR
- Secret scanning: detect-secrets pre-commit hook; GitHub secret scanning enabled
- Dependency audit: pip-audit + safety on every push (see `secure-dependencies`)
- DAST: manual sweep of all 12 dashboard tabs after every data.js rebuild
- Penetration testing: quarterly manual review of dashboard JS for XSS / prototype
  pollution / CSP bypasses

---

## Least-Privilege Workflow Permissions

**GitHub Actions token permissions — default for all jobs:**

```yaml
permissions:
  contents: read     # never write unless the job explicitly needs it
  pull-requests: read
  checks: none
  deployments: none
```

**Override only where required:**

```yaml
# Job that comments on a PR
permissions:
  pull-requests: write
  contents: read

# Job that pushes a tag or release artifact
permissions:
  contents: write
  pull-requests: read
```

Never use `permissions: write-all`. Never use `GITHUB_TOKEN` for actions that
could be done with a scoped PAT. Rotate PATs on a 90-day schedule.

---

## Engineering Metrics (DORA + Local)

See `references/metrics.md` for full metric definitions and measurement approach.

**Target thresholds for this project:**

| Metric | Target | Current Measurement |
|---|---|---|
| Deployment Frequency | ≥ 2 per week | PR merge rate to main |
| Lead Time for Changes | < 3 days | PR open → merge |
| Change Failure Rate | < 5% | Reverts + hotfixes ÷ total merges |
| Mean Time to Restore | < 4 hours | Incident open → resolved |
| Test Pass Rate | 100% (gate) | `python -m unittest discover` |
| Build Determinism | 100% | Two-run hash comparison |

---

## Developer Experience

See `references/developer-experience.md` for local setup, IDE configuration,
AI-assistant adoption, and feedback loop practices.

**Quick reference:**

- Local pre-commit: py_compile + bandit + unit tests (< 30 s total)
- Branch protection: require 1 reviewer + all CI checks before merge to main
- PR size target: < 400 lines changed (large PRs reviewed in segments)
- Onboarding: new contributor can run full test suite within 30 minutes of clone
- Feedback cadence: weekly retro on blocked PRs, flaky tests, slow CI stages

---

## Interaction with Other Skills

| Need | Route to |
|---|---|
| Dependency CVEs, SBOM, license compliance | `secure-dependencies` |
| Agent bounded execution, evidence grounding, prompt injection | `run-evidence-grounded-agents` |
| Dashboard data quality, FY validation, metric reconciliation | `honasa-data-engineering` |
| CM2 provisional governance | `honasa-cm2-expense-classification` |
| Dashboard QC, release readiness | `honasa-dashboard-qc-reconciliation` |
| **CI/CD, security testing, DORA metrics, developer experience** | **this skill** |

---

**Last Updated:** 2026-07-25
**Maintained By:** Data Engineering / Security
**Scope:** All CI/CD, security-testing, and developer-productivity operations on the
Honasa MT Analytics Platform
