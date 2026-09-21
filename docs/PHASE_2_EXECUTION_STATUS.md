# Phase 2 Execution Status — Same-Store Growth (SSG)

**PHASE 2B = COMPLETE**
**STATUS = READY_FOR_SOURCE_INGESTION**
**DEPENDENCY = FY26 Apr'25-Mar'26 Store × Article Offtake**
**NEXT PHASE = PHASE 2C — CONTROLLED HISTORICAL INGESTION** (see §"Phase 2C" below)

This tracks execution status only. The underlying feasibility analysis lives
in `docs/PHASE2_SSG_FEASIBILITY.md` (completed 2026-09-20, read-only, not
re-run from zero here) — this document does not repeat that evidence, it
picks up from its conclusion.

## Objective

Add a governed Same-Store Growth measure (store-level YoY, isolating
existing-store growth from new-store/expansion contribution) as the natural
next step after PR #167's Account/Chain YoY Intelligence — same governance
philosophy (comparability flags, never treating missing data as zero), one
grain lower (store, not chain).

## Previously Completed

- Full read-only inventory of every real store-level source file in this
  repo (`docs/PHASE2_SSG_FEASIBILITY.md` §1-2): confirmed `(Chain Name, Site
  Code)` is a usable, reasonably stable compound cohort key — 87.9%
  month-over-month persistence across the 5 real FY27 months that exist,
  97.0% store-name agreement on matched codes.
- Identified the actual blocker precisely (§3): zero FY26-or-earlier
  store×article extracts exist anywhere in this repository — a completeness
  gap, not a data-quality problem.
- Answered all 10 required inventory questions with direct evidence (§4).
- Classified: **`READY_WITH_GAPS`**.
- Designed (not implemented) the full governance rule set for when the
  gap closes: canonical cohort key, comparable-store definition, minimum
  history requirement, opening/closed-store rules, missing-month rule,
  zero-sales rule, chain-transfer rule, duplicate-store rule,
  returns/negative-sales rule (§6) — each one explicitly modeled on a
  precedent already shipped in PR #167 (`comparability` flag,
  `TestNegativeValues`), not invented fresh.
- **Since the above:** built and tested the actual readiness-gate
  infrastructure (commit `0cd8126`) so it's ready to run the moment a
  FY26 file exists, rather than being designed only on paper:
  - `docs/PHASE_2_DATA_CONTRACT.md` — exact field-level request, plus an
    audit of what the real FY27 files contain today.
  - `docs/STORE_IDENTITY_GOVERNANCE.md` — the crosswalk schema and
    match-method cascade, formalizing §6 above.
  - `docs/PHASE_2_DATA_READINESS_GATE.md` — the validator's check list,
    verdict logic, and the folder-structure decision (reuses
    `PowerBI/RawDataFolders/`, not a new parallel `data/` tree).
  - `scripts/store_history_readiness.py` — `validate_store_history()`
    (11 checks) and `build_crosswalk_candidates()` (never auto-confirms
    below `HIGH` confidence).
  - `scripts/test_store_history_readiness.py` — 23 tests against
    synthetic fixtures; caught and fixed one real ordering bug in the
    crosswalk builder during development (see commit message).
  - Confirmed the release condition works against this repo's real
    current state: running the validator with no FY26 file present
    reports `BLOCKED_BY_SOURCE_DATA`, exit 1, exactly as designed.

## Remaining

1. Obtain the exact missing input named in the feasibility doc: a real FY26
   (Apr'25–Mar'26) store×article offtake extract, in the same shape as
   `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_*.csv`.
   **This is now the only step blocking everything else** — run
   `python scripts/store_history_readiness.py --src <file> --fy27-reference
   <a FY27 file>` against it the moment it arrives.
2. Once supplied: register it in `config/data_source_registry.yml` (per
   `CLAUDE.md`'s "New data source checklist" — grain, date column, FY
   mapping, effective-dating, coverage, duplicate risk, downstream KPI,
   validation, unattended-refresh behavior — all 10 items, before it feeds
   any calculation).
3. The two open sub-questions the feasibility doc flagged as untested
   (whether a zero-sales store gets a real row or no row at all; whether
   any `(Chain, Site Code)` pair repeats within a single month) are now
   answered automatically by the readiness gate's `missing_as_zero_treatment`
   and `duplicate_grain` checks the moment real data runs through it —
   no separate manual step needed.
