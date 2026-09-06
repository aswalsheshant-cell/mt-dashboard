# Dashboard QA Sentinel

Autonomous monitoring and auto-fix for MT Dashboard runtime & data integrity issues.
Detects and resolves issues before they reach leadership calls.

## Trigger Conditions (Auto-Activate)

1. **Data Pipeline Changes**: `build_dashboard_data.py` modified → validate output
2. **HTML Changes**: `dashboard/index.html` modified → validate rendering logic
3. **Chart Functions**: `render*Chart()` or `build*()` functions edited → regression test
4. **Data Structure Changes**: `offtake`, `primary` schema updated → backward-compat check

## Detection Protocol

On each trigger, automatically run 30-second audit:

```python
CHECKS = {
    'nan_regression': '/:\s*NaN\b/ in data.js',
    'json_validity': 'JSON.parse(data.js) succeeds',
    'chain_count': 'primary.by_chain.length > 0',
    'offtake_total': 'offtake.total exists and has fy keys',
    'unmapped_filter': 'No Unmapped Chain in output chains',
    'canvas_pattern': 'createElement("canvas") in HTML',
    'fix_integrity': 'All 5 fixes present in code'
}
```

## Auto-Fix Rules

**If Check Fails → Auto-Fix Without Asking:**

### Rule 1: NaN Regression (Critical)
- **Detect**: Raw `NaN` in data.js
- **Fix**: Run regex `s/:\s*NaN\b/: null/g` on data.js
- **Log**: "Fixed NaN regression: X→null"
- **Action**: Commit & push immediately

### Rule 2: Offtake Schema Mismatch (Critical)
- **Detect**: `offtake.total` missing or empty
- **Fix**: Regenerate `data.js` using `build_dashboard_data.py --offtake-patch`
- **Log**: "Offtake schema regenerated"
- **Action**: Commit & push

### Rule 3: Unmapped Chain Leak (Medium)
- **Detect**: `Unmapped Chain` in output primary chains
- **Fix**: Add `.filter(c=>c.name!=='Unmapped Chain')` to buildChannelDynamics
- **Log**: "Unmapped chain filter restored"
- **Action**: Commit & push

### Rule 4: Canvas Element Missing (Medium)
- **Detect**: `getContext('2d')` on non-canvas in `render*Chart()`
- **Fix**: Inject canvas creation:
  ```javascript
  const cvDiv = document.getElementById('cvXXX');
  const cv = document.createElement('canvas');
  cvDiv.appendChild(cv);
  ```
- **Log**: "Canvas creation pattern added to renderXXXChart"
- **Action**: Commit & push

### Rule 5: FY Fallback Missing (Low)
- **Detect**: FY27 selected but no fallback logic in buildChannelDynamics
- **Fix**: Add fallback:
  ```javascript
  if (!data[primYr]) {
    data = {...data, [primYr]: data[fallbackFy]};
  }
  ```
- **Log**: "FY fallback logic restored"
- **Action**: Commit & push

## Decision Tree

```
Issue Detected?
├─ YES + Critical + Auto-Fixable
│  └─ Apply Fix → Test → Commit → Notify User
├─ YES + Critical + Requires Input
│  └─ Flag to User (ask: "approve this fix?")
└─ NO
   └─ Silent pass, log success
```

## Notification Format

**On Success** (auto-fix applied):
```
✅ Dashboard QA Sentinel: Auto-fixed [ISSUE]
   Issue: [Description]
   Fix: [Code change]
   Commit: [SHA]
   Action: Pushed to [branch]
```

**On Failure** (requires human):
```
❌ Dashboard QA Sentinel: Manual intervention needed
   Issue: [Description]
   Check: [Failed assertion]
   Suggestion: [Proposed fix]
   Action: Awaiting your approval
```

## Activation Instructions

### 1. Enable in CI/CD (GitHub Actions)
   Add step to `.github/workflows/dashboard-health-check.yml`:
   ```yaml
   - name: Run Dashboard QA Sentinel
     if: failure()
     uses: claude-code-remote://sentinel
     with:
       action: auto-fix
       branch: ${{ github.head_ref }}
   ```

### 2. Enable Locally (Pre-Commit Hook)
   Add to `.git/hooks/pre-commit`:
   ```bash
   node scripts/verify_data_health.js || \
   (echo "Running QA Sentinel auto-fix..." && \
    node .claude/skills/dashboard-qa-sentinel/auto-fix.js && \
    git add dashboard/data.js dashboard/index.html && \
    echo "✅ Auto-fixes applied")
   ```

### 3. Manual Trigger (On-Demand)
   ```bash
   npm run sentinel:check     # Run checks only
   npm run sentinel:fix       # Apply all fixes
   npm run sentinel:report    # Generate report
   ```

## Monitoring Dashboard

Check `/tmp/dashboard_qa_sentinel_report.json` after each run:
```json
{
  "timestamp": "2026-09-06T12:34:56Z",
  "branch": "main",
  "checks_run": 8,
  "passed": 7,
  "failed": 1,
  "auto_fixed": 1,
  "issues": [
    {
      "check": "nan_regression",
      "status": "FIXED",
      "detail": "Replaced 23 NaN with null"
    }
  ]
}
```

## Response Format for Auto-Fixes

Every fix commit MUST include:

```
fix(dashboard): [Issue Name]

Sentinel auto-fix: [Description]

Checks run: [count]
Passed: [count]
Failed: [count]
Fixed: [description]

Co-Authored-By: Dashboard QA Sentinel <noreply@anthropic.com>
Claude-Session: [link]
```

## Limitations & Manual Escalation

**Cannot Auto-Fix (Escalate to User):**
- P&L/Compliance data missing (separate build path)
- Power BI schema changes (requires manual mapping)
- New tab rendering (architectural change)
- Data content issues (requires SME validation)

**Escalation Template:**
```
🟡 QA Sentinel escalates to user:

Issue: [Description]
Root cause: [Analysis]
Why auto-fix blocked: [Reason]
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
- **Mean Time to Resolution (MTTR)**: < 5 minutes (auto-fix)
- **False Positive Rate**: < 5% (only real regressions fixed)
- **Leadership Call Readiness**: 100% (zero data surprises)
