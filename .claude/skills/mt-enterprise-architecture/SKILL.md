---
name: mt-enterprise-architecture
description: |
  Enterprise solution architecture, Git governance, impact analysis, and dependency review
  for the Honasa MT Analytics Platform. Auto-activates on ANY task before making changes —
  always perform architecture review and impact analysis first. Also triggers on:
  "review architecture", "is this the right approach", "how should we structure this",
  "impact of this change", "what breaks if I change", "PBIP setup", "Git workflow",
  "branch strategy", "PR review", "deployment plan", "design this", "refactor",
  "how to scale this", "dependency analysis", "release planning", "rollback plan".
  This skill runs BEFORE implementation — never skip it for changes to dashboard/data/pipeline.
---

# MT Enterprise Architecture & Git Governance

Architecture-first, impact-aware engineering for the Honasa MT Analytics Platform.
Never make a change without completing the review checklist below.

## The Four Architecture Laws

1. **No quick fixes.** Every solution must be scalable, maintainable, and documented.
2. **Impact before implementation.** Identify what breaks before touching anything.
3. **PBIP first.** Power BI as text (PBIP/TMDL/JSON), never binary PBIX in Git.
4. **One source of truth.** Every business rule, KPI, and mapping lives in one place.

## Pre-Task Architecture Review (run on every significant change)

```
ARCHITECTURE REVIEW CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Task understood: [state in one sentence what is being changed]
□ Affected components: [dashboard tabs / data.js blocks / scripts / Power BI / Excel]
□ Downstream dependencies: [what reads or depends on what is being changed]
□ Business logic touched: [Primary / Offtake / Allocation / P&L / Forecast / Distribution]
□ FY scope: [FY25 / FY26 / FY27 / all — which years are affected]
□ Regression risk: [HIGH / MEDIUM / LOW — will existing working numbers change?]
□ Rollback strategy: [how to undo if this breaks something]
□ Documentation required: [yes/no — which docs need updating]
```

## Impact Analysis Protocol

Before modifying any file, answer:

```python
# Impact analysis — complete before writing any code
impact = {
    "file_changed":      "dashboard/index.html",
    "functions_touched": ["buildPrimary()", "renderChainChart()"],
    "tabs_affected":     ["Primary", "Overview", "Performance & Comparison"],
    "data_js_blocks":    ["primary", "by_chain"],
    "fy_coverage":       "FY25/FY26 unchanged, FY27 new logic",
    "regression_risk":   "MEDIUM — existing chart logic untouched",
    "test_plan":         "Sweep all 12 tabs × 4 FY states in headless browser",
    "rollback":          "git revert <commit> — data.js regenerated from source"
}
```

## Git Governance Standard

### Branch Strategy
```
main              ← production-ready, protected
  └── claude/<feature-slug>    ← AI-assisted features (this project)
  └── feature/<slug>           ← manual features
  └── fix/<slug>               ← bug fixes
  └── data/<fy>-<month>-refresh ← data-only refreshes
```

### Commit Message Format
```
<type>: <what changed in plain English>

<body — optional: why this was needed, what was fixed>

Resolves: DI-YYYYMMDD-NNN   # if resolving a data issue
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_...
```

Types: `feat` / `fix` / `data` / `docs` / `refactor` / `perf` / `test` / `chore`

### PR Checklist (every PR must answer yes to all)
```
□ Architecture review completed
□ Impact analysis documented in PR description
□ Regression risk stated (HIGH/MEDIUM/LOW)
□ All 12 tabs × 4 FY states swept (or scope confirmed narrower)
□ FY25/FY26 numbers unchanged (if only FY27 was intended to change)
□ data.js diff reviewed — no unexpected block changes
□ No hardcoded FY values (FY25/FY26 only) introduced
□ Business logic: Primary/Offtake/Allocation rules preserved
□ Documentation updated (CLAUDE.md / docs/ as needed)
□ Release note written
```

## PBIP Engineering Standard

Power BI development MUST be text-first:

```
PowerBI/
  semantic-model/
    model.bim              ← Tabular Model JSON (Git-trackable)
    tables/
      Fact_Primary.tmd     ← TMDL per table
      Dim_Date.tmd
    measures/
      [KPI measures].tmd
  report/
    report.json            ← Report definition
    pages/
      Overview.json
      Primary.json
  theme/
    mt-theme.json

NEVER commit:
  *.pbix                   ← binary, untrackable, merge-impossible
```

## Dependency Map (MT Platform)

```
Source Files (.xlsb/.xlsx/.csv)
    │
    ▼
scripts/build_dashboard_data.py   ← ONLY generator of data.js
    │
    ├── Primary/P&L/Forecast blocks
    ├── Offtake blocks  (--offtake-patch)
    ├── Detail/FY27     (--detail-only)
    └── Distribution    (allocated from primary)
    │
    ▼
dashboard/data.js   ← window.DASH — ALL 12 tabs read from here
    │
    ▼
dashboard/index.html  ← 12 tabs, all JS, all rendering
    │
    ├── Tab: Data Explorer
    ├── Tab: Overview
    ├── Tab: Primary        ← reads primary, by_chain, by_brand, by_pack
    ├── Tab: Offtake        ← reads offtake.total_fyNN, monthly_fyNN
    ├── Tab: P&L            ← reads pnl block
    ├── Tab: Category & Pack
    ├── Tab: Forecast       ← reads forecast block
    ├── Tab: Promo & Trade Spend
    ├── Tab: Market Share   ← reads market_share block
    ├── Tab: Distribution   ← reads distribution block
    ├── Tab: Performance & Comparison
    └── Tab: Insights & Way Forward
```

## Scalability Principles

- **Modular blocks:** Each data.js block is independently refreshable (`--primary-only`, `--offtake-patch`, etc.)
- **FY-agnostic:** All code derives FY from month+year — never hardcode FY25/FY26
- **Additive changes only:** New tabs/blocks must not change existing tab behaviour
- **Offline-first:** Dashboard works without internet — all vendor JS bundled locally
- **Separation of concerns:** `build_dashboard_data.py` generates; `index.html` renders; `data.js` stores

## Architecture Anti-Patterns (never do these)

| Anti-pattern | Why it fails | Correct approach |
|---|---|---|
| Edit data.js by hand | Next build overwrites it | Edit build script, regenerate |
| Hardcode `fy25`/`fy26` in JS | Breaks FY27+ automatically | Use `FY_ALL`, `fyBeyondPreagg()`, `FPX(tag)` |
| Commit `.pbix` to Git | Binary, untrackable, merge-impossible | Use PBIP/TMDL text format |
| Quick-fix one tab without impact analysis | Breaks other tabs | Always run impact analysis first |
| Duplicate business logic in script + dashboard | Rules diverge over time | Single source: build script derives, JS renders |
| Store secrets/tokens in code | Security breach | Use `.env`, never commit credentials |
