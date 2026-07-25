# CI/CD Pipeline — Design, Validation, and Rollback

**Scope:** GitHub Actions pipeline structure, stage definitions, secure build
practices, deployment gates, and rollback procedures for the Honasa MT Dashboard.

---

## Pipeline Architecture

### Trigger Rules

```yaml
on:
  push:
    branches: ["**"]           # all branches: run lint, test, security-scan
  pull_request:
    branches: [main]           # PRs to main: run full pipeline including build-check
  workflow_dispatch:           # manual trigger for production deploy
```

Production deployment (`deploy-production`) triggers only on `workflow_dispatch`
after a human explicitly approves the deploy. It never triggers automatically on
push to main — the dashboard is a static site deployed via Vercel, and Vercel
handles preview automatically; production promotion is intentional.

### Stage Dependency Graph

```
lint-and-compile
     │
     ▼
unit-tests ──── security-scan
     │                │
     └────────┬───────┘
              ▼
         build-check
              │
              ▼
      determinism-check
              │
        ┌─────┴──────┐
        ▼             ▼
  deploy-preview  (manual gate)
                       │
                       ▼
                deploy-production
```

`deploy-preview` and `deploy-production` are separate jobs. Preview runs on every
PR branch automatically (Vercel handles this). Production is `workflow_dispatch` only.

---

## Stage Specifications

### Stage 1 — Lint and Compile

**Purpose:** Catch syntax errors and import failures before any test runs.

```yaml
- name: Compile check
  run: python -m py_compile scripts/build_dashboard_data.py

- name: Lint
  run: |
    pip install flake8
    flake8 scripts/ --max-line-length=120 --ignore=E501,W503
```

**Gate:** Exit non-zero on any syntax or import error. Flake8 warnings are reported
but do not block (exit 0) unless configured to fail on specific codes.

**Duration target:** < 30 seconds.

### Stage 2 — Unit Tests

**Purpose:** Confirm all 177 project tests pass with no regressions.

```yaml
- name: Run tests
  run: python -m unittest discover -s tests -p 'test_*.py'
```

**Gate:** Any test failure blocks the pipeline. New tests added by a PR must
pass on the first run — no `expectedFailure` waivers without documented justification.

**Duration target:** < 60 seconds.

### Stage 3 — Security Scan

**Purpose:** SAST + dependency audit on every PR (see `security-testing.md`
for full protocol).

```yaml
- name: Bandit SAST
  run: |
    pip install bandit
    bandit -r scripts/ -ll --exit-zero  # medium+ severity reported; high = fail

- name: Dependency audit
  run: |
    pip install pip-audit safety
    pip-audit || true        # exit 2 (unavailable) is non-blocking
    safety check || true     # exit 2 (unavailable) is non-blocking
```

**Gate:** bandit HIGH severity = pipeline fail. Dependency audit exits 1 (CVE
found without exception) = pipeline fail. Exit 2 (scanner unavailable) = alert
ops, do not block.

### Stage 4 — Build Check

**Purpose:** Confirm `build_dashboard_data.py` compiles and imports cleanly.
Does not run a full rebuild (source workbooks are not in the repo).

```yaml
- name: Build script compile
  run: python -m py_compile scripts/build_dashboard_data.py

- name: Data engineering health (read-only)
  run: python3 -m scripts.dataeng.cli health
  continue-on-error: false
```

**Gate:** Health check exit non-zero = pipeline fail.

### Stage 5 — Determinism Check

**Purpose:** Verify that any data.js rebuild is byte-identical on two consecutive
runs. Catches non-determinism from `set()`, `hash()`, timestamp injection, or
random sampling.

```yaml
- name: Determinism check (if data.js was rebuilt)
  if: ${{ steps.detect_rebuild.outputs.rebuilt == 'true' }}
  run: |
    sha256sum /tmp/build1.js /tmp/build2.js
    diff /tmp/build1.js /tmp/build2.js
```

Non-determinism is a pipeline fail. The fix is always in the build script —
use `hashlib.sha256`, sort with explicit keys, use `Decimal` for money.

---

## Secure Build Practices

### Pinned Actions

All `uses:` references must pin to a full commit SHA, not a floating tag:

```yaml
# WRONG — floating tag can be hijacked
uses: actions/checkout@v4

# RIGHT — pinned to exact commit
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
```

Unpin and re-pin during planned upgrades only. Run `dependabot` or manual audit
quarterly to check for action CVEs.

### Secret Handling in CI

- Secrets are injected via GitHub Actions `secrets.*` — never hardcoded in YAML
- Secret names are UPPER_SNAKE_CASE: `VERCEL_TOKEN`, `SLACK_WEBHOOK_URL`
- Mask secrets in logs: GitHub Actions masks them automatically when injected via
  `${{ secrets.* }}` — never echo secrets directly
- No secret is passed as a positional argument to a command (visible in `ps`)
- Use `::add-mask::` for derived secrets computed in a step:
  ```yaml
  - run: echo "::add-mask::$DERIVED_TOKEN"
  ```

### Artifact Integrity

Every build artifact uploaded to GitHub Actions or deployed to Vercel must have
its SHA-256 recorded in the workflow summary:

```yaml
- name: Record artifact hash
  run: |
    sha256sum dashboard/data.js >> $GITHUB_STEP_SUMMARY
    echo "data.js SHA-256: $(sha256sum dashboard/data.js | cut -d' ' -f1)" >> $GITHUB_STEP_SUMMARY
```

---

## Deployment Gates

### Preview Deployment (Automatic)

Vercel deploys a preview on every push to any PR branch. No manual gate.
Preview URL is posted to the PR by Vercel bot.

**Verification before merge:**
1. Open the preview URL
2. Sweep all 12 tabs in FY25, FY26, FY27 states
3. Confirm no NaN / undefined / broken cards / JS errors
4. Confirm FY25/FY26 numbers unchanged if only FY27 was intended to change

### Production Deployment (Manual Gate)

Production promotion to Vercel is `workflow_dispatch` only:

```yaml
deploy-production:
  needs: [determinism-check]
  if: github.event_name == 'workflow_dispatch'
  environment:
    name: production
    url: https://mt-dashboard.vercel.app
  runs-on: ubuntu-latest
```

The `environment: production` block enables GitHub's environment protection rules:
required reviewers, deployment branch restrictions, and manual approval. Configure
at least 1 required reviewer in the repository's Environment settings.

---

## Rollback Procedure

### Vercel Rollback (< 5 minutes)

Vercel retains all previous deployments. To roll back:

1. Go to Vercel dashboard → mt-dashboard → Deployments
2. Find the last known-good deployment
3. Click "Promote to Production"
4. Verify the rollback URL serves the correct version

### Git Revert (for source changes)

When a broken commit reaches main:

```bash
# Identify the bad commit
git log --oneline -10

# Create a revert commit (do NOT force-push main)
git revert <bad-commit-sha> --no-edit
git push origin main
```

Never `git reset --hard` on main — it rewrites shared history. Always revert.

### Emergency Hotfix Branch

If a revert is insufficient (e.g., data corruption requires a patch):

```bash
git checkout -b hotfix/<description> main
# apply minimal fix
git push -u origin hotfix/<description>
# open PR, get 1 reviewer approval, merge immediately
```

Hotfix branches skip the "draft" convention — they are regular PRs merged with
urgency. Document the incident in `outputs/incidents/` after stabilisation.

---

## Pipeline Maintenance

### When to Update Pinned Actions

- Security advisory published for an action → update within 48 hours
- Major version bump available → evaluate quarterly; update after review
- GitHub announces deprecation → update before EOL date

### Flaky Test Protocol

A test that fails intermittently is worse than no test (it trains engineers to
ignore failures). On the first observed flake:

1. Add `@unittest.skip("FLAKY — <issue URL>")` immediately
2. Open a GitHub issue with repro steps and failure log
3. Fix the root cause (usually timing, test ordering, or external state)
4. Re-enable the test and confirm 10 consecutive green runs before removing skip

### CI Cost Management

- Cache pip dependencies between runs: `actions/cache` on `~/.cache/pip`
- Run security scans only when `scripts/` or `requirements*.txt` changed (path filter)
- Run determinism check only when `data.js` or `build_dashboard_data.py` changed

---

**Reference version:** 2026-07-25