4. Build the store-level `same_period_block()`-equivalent (one grain below
   chain), reusing its exact shared-months and comparability-flag pattern
   rather than a new implementation.
5. Wire it into a UI location — not yet decided; natural candidates are a
   new sub-view under Channel & Chain Performance's Primary Sales, or a new
   card under the existing Account & Zone Scorecard, following PR #167's
   precedent of extending rather than adding a new top-level tab.
6. Register the new measure in `docs/METRIC_REGISTRY.md`.
7. Full validation cycle (py_compile, full pytest suite, `ci_validate_datajs.py`,
   E2E suite, `dashboard_sweep.js`, mutation guard) before any PR.

## Dependencies

- **Hard dependency, blocking everything below it:** the FY26 store×article
  file (item 1 above). Nothing else in this list can start meaningfully
  without it — building the cohort logic against only FY27 data would
  produce an intra-FY27 view, not the requested YoY measure, and risks
  being mistaken for the real thing if built prematurely.
- PR #167 merging first is not a hard technical dependency (Phase 2 would
  touch different code paths — a new store-level function, not
  `same_period_block()`'s existing chain/zone/brand dims) — but doing so
  keeps one governed baseline active at a time, per this session's own
  stated principle in the certification work.

## Governed Blockers

Same as `docs/POST_RESTART_VALIDATION_REPORT.md`'s `GB-01`/`GB-02`
(pre-existing, unrelated to Phase 2) plus:

- **`GB-03`:** No FY26-or-earlier store×article source file exists in this
  repository. Owner: whoever supplies the monthly
  `offtake_store_article_*.csv` drops today (per
  `config/data_source_registry.yml`'s existing ownership for this source
  family). Business impact: Same-Store Growth cannot be computed until
  resolved — no workaround, no proxy, no estimate, per this repo's "no
  dummy data" rule. Next action: request the file; nothing else in this
  document can proceed past step 1 without it.

## KPI / Business Logic Impact

None yet — no code has been written for Phase 2. Once built, the new
Same-Store Growth measure would sit alongside (not replace) PR #167's
existing chain/zone/brand YoY, following the same "never silently read
missing data as zero" rule already established there.

## Expected File Changes (once the blocker clears)

- `config/data_source_registry.yml` — register the new FY26 source.
- `scripts/build_dashboard_data.py` — new store-level cohort function.
- `dashboard/index.html` — new UI surface (location TBD, see Remaining §5).
- `docs/METRIC_REGISTRY.md` — new measure row.
- `scripts/test_*.py` (new file) — edge-case tests, following
  `scripts/test_account_yoy_edge_cases.py`'s pattern.
- `dashboard/data.js` — regenerated (only after all of the above land, and
  only via `--offtake-patch` or equivalent, never hand-edited).

## Required Validation

Identical checklist to this session's post-restart pass: `py_compile`, full
`pytest scripts/ tests/` suite, `ci_validate_datajs.py`, the real E2E suite
(`tests/e2e_v1.1.0_consolidation.spec.js`), `dashboard_sweep.js`, and the
mutation guard — plus new edge-case tests specific to store-level rules
(opening-store, closed-store, duplicate-store, zero-sales-vs-missing-row).

## Required Approval

