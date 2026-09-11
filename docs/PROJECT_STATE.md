# Project State

Single source of truth for where this project is, so a resumed environment does
not have to reconstruct weeks of work from conversation history. The SessionStart
hook prints the "Next Approved Task" section on every resume.

**Contains no confidential data.** No employee name, employee ID, incentive
amount or DMS client identity belongs in this file — counts only.

Update after a **validated** milestone, then commit and push with that milestone.

---

## V1 Status — CLOSED

**V1 is code-complete and closed.** Build mode is over; the project is now in
operate-and-improve mode. Monthly business runs, validating recommendations and
measuring outcomes are the work — not further architecture.

Source workbooks live at `D:\sALES & eXPENSES` (local Windows storage, outside
Git by design). The repository stores how to find them, never the files. See
`docs/RUNBOOK.md` section 0.

### V1.1 backlog — deliberately deferred, none of it blocking

- Rename the four `@agent-*` handles in CLAUDE.md to the skills that deliver them
- Decide the boundary between `executive-commercial-storytelling` and
  `mt-executive-storytelling` (both carry unique content; neither should be deleted)
- `require()` is duplicated across three incentive scripts — could import from
  `scripts/input_paths.py`
- CLAUDE.md redistribution (invariants stay; the routing table is procedural)
- Continuous-learning loop: recommendation -> expected impact -> action -> actual
  -> variance -> learning
- Move source workbooks to approved company storage if the D: drive becomes a
  backup or access concern — that changes one environment variable, no code

---

## Current Phase

Phase 4 complete — commercial analytics validated; incentive foundation gated on
business inputs. Environment resilience added. Knowledge base (KA-01..KA-10) and
the governed incentive Excel working model are built and validated; the workbook
produces no payout while mandatory decisions are open.

## Last Validated Commit

`ec55115` — Fail with an actionable message when an incentive input is missing
Validated: 2026-09-11 — fresh-clone reproducibility PASS

> A milestone's own commit hash does not exist while this file is being written
> for it, so this section is corrected in the **next** commit. Check it against
> `git log --oneline -1` on resume; the hook prints both.

## Next Approved Task

**Business input closure — the work is now waiting on people, not on data.**
`incentive_working/target_scope_decision_pack.md` is the pack to send. Open items,
each with an owner and a value, are in `08_Exceptions` and `12_Rule_Decisions`:
  (a) MT Leadership — are North and Central H1-only? (~Rs 5,091.77 L)
  (b) MT Leadership — 5 accounts with no target row (Nykaa, Sancus, Ratnadeep,
      Guardian, Vijetha, ~Rs 2,598.18 L); and are 445 D-Mart stores with no WoA
      deployment inside the incentive measurement scope? (Rs 7,535.62 L of actuals)
  (c) Finance — Rs 2,456.83 L of the target gap is explained by nothing
  (d) MT Ops — 28 WoA signatures (largest role line Rs 6,398.95 L) + 3 exceptions
  (e) HR — 9 unpayable grades (5 `#N/A`, 4 blank)
Still outstanding: target basis (Primary vs Offtake), C1-C6, caps, proration.
Do NOT calculate any incentive payout. Do NOT start NPD, OSA/OOS,
profitability or persona reporting — all gated.
Do NOT start the Power BI incentive dashboard.
One bounded component per run: implement, validate, commit, stop.

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
- Knowledge base: 10 sourced articles + routing index, with a staleness gate
- Target scope reconciliation (KA-11) — 76% of the Rs 10,146.78 L gap traced to
  named causes; nothing scaled or allocated
- Employee actual attribution (KA-12) — Apr-Jul store actuals credited through the
  WoA sheet; all four role lines reconcile with a zero difference; no candidate
  identity is ever treated as approved
- Knowledge base extended to 16 articles (KA-11..KA-16) with router entries
- Governed incentive workbook `MT_Incentive_Working_FY27.xlsx` — 14 sheets, every
  sheet an Excel Table, calculated cells are formulas, blocked rows stay blocked
  and never read as zero. Restricted: written to `incentive_working/`, gitignored.

## Partial Capabilities

- Store-grain sales — dedup runs at chain level; store-grain chain offtake not in the build
- Employee attribution — actuals now credited through the WoA sheet, but 0 of 67 identities are approved so nothing is credited yet. 609 of 1,147 selling stores (mostly the D-Mart estate) have no WoA row at all — a scope question, not a mapping failure
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

1. ~~Incentive grade for 14 RKAM/NKAM/BA Lead employees~~ — **received**, all 14 valid.
   Residual: 5 rows hold `#N/A` (spreadsheet errors) and 4 are blank — 9 of 51 still unpayable
2. Employee IDs on the WoA hierarchy sheet — names are not a safe production key
3. Official targets — **RKAM target planning file received** (3,100 rows, FY27, all 12 months,
   at FY x Month x State x Chain x Brand x BDO/BDE x RKAM grain). Not yet usable: it totals
   ₹328.68 Cr against the ₹441.33 Cr business target (74.5%), and carries 16 chain/brand
   spelling variants. Needs a coverage explanation and normalisation before payout use
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
- (resolved) The two pytest-based test files no longer error on import —
  `scripts/setup_environment.sh` installs `requirements.txt`.

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
| unittest suite | 64 pass, 1 skipped |
| Baseline invariants | 7/7 hold (`config/baselines.json`) |
| Fresh clone | dashboard reproduces fully: 44 states, 0 failures, 0 JS errors |
| Incentive workbook | 51 employees / 42 VALID grades / 85 slab rows / 3,124 target rows / 67 WoA rows / 267 actual rows; payout NOT CALCULATED |
| Target file (refreshed) | Rs 33,986.08 L; 77.0% of business target; gap 76% explained |
| Actual attribution | Rs 14,118.82 L Apr-Jul; all 4 role lines reconcile, difference 0 |

| pytest suite | 13 pass |

Run: `./scripts/run_dashboard_sweep.sh tests/dashboard_sweep.js`, `python3 -m unittest discover tests`,
`python3 -m pytest tests -q`, `python3 scripts/ci_validate_datajs.py`,
`./scripts/environment_health_check.sh`

On a fresh VM, run `./scripts/setup_environment.sh` first (Python deps).

## Privacy Boundary

`dashboard/` publishes to GitHub Pages — everything in it is public.

| Class | Data | Where it may live |
|---|---|---|
| PUBLIC | Commercial aggregates, targets, PVM, scorecards | `dashboard/data.js` |
| CONFIDENTIAL | Employee names/IDs, DMS client identities | Outside the repo only |
| RESTRICTED_HR_FINANCE | Incentive slabs, grades, payouts | Excel / restricted Power BI only |

Enforced by `tests/test_published_assets_privacy.py`, `tests/test_incentive_workbook.py`
and `.gitignore`. The incentive workbook builder refuses to write into `dashboard/`.
DMS/Massit is **incentive-scope only** and must not appear in commercial reports.

## Environment Notes

Cloud environments are reclaimed after idle — that is expected and is not a
project fault. Measured at the last restart: 15.4 GB of 16 GB memory free, 29 GB
disk free, no stray processes. No resource pressure; no keep-alive workaround
is warranted or attempted.

On resume: the SessionStart hook prints repo state, resources, asset presence
and this file's next task. Verify restricted inputs are present before any
incentive work — never reconstruct them from memory.
