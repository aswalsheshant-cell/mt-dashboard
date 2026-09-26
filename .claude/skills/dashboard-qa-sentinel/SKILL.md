---
name: dashboard-qa-sentinel
description: Use after dashboard/index.html, scripts/build_dashboard_data.py or the data.js schema changes, or before a leadership call, to run read-only health checks (raw NaN in data.js, offtake total present, Unmapped Chain not hidden, canvas pattern, FY27+ gating, alert wiring) and report failures with the governed fix route. Never edits data.js, never commits or pushes.
---

# Dashboard QA Sentinel

Read-only monitoring for MT Dashboard runtime & data integrity issues.
Detects issues before they reach leadership calls and routes each one to its governed fix.
It never changes files, commits or pushes on its own.

## Trigger Conditions (Auto-Activate)

1. **Data Pipeline Changes**: `build_dashboard_data.py` modified → validate output
2. **HTML Changes**: `dashboard/index.html` modified → validate rendering logic
3. **Chart Functions**: `render*Chart()` or `build*()` functions edited → regression test
4. **Data Structure Changes**: `offtake`, `primary` schema updated → backward-compat check

## Detection Protocol

On each trigger, run the read-only 30-second audit:

```python
CHECKS = {
    'nan_regression': '/:\s*NaN\b/ in data.js',
    'json_validity': 'JSON.parse(data.js) succeeds',
    'chain_count': 'primary.by_chain.length > 0',
    'offtake_total': 'offtake.total is a positive number (or non-empty FY object)',
    'unmapped_visible': 'No chain view filters out Unmapped Chain',
    'canvas_pattern': 'createElement("canvas") in HTML',
    'fix_integrity': 'All 5 fixes present in code'
}
```

## Fix Routing (report, then fix on a branch — never auto-fix)

`dashboard/data.js` is generated (CLAUDE.md: "DO NOT hand-edit"). A fix to it made by
regex is overwritten by the next rebuild and hides the real bug. Every fix below is
proposed to the user, made on a feature branch, passes the validation sweep in
CLAUDE.md, and merges only with explicit approval.

### Rule 1: NaN Regression (Critical)
- **Detect**: Raw `NaN` in data.js
- **Route**: find where `scripts/build_dashboard_data.py` produces it, fix the generator,
  rebuild, confirm FY25/FY26 blocks are unchanged. Never `sed` data.js.

### Rule 2: Offtake Schema Mismatch (Critical)
- **Detect**: `offtake.total` missing, empty or not a positive number
- **Route**: rebuild with `build_dashboard_data.py --offtake-patch --src <dir>` using the
  real source files. If the source is missing, name the file (BLOCKED_INPUT).

### Rule 3: Unmapped Chain Hidden (Medium)
- **Detect**: a chain view filters out `Unmapped Chain`
- **Route**: Unmapped Chain is a real NSV bucket (FAILURE_MODE_REGISTER FM-17/19/20).
  Hiding it makes chain totals stop tying to Primary. Reduce it through mapping
  governance (FM-19); whether to show it in a view is a business display decision.

### Rule 4: Canvas Element Missing (Medium)
- **Detect**: `getContext('2d')` on non-canvas in `render*Chart()`
- **Route**: create the canvas in the chart's container before the `mk*` call:
  ```javascript
  const cvDiv = document.getElementById('cvXXX');
  const cv = document.createElement('canvas');
  cvDiv.appendChild(cv);
  ```

### Rule 5: FY27+ Gating Missing (Low)
- **Detect**: FY27+ rendering without the `fyBeyondPreagg()` / `FPX(tag)` gate
- **Route**: restore the gate (CLAUDE.md, THE ONE FY RULE). When an FY has no data,
  show `–` or "not in source". **Never** copy another FY's numbers into the missing FY —
  that presents FY26 figures as FY27 (fabricated data).

## Decision Tree

```
Issue Detected?
├─ YES → Report (issue, failed assertion, governed route) → wait for user approval
│        → fix on a branch → validation sweep → PR (never push to main)
└─ NO  → Pass, log success
```

## Notification Format

**On Pass**:
```
✅ Dashboard QA Sentinel: [n]/[n] checks passed (read-only; no files changed)
```

**On Failure** (requires human):
```
❌ Dashboard QA Sentinel: Manual intervention needed
   Issue: [Description]
   Check: [Failed assertion]
   Suggestion: [Proposed fix]
   Action: Awaiting your approval
```

## How to Run

```bash
node .claude/skills/dashboard-qa-sentinel/auto-fix.js   # read-only; exit 1 if a critical check fails
```

The script keeps its old file name so existing references still work, but it only reads
`dashboard/data.js` and `dashboard/index.html` and writes the report below. Do not wire it
into a pre-commit hook or workflow that stages, commits or pushes files.

## Monitoring Dashboard

Check `/tmp/dashboard_qa_sentinel_report.json` after each run:
```json
{
  "timestamp": "2026-09-06T12:34:56Z",
  "branch": "main",
  "checks_run": 8,
  "passed": 7,
  "failed": 1,
  "issues": [
    {
      "check": "nan_regression",
      "status": "FAILED",
      "detail": "Raw NaN found in dashboard/data.js"
    }
  ]
}
```

## Limitations & Manual Escalation

**Always escalate to the user (in addition to every rule above):**
- P&L/Compliance data missing (separate build path)
- Power BI schema changes (requires manual mapping)
- New tab rendering (architectural change)
- Data content issues (requires SME validation)

**Escalation Template:**
```
🟡 QA Sentinel escalates to user:

Issue: [Description]
Root cause: [Analysis]
Why it needs you: [Reason]
Recommended action: [Next step]
Estimated effort: [Low/Medium/High]
```

---

## Files This Skill Monitors

- `dashboard/index.html` — Rendering logic, chart functions, tab wiring
- `dashboard/data.js` — JSON validity, schema, data completeness
- `scripts/build_dashboard_data.py` — Data transformation logic
- `.github/workflows/dashboard-health-check.yml` — CI/CD validation

## Success Metrics

- **Mean Time to Detection (MTTD)**: < 2 minutes (CI runs)
- **Mean Time to Report**: < 5 minutes (issue + governed route in front of the user)
- **False Positive Rate**: < 5% (only real regressions reported)
- **Leadership Call Readiness**: 100% (zero data surprises)
