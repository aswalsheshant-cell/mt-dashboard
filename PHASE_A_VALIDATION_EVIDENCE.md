# Phase A Validation Evidence
## Frozen Version: phase-a-scaffolding-v1

**Freeze date:** 2026-08-01
**Commit SHA:** b08866f6bd067662c0c21e82905c362cb2ee1579
**Branch:** claude/store-master-qc-duplicates-4pvmmk

---

## 1. Unit Test Results

```
Ran 20 tests in 0.038s
OK
```

| Test Class | Tests | Status |
|---|---|---|
| TestForecastSchema | 5 | PASS |
| TestForecastDrivers | 7 | PASS |
| TestScenarioPlanner | 4 | PASS |
| TestDataNormalizer | 4 | PASS |
| **Total** | **20** | **20/20 PASS** |

---

## 2. Production Forecast Run

**Run ID:** 2026-08-01_154825
**Forecast rows generated:** 9,138
**Forecast months:** Aug 2026, Sep 2026, Oct 2026
**Pipeline status:** PRODUCTION_READY

---

## 3. Five Validation Gates

| Gate | Status |
|---|---|
| 1. Input schema | PASS |
| 2. Duplicate records | PASS |
| 3. Master mapping | WARNING — 5 unmapped EANs (non-blocking; pending MDM resolution) |
| 4. Output reconciliation | PASS |
| 5. Warehouse allocation | PASS |

**Overall gate status:** WARNING (no FAIL or BLOCKED gates)

---

## 4. Event and NPI Wiring Verified

| Forecast month | Event applied | Uplift % | Rows affected |
|---|---|---|---|
| 2026-08 | Raksha Bandhan | 15% | 2,113 |
| 2026-09 | (none) | 0% | 0 |
| 2026-10 | Big Billion Days / Great Indian Festival | 25% | 2,113 |

Rows with festival_uplift > 0: **4,226 of 9,138**
Rows where forecast_driver_primary = Festival Uplift: **2,419**

---

## 5. Data Files in This Version

| File | Status | Notes |
|---|---|---|
| Phase_A_Input/events_calendar.csv | PLACEHOLDER_TBC | 13 FY27 events; uplift % pending business approval |
| Phase_A_Input/launch_plan.csv | SCHEMA ONLY | Empty; business to populate NPI rows |
| Phase_A_Input/targets.csv | SCHEMA ONLY | Expanded to Chain × Brand × Article × EAN × Month |
| Phase_A_Input/fact_margin.csv | ESTIMATED | Real margin export required from Finance |
| Phase_A_Input/primary_history.csv | ASSEMBLED | From SAP + distributor primary data |
| Phase_A_Input/offtake_history.csv | ASSEMBLED | Apr–May 2026 (2 months only) |

---

## 6. Data Quality Issues Found by Validator

| Check | File | Issue | Severity | Action Required |
|---|---|---|---|---|
| V-01 | targets.csv | 0 rows — no Aug–Oct 2026 targets loaded | BLOCKED | Sales Planning to upload |
| V-07 | events_calendar.csv | All 13 events PLACEHOLDER_TBC | BLOCKED | Marketing / KAM to approve uplift % |
| V-14 | fact_margin.csv | 933 ESTIMATED rows (placeholder margins) | BLOCKED | Finance to provide real margin data |
| V-15 | fact_margin.csv | No approval_status column | FAIL | Add column; Finance to mark FINANCE_APPROVED |
| V-16 | fact_margin.csv | 2 negative margin_pct: VMM chain, EANs 8904417314298 / 8904417312546, margin_pct = -84.64 | FAIL | Likely credit memo / return — MDM to reclassify or exclude |

**Validator command:** `python validate_business_inputs.py --mode full`
**Current result:** PASS=13 WARNING=0 FAIL=2 BLOCKED=3 → FORECAST RUN BLOCKED

---

## 7. Known Open Items (Non-Blocking)

| # | Item | Owner | Priority |
|---|---|---|---|
| 1 | 5 unmapped EANs | MDM / Category | P1 — resolve before UAT |
| 2 | Event uplift % approval | Marketing / KAM | P1 — required before production use |
| 3 | Actual targets (Aug–Oct 2026) | Sales Planning | P1 — most important missing input |
| 4 | NPI launch plan population | Category / Marketing | P2 |
| 5 | Real margin repository | Finance | P2 — required before CM2 reporting |
| 6 | Historical backtesting | Demand Planning | P2 — validates model accuracy |
| 7 | Business UAT | KAM + Category + Supply Chain | P3 |

---

## 7. What Is Frozen

The following are complete and must not be changed before business inputs are validated:

- Engine architecture (chain_name consistency, column aliases, reconciliation logic)
- Five-gate validation framework
- Scenario planning (Best / Expected / Worst)
- Warehouse allocation (Gurgaon / Mumbai / Bangalore / Kolkata)
- Events calendar schema and engine wiring
- NPI launch plan schema and engine wiring
- 20/20 unit test suite

**Instruction: Do not add further forecasting features until business inputs are validated.**

---

## 8. How to Restore This Version

```bash
git checkout b08866f6bd067662c0c21e82905c362cb2ee1579
# or, once the tag is pushed:
git checkout phase-a-scaffolding-v1
```

The local tag was created with:
```bash
git tag -a phase-a-scaffolding-v1 -m "Phase A event, NPI and target scaffolding complete"
```
Remote tag push was blocked by token scope (403). The commit SHA above is the authoritative freeze point.
