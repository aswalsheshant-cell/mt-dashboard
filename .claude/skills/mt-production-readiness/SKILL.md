---
name: mt-production-readiness
description: |
  Production readiness review, security audit, documentation generation, continuous
  improvement tracking, and monthly release automation for the Honasa MT Analytics Platform.
  Auto-activates before marking ANY task complete. Also triggers on: "is this ready",
  "ready to release", "production check", "security review", "generate docs",
  "release notes", "deployment checklist", "what's the technical debt", "security audit",
  "PII check", "secrets check", "permissions review", "document this", "write the guide",
  "user guide", "improvement backlog", "what should we improve next", "monthly release",
  "release automation", "deployment guide", "regression check", "go/no-go".
  Nothing is marked COMPLETE until this skill's 10-gate checklist passes.
---

# MT Production Readiness

The final gate before any release. Nothing ships without passing all ten gates.

## The 10-Gate Production Checklist

```
PRODUCTION READINESS REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Gate 1 — ARCHITECTURE PASS
  □ No quick fixes — solution is scalable and maintainable
  □ Impact analysis completed and documented
  □ No hardcoded FY values (FY25/FY26 only) introduced
  □ No binary .pbix committed to Git

Gate 2 — PERFORMANCE PASS
  □ data.js size acceptable (≤9MB ceiling)
  □ Dashboard loads in <3s on clean browser cache
  □ No SUMX over full fact tables where SUM(column) works
  □ Unused Power Query columns removed

Gate 3 — BUSINESS PASS
  □ Primary / Offtake / P&L business rules validated
  □ FY25/FY26 regression — prior totals unchanged
  □ Allocation logic verified against Business Logic Guardian
  □ Reliance Brand Counter filter confirmed

Gate 4 — SECURITY PASS
  □ No secrets / tokens / passwords in committed code
  □ No PII (customer names, phone numbers, addresses) in data.js
  □ GitHub repository visibility confirmed (private for raw data)
  □ data.js contains only aggregated metrics — no row-level PII

Gate 5 — QC PASS
  □ Health Score ≥ 95 (or exceptions documented and approved)
  □ Zero unexplained reconciliation differences
  □ All 12 QC gates from mt-data-governance passed
  □ No NaN / undefined / empty-broken cards in dashboard

Gate 6 — DOCUMENTATION PASS
  □ CLAUDE.md reflects any new architectural decisions
  □ Business rule changes documented in docs/BUSINESS_RULES.md
  □ New KPIs added to docs/KPI_DICTIONARY.md
  □ Data issue records updated (docs/data-issues/)

Gate 7 — GIT PASS
  □ Clean branch — no uncommitted changes
  □ PR description includes: what changed, impact analysis, regression status
  □ Commit messages follow standard format
  □ No merge conflicts

Gate 8 — PBIP PASS (Power BI changes only)
  □ No .pbix committed
  □ TMDL / JSON files updated
  □ Relationships validated in text format

Gate 9 — AUTOMATION PASS (pipeline changes only)
  □ Pipeline runs end-to-end without errors
  □ Output is idempotent (rerun produces same result)
  □ Partial refresh modes (--primary-only, --offtake-patch) still work

Gate 10 — EXECUTIVE REVIEW PASS
  □ Dashboard numbers spot-checked against source data for current period
  □ Key cards and totals verified manually for latest FY
  □ Release note written in non-technical language for business stakeholders

VERDICT: [ ] PASS  [ ] PASS WITH WARNINGS  [ ] BLOCKED
```

## Security Audit Checklist

Run before every PR merge and monthly:

```python
SECURITY_CHECKLIST = {
    "secrets": [
        "No API keys / tokens in .py, .js, .html, .json files",
        "No passwords in build scripts",
        ".env files in .gitignore",
        "No credentials in CLAUDE.md or docs/",
    ],
    "pii": [
        "data.js contains only aggregated metrics — no store-employee mapping at PII level",
        "No customer names or contact details in any committed file",
        "No personally identifiable distributor contact info",
    ],
    "repository": [
        "Source .xlsb/.xlsx files are in .gitignore (never committed)",
        "GitHub repo is private (raw financial data)",
        "GitHub Actions secrets used for any CI/CD credentials",
    ],
    "power_bi": [
        "Power BI workspace access restricted to authorized users",
        "Sensitivity labels applied to reports with financial data",
        "Row-level security (RLS) configured if report shared externally",
    ],
}
```

