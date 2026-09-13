# Business Logic Registry

**Frozen:** 2026-08-07  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `91b66c3`  
**Authority:** This document is the source-of-truth inventory of all business-critical calculations in the MT Dashboard pipeline. Any change to these rules requires explicit Finance or business owner approval before implementation.

---

## BL-01 — THE ONE FY RULE

**Category:** Temporal classification  
**Implemented in:** `scripts/build_dashboard_data.py` (lines 42–93); `dashboard/index.html` (`FY_ALL`/`PREAGG_FYS`/`fyBeyondPreagg()`/`FPX(tag)`)  
**Rule:**
- Apr–Dec of calendar year Y → FY(Y+1). Example: Apr-2026 → FY27
- Jan–Mar of calendar year Y → FY(Y). Example: Mar-2026 → FY26

**Python helpers:** `fy_tag_from_ym(year, month)`, `fy_tag_from_label(label)`, `fy_start_year(tag)`, `fy_source_key(tag)`, `month_labels(start_year, n_months)`, `quarter_labels_for(months)`  
**Coverage window:** `MONTHS = month_labels(2024, 26)` → Apr-24 to May-26 (26 months)  
**Extension rule:** Adding FY28+ requires only bumping `n_months` — no hardcoded FY references.  
**Owner:** Analytics Engineering  
**Finance approval required:** No — pure temporal classification  

---

## BL-02 — Distributor-to-Chain Allocation (Primary NSV)

**Category:** Revenue allocation  
**Implemented in:** `scripts/build_dashboard_data.py`: `load_chain_allocation_weights()`, `apply_chain_allocation()`  
**Documented in:** `PowerBI/docs/DistributorPrimaryAllocation_Logic.md`  

**Rule:**
1. **Direct rows** (`PO Type ≠ 'Dist.'`): Chain Name is taken as-is — no re-allocation.
2. **Distributor rows** (`PO Type = 'Dist.'`): NSV is re-split across chains using secondary-offtake-derived contribution fractions from `Primary_ShipTo_FY25-26_to_May26.csv`.
3. **Eligibility gate:** A primary row is allocated to a chain only if that Chain×Brand×Article combination has secondary offtake evidence in month M or M+1. Rows with no offtake evidence are tagged `Blocked`.
4. **Jun'26 gap:** Shipment CSV covers May'25–May'26. Jun'26 distributor rows use May'26 contribution splits (nearest-month fallback). Status: PROVISIONAL — Finance approval pending (Decision 1).

**Reconciliation identity:**
```
Original Primary NSV = Allocated NSV + Blocked NSV
Variance = 0  (exact — never force-fit to 100%)
```

