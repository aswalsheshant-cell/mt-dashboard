# Project State

Single source of truth for where this project is, so a resumed environment does
not have to reconstruct weeks of work from conversation history. The SessionStart
hook prints the "Next Approved Task" section on every resume.

**Contains no confidential data.** No employee name, employee ID, incentive
amount or DMS client identity belongs in this file — counts only.

Update after a **validated** milestone, then commit and push with that milestone.

---

## V1 Status — CONDITIONALLY READY

**Code is closed. One external business input is outstanding.** Real Windows
acceptance (2026-09-12) proved the dashboard reproduces completely from a fresh
clone — 44 states, 0 failures, 0 JS errors — and proved the incentive scripts
correctly resolve real paths (space + `&` included) and fail safely when an
input's shape doesn't match. It also found that the company's live FY27 slab
master is a different shape from what `--slabs` expects (see
`docs/RUNBOOK.md` §"The slab file must be the flattened Designation schema").

That gap is an **external business input, not a code defect**: no reproducibility
failure, no fabricated output, no invariant broken. `read_slabs()` now names the
exact expected schema and exits cleanly rather than crashing — verified against
a synthetic fixture shaped like the real matrix workbook.

**Blocking full closure:** locate or (once, by a person, against the incentive
communication) produce the flattened, `Designation`-keyed slab file. Everything
else in `docs/RUNBOOK.md` §5 is unaffected.

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

`a49e998` — PR #218 merged; recovery stream #216–#219 complete
Validated: 2026-09-25 — production certification on merged `main`
(READY_WITH_GOVERNED_BLOCKERS; see "Production certification — 2026-09-25" below).
Previous: `ec55115`, 2026-09-11, fresh-clone reproducibility PASS.

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

- Data discovery layer (2026-09-13): `config/data_source_registry.yml` +
  `scripts/data_catalog.py` + `docs/DATA_AVAILABILITY_MATRIX.md` +
  `docs/DATA_LINEAGE.md`. Query this BEFORE concluding a metric/month is
  unavailable — it fixed a real case where Aug'25 Offtake was wrongly called
  missing (it's in `dashboard/data.js`'s pre-aggregated block, not the FY27+
  raw watch folder) and where Aug'26 chain-level Primary was computed with a
  naive groupby instead of the existing governed allocation tool
  (`scripts/aug26_data_readiness_gate.py`, now registered under BL-14 in
  `docs/BUSINESS_LOGIC_REGISTRY.md`). Two known gaps this pass did NOT
  resolve: Aug'26 Primary total has an unreconciled ~Rs2.1 Cr SOURCE_CONFLICT
  between two files (see `docs/DATA_LINEAGE.md`), and only Primary/Offtake/
  chain-allocation/category-mapping are catalogued so far — extend the
  registry the next time another metric's lineage is actually traced, don't
  pre-fill entries for ones that haven't been.
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

## Dashboard Enhancement Round (2026-09-16) — COMPLETE

Found via a deliberate tab-by-tab, sub-tab-by-sub-tab root-cause audit of
`dashboard/index.html` (requested specifically to find issues the 44-state
automated sweep would not catch on its own — it only asserts "no crash," not
"actually works"). One real bug + 7 proposed additions, all merged to `main`.
Each item was independently cross-checked against real numbers in Python
before commit — no fabricated figures. Unrelated to the incentive workbook /
V1 status above; does not change any Regression Baseline number.

