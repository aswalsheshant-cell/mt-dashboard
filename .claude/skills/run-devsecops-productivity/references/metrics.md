# Engineering Metrics — DORA and System-Level Productivity

**Scope:** Metric definitions, measurement approach, and improvement protocols
for the Honasa MT Analytics Platform engineering team. Metrics describe system
health — they are never used to rank or compare individual developers.

---

## Core DORA Metrics

DORA (DevOps Research and Assessment) metrics measure software delivery
performance at the system level. Four key metrics:

### 1. Deployment Frequency

**Definition:** How often code is successfully deployed to production.

**Measurement for this project:**
```
Deployment Frequency = count(merges to main) per calendar week
```

Vercel promotes to production on `workflow_dispatch` after merge to main.
Count only successful productions (not failed deploys or reverts).

**Target:** ≥ 2 per week (Elite: on-demand; High: weekly; Medium: monthly)

**Tracking:** GitHub PR merge log → filter to `base: main` + `merged: true`

### 2. Lead Time for Changes

**Definition:** Time from code committed to running in production.

**Measurement:**
```
Lead Time = production_deploy_timestamp - first_commit_timestamp_in_pr
```

**Target:** < 3 days (Elite: < 1 hour; High: < 1 day; Medium: 1 week)

**Tracking:** PR `created_at` (proxy for first commit if branch is short-lived)
to Vercel deploy timestamp.

### 3. Change Failure Rate

**Definition:** Percentage of deployments that cause a production failure
requiring hotfix, rollback, or patch.

**Measurement:**
```
CFR = (hotfix PRs + production reverts) ÷ total production deploys × 100
```

**Target:** < 5% (Elite: 0–15%; High: 0–15%)

**What counts as a failure:**
- Data.js rebuild produces NaN/undefined in any rendered tab
- A test passes in CI but fails against live data post-deploy
- A Vercel deploy is rolled back within 24 hours of promotion

### 4. Mean Time to Restore (MTTR)

**Definition:** Time from production failure detected to service restored.

**Measurement:**
```
MTTR = restore_timestamp - incident_detected_timestamp
```

**Target:** < 4 hours (Elite: < 1 hour; High: < 1 day)

**Restore options (fastest first):**
1. Vercel rollback to prior deployment (< 5 min)
2. Git revert + fast merge + redeploy (< 30 min)
3. Hotfix branch + PR + merge + redeploy (< 4 hours)

---

## Project-Specific Additional Metrics

Beyond DORA, these metrics are meaningful for the Honasa MT Analytics Platform:

### Test Suite Health

| Metric | Formula | Target |
|---|---|---|
| Test Pass Rate | passing tests ÷ total tests | 100% (gate) |
| Flaky Test Rate | flaky tests ÷ total tests | 0% (zero tolerance) |
| Test Execution Time | wall-clock time for full suite | < 60 seconds |
| Test Coverage (new code) | lines covered ÷ new lines added | > 80% |

### Build Quality

| Metric | Formula | Target |
|---|---|---|
| Build Determinism | builds with byte-identical output ÷ total builds | 100% |
| FY Invariant Violations | FY25/FY26 changes in unintended rebuilds | 0 |
| Compile Error Rate | compile failures ÷ total commits | 0% |
| Bandit HIGH findings | count of HIGH-severity SAST findings | 0 (gate) |

### CI Pipeline Health

| Metric | Formula | Target |
|---|---|---|
| CI Pass Rate | green pipelines ÷ total pipeline runs | > 95% |
| Pipeline Duration (P95) | 95th percentile wall-clock time | < 5 minutes |
| Queue Wait Time (P95) | time from trigger to first job start | < 2 minutes |
| Dependency Audit Availability | successful scans ÷ total attempts | > 95% |

---

## Measurement Collection

### Automated (GitHub Actions)

Each pipeline run writes a metrics snapshot to `outputs/metrics/ci_run_<sha>.json`:

```json
{
  "timestamp": "2026-07-25T12:00:00Z",
  "commit_sha": "72f2840",
  "branch": "claude/june-26-sales-data-xzbhub",
  "stages": {
    "lint_and_compile": { "status": "PASS", "duration_ms": 8200 },
    "unit_tests": { "status": "PASS", "duration_ms": 23800, "tests_run": 177, "tests_failed": 0 },
    "security_scan": { "status": "PASS", "duration_ms": 4100, "bandit_high": 0 },
    "build_check": { "status": "PASS", "duration_ms": 1200 },
    "determinism_check": { "status": "SKIPPED", "reason": "data.js not rebuilt in this run" }
  },
  "overall_status": "PASS",
  "total_duration_ms": 37300
}
```

### Manual (Monthly)

At the end of each month, calculate DORA metrics from GitHub PR history:

```bash
# PR merge count (proxy for deployment frequency)
gh pr list --base main --state merged --json mergedAt --jq '[.[] | .mergedAt] | length'

# Lead time (rough: PR created_at to merged_at)
gh pr list --base main --state merged --json createdAt,mergedAt \
  --jq '.[] | ((.mergedAt | fromdateiso8601) - (.createdAt | fromdateiso8601)) / 3600 | "\(.) hours"'
```

---

## Improvement Protocol

### Reading the Metrics

Metrics are a signal, not a verdict. When a metric degrades:

1. **Identify the constraint.** Where is the bottleneck? (CI speed? PR review queue?
   Flaky tests? Scope creep per PR?)
2. **Propose one change.** Prefer the smallest intervention that addresses the
   root constraint. Multiple simultaneous changes make causation impossible to
   determine.
3. **Measure before and after.** Compare the metric for 2 weeks pre- and
   post-intervention.
4. **Document the experiment.** What was changed, what the hypothesis was, what
   the outcome was. Store in `outputs/metrics/improvements/`.

### What Metrics Are NOT For

- Individual developer performance evaluation
- Sprint velocity targets or story-point quotas
- Justifying headcount decisions
- Comparing team members

Using system metrics for individual evaluation is counterproductive: it
incentivises gaming (splitting PRs to inflate frequency, inflating story points)
rather than improving the system.

### Improvement Backlog

Track improvement ideas in GitHub issues with label `dx/improvement`. Fields:

```markdown
## Improvement: <title>

**Metric(s) affected:** Deployment Frequency / Lead Time / CFR / MTTR / Test Suite Health / ...
**Current baseline:** <value>
**Target:** <value>
**Proposed change:** <one sentence>
**Estimated effort:** <hours/days>
**Measurement window:** <2 weeks / 1 sprint>
```

---

## Monthly Engineering Health Report

Send to the engineering lead at month end. Template:

```markdown
# Engineering Health — <Month YYYY>

## DORA Summary
| Metric | This Month | Last Month | Trend |
|---|---|---|---|
| Deployment Frequency | X/week | Y/week | ↑/↓/→ |
| Lead Time | X days | Y days | ↑/↓/→ |
| Change Failure Rate | X% | Y% | ↑/↓/→ |
| MTTR | X hours | Y hours | ↑/↓/→ |

## Test Suite
- Tests: 177 (X new added, Y removed)
- Flaky tests: 0 (or list)
- Average suite time: Xs

## Security
- Bandit HIGH findings: 0 (or list)
- New exceptions approved: N
- Exceptions expiring next month: N

## CI Pipeline
- Pass rate: X%
- P95 duration: Xs

## Improvement Experiments
- <In progress: experiment title>
- <Completed: experiment title — result>

## Blockers / Escalations
- <If any>
```

---

**Reference version:** 2026-07-25