**Source file flag:** `PO Type` column distinguishes Direct vs Distributor (NOT `MTD-Sale type`).  
**Owner:** Analytics Engineering + Finance (for jun26 approval)  
**Finance approval required:** Yes — Decision 1 (Jun'26) PENDING  

---

## BL-03 — Canonicalization (Chain / Brand / Zone / State)

**Category:** Master data normalization  
**Implemented in:** `scripts/build_dashboard_data.py` (lines 107–217)  

**Chain canonicalization:** `CHAIN_ALIASES` (50+ entries) + `canon_chain()` — collapses source spelling variants across all four source files to one business-facing chain name.  
**Brand canonicalization:** `BRAND_MAP` (8 brands) + `canon_brand()`.  
**Zone canonicalization:** `canon_zone()` — 5 zones (North, South 1, South 2, West, East).  
**State canonicalization:** `STATE_ALIASES` (13 aliases) + `canon_state()`.  

**Critical rule:** Canonicalization happens at load time, before any aggregation. New chain spellings appearing in future source files will route to the unresolved form (pass-through) — they must be added to `CHAIN_ALIASES` before next production build.  
**Owner:** Analytics Engineering  
**Finance approval required:** No — but new chain additions require Analytics sign-off  

---

## BL-04 — Negative Contribution Fraction Treatment

**Category:** Data quality / reconciliation  
**Implemented in:** `scripts/build_dashboard_data.py` (allocation logic — retain by default)  
**Documented in:** `PowerBI/docs/Finance_Approval_Decision_Log.md` (Decision 2)  
**Gate:** `release_gate.py:644` — `negative_frac_treatment_status` in G10  

**Rule (current default):**
- **RETAIN** negative fraction rows in the model.
- 8 source rows with negative `Cont%` (credit/reversal entries from Az Enterprises, D.L. Sales - MT, VENKATESHWARA AGENCIES-TG).
- 157 affected article-level rows. Total negative NSV impact: −₹0.2093 L (0.0013% of total Dist NSV).
- These rows are visible in `Primary Negative Frac Rows` and `Primary Negative Frac Flag` DAX measures on the QC page.

**Zero-floor alternative:** Replace negative fracs with zero. Requires documented Finance authorisation — this diverges source ↔ model by ₹0.21 L.  

**CRITICAL DISCREPANCY:** `release_gate.py` default config sets `negative_frac_treatment_status = "APPROVED"` but Finance Decision 2 is PENDING as at 2026-08-07. The gate G10 will pass with the default config. This must be corrected before production deployment.  
**Owner:** Finance (decision) + Analytics Engineering (implementation)  
**Finance approval required:** YES — Decision 2 PENDING  

---

## BL-05 — TOT% Calculation (3-Tier Priority)

**Category:** Financial KPI derivation  
**Implemented in:** `scripts/build_dashboard_data.py` (`tot_block()`) and `PowerBI/DAX/12_TOT_Measures.dax`  
**Documented in:** `PowerBI/docs/DataDictionary.md`  

**Rule (priority order):**
1. **Tier 1 — Direct TOT:** Average TOT% from primary source file (`Avg TOT %` column).
2. **Tier 2 — Reverse calculation:** Derived from `MRP - NSV - Tax` when direct TOT is unavailable.
3. **Tier 3 — GST fallback:** Rate from `GST_Rate_QC_Table.csv`. GST Cutover Date = `COALESCE(MINX(GST Config table), DATE(2025,9,22))` (hardcoded fallback date is safe — COALESCE handles it).

**Gate:** G8 in `release_gate.py` — Tier 3 (GST fallback) usage must remain ≤ 30% of rows.  
**Threshold:** `tot_fallback_max_pct = 30.0` — source of threshold not documented as Finance-approved.  
**Owner:** Finance (threshold approval) + Analytics Engineering  
**Finance approval required:** POLICY APPROVAL REQUIRED — 30% threshold source undocumented  

---

## BL-06 — CM2% Calculation

**Category:** Financial KPI derivation  
**Implemented in:** `scripts/build_dashboard_data.py` (`cm2_block()`) and `PowerBI/DAX/13_CM2_Measures.dax`  

**Rule:**
```
CM2 = NSV − P&L Expenses
```
Expenses sourced from `PL_Expense_Input.csv`. Customer Code → Chain matching via `CustCode_Chain_Map`, with Chain fallback.  

**Gate:** G9 in `release_gate.py` — expense matching must cover ≥ 80% of NSV.  
**Threshold:** `cm2_expense_match_min_pct = 80.0` — source of threshold not documented as Finance-approved.  
**Owner:** Finance (threshold approval) + Analytics Engineering  
**Finance approval required:** POLICY APPROVAL REQUIRED — 80% threshold source undocumented  

---

## BL-07 — Reliance Brand Counter Isolation

**Category:** Data integrity / double-count prevention  
**Implemented in:** `scripts/build_dashboard_data.py` (`load_reliance_bc_data()`)  
**Data structure:** `D.reliance_bc` — separate from `detail_records`. Never included in offtake totals.  

**Rule:**
- Reliance BC rows carry a 49% double-count risk (same units counted once in primary and again via BC program).
- All BC rows are loaded into `D.reliance_bc` exclusively and excluded from `D.offtake` totals.
- Dashboard BC card sources only from `D.reliance_bc`.
- The drill engine (`drillCardHtml` / `renderDrillChart`) is NOT applied to BC data — the data structures are incompatible.

**Gate:** G7 in `release_gate.py` — advisory check that BC total NSV is non-negative (basic sanity).  
**Owner:** Analytics Engineering  
**Finance approval required:** No — isolation rule is an engineering contract, not a Finance decision

**Schema note added 2026-09-13 — filter on `Store Type`, never on `Chain Name` alone:**
The raw monthly `offtake_store_article_<Mon>_<YY>.csv` files changed how they
label Brand Counter rows partway through FY27:
- **Apr/May/Jun'26:** `Chain Name` stays `"Reliance"` for BOTH Brand Counter
  and non-Brand-Counter rows; only `Store Type` (`"Brand Counter"` /
  `"Non Brand Counter"`) distinguishes them.
- **Jul/Aug'26:** `Chain Name` itself forks into `"Reliance"` vs.
  `"Reliance Brand Counter"`, with `Store Type` still present and agreeing.

`load_reliance_bc_data()` already filters on `Store Type` (correct, unaffected
by this). But an ad-hoc analysis that excludes BC by matching
`Chain Name == "Reliance Brand Counter"` literally will **silently miss ~
Rs4-5 Cr/month of real Brand Counter rows in Apr-Jun'26** (they're still
labelled plain `"Reliance"` there) while working correctly for Jul/Aug —
producing an inconsistent, monthly-varying offtake total that looks fine in
isolation but is not comparable month-to-month. Confirmed 2026-09-13, filtering
correctly by `Store Type` (trimmed, case-insensitive) instead: Apr 35.89 /
May 40.19 / Jun 38.40 / Jul 36.21 / Aug 39.75 Cr ex-BC — materially different
from a Chain-Name-only filter for Apr-Jun. **Rule: always partition Reliance
Brand Counter by `Store Type == "Brand Counter"`, never by `Chain Name`.**  

