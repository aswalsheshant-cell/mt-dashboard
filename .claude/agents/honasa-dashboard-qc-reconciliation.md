---
name: honasa-dashboard-qc-reconciliation
description: |
  Dashboard QC, reconciliation, and release-readiness checks for the Honasa / Mamaearth MT Dashboard.
  Use this skill for: dashboard QC, PASS/WARN/FAIL/BLOCKED reconciliation, unmapped EANs,
  blank Brand/Category/Subcategory/Range, product-master validation, source-to-dashboard
  reconciliation, Primary/Offtake/CM2 validation, duplicate-risk review, release-readiness decisions.
---

# Honasa MT Dashboard — QC & Reconciliation Skill

## Purpose
Validate every numeric block in `dashboard/data.js` before release. Produce a reconciliation
report with PASS / WARN / FAIL / BLOCKED status, owner, corrective action, closure criterion,
and review trigger for every check. End with a release decision: READY / READY WITH ACCEPTED
EXCEPTIONS / NOT READY.

## Key data structures (data.js → window.DASH)
- `primary` — pre-aggregated FY25/FY26 primary (ends Mar-26)
- `detail_meta.fyx_primary.FY27` — FY27 article-level primary (by_brand, by_channel, by_zone, monthly)
- `offtake` — chain offtake FY25/FY26/FY27
- `cm2` — CM2 block (NSV − trade expenses)
- `dist_gap` — distribution opportunity
- `detail_records` — top-N article rows (capped; browser display only)
- `alloc` — Dist.-allocation detail + cust_article table

## THE ONE FY RULE
- Apr–Dec year Y → FY(Y+1)  e.g. Apr-26 → FY27
- Jan–Mar year Y → FY(Y)    e.g. Mar-26 → FY26

## Excluded brands (must never appear in any aggregation)
- Pure Origin, Lumineve, Staze
- Records preserved in `PowerBI/Excluded_Data/Excluded_Brands/`

## QC status definitions
| Status   | Meaning |
|----------|---------|
| PASS     | Diff ≤ 0.12 L (rounding tolerance) |
| WARN     | Documented, accepted difference. Owner + action + closure criterion assigned. |
| FAIL     | Unexpected difference — must be resolved before release |
| BLOCKED  | Cannot be resolved by dashboard team; requires source data fix by named owner |

## Release decision rules
- Any FAIL → NOT READY
- Any BLOCKED without stakeholder sign-off → NOT READY
- All PASS + accepted WARNs → READY WITH ACCEPTED EXCEPTIONS
- All PASS → READY

## Check blocks

### A — Primary FY25 / FY26
- Channel sum = nsv_fy25 / nsv_fy26
- Brand sum ≈ nsv_fy25 / nsv_fy26
- Zone sum ≈ nsv_fy25 / nsv_fy26
- Monthly sum vs nsv (KNOWN diff = excluded brands in monthly pre-agg)

### B — FY27 Primary (article-level)
- Monthly sum = FY27.nsv
- Channel sum = FY27.nsv
- Brand sum = FY27.nsv (includes (Unmapped/Blank Brand) bucket if blank codes exist)
- Zone sum ≈ FY27.nsv (expect overcount if returns with blank zone codes present)
- Chain sum ≈ FY27.nsv (expect undercount if blank chain codes present)

### C — Offtake FY25 / FY26 / FY27
- Monthly sum = total_fy* for each FY

### D — Brand exclusion audit
- Pure Origin, Lumineve, Staze absent from primary.by_brand, fyx_primary.FY27.by_brand,
  dims.Brand, cm2.by_brand, detail_records

### E — CM2
- NSV − expense = cm2_value (arithmetic identity)
- by_brand NSV sum = total_nsv
- by_chain expense sum = total_expense
- by_brand CM2 sum ≈ cm2_value (KNOWN: unattributed expense)
- by_chain CM2 sum ≈ cm2_value (KNOWN: allocation rounding)

### F — Distribution Gap
- total_addon_ann ≥ sum(visible rows)
- total_addon_window ≥ sum(visible rows)

### G — Regression / Unmapped Dimension Checks
- FY27.by_zone sum vs FY27.nsv (blank-zone returns inflate if positive)
- FY27.by_chain sum vs FY27.nsv (blank-chain codes reduce if undercount)
- detail_records null Brand/Channel/Zone/Category/SubCategory/Range counts
- EAN conflict check (same EAN → multiple brands in detail_records)
- NaN/undefined in NSV/MRP/Qty fields

## EAN mapping protocol (when source file is available)

### Required source file
`primary_article.xlsb` (or `primary_article.xlsx`) in the `--src` directory.

### EAN normalization rules
1. Trim whitespace
2. Remove trailing `.0` from spreadsheet numeric conversion
3. Convert scientific notation to full digit string (decimal, not rounded)
4. Preserve leading zeros
5. Keep both EAN_Raw and EAN_Normalized
6. Flag non-digit / truncated / check-digit-fail EANs as exceptions

### Mapping priority
1. Approved product master (exact EAN match)
2. Unanimous historical EAN mapping (same EAN → same brand in all historical periods)
3. Effective-dated approved mapping
4. Exact Article Code support (secondary evidence only)
5. Manual review — retain `(Unmapped/Blank Brand)` etc. for unresolved rows

### Prohibited actions
- No guessing Brand from Article Name
- No fuzzy auto-mapping as final resolution
- No partial EAN matching
- No removal of leading zeros to force a match
- No silent exclusion of unresolved rows from totals

## Unmapped bucket rule
`(Unmapped/Blank Brand)` (and similar) must remain in the by_brand array until the
mapped value reaches zero. Never filter it with `if k` in build_dashboard_data.py.

## Build commands
```bash
# Apply EAN mapping and rebuild FY27 only:
python scripts/build_dashboard_data.py --detail-only --src <dir> --out dashboard/data.js

# Verify syntax:
python -m py_compile scripts/build_dashboard_data.py
```

## Validation
After any rebuild, run Playwright against all 12 tabs × 4 FY states and assert:
- No NaN / undefined / empty cards / JS errors
- FY25/FY26 numbers unchanged when only FY27 was intended to change

## Source integrity constraints
- Do NOT edit raw source files
- Store approved mappings in a separate crosswalk file (e.g. `PowerBI/SeedData/ean_brand_mapping.csv`)
- Apply mappings reproducibly through the build script
- Create a backup of data.js before any rebuild: `cp dashboard/data.js dashboard/data.js.bak`