Business/Finance sign-off is not obviously required for the mechanism
itself (it's a read-only analytical view, like PR #167), but the **exact
comparable-store definition** (minimum history window, how a mid-period
store closure is treated, whether a store that changes chain ownership
keeps its history) should be confirmed with MT Leadership before shipping,
the same way PR #163's Chain×EAN launch-grain change was surfaced and
approved before implementation — this is exactly the kind of methodology
choice that changes a reported number, not just a technical detail.

## Recommended Next Implementation Unit

**Not a code change.** The single smallest safe next action is: **request
the FY26 (Apr'25–Mar'26) store×article offtake extract** from whoever
supplies the monthly `Offtake_Monthly/offtake_store_article_*.csv` drops.
The readiness gate itself (`scripts/store_history_readiness.py`, tested)
is already built and waiting — the cohort-calculation engine and its UI are
the only pieces still to write, and starting either before the file exists
would mean building against data that cannot answer the actual question
asked (a genuine FY27-vs-FY26 comparison).

## Phase 2B closeout (this pass)

Extended the readiness gate from a design-plus-basic-validator into the
actual intake mechanism, per `docs/PHASE_2_SOURCE_INTAKE_CHECKLIST.md`
(new this pass):

- Standardized exit codes: `0`=READY, `2`=READY_WITH_GOVERNED_EXCEPTIONS,
  `3`=BLOCKED_BY_SOURCE_DATA, `4`=BLOCKED_BY_DATA_QUALITY.
- `READY_FOR_SOURCE_INGESTION` printed alongside `BLOCKED_BY_SOURCE_DATA`
  when no file is supplied — two complementary signals, not a contradiction.
- QC JSON artifact (default `docs/phase2_qc/store_history_readiness_report.json`)
  now carries full provenance: `run_id`, `generated_at_utc`, `git_commit`,
  `validator_version`, `detected_grain`, source filename/checksum/row
  count, canonical date range, every check result, and — when a FY27
  reference is supplied — crosswalk/cohort/match-method counts.
- **Determinism verified directly, not assumed:** ran the validator twice
  against the identical file; `run_id` and `generated_at_utc` differed as
  expected, `git_commit` matched, and every other field in the QC artifact
  was byte-identical.
- Crosswalk builder now covers the **union** of FY26 and FY27 store
  universes (not just FY26 looking forward) — a FY27-only store now
  correctly gets a `NEW_STORE` row instead of being invisible; added
  `Cohort_Status` (`COMPARABLE_STORE` / `NEW_STORE` / `UNMATCHED_STORE` /
  `BLOCKED_FOR_REVIEW`) to every crosswalk row, enforced in code so a
  low-confidence match can never reach `COMPARABLE_STORE` on its own.
  `CLOSED_OR_LOST_STORE` and `DATA_INCOMPLETE` are named in
  `docs/STORE_IDENTITY_GOVERNANCE.md`'s taxonomy but not yet
  mechanically distinguished from `UNMATCHED_STORE` — see the open note
  below.
- 9 new test scenarios added (duplicate store ID, chain migration never
  auto-matched across the chain boundary, ambiguous name-only match stays
  `BLOCKED_FOR_REVIEW`, new/comparable cohort classification, cohort and
  match-method count tallies, checksum determinism) — 32 tests total, all
  synthetic (still no real FY26 data exists).
- Found and fixed a real usability gap while smoke-testing end-to-end
  against real (renamed) FY27 data: `--fy27-reference` raised an
  unhandled `KeyError` traceback if passed a file still using raw source
  column names (`Chain Name` instead of the contract's `Chain`) — now
  fails with a clear `BLOCKED_BY_DATA_QUALITY` message pointing at the
  intake checklist's rename step, instead of a stack trace.

**Open design note carried into Phase 2C, not implemented now:** a
reviewer flagged that collapsing "how confident is this identity match"
and "did the chain relationship change in a way that could distort
chain-level SSG" into one `Cohort_Status` field risks treating a genuine
chain migration/acquisition the same as a harmless chain-name
standardization. The suggested fix — separate `Identity_Status` and
`Chain_Continuity_Status` fields alongside `Cohort_Status` — is sound and
should be designed into the crosswalk schema before Phase 2C runs against
real FY26 data, but wasn't added this pass since no real chain-migration
case exists yet to design the distinction against without guessing. Track
it as a Phase 2C task, not a Phase 2B gap.

## Phase 2C — Controlled FY26 Historical Data Ingestion & Identity Certification

**Entry condition:** an approved FY26 source file exists in the governed
raw landing location (`PowerBI/RawDataFolders/Offtake_Monthly/`).

**Objective:** certify the actual historical data is trustworthy enough to
enter the analytical system — this is explicitly NOT "build the SSG
engine." Sequence: source → checksum → contract validation → data
quality → store identity → chain continuity → financial reconciliation →
cohort certification. Only a certified cohort may feed a future SSG engine
(Phase 2D, not yet scoped).

Until the entry condition is met, no further code should be written here —
per this session's own instruction, the next real project event is the
FY26 file arriving, not another engineering pass.