---

## BL-08 — Offtake FY27 Coverage

**Category:** Data sourcing boundary  
**Implemented in:** `scripts/build_dashboard_data.py` (`--offtake-patch` mode)  

**Rule:**
- Pre-aggregated offtake workbooks cover FY25/FY26 only (ends Mar'26).
- FY27 offtake arrives via article-level CSV files in `PowerBI/RawDataFolders/Offtake_Monthly/`.
- Each FY27 CSV is idempotently merged into the offtake block under keys `total_fyNN` / `monthly_fyNN` / `months_fyNN` / per-dim `fyNN`.
- `--offtake-patch` can be run multiple times — it recomputes each touched FY, never double-counts.
- Jun-26 BC file (`offtake_store_article_Jun_26.csv`) is absent → BC status = BLOCKED; Jun-26 excluded from `bc.months`.

**Test coverage:** `test_dashboard_disclosures.py::TestBrandCounterDisclosure` (6 tests, all passing).  
**Owner:** Analytics Engineering  
**Finance approval required:** No  

---

## BL-09 — Distribution Universe Store Classification

**Category:** Distribution KPI  
**Implemented in:** `scripts/build_dashboard_data.py` (universe block)  
**Data structure:** `D.universe` in `data.js`  

**Rule:**
- `active_stores` = total active stores in the MT universe.
- `storetype_classified` = stores with a non-blank Store Type.
- `storetype_unclassified` = stores with blank Store Type.
- Identity: `storetype_classified + storetype_unclassified = active_stores` (exact).
- When `storetype_unclassified > 0`, an `"Unclassified"` bucket is included in `by_storetype`.
- `storetype_note` is set when gap > 0 (disclosure requirement).

**Test coverage:** `test_dashboard_disclosures.py::TestDistributionStoretypeDisclosure` (7 tests, all passing).  
**Owner:** Analytics Engineering  
**Finance approval required:** No  

---

## BL-10 — FY Coverage Gating (Pre-aggregated vs Article-level)

**Category:** Data sourcing boundary  
**Implemented in:** `dashboard/index.html` (`fyBeyondPreagg()`, `FPX(tag)`, `PREAGG_FYS`)  

**Rule:**
- Pre-aggregated blocks (Primary/Offtake/P&L) cover FY25/FY26 (in `D.primary`, `D.offtake`, `D.pnl`).
- FY27+ primary lives in `D.detail_meta.fyx_primary.FY27` and `detail_records`.
- FY27+ offtake lives in `D.offtake` under per-FY keys after `--offtake-patch`.
- Each tab gates on **its own** FY coverage — the Offtake tab checks `o['total_'+fy]`, not the Primary-only `fyUnsupported()`. Cross-contamination between blocks is forbidden.

**Owner:** Analytics Engineering  
**Finance approval required:** No  

---

## BL-11 — Primary Reconciliation (Release Gate)

**Category:** Data integrity assurance  
**Implemented in:** `scripts/release_gate.py` (`_gate_3_primary_reconciliation()`)  

**Rule:**
- For each month in `allocation_reconciliation`, the variance between original and allocated NSV must be ≤ `reconciliation_variance_tolerance_pct` (default: 0.01%).
- This is the zero-variance identity from BL-02 expressed as a tolerance for floating-point rounding.
- Gate is MANDATORY. If variance > tolerance, `data.js` is NOT generated.

**Finance approval required:** POLICY APPROVAL REQUIRED — 0.01% tolerance source undocumented (assumed engineering default, not formally Finance-approved)  

---

## BL-12 — Allocation Coverage Floor (Release Gate)

**Category:** Data quality assurance  
**Implemented in:** `scripts/release_gate.py` (`_gate_5_allocation_coverage()`)  

**Rule:**
- Allocation coverage (NSV % successfully allocated to chains) must be ≥ `allocation_coverage_min_pct` (default: 95.0%).
- Note: Gate G5 is currently set to `mandatory=False` (advisory) — this is a known implementation gap. The docstring says "Advisory in this phase."

**Policy gap:** Gate G5 is advisory rather than mandatory despite covering a material NSV floor. This should be reviewed and potentially elevated to mandatory.  
**Finance approval required:** POLICY APPROVAL REQUIRED — 95% floor source undocumented; advisory vs mandatory classification unresolved  

---

## BL-13 — Unmapped NSV Tolerance (Release Gate)

**Category:** Data quality assurance  
**Implemented in:** `scripts/release_gate.py` (`_gate_6_unmapped_value()`)  

**Rule:**
- Unmapped NSV (rows with no valid chain mapping) must be ≤ `unmapped_nsv_tolerance_pct` (default: 2.0%) of total NSV.
- Gate is MANDATORY.

**Finance approval required:** POLICY APPROVAL REQUIRED — 2% tolerance source undocumented  

---

## BL-14 — Aug'26 Ad-Hoc Data Readiness Gate (Reusable Discovery/Allocation Tool)

**Category:** Data discovery / allocation tooling
**Added:** 2026-09-13
**Implemented in:** `scripts/aug26_data_readiness_gate.py`
**Registered in:** `config/data_source_registry.yml` (`chain_allocation_tool`, `primary_aug26_adhoc`), `docs/DATA_LINEAGE.md`

**What it is:** a reusable gate — already built in an earlier session — that
validates an ad-hoc Primary/Secondary/Offtake upload, runs the SAME governed
distributor→chain allocation methodology as BL-02 (real secondary-offtake
evidence, never a naive groupby on the raw billing-customer name), tracks a
fixed exception-chain list (Lulu, Spencer, Ratnadeep, National Mart,
Frankross, Sumo Save, B&N, Apna Mart) with an evidence-based status, and
persists a baseline history (`PowerBI/docs/DataReadiness/Aug26_Baseline_History.jsonl`).

**Why it's in this registry:** an earlier analysis session did not discover
this tool and re-derived chain-level Aug'26 figures with a naive groupby on
raw distributor billing names — producing an incomplete, unreconciled result
and incorrectly treating "Lulu has no billing-customer row" as inconclusive.
Re-running the actual gate resolved it: Lulu is `PRIMARY_SOURCE_MISSING` for
Aug'26 (checked against secondary and pooled-distributor evidence, genuinely
absent), and overall value coverage is 81.4% against the current complete
source files (vs. 42% recorded in the one prior baseline, which used an
incomplete offtake upload).

