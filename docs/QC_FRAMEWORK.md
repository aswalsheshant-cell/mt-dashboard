# MT QC Framework

**Automated quality control gates for every pipeline and dashboard release.**
Run every gate before marking any output complete.

---

## Release Decision Rules

| Verdict | Condition |
|---|---|
| **PASS** | All mandatory checks pass, reconciliation within tolerance, no critical exceptions |
| **PASS WITH WARNINGS** | Mandatory controls pass, exceptions documented, impact quantified, authorized owner approves |
| **BLOCKED** | Any mandatory check fails — do not release until resolved |

---

## Gate 1: Schema Validation

```python
REQUIRED_COLUMNS = {
    "primary":  ["month_label", "chain_name", "brand_name", "pack_size", "nsv_lakhs"],
    "offtake":  ["month_label", "chain_name", "site_code", "ean", "value_sold_lakhs"],
    "pnl":      ["month_label", "chain_name", "gm_lakhs", "trade_spend_lakhs"],
    "dist":     ["month_label", "chain_name", "ean", "numeric_dist"],
}
REQUIRED_DATA_TYPES = {
    "month_label": str,       # e.g. "Apr-26"
    "chain_name":  str,
    "site_code":   str,       # must remain text (leading zeros)
    "ean":         str,       # 13-digit text
    "nsv_lakhs":   float,
}
```

---

## Gate 2: Business Key Uniqueness

```
Primary grain:   (month_label, chain_name, brand_name, pack_size) → 1 row
Offtake grain:   (month_label, chain_name, site_code, ean) → 1 row
P&L grain:       (month_label, chain_name) → 1 row
Distribution:    (month_label, chain_name, ean) → 1 row

FAIL if any duplicate exists on these keys.
```

---

## Gate 3: Null Checks

```
Mandatory non-null columns:
  □ month_label     — every row must have a valid month
  □ chain_name      — no unmapped chains
  □ nsv_lakhs       — primary value must be numeric (0 is valid, null is not)
  □ fy_tag          — every row must have a derived FY

Warning (not blocking):
  □ site_name       — may be null for new/unregistered stores
  □ brand_name      — may be null for non-brand-level offtake
```

---

## Gate 4: Value Range Checks

```
NSV:              must be numeric; negative values require MRN log confirmation
GM%:              must be between -20% and 85% (outside = calculation error)
Trade Spend%:     must be between 0% and 50% (outside = formula error)
Numeric Dist%:    must be between 0% and 100%
DOS:              must be between 0 and 180 days (outside = data anomaly)
Return Rate:      must be between 0% and 30% (outside = flag for review)
Month label:      must parse to a valid date in format "Mmm-YY"
EAN:              must be exactly 13 characters, numeric
```

---

## Gate 5: Mapping Coverage

```
Chain mapping:    100% of chain_name values must exist in chain master
EAN mapping:      ≥98% of EAN values must exist in product master
Store mapping:    ≥95% of site_code values must map to a chain (≤5% UNMAPPED is acceptable)
Brand mapping:    100% of brand_name values must exist in brand master

FAIL if chain_name = "UNMAPPED" for any primary NSV row.
WARN if >5% of store records are UNMAPPED.
Log all unmapped records to alloc.missing_mapping.
```

---

## Gate 6: Cross-Source Reconciliation

```
Check 1 — Primary vs Offtake (by chain, by month)
  |Primary NSV − Offtake Value| / Primary NSV ≤ 10%
  Action if exceeded: document gap driver (DOS build, scheme timing, or coverage)

Check 2 — Allocation balance
  Sum of allocated chain NSV = Distributor total NSV ± 0.5%
  Action if exceeded: BLOCKED until allocation reconciles

Check 3 — P&L vs Primary
  P&L NSV = Primary NSV ± 2pp GM% tolerance
  Action if exceeded: flag to Finance; document in release note

Check 4 — Article-level vs Chain-level
  Sum of article NSV per chain = chain-level total ± 0.1L
  Action if exceeded: formula or groupby error in build script
```

---

## Gate 7: FY Continuity Check

```
For each FY in the output:
  □ No gap months (e.g. if FY27 Apr-26 and Jun-26 are present, May-26 must also be present)
  □ Month labels in expected format "Mmm-YY" (e.g. "Apr-26", not "04-26" or "April 2026")
  □ FY tag derived correctly: Apr-26 → FY27, Mar-26 → FY26
  □ Pre-agg FYs (FY25/FY26) only from pre-agg workbooks
  □ FY27 only from detail_meta.fyx_primary / offtake patch sources
```

---

## Gate 8: Regression Check

```
After every build that modifies existing FY data:
  □ FY25 total NSV = [prior approved total] ± 0L
  □ FY26 total NSV = [prior approved total] ± 0L
  □ FY25 chain-level totals unchanged
  □ FY26 chain-level totals unchanged

Zero tolerance for prior-FY regressions.
BLOCKED if any prior-FY number changes unexpectedly.
```

---

## Gate 9: Dashboard Sweep (12 tabs × 4 FY states)

```
Run with Playwright headless browser:
  playwright --chromium /opt/pw-browsers/chromium

For each of: [no-filter, FY25, FY26, FY27] × [all 12 tabs]:
  □ No JavaScript console errors
  □ No NaN displayed in any card or chart
  □ No "undefined" text in any metric
  □ No empty-broken cards (cards with no value where a value is expected)
  □ No card overlap or layout breakage
  □ Key totals match source reconciliation

Script location: scripts/qc_sweep.py (Playwright headless)
```

---

## Gate 10: Data Issue Log

```
All open data issues documented in docs/data-issues/DI-YYYYMMDD-NNN.md
Active issues table updated in mt-error-resolution skill
Each issue classified: OPEN / IN REVIEW / AWAITING DATA / RESOLVED / ACCEPTED
No OPEN Critical issues at release time
```

---

## QC Run Log Template

```
QC RUN — [Date] [Time]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pipeline mode:    [full / --primary-only / --offtake-patch / --detail-only]
Source files:     [list of files processed]
Output:           dashboard/data.js

Gate 1 — Schema:          [PASS / FAIL]
Gate 2 — Uniqueness:      [PASS / FAIL]
Gate 3 — Nulls:           [PASS / FAIL]
Gate 4 — Ranges:          [PASS / FAIL — list any out-of-range]
Gate 5 — Mapping:         [PASS / WARN — coverage %]
Gate 6 — Reconciliation:  [PASS / FAIL — list any gaps]
Gate 7 — FY Continuity:   [PASS / FAIL]
Gate 8 — Regression:      [PASS / FAIL]
Gate 9 — Dashboard Sweep: [PASS / FAIL — tab × FY matrix]
Gate 10 — Issue Log:      [PASS / OPEN ISSUES LISTED]

Health Score:     [XX/100]
Verdict:          [PASS / PASS WITH WARNINGS / BLOCKED]
Approved by:      [Name]
Release tag:      [release/FY27-Jun-26]
```
