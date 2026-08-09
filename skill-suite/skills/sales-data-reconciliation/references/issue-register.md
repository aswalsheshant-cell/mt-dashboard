# Data issue record — template and register

Use one record per issue for any finding from a pre-release review, UAT or data quality
sweep that cannot be fixed in the current change: a missing source, a pending business
confirmation, a defect resolvable only by a data refresh, or an accepted limitation.

Store completed records in `docs/data-issues/`, one file per issue, named
`DI-YYYYMMDD-NNN.md`. Reference the issue ID in any commit or pull request that
resolves it (`Resolves: DI-20260805-001`).

## Template

```
========================================
MT DASHBOARD — DATA ISSUE RECORD
========================================
ID:               [DI-YYYYMMDD-NNN]
Raised:           [YYYY-MM-DD]
Raised by:        [Name / agent / script]
Status:           [OPEN | IN REVIEW | AWAITING DATA | RESOLVED | ACCEPTED]

-- WHAT IS WRONG --
Tab / Section:    [e.g. Primary -> FY27 by_chain]
Metric affected:  [e.g. Chain NSV — Relay]
Current value:    [e.g. -0.07 L]
Expected value:   [e.g. 0 or positive (MRN return unconfirmed)]
Difference:       [e.g. -0.07 L]
Visible to user:  [YES | NO]

-- ROOT CAUSE (known or suspected) --
Error class:      [Source | Schema | Grain | Mapping | Formula | Filter | Time period | Output | Environment]
Description:      [One paragraph: which pipeline stage, which source file, which
                   business rule produces this value.]

-- IMPACT --
FY scope:         [FY25 | FY26 | FY27 | Multiple]
Chains affected:  [names, "All", or "None — metadata only"]
Value impact:     [quantified]
Blocking release: [YES | NO]
Risk level:       [Critical | High | Medium | Low | Cosmetic]

-- RESOLUTION PATH --
Source file needed:   [exact filename, or N/A]
Action required:      [who does what]
Resolvable by data update alone: [YES | NO — requires code change]
Estimated effort:     [e.g. one data refresh cycle]

-- INTERIM MITIGATION --
[What is currently shown, and what governance disclosure exists.]

-- RESOLUTION LOG --
[Date] [Who] [What was done]
========================================
```

## Register — status at 2026-08-05

Carried forward from the previous skill revision. Re-verify each entry before citing it;
these are point-in-time findings, not current truth.

| ID | Metric | Current | Expected | Status | Data update alone? |
|---|---|---|---|---|---|
| DI-20260805-001 | FY27 by_chain: Relay NSV | -0.07 L | 0 or positive | OPEN (likely MRN) | Yes — confirm with business |
| DI-20260805-002 | FY27 by_chain: Sohum Shoppe NSV | -2.51 L | 0 or positive | OPEN (likely MRN) | Yes — confirm with business |
| DI-20260805-003 | FY27 by_brand: Pure Origin NSV | -0.32 L | 0 or positive | OPEN (likely MRN) | Yes — confirm with business |
| DI-20260805-004 | Guardian Healthcare, 53 rows / 2.0 L | Unmapped (FY26 Nov) | Chain assigned | OPEN | Yes — add to chain mapping CSV |
| DI-20260805-005 | Reliance BC June-26 NSV (943.68 L) | BLOCKED, source missing | Included | AWAITING DATA | Yes — when June XLSB available |
| DI-20260805-006 | P&L vs Primary FY26 delta | 0.91 L | Reconciled | ACCEPTED (SIS scope) | No — by design |
| DI-20260805-007 | generated_at_note (patch flag) | "Patched in place" | Full build timestamp | OPEN | Yes — next full `--src` rebuild |
| DI-20260805-008 | Comparison tab: FY26 baseline missing when FY27 selected | Blue dots all ₹0 L | FY26 chain values as baseline | RESOLVED 2026-08-05 | No — resolved by code change |

## Using the register

An OPEN issue on a metric being reported must be disclosed alongside the number, with
its quantified impact. An issue marked ACCEPTED is a documented limitation and does not
block release. AWAITING DATA blocks any claim of completeness for the affected period —
report the figure as partial and name the missing file.