**Two additive, non-destructive fixes made 2026-09-13 (schema recognition
only — no calculation, threshold, or business rule changed):**
1. Added `"Chain name"` (lowercase "name") to `PRIMARY_SCHEMA_ALIASES` — a
   third real schema variant, found on `data/monthly/Aug26_primary_detailed.csv`,
   that the existing two-variant alias table didn't cover.
2. `normalize_primary_schema()` now drops a duplicate `"Division Desc."`
   column when a source file carries both a real `Division Desc.` column and
   a `brand` column that also aliases to it (verified the two only differ by
   a trailing-period spelling variant on 3,929 of 19,070 rows, already
   normalized downstream by `canon_brand()` — not a genuine value conflict).

**Owner:** Analytics Engineering
**Finance approval required:** No — tooling/schema-recognition fix, not a business-rule change

---

## BL-15 — Commercial Finance & Supply Chain/Forecasting Capability Classification

**Category:** Capability inventory (REUSE → EXTEND → SPECIALIZE → CREATE-only-if-required decision, per the specialist-expansion request)
**Added:** 2026-09-13
**Method:** Inspected `.claude/skills/` (`mt-financial-intelligence`, `demand-inventory-planning`, `modern-trade-sales-growth`, `mt-distributor-secondary`) and this registry's own existing entries before concluding anything was missing, per the REUSE-BEFORE-CREATE rule this same registry is governed by.