| # | Item | PR | What |
|---|---|---|---|
| Fix | Reliance Brand Counter sub-view always empty | [#143](https://github.com/aswalsheshant-cell/mt-dashboard/pull/143) | Filter matched `Brand==='Reliance'` (never true — Reliance is a Chain, not a Brand); fixed to `Chain==='Reliance Retail'`. Recovered 32,505 real transactions, correct zone split. Write-up: `docs/CASE_STUDIES.md` CS-01 |
| #5 | Data Model doc | [#144](https://github.com/aswalsheshant-cell/mt-dashboard/pull/144) | `docs/DATA_MODEL.md` — names `detail_records` as the fact table in star-schema terms; flags `docs/DATA_JS_SCHEMA.md` as stale (not fixed — see below) |
| #6 | SQL cookbook | [#145](https://github.com/aswalsheshant-cell/mt-dashboard/pull/145) | `docs/mt_sql_cookbook.sql` — 3 queries verified against a real SQLite load of `detail_records` |
| #3 | Cumulative Rank & Running Total card | [#146](https://github.com/aswalsheshant-cell/mt-dashboard/pull/146) | Channel & Chain Performance → Primary Sales sub-view; cumulative % crosses 90% at Wellness Forever, matches SQL cookbook exactly |
| #1 | SKU NSV Volatility card | [#147](https://github.com/aswalsheshant-cell/mt-dashboard/pull/147) | Commercial Analytics tab; coefficient-of-variation ranking, min 3 months / ₹5L avg NSV to qualify |
| #2 | Promo Depth vs. Sell-Through correlation card | [#148](https://github.com/aswalsheshant-cell/mt-dashboard/pull/148) | Demand & S&OP Planning → Promotional Impact sub-view; Pearson r = -0.157 across 17 matched FY27 chains, labelled correlation-not-causation |
| #4 | Audit-confidence margin-of-error note | [#149](https://github.com/aswalsheshant-cell/mt-dashboard/pull/149) | Store Audit Scorecard; finite-population-corrected 95% CI (n=189 of N=426 → ±3.8pp), flags when below the governed minimum audit coverage % |
| #7 | Case study doc | [#150](https://github.com/aswalsheshant-cell/mt-dashboard/pull/150) | `docs/CASE_STUDIES.md` — full CS-01 write-up of the Reliance Brand Counter bug (problem → root cause → fix → verification → reusable methodology) |

**Not actioned this round, flagged as a real finding:** `docs/DATA_JS_SCHEMA.md`
is significantly stale — documents 14 `data.js` blocks vs. 30 real ones, and
lists wrong `detail_records` field names (e.g. `article_id` instead of the
real field) plus two blocks that don't exist (`release_gate_report`, `share`).
Not fixed in this round; a follow-up task if anyone picks it up next.

Validated: 2026-09-16 — full 44-state sweep clean after every merge; every
number quoted above was independently reproduced in Python against the live
`dashboard/data.js` before its commit, not just eyeballed in the browser.

### Follow-on: Article Classification card + 2 candidate methodologies (2026-09-17)

Business shared two supply-chain reference frameworks (Min-Max Inventory,
FMS/ABC/RIS classification) and an FP&A EBITDA-bridge example. Same
verify-before-build discipline as the round above:

- **Built and live:** `computeInventoryClassification()` / `inventoryClassificationSection()`
  in `dashboard/index.html`, Inventory & Supply Health → Demand-Supply Gap
  sub-view. Classifies every qualifying article on real NSV/frequency this
  period — Value (ABC, cumulative NSV share), Movement (FMS, share of months
  with a real sale), Demand pattern (RIS, coefficient of variation) — plus a
  suggested action per combination. Standard external convention, not a
  Honasa-specific rule; reuses the same per-article monthly-NSV aggregation
  `computeSkuVolatility()` already uses. Top row verified exactly against a
  fresh Python read of `data.js`: n=15 months, total ₹4,668.79L, CV 22.90%.
  44-state sweep: 0 failures, 0 JS errors.
- **Registered as candidate methodology, not built (blocked on real data):**
  Min-Max Inventory (see Blocked Capabilities, `forecast_stock_inventory` in
  the registry) and the EBITDA Bridge P&L waterfall (see Blocked
  Capabilities, `cm2_pl_expense_input` in the registry) — both share the
  same root cause as the existing CM2/stock-on-hand gaps, so building either
  for real today would mean fabricating a number a store, DC, or Finance
  reviewer could act on.

### Phase 2B — Canonical Financial Truth remediation, closed (2026-09-24/25)

`docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md`'s full inventory (F1-F22 across two
discovery passes) is now fully resolved or explicitly closed with no action needed.
Regenerated `dashboard/data.js` from real raw source for the first time this session
(PR #209) — found and fixed two independent, pre-existing bugs along the way
(`--primary-only` never re-applying the `by_channel` correction; a chain-table
`every()`/`filter()` bug F14's own already-merged fix exposed). Follow-up pass (item
7 of the remediation order) fixed F19 (Reliance Brand Counter period-leakage — found
to be dormant/dead code, not live, correcting the original discovery agent's
severity call), F21 (Power BI P&L silently defaulting a missing month to a
fabricated 50% Gross Margin — now fails closed, plus a new release gate), and F17/
F15 (two more dormant hardcoded/fabricated-data landmines). PRs #209, #210, #211 —
full detail and evidence in the inventory doc itself, not duplicated here.

**What's left is a business input, not code:** Finance must supply the
Jun/Jul/Aug'26 `AssumptionTable.csv` rows (Required Business Inputs #7 above) —
enforced by a release gate now, so it can't be missed silently, but not something
this project can produce itself.

### Selective recovery from a closed branch — PR #14 (2026-09-25)

Branch `claude/offline-ai-data-analyst-iiincp` (last commit `aac1543`,
2026-07-24) holds useful work that never reached `main`:
[PR #14](https://github.com/aswalsheshant-cell/mt-dashboard/pull/14) was closed
without merge on 2026-08-23. The session behind it stopped on a usage-credit
limit, not on context compaction. The branch shares **no git history** with
current `main`, so it cannot be merged or cherry-picked as-is.

- **Status of the branch:** historical evidence only. Do not merge, rebase,
  modify or delete it. Nothing on it is approved production truth. Its own
  checkpoint file `ai-agent/SESSION_STATE.md` is stale (last updated 07-10;
  8 later commits are not reflected), and its "95 tests pass" claim has not
  been re-verified.
- **Recovered so far:** filter-value normalisation (the branch's `normVal`),
  rebuilt against current `main` — duplicate filter choices that differ only
  by case or spacing now collapse to one. On current data this affects Range
  (2 pairs) and Article (3 pairs); Zone/State have no variants today, so the
  original West/WEST case is preventive. Display/matching only — no record or
  total changes. Test: `tests/test_filter_value_normalisation.js`.
- **Candidates, not yet recovered — audit component by component
  (KEEP / REBUILD / ALREADY_REPLACED / OBSOLETE / BLOCKED) before any port:**
  offline AI analyst module (`scripts/ai_analyst/`), its Excel QC scanner
  (`xlsx_qc.py`), the AI Analyst dashboard tab, `scripts/audit_jun26_mapping.py`,
  `PowerBI/docs/Jun26_Onboarding_Execution_Log.md`.
- **AI Analyst (NL query engine, `ai_analyst/` package, 13th tab) — ARCHIVED
  as reference, 2026-09-25.** No verified business requirement for
  natural-language querying exists today: `docs/CANONICAL_METRIC_IMPLEMENTATION_PLAN.md`
  places an NL "AI Insight Agent" at Phase 9, gated on Phases 1–8 certified plus
  one full reporting cycle, and it may only consume certified measures, never
  compute them. Its old 95 passing tests are not a reason to port it. Revisit
  only if MT Leadership raises the need; then design fresh against the
  canonical engine. The Excel QC scanner was recovered separately (PR #218).
- **Not to be recovered:** the branch's Power BI DAX / Power Query changes —
  the current Power BI kit has moved past them. Compare only if a specific
  business rule is shown to be missing from current assets.
- **Blocked:** "METock" workbook QC — `BLOCKED_INPUT`, needs the source
  `.xlsx` (never in the repo). Does not block the rest of the recovery.

### Production certification — 2026-09-25 (main `a49e998`)

**Verdict: READY_WITH_GOVERNED_BLOCKERS.** Code, tests, gates and deploy are
green on merged `main`. What remains is business input, owner decisions and PR
housekeeping, each listed below with an owner — none is an unexplained failure.

Recovery PRs merged, one approval each: #217 `a77b899` → #216 `54fa67d` →
#219 `50ec081` → #218 `a49e998`. Across all four, `dashboard/data.js`,
`config/`, `PowerBI/` and seed data are byte-identical to pre-recovery `8b5797d`.

Evidence (run on `a49e998`): `pytest tests/` 368 passed; `pytest scripts/` 389
passed (excl. `test_json_serialization.py`, see CB-02); `tests/canonical/` 100;
`answer_governance/` 60; every `canonical_gate_checks.py` gate PASS
(reconciliation, numeric-safety, governance, fallback-safety, unit-isolation,
missing-never-zero, availability-metadata, source-contracts);
`validate_historical_baseline.py`, `validate_promo_schema.py`,
`ci_validate_datajs.py` (7 baseline invariants) PASS; 18 JS test files 0
failing; 44-state sweep 0 failures / 0 JS errors; smoke test 7/7 governed
baselines. Post-merge CI on `main`: Validation & QC, CodeQL, Power BI Windows
CI, GitHub Pages deploy all success.

| ID | Blocker | Class | Evidence | Owner | Next action / exit condition |
|---|---|---|---|---|---|
| CB-01 | FY27 zone rollup in `data.js` carries Rs 11.64 Cr eB2B + SIS (non-MT) primary; Nykaa (FSN) billed via eB2B | BLOCKED_INPUT + BLOCKED_HUMAN_DECISION | `scripts/mt_channel_reconciliation.py dashboard/data.js` → BLOCKED (exit 2); runs non-blocking in the Production Acceptance Gate by design. **Doc drift:** `docs/ISSUE_MT_CHANNEL_CONTAMINATION.md` says CLOSED — true for the July deck, not for the dashboard's zone rollup | MT Leadership (Nykaa treatment); MT Analytics (source file) | Supply full July-26 article-wise primary; decide Nykaa treatment; re-run check until exit 0, then make that CI step blocking |
| CB-02 | `scripts/test_json_serialization.py` cannot import `_cm2_provisional_state` | MERGE_REQUIRED (owner approval) | Scratch merge of #159 + #158 onto `a49e998`: file 38 passed, `scripts/` 427 passed, no data/config change. #159 alone: 16 failures (needs #158's strict JSON boundary) | Repo owner | Approve #159 and #158 (each separately, after re-verify on then-current `main`) |
| CB-03 | METock workbook QC | BLOCKED_INPUT | Workbook never supplied; scanner ready (`scripts/xlsx_qc.py --allowed`) | Workbook owner | Supply the `.xlsx` |
| CB-04 | 9 open PRs share no history with `main`: #119, #129–#136 | BLOCKED_HUMAN_DECISION | `git merge-base` finds none (history rewritten after they opened, same as PR #14) | Repo owner | Per PR: close as superseded, or rebuild on `main` |
| CB-05 | 10 open PRs mergeable but unreviewed: #156, #158, #159, #160, #165, #168, #169, #170, #215 clean; #179 conflicts | BLOCKED_HUMAN_DECISION | `git merge-tree` against `a49e998`; 4–151 commits behind | Repo owner | Review in order: #215 (flagged CRITICAL), CB-02 pair, then the rest |
| CB-06 | FY27 incentive business inputs (Next Approved Task) | BLOCKED_HUMAN_DECISION | Unchanged by this work | MT Leadership / Finance | See Next Approved Task |
| CB-07 | `main` has no branch protection | BLOCKED_HUMAN_DECISION | `docs/MAIN_BRANCH_PROTECTION_AUDIT.md` | Repo owner | Add a ruleset (Settings access) |
| CB-08 | Live GitHub Pages fetch from this container | BLOCKED_ENVIRONMENT | Egress proxy `connect_rejected`; Pages deploy workflow succeeded for every merge | — | Check the live URL from a browser |
| CB-09 | `github-advanced-security` intermittent `CAPIError 400 model not supported` | BLOCKED_ENVIRONMENT | Failed before scanning on some 25-Sep runs; later runs (#218) passed | GitHub | None; re-runs on next push |
| CB-10 | Skills that do not load: `github-qc-before-answer` (file is `skill.md`), `deep-research-solve` (cause not yet found) | Housekeeping | Missing from the session skill list | Repo owner | Small skills gap-fill PR via `agent-skill-governance` |

Deferred until the blockers above are dispositioned: recovery of the five
historical Claude chats (each checked against certified `main`, never trusted
from the chat), and any optional local-AI work (e.g. AMD/Lemonade) —
OPTIONAL_POST_CERTIFICATION.

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
| OSA / OOS | Store audit covers 44.4% of stores, wrong period (`compliance_metrics.json`'s audited chains — DMart/Reliance Retail/More Retail/Spencer's — only partly match the universe's own chain names, and DMart's audited door count (83) exceeds DMart's universe store count (24); the audit's chain grain is not the same as the commercial universe's). The universe-side contamination this QC also found (below) is now fixed. |
| Inventory days | No stock-on-hand feed. Min-Max Inventory formula (Min/Max/Order Qty) registered as a candidate methodology, ready to wire — see `forecast_stock_inventory` in `config/data_source_registry.yml`. Still needs: stock-on-hand extract, lead time per chain/distributor, confirmed safety-stock norm |
| EBITDA Bridge (P&L waterfall) | Same gap as CM2 (`cm2.has_expense_data = false`, only template rows in `PL_Expense_Input.csv`, see FM-01) — no real Employee Cost / Sales & Marketing / Other Opex split exists for any period. Bridge chart type + Variance→Driver→Impact→Action framework registered as a candidate methodology on `cm2_pl_expense_input` in `config/data_source_registry.yml`, ready to wire onto the existing P&L tab once Finance supplies real category-level expense actuals |

## Resolved (2026-09-14, business rules confirmed + root QC)

- **Profitability / margin** — standard cost confirmed as 14% of MRP (COGS) + 3% of MRP (logistics), applied to `detail_records` (`profitability_block()` in `build_dashboard_data.py`). FY-to-date: margin 60.68% of NSV. This is a standard-cost rate, not a per-article SAP COGS extract — CM2/P&L are unaffected, they keep their own separate basis.
- **NPD tracker** — redefined as demand-based, not master-join-based: an article-chain pair is NPD for the FY after its first-ever sale at that chain, when that first sale falls in calendar March (`npd_block()`). FY27: 140 article-chain pairs flagged. No join key to `PowerBI/SeedData/NPI_Master.csv` needed any more for this definition.
- **Universe chain-wise breakdown** — root-QC'd across the whole PowerBI SeedData folder (not just `UniverseMT.csv` alone). Found `universe.by_chain` summed to 415 of 426 stores because of two real bugs, both fixed in `universe_block()`: (a) a silent `[:20]` truncation with no disclosure (now discloses any excluded tail via an "Other" bucket + note, matching the existing `by_storetype`/`storetype_note` pattern), and (b) 18 of `UniverseMT.csv`'s 36 raw "Chain Name" values were actually Primary-billing Ship-To/DC codes for distributors, not chains — confirmed against `PowerBI/SeedData/Masters/ShipToMaster.csv`'s own governed `Primary Chain`/`Chains Served` columns (e.g. "G.V Enterprises" serves Apollo, D-Mart, Lulu and Pothys; it is not its own chain). 16 of those 18 are reassigned to their distributor's governed Primary Chain — cross-validated independently against `data/monthly/Aug26_primary_detailed.csv`'s "Customer Name.1" pooled-chain hints, which list nearly the same served-chain sets. The remaining 1 ("RRL-FOC-Sample") is now also resolved: ShipToMaster.csv carries a governed "Reliance Retail Limited-FOC" entry (Direct, Primary Chain = Reliance Retail) — the same entity type — so it folds into Reliance Retail too. Result: 16 real chains, reconciling exactly to all 426 stores, no truncation needed. `universe.n_chains`/`universe.chains` are now actually produced by code (previously an orphaned field with no producing path anywhere in the repo — any full rebuild would have silently dropped them). `config/baselines.json`'s `n_chains` invariant corrected 20 → 17 → 16 with the full justification recorded there (owner: MT Ops).
- **Chain-level Primary mapping** — was reported at 67.65% (stale, from an earlier Aug'26-only raw-invoice analysis run via `aug26_data_readiness_gate.py`). Added `--mapping-health-only` build mode to recompute `mapping_health` from the current, complete `detail_records` (already spans all 5 FY27 months) instead of that one-off snapshot. Real, current completeness: **FY26 99.99%, FY27 99.95%** — independently cross-checked by hand-summing `detail_records` directly. `chain_primary` readiness gate flips BLOCKED → PASS on real, verified evidence, not a relaxed threshold. Residual unmapped: ₹0.12 Cr (FY27) / ₹0.02 Cr (FY26), 10 named ship-to parties, itemized in `mapping_health.exceptions`.
- **Chain-allocation weights pipeline was silently broken** — `load_chain_allocation_weights()` looked only for `PowerBI/SeedData/DIST/ChainAllocationWeights.csv` (doesn't exist in this repo) with no fallback to the real, already-**Approved** `DistPrimaryContWeightsArticle.csv` sitting in the same folder (5 distributors × 4 months, real Cont% splits). Now falls back to it. While tracing this, found and fixed a genuinely more serious, separate bug: `scripts/allocate_dist_enhanced.py`'s Tier-3 fallback (used when neither explicit weights nor offtake evidence exist for a Dist. row) was **fabricating** a generic "typical Modern Trade distribution" split (DMart/Reliance/"Q-Comm"/"Others" — "Q-Comm" isn't even a chain this business sells through) that also only summed to 85%, silently losing 15% of every such row's value despite the function's own "zero revenue leakage" guarantee. Replaced with the same "Unmapped Chain" (100% of value, honestly tagged, zero leakage) pattern already used elsewhere in this repo — never invent a chain split for real money. Also found and fixed, via a new regression test: Tier 1 (explicit weights) would have crashed the instant it actually matched, because `load_chain_allocation_weights()`'s documented tuple-shaped output `(chain, fraction)` was never compatible with this function's dict-shaped `split["chain"]`/`split["weight"]` reads — a real bug that had simply never fired because Tier 1 had no real weights file to match against until this same pass. New tests: `tests/test_chain_allocation_no_fabrication.py` (6 tests).

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
7. Power BI P&L (`PowerBI/SeedData/Masters/AssumptionTable.csv`) — approved
   Gross Margin %/Trade Spend %/Visibility/Scheme Spend rows for Jun/Jul/Aug'26
   (real Primary/Offtake monthly data already exists for all three; only the
   Assumption Table itself is missing them). Unrelated to the incentive
   workbook — this is the Power BI trade-P&L build kit's own gap (F21,
   `docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md`). Enforced by
   `scripts/check_assumption_coverage.py` / the "Assumption Coverage Gate"
   CI check (PR #211) — do not fabricate, interpolate, or estimate these

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
| FY27 primary (article-level) | ₹22,239.59 L (was ₹18,581.29 L before 2026-09-13 -- intentional: Aug'26 was production-ingested that day, adding ₹36.58 Cr for a 5th month, Apr-Aug now vs. Apr-Jul before. Evidence: `docs/DATA_LINEAGE.md` Aug'26 reconciliation; not a frozen invariant in `config/baselines.json`, so this is documentation catching up to an intended change, not a baseline violation) |
| Active MT stores | 426 |
| FY27 target | ₹441.33 Cr |
| PVM reconciliation | PASS, variance 0.00 |
| Dashboard sweep | 44 states, 0 NaN/undefined, 0 JS errors |
| unittest suite | 66 pass, 1 skipped |
| Baseline invariants | 7/7 hold (`config/baselines.json`) |
| Fresh clone | dashboard reproduces fully: 44 states, 0 failures, 0 JS errors |
| Incentive workbook | 51 employees / 42 VALID grades / 85 slab rows / 3,124 target rows / 67 WoA rows / 267 actual rows; payout NOT CALCULATED |
| Target file (refreshed) | Rs 33,986.08 L; 77.0% of business target; gap 76% explained |
| Actual attribution | Rs 14,118.82 L Apr-Jul; all 4 role lines reconcile, difference 0 |

| pytest suite | 105 pass, 1 skipped |

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
