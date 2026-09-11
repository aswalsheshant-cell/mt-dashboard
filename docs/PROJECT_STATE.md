# Project State

Single source of truth for where this project is, so a resumed environment does
not have to reconstruct weeks of work from conversation history. The SessionStart
hook prints the "Next Approved Task" section on every resume.

**Contains no confidential data.** No employee name, employee ID, incentive
amount or DMS client identity belongs in this file — counts only.

Update after a **validated** milestone, then commit and push with that milestone.

---

## Current Phase

Phase 4 complete — commercial analytics validated; incentive foundation gated on
business inputs. Environment resilience added.

## Last Validated Commit

`8c35c5b` — Re-scope DMS/Massit to the incentive working only; add May-26
Validated: 2026-09-11

## Next Approved Task

Obtain the blocked business inputs, then build the incentive engine.
Do NOT start NPD, OSA/OOS, profitability or persona reporting — all gated.
Do NOT calculate incentive payouts until the readiness gate passes.
Highest-value inputs to chase first: incentive grade for 14 employees, and
Employee IDs on the WoA hierarchy. Both are one extra column on files that
already exist.

## Completed Capabilities

- Primary/Offtake baseline, FY27 coverage gate, like-for-like same-period YoY
- Target / Achievement % / Gap / Current + Required Run Rate (total, zone, chain)
- Month-on-Month view (auto-extends as months arrive)
- Account & Zone scorecard with config-driven RAG and an action per row
- Price-Volume-Mix at article grain (buckets reconcile to the exact delta)
- Chain mapping health + unmapped exception register
- Data readiness gate (8 layers), central config, canonical zone normalisation
- Emerging-brand rule (all brands except Mamaearth) — business-confirmed
- DMS/Massit consolidation, fenced to the incentive domain only
- Privacy boundary + regression tests; environment health check; resume recovery

## Partial Capabilities

- Store-grain sales — dedup runs at chain level; store-grain chain offtake not in the build
- Employee attribution — DMS client id joins the store hierarchy; hierarchy carries names, not IDs
- Focus Pack — EAN source registered (F1/F2); achievement not computed (EAN→brand map needed)
- WoA — working sheet available; the WoA formula itself is not stated

## Blocked Capabilities

| Capability | Blocked on |
|---|---|
| Incentive calculation | 4 of 5 mandatory inputs (see Required Business Inputs) |
| Persona reporting (KAM/RKAM/BDE) | Employee IDs on the WoA hierarchy |
| Chain-level Primary | Distributor→chain mapping at 67.65% (₹60.11 Cr unattributed) |
| NPD tracker | No join key between NPD master and transaction grain |
| OSA / OOS | Store audit covers 44.4% of stores, wrong period |
| Profitability | No article-level COGS / standard cost |
| Inventory days | No stock-on-hand feed |

## Required Business Inputs

1. Incentive grade (Asst / regular / Sr) for 14 RKAM/NKAM/BA Lead employees — ~₹38.1 L payout ambiguity
2. Employee IDs on the WoA hierarchy sheet — names are not a safe production key
3. Official Zone / Account / Territory targets — current zone/chain targets are DERIVED
4. Target basis confirmation — Primary or Offtake (89.0% vs 109.8% achievement)
5. Jul-26 DMS extract — completes the Apr–Jul incentive window
6. Business-rule confirmations C1–C6, payout caps, nested lower-is-better slab rule

## Current Assumptions

| Assumption | Status |
|---|---|
| Target basis = Offtake | **ASSUMED** — matches the existing forecast convention, not confirmed |
| Zone / chain targets | **DERIVED** from prior-year same-period contribution |
| Emerging brands = all except Mamaearth | **CONFIRMED** by the business, 2026-09-11 |
| Slab values | **RECONCILED** — docx and Excel match 85/85, zero mismatches |

## Known Issues

- Slab master has no formulas; it is a rate card. Calculation logic must be built.
- 3 attrition slab rows: `Amount %` contradicts `Payout Amount` (label appears wrong).
- Payout caps and the BDE Q1-only top-up restriction are not encoded in the slab sheet.
- `unit_economics.nsv_per_unit` is degenerate (0.02 everywhere); PVM uses article Qty instead.
- 5 pre-existing ruff F541 findings in `build_dashboard_data.py` (cosmetic, untouched).

## Regression Baseline

Every change must leave these unchanged:

| Check | Expected |
|---|---|
| Primary NSV FY26 | ₹32,900.36 L |
| Offtake FY26 / FY27 | ₹31,119.87 L / ₹15,069.86 L |
| FY27 primary (article-level) | ₹18,581.29 L |
| Active MT stores | 426 |
| FY27 target | ₹441.33 Cr |
| PVM reconciliation | PASS, variance 0.00 |
| Dashboard sweep | 44 states, 0 NaN/undefined, 0 JS errors |
| Tests | 24 pass |

Run: `./scripts/run_dashboard_sweep.sh tests/dashboard_sweep.js`, `python3 -m unittest discover tests`,
`python3 scripts/ci_validate_datajs.py`, `./scripts/environment_health_check.sh`

## Privacy Boundary

`dashboard/` publishes to GitHub Pages — everything in it is public.

| Class | Data | Where it may live |
|---|---|---|
| PUBLIC | Commercial aggregates, targets, PVM, scorecards | `dashboard/data.js` |
| CONFIDENTIAL | Employee names/IDs, DMS client identities | Outside the repo only |
| RESTRICTED_HR_FINANCE | Incentive slabs, grades, payouts | Excel / restricted Power BI only |

Enforced by `tests/test_published_assets_privacy.py` and `.gitignore`.
DMS/Massit is **incentive-scope only** and must not appear in commercial reports.

## Environment Notes

Cloud environments are reclaimed after idle — that is expected and is not a
project fault. Measured at the last restart: 15.4 GB of 16 GB memory free, 29 GB
disk free, no stray processes. No resource pressure; no keep-alive workaround
is warranted or attempted.

On resume: the SessionStart hook prints repo state, resources, asset presence
and this file's next task. Verify restricted inputs are present before any
incentive work — never reconstruct them from memory.