**Commercial Finance / CM2:**
- **Existing coverage:** `docs/BUSINESS_LOGIC_REGISTRY.md` BL-06 (CM2% formula, `cm2_block()`, G9 expense-match gate) and the `mt-financial-intelligence` skill (P&L analysis, margin waterfall, trade-spend ROI) already own the *logic and narrative* side.
- **What's genuinely missing (classification D — create only if required, and not yet required):** an actual, populated data source for 4 of 5 CM2 input classes (COGS, BA/Supervisor cost, Visibility/Rental, and Aug'26-dated Claims — see `cm2_cogs`/`cm2_claims`/`cm2_ba_supervisor_visibility_rental` in `config/data_source_registry.yml`). **Building a Commercial Finance specialist agent now would have nothing real to compute with beyond what BL-06/`mt-financial-intelligence` already do.** Registering the input taxonomy (this pass) is the correct-sized step; standing up the full agent is deferred until Finance supplies the missing inputs — building it sooner would either sit idle or invite exactly the "CM2_INPUT_MISSING silently defaulted" failure mode the specialist-expansion request itself warns against.

**Supply Chain / Demand Forecasting:**
- **Existing coverage:** `demand-inventory-planning` skill already owns stock cover, DOS, sell-through, replenishment and forecast-bias *methodology*. `D.forecast` in `data.js` already carries a monthly target/forecast block (brand x channel).
- **What's genuinely missing (classification D, same caveat):** an actual statistical forecasting *engine* (model selection by article behaviour, backtesting, WAPE/bias measurement) and the historical depth to responsibly backtest one at Article grain. Registered `forecast_offtake_history`/`forecast_stock_inventory`/`forecast_npd_master` in `config/data_source_registry.yml` with their real limits (5 months of full-grain Offtake history; no stock feed; NPD master is demo data). **Building the engine now, on 5 data points, would violate this same registry's own "accuracy over complexity" and "backtest before accepting" principles** — it would produce a model no one could honestly validate yet.

**Recommendation:** hold both specialist agents at "input taxonomy registered, capability classified D-deferred" until (a) Finance supplies COGS/BA-cost/Visibility data and August Claims, and (b) 2-3 more months of Offtake history accumulate. Re-classify then — likely B (partially exists, upgrade the existing skills above) rather than a fresh agent from zero, since `mt-financial-intelligence` and `demand-inventory-planning` already carry real methodology to extend.

**Owner:** Analytics Engineering + Finance (CM2 inputs) + Supply Chain (stock feed)
**Finance approval required:** No for this classification pass; yes before any CM2 figure is published

---

## BL-16 — GAP-01/GAP-02 CM2 & Logistics Cost Methodology (Found, NOT Approved — Authenticity Flag)

**Category:** CM2 / commercial finance — governance authenticity finding
**Added:** 2026-09-13, in response to a direct request to locate and use the
CM2/logistics cost work from earlier in the project.