## Documentation Generator

Every completed feature automatically produces these artifacts:

### Feature Documentation Template
```markdown
## [Feature Name] — Release [Date]

### Architecture
[What was built, which components were added/modified]

### Business Rule
[Which business rules govern this feature — reference BUSINESS_RULES.md]

### Data Flow
[Source → Transform → Output path]

### Technical Notes
[Any non-obvious implementation decisions, workarounds, constraints]

### Data Dictionary
[New fields/metrics added — name, description, formula, grain, source]

### Measure Dictionary (Power BI only)
[New DAX measures — name, formula, dependencies, usage]

### User Guide
[How does a business user use this feature? Step-by-step]

### Support Guide
[Common issues, how to diagnose, how to fix]

### Known Limitations
[What this feature does NOT do, and why]
```

### Release Note Template (non-technical, for business)
```markdown
## MT Dashboard Release — [Date]

### What's New
- [Plain-English description — what can users now see or do?]

### What's Fixed
- [Plain-English description of any corrections]

### Numbers to Verify
- [Tell the business user what to spot-check to confirm the release is correct]

### Next Planned Update
- [One sentence on what's coming next]
```

## Continuous Improvement Engine

After every release, auto-generate:

```
IMPROVEMENT REGISTER — Post-Release [Date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TECHNICAL DEBT
  TD-001: [description] | Effort: S/M/L | Impact: High/Med/Low
  TD-002: ...

RISK REGISTER
  R-001: [risk description] | Likelihood: H/M/L | Mitigation: [action]

IMPROVEMENT BACKLOG
  Priority: [P1/P2/P3]
  [Feature or fix] — Business value: [one sentence] — Effort: [S/M/L]

PERFORMANCE OPPORTUNITIES
  [Where is the dashboard / pipeline slowest? What would a 2× speed-up require?]

AUTOMATION OPPORTUNITIES
  [What is still done manually that could be automated?]

AI OPPORTUNITIES
  [What insights are generated manually that AI could surface automatically?]

BUSINESS OPPORTUNITIES
  [What questions do stakeholders ask repeatedly that the dashboard doesn't answer?]
```

## Monthly Release Automation Checklist

```
MONTHLY MT DASHBOARD RELEASE — [Month FY]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Source files received: Primary / Offtake / P&L (confirm with data owner)
□ File validation: schema, row count, date range confirmed
□ Pipeline run: python build_dashboard_data.py --[mode] --src [dir] --out dashboard/data.js
□ QC report generated and reviewed (Health Score ≥ 95)
□ Regression check: FY25/FY26 totals unchanged from prior release
□ New period data spot-checked against source (5 spot checks minimum)
□ All 12 tabs × 4 FY states swept — no errors, no broken cards
□ Release note written
□ Git commit + PR created
□ Stakeholder notification sent
□ data.js backed up (tag: release/[fy]-[month])
```

## Files-to-Prompt Usage (feed project to Claude)

The `files-to-prompt` tool (included in this repo's tooling) lets you bundle the
entire codebase into one context for Claude:

```bash
# Install
pip install files-to-prompt

# Feed the whole dashboard to Claude (Claude XML format)
files-to-prompt dashboard/ scripts/ docs/ CLAUDE.md --cxml -o /tmp/mt-context.xml

# Feed only the scripts (for pipeline debugging)
files-to-prompt scripts/ -e py --cxml -o /tmp/scripts-context.xml

# Feed with line numbers (for precise code review)
files-to-prompt dashboard/index.html -n --markdown

# Ignore generated files (data.js is huge)
files-to-prompt dashboard/ --ignore "data.js" --ignore "*.min.js" --cxml
```

Then paste the output into Claude for full-context analysis or debugging.

## Go / No-Go Decision

```
GO:     All 10 gates PASS — release immediately
HOLD:   1–2 gates PASS WITH WARNINGS — document exceptions, get business approval
NO-GO:  Any gate BLOCKED — stop, fix root cause, re-run all gates
```

Never override a NO-GO without explicit written approval from the business owner.
Document the override in the PR description with reason and approver name.