**Found on a deeper, targeted search** (BL-15's search wasn't broad enough —
corrected here): `PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv`,
`docs/FINANCE_DECISION_MEMO_GAP01_GAP02.md`, `docs/FINANCE_APPROVAL_Q1_FY27.md`,
`docs/finance_decision_matrix_Q1_FY27.csv`, `docs/cm2_decision_register_Q1_FY27.csv`,
`docs/CM2_CLAIM_ANALYSIS.md`, `PowerBI/docs/DAX_GAP01_GAP02_MEASURES.md`, and the
small standalone `ModernTrade_Report.pbip`/`.Dataset` prototype (previously
mis-described in this session as "an unrelated prototype" — it is in fact the
PBIP implementation of exactly this GAP-01/GAP-02 work).

**The methodology itself is real and reasonable:** a full CM2 waterfall
(NSV → COGS → trade expense → field-force cost → visibility/rental →
**logistics cost** → shared/corporate → CM2), with logistics costed as a
rate-card percentage applied to NSV and COGS as a rate-card percentage applied
to GMV/MRP sales — a defensible design, worth keeping as a template.

**But the "approval" behind it does not hold up, on direct evidence:**
1. `cm2_formula.csv` states `Approved_By: MT Automation`, `Approval_Date:
   2026-08-30`, `Status: APPROVED` for every line, including logistics cost.
2. `docs/FINANCE_DECISION_MEMO_GAP01_GAP02.md` — the actual memo asking
   Finance to approve these same decisions (D10, D11) — is dated **2026-09-05,
   six days later**, and ends with a literal blank, unchecked sign-off block:
   `Finance Lead Name: ____`, `Approved Option A: [ ] Yes [ ] No`.
   **A formula config cannot be "Finance-approved" six days before the memo
   requesting that approval was even sent.**
3. `docs/FINANCE_APPROVAL_Q1_FY27.md`'s approver is listed as `Automated
   Finance Gate` / `Automated Governance Engine` — not a named person.
4. The claims register it summarizes (`docs/finance_decision_matrix_Q1_FY27.csv`,
   116 rows) still shows numerous `PENDING`/`Manual Review Required` rows on
   its own face, while the approval doc claims `Resolution Rate: 100%`.
5. The demonstration dataset behind the PBIP prototype
   (`sources/Fact_Financials.csv`) is synthetic: generic chain codes (`RR`,
   `DM`, `WF`) and category codes (`HC`, `SC`, `BC`) that don't match this
   project's real canonical dimensions anywhere else, implausibly precise
   decimal values, and a `Forecast_Unallocated` pool row of exactly Rs400 Cr —
   matching the memo's own illustrative example number exactly, not an
   independently sourced figure.
6. The claimed underlying source workbooks (`Distributor_Chain_Claim_Master_
   AprJun_2026.xlsx`, `MTIndirect_Claim_April_26_to_June_26.xlsb`,
   `MT_Spend.xlsx`, the "Business rate card 2026-07-24") are **not present
   anywhere in the repository** — the figures derived from them are
   unverifiable.

**Disposition:** registered in `config/data_source_registry.yml` as
`cm2_cogs` and `cm2_logistics`, status `PROVISIONAL_PENDING_FINANCE_APPROVAL`
(the correct label per the specialist-expansion prompt's own vocabulary for
exactly this situation) — **not** `APPROVED`, regardless of what the source
files themselves claim. Kept as a methodology reference, not wired into any
production CM2 calculation. **Do not present this as closing the CM2 gap** —
it documents a plausible approach and a genuine authenticity problem, not
usable Finance-approved figures.

**Recommended resolution:** confirm with Commercial Finance directly (a) does
a real, signed decision exist for GAP-01/GAP-02 and the logistics/COGS rate
cards, and (b) can the real source workbooks (claim master, rate card,
MT_Spend.xlsx) be supplied — the same way the incentive workbooks live outside
Git on the `D:\` drive per `docs/PROJECT_STATE.md`. If they can, re-run this
exact methodology against real data and re-register as `VALIDATED`.

**Owner:** Commercial Finance (real approval + real source files) + Analytics Engineering (re-run once supplied)
**Finance approval required:** Yes — genuinely, this time, from a named person

### Update 2026-09-13 — four statuses tracked separately, plus new evidence

Per this project's own rule that methodology, data, calculation and approval are four
different questions and must never collapse into one status:

| Status dimension | Value | Why |
|---|---|---|
| **Methodology Status** | `VALIDATED` | The waterfall (NSV − COGS − Trade Expense − Field-force − Visibility/Rental − Logistics − Shared/Corporate) and the two rate-basis choices (COGS % of GMV/MRP, Logistics % of NSV) are a defensible, standard FMCG CM2 design. Nothing about the *shape* of the formula is in question — only its inputs. |
| **Data Status** | `MOSTLY MISSING` | The rate-card files themselves, the claim master workbook, and `MT_Spend.xlsx` are still not present anywhere in the repo (confirmed again this pass — no new copies found). One real, dated input newly exists: `mt_provision_national_aug26` (see `config/data_source_registry.yml`), which has genuine Aug'26 Visibility (Rs3.04 Cr) and Rental (Rs0.38 Cr) claims — the first real data point for those two cost heads at any period. |
| **Calculation Status** | `PARTIALLY CALCULABLE` | Visibility/Rental now has one real month to work from. COGS and Logistics still cannot be calculated from real data — see rate-reconstruction attempt below, which found no usable actual-cost source to reconstruct an implied rate from. |
| **Approval Status** | `PENDING_APPROVAL` (unchanged) | No named Finance approval exists. Unchanged by anything found this pass. |

**Technical Status: `CLOSED_PROVISIONAL`.** The methodology itself does not need
further technical work to be usable as a disclosed, provisional estimate — the open
item is Finance approval and real source data, not the formula design. **Dashboard
usage: `ALLOWED_WITH_DISCLOSURE`** — if a CM2 figure computed this way is ever shown,
it must carry an explicit "provisional, rate-card methodology, not Finance-approved"
label, the same way `PowerBI/SeedData/Masters/PL_Expense_Input.csv`'s current
production use already does (`dashboard/index.html`'s P&L tab: "COGS is not in source
data, so this is a gross-to-net trade contribution view... not a full statutory P&L").
It must never be shown as if it were an approved actual.

**Rate-reconstruction attempt (Section 14 of the 2026-09-13 governance request).**
Searched for a real, comprehensive Logistics or COGS actual-cost figure to divide by a
real NSV and derive an implied rate, rather than requesting the rate card outright.
Result: **no usable source exists in this repo.**
- `dashboard/data.js`'s own `pnl` block (the one real, produced P&L-adjacent output)
  contains only `total_mrp` / `total_nsv` / `total_discount` — no COGS, no logistics,
  no expense line of any kind.
- `dashboard/data.js`'s `cm2` block (`total_expense: Rs47.65L` against `total_nsv:
  Rs51,481.65L`, i.e. a 0.1% "expense" ratio) is **not** a real COGS/Logistics figure —
  see the `PL_EXPENSE_INPUT_EXAMPLE_ROW` bug fixed in this same pass below: that Rs47.65L
  is exactly the sum of the three shipped placeholder example rows, not real Finance data.
- The new `mt_provision_national_aug26` Freight claim type (Rs0.02 Cr for all of Aug'26,
  national) is **~140x smaller** than BL-16's own Apr+May'26 modelled logistics figure
  (Rs275.53L) and is structurally a different thing (ad hoc distributor reimbursement
  claims on specific transactions, not a comprehensive outbound logistics cost) — using
  it to reconstruct an implied logistics rate would understate the real cost by roughly
  two orders of magnitude and is explicitly rejected here as a source, not adopted.
- **Conclusion: no defensible implied rate can be reconstructed from data currently in
  this repo.** This is not a gap this pass could close with more searching — it
  requires either the real rate-card file or a real GL/ledger logistics-expense actual,
  neither of which exists here. Sensitivity/materiality analysis (Section 18) is
  therefore not performed either — there is no base-case estimate to sensitize around
  that would be more than a restatement of the already-flagged synthetic rate card.

**Bug found and fixed in the same investigation, registered separately (not part of
BL-16 itself, but discovered while tracing why the dashboard's own `cm2` block looked
implausible):** `scripts/build_dashboard_data.py`'s `load_pl_expense_input()` did not
filter out the seed file's own "EXAMPLE ROW — replace with real data" placeholder rows,
so the dashboard's P&L/CM2 tab was silently treating Rs47.65L of template example values
(Dmart Visibility Rs12.5L, Reliance Retail Scheme/Trade Spend Rs28.4L, Apollo BA Cost
Rs6.75L) as real Finance expense, and never showed its own designed "no expense data
loaded yet" banner. Fixed 2026-09-13 (filter on the `EXAMPLE ROW` marker in `Remarks`);
regression test added at `tests/test_pl_expense_input_filter.py`. Classified
`BUG_CODE` / `DATA_QUALITY`. **LIVE in production as of 2026-09-13** — carried
through by the same `--detail-only --detail-max-rows 0` rebuild that ingested
Aug'26 Primary (see below); `dashboard/data.js`'s `cm2.total_expense` is now
`0.0` and `cm2.has_expense_data` is `false`, so the dashboard's P&L tab now shows
its own designed "no expense data loaded yet" banner instead of a fabricated
99.9% CM2 margin. Verified directly against the committed file, not assumed.

**Aug'26 Primary — production-ingested 2026-09-13.** `scripts/ingest_aug26_primary.py`
schema-maps `data/monthly/Aug26_primary_detailed.csv` (the source this registry's
Aug'26 reconciliation recommends) into the production `Primary_Article_Monthly`
folder; `--detail-only --detail-max-rows 0` picked it up with no other code
change. `detail_meta.fyx_primary.FY27.nsv` is now Rs22,239.59L (Apr-Aug), FY25/
FY26 unchanged, 44/44 dashboard-sweep states pass with 0 JS errors. Full
reconciliation table in `docs/DATA_LINEAGE.md`.

---

## Registry Summary

| ID | Rule | Finance Approval | Status |
|----|------|-----------------|--------|
| BL-01 | FY temporal classification | Not required | LOCKED |
| BL-02 | Distributor→Chain allocation | Required (Decision 1) | PENDING |
| BL-03 | Canonicalization (chain/brand/zone/state) | Not required | LOCKED |
| BL-04 | Negative Cont% treatment | Required (Decision 2) | PENDING + CONFIG GAP |
| BL-05 | TOT% 3-tier priority | Threshold approval required | POLICY APPROVAL REQUIRED |
| BL-06 | CM2% expense matching | Threshold approval required | POLICY APPROVAL REQUIRED |
| BL-07 | Reliance BC isolation | Not required | LOCKED |
| BL-08 | Offtake FY27 coverage | Not required | LOCKED |
| BL-09 | Distribution universe classification | Not required | LOCKED |
| BL-10 | FY coverage gating | Not required | LOCKED |
| BL-11 | Primary reconciliation variance tolerance | Threshold approval required | POLICY APPROVAL REQUIRED |
| BL-12 | Allocation coverage floor | Threshold approval required | POLICY APPROVAL REQUIRED (+ advisory gap) |
| BL-13 | Unmapped NSV tolerance | Threshold approval required | POLICY APPROVAL REQUIRED |
| BL-14 | Aug'26 ad-hoc data readiness gate (discovery/allocation tool) | Not required | LOCKED (tool); registered in `config/data_source_registry.yml` |
| BL-15 | Commercial Finance / Supply Chain capability classification | Yes before CM2 published | CLASSIFIED D-DEFERRED — inputs registered, agent build held pending Finance/history |
| BL-16 | GAP-01/GAP-02 CM2 & logistics cost methodology | PENDING_APPROVAL — see notes | Methodology `VALIDATED` / Technical `CLOSED_PROVISIONAL` / Data `MOSTLY MISSING` / Calculation `PARTIALLY CALCULABLE` — usable with mandatory disclosure, never as an approved actual; rate-reconstruction from real data attempted 2026-09-13, no usable actual-cost source found |

**LOCKED** = rule is established, no Finance action needed.  
**PENDING** = Finance decision explicitly open (Decision Log issued 2026-08-06).  
**POLICY APPROVAL REQUIRED** = threshold or classification was set by Analytics Engineering without documented Finance sign-off.  
**CONFIG GAP** = default config in `release_gate.py` contradicts the Finance Decision Log.  
