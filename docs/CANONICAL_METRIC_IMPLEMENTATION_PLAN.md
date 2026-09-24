# Canonical Metric Implementation Plan

**Status:** DESIGN ONLY. This document plans the implementation; it does not perform any of it. No file listed as "expected to change" below has been touched by this document or this branch.
**Depends on:** `docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md` (Design Acceptance Gate: `DESIGN READY FOR REVIEW`, all 14 items resolved, ADR-001 through ADR-008 approved) and `docs/CANONICAL_METRIC_DEPENDENCY_MAP.md`.
**Governs:** the sequence, scope, and gates for every future PR that actually builds the canonical layer. No phase below may be combined with another phase in a single PR — each is independently gated, reviewed, and reconciled before the next begins.

## How to read each phase

Every phase specifies exactly: scope, source, affected metrics, dependencies (what must already be true/merged), regression tests, reconciliation tests, rollback plan, acceptance gate, files expected to change, and files explicitly forbidden from changing in that phase. A phase PR that touches a forbidden file is out of scope for that PR, full stop — it becomes a later phase's work or a separate PR, never smuggled in.

---

## Phase 0 — Certified baseline protection

**Scope:** No code change. Establishes the rollback anchor every later phase measures against.
**Source:** `main` @ `ca67f67173dd9c1d71ae715b3abf47a2e072ed63` (per `docs/POST_MERGE_CERTIFICATION_PR193.md`) plus this design's own merge commit once PR #197 lands.
**Affected metrics:** All — this is the reference point every canonical metric is reconciled against.
**Dependencies:** PR #193, PR #196 merged (done). PR #197 (this design) reviewed and merged.
**Regression tests:** N/A (no code).
**Reconciliation tests:** N/A (no code) — this phase's only output is the recorded baseline SHA every later phase's reconciliation compares against.
**Rollback plan:** N/A — nothing to roll back.
**Acceptance gate:** PR #197 merged; the merge commit SHA recorded here (in a follow-up edit to this doc, or in Phase 1's PR description) as "the baseline every canonical output is reconciled against."
**Files expected to change:** None.
**Files explicitly forbidden from changing:** Everything — this phase is a checkpoint, not a code change.

---

## Phase 1 — Canonical metric engine

**Scope:** Build the pure calculation layer only. No dashboard integration, no change to `dashboard/data.js`'s schema, no change to what any current view reads. The engine exists, is tested, and is not yet consumed by anything.
**Source:** New Python package, e.g. `scripts/canonical/` (`metrics.py`, `primary.py`, `offtake.py`, `fiscal.py`, `units.py`, `policies.py` — names illustrative, exact module boundaries are an implementation-PR decision, not fixed here). `fiscal.py` should wrap THE ONE FY RULE's existing `_fylabel()`/`fy_tag_from_label()` functions rather than reimplementing FY derivation a second time.
**Affected metrics:** All 9 (`PRIMARY_NSV`, `OFFTAKE_NSV`, `CHANNEL_PRIMARY_NSV`, `CHAIN_OFFTAKE_NSV`, `CATEGORY_OFFTAKE_NSV` [stub returning `NOT_AVAILABLE`], `STORE_OFFTAKE_NSV` [stub returning `NOT_AVAILABLE`], `RBC_PRIMARY_NSV`, `RBC_OFFTAKE_NSV`, `RBC_GAP_NSV`) — the engine implements the contract for each, including the two that resolve to "not available" by design, not by omission.
**Dependencies:** Phase 0 complete.
**Regression tests:** New unit tests for every policy in the ADR register: ADR-001 (no cross-FY fallback — a request for an absent FY returns `NOT_AVAILABLE`, never another FY's value or an all-period aggregate), ADR-007 (missing data never silently becomes 0), ADR-003 rules 1-6 (Primary/Offtake never substitute for each other; Gap requires both operands).
**Reconciliation tests:** None yet at this phase — the engine has no consumer to reconcile against. (Reconciliation begins in Phase 2.)
**Rollback plan:** Delete the new package; nothing else in the repo references it yet, so rollback is a pure revert with zero blast radius.
**Acceptance gate:** 100% of the ADR-001/003/007 policy unit tests pass; `py_compile` clean; the engine is provably unused by `dashboard/index.html` or the existing `scripts/build_dashboard_data.py` build path (a grep-based check, mirroring this design's own dependency-mapping method).
**Files expected to change:** New files only, under `scripts/canonical/` (or equivalent), plus new files under `tests/canonical/` (or equivalent).
**Files explicitly forbidden from changing:** `dashboard/index.html`, `dashboard/data.js`, `scripts/build_dashboard_data.py`, any existing file under `tests/` (existing tests must stay green, untouched, throughout this phase), `config/`, `PowerBI/`.

---

## Phase 2 — Reconciliation framework

**Scope:** Build the "old output vs. canonical output" comparison harness itself — not any specific reconciliation yet, the reusable framework every later phase's reconciliation test is built on.
**Source:** New test/tooling module, e.g. `scripts/canonical/reconcile.py` + `tests/canonical/test_reconciliation_framework.py`. Should generalize the pattern already proven in `tests/test_pr193_reconciliation.py` (load real `data.js`, compute an independent aggregate, assert variance within a stated tolerance) into a reusable comparator: given a metric ID, an "old" value/source and a "canonical" value/source, assert equality within that metric's contract-defined tolerance, and produce a structured PASS/FAIL/variance report (mirroring `docs/PR_193_PRODUCTION_CERTIFICATION.md`'s table format, so every later phase's reconciliation report reads consistently).
**Affected metrics:** None directly — this is tooling, not a metric.
**Dependencies:** Phase 1 merged.
**Regression tests:** Tests for the framework itself (does it correctly flag a variance beyond tolerance, does it correctly pass an exact match, does it correctly report "old" as unavailable when the old code path itself had no value).
**Reconciliation tests:** N/A — the framework is what later phases' reconciliation tests are built with, not itself reconciled against anything.
**Rollback plan:** Delete the new module; still unused by production code, zero blast radius.
**Acceptance gate:** Framework unit tests pass; a dry run against `PRIMARY_NSV`'s two known current sources (`primary.by_channel` vs. `detail_records`, per the Current State section of the design doc) produces a correctly-formatted report showing the two DO agree post-PR-193 (Control 1's 0.00 L variance) — proving the framework reproduces a result this repo has already manually certified once, before it's trusted to certify anything new.
**Files expected to change:** New files only, under `scripts/canonical/` and `tests/canonical/`.
**Files explicitly forbidden from changing:** Same list as Phase 1, plus the new Phase 1 files (append to them only if genuinely part of the reconciliation framework, not scope creep back into metric logic).

---

## Phase 3 — Offtake canonicalization

**Scope:** Point the canonical engine's `OFFTAKE_NSV` and `CHAIN_OFFTAKE_NSV` implementations at real data, and — critically — **this is where `KI-OFFTAKE-001` (Issue #195) closes**, per ADR-001/ADR-002. Still no dashboard change; the canonical engine now produces real, reconciled offtake numbers, but nothing reads them yet except this phase's own reconciliation tests.
**Source:** `scripts/build_dashboard_data.py`'s existing offtake loaders (`load_offtake()`, `load_offtake_article_files()`) feed the canonical engine's fact layer — implementation-phase decision on whether these loaders are reused as-is or the fact layer wraps them, not decided here. **Implementation target, per ADR-001/002 (do not implement before Phase 3 — recorded here only as the target):**
```
CHAIN_OFFTAKE_NSV(fy, chain) =
    SUM(canonical_offtake_fact.nsv)
    WHERE canonical_offtake_fact.fy = fy AND canonical_offtake_fact.chain = chain

Never: offtake.by_chain[chain].value (an all-months-combined field with
no FY subscript, per the design doc's root-cause trace of
offtake_rebuild_block()'s dim_rows()).
Never: substitute another FY's <fy>-keyed value.
If no canonical_offtake_fact rows exist for (fy, chain): return NOT_AVAILABLE.
```
**Affected metrics:** `OFFTAKE_NSV`, `CHAIN_OFFTAKE_NSV`.
**Dependencies:** Phase 2 merged (reconciliation framework exists to prove this phase's output against the current data.js's `offtake.total_<fy>`/`by_chain` fields).
**Regression tests:** Unit tests proving no cross-FY fallback occurs for the 4 chains currently affected by `KI-OFFTAKE-001` (e.g. Vijetha) — asserting `CHAIN_OFFTAKE_NSV('fy27', 'Vijetha')` returns `NOT_AVAILABLE`, not a stale FY26 figure.
**Reconciliation tests:** Using Phase 2's framework: `OFFTAKE_NSV(fy)` vs. `offtake.total_<fy>` (expect exact match, per the 0.00 L variance already proven in `docs/PR_193_PRODUCTION_CERTIFICATION.md` Control 4) for every chain/FY combination that has real data; explicit documentation (not silent passing) of every chain/FY combination where the canonical engine now correctly returns `NOT_AVAILABLE` where the old `by_chain[].value` fallback used to silently return a number — this list IS `KI-OFFTAKE-001`'s closure evidence.
**Rollback plan:** The canonical engine is still not wired into any dashboard view at this phase — rollback is deleting/reverting the new fact-layer code, zero UI blast radius. Issue #195 would need to stay open if this phase is rolled back.
**Acceptance gate:** All chain/FY combinations reconcile within tolerance where the old system had real data; every combination where the old system's `.value` fallback fired is now explicitly listed as `NOT_AVAILABLE`, not silently matched to the old (wrong) figure; Issue #195 closes referencing this phase's reconciliation report.
**Files expected to change:** `scripts/canonical/offtake.py` (or equivalent) and its tests. Issue #195 closed via commit/PR reference, not code.
**Files explicitly forbidden from changing:** `dashboard/index.html` (the `KI-OFFTAKE-001` UI symptom — the "Top Chains by Offtake" table — is not touched until Phase 6), `dashboard/data.js`, `scripts/build_dashboard_data.py`'s existing `offtake_block()`/`offtake_rebuild_block()`/`patch_offtake_new_months()` (they keep producing today's fields for today's dashboard until Phase 6 migrates the consumer; this phase adds a parallel canonical path, it does not yet retire the old one).

---

## Phase 4 — Primary canonicalization

**Scope:** Point the canonical engine's `PRIMARY_NSV`, `CHANNEL_PRIMARY_NSV`, `RBC_PRIMARY_NSV` implementations at real data. Same "parallel path, nothing retired yet" discipline as Phase 3.
**Source:** `detail_records_real()` (article-wise, already confirmed the authoritative source for `CHANNEL_PRIMARY_NSV` per PR #193) becomes the canonical engine's Primary fact source; the pre-agg `Primary_FY202426_10.csv` path is either reduced to a pure cross-check or retired — that decision is this phase's own design sub-task, not pre-decided here (ADR-002's discipline extended: one canonical source, not two hoping to agree).
**Affected metrics:** `PRIMARY_NSV`, `CHANNEL_PRIMARY_NSV`, `RBC_PRIMARY_NSV`.
**Dependencies:** Phase 2 merged.
**Regression tests:** Unit tests for the same ADR-001/007 policies, applied to Primary this time.
**Reconciliation tests:** `CHANNEL_PRIMARY_NSV` vs. the already-certified ₹32,900.36 L FY26 baseline (0.00 L variance, per PR #193); `RBC_PRIMARY_NSV` vs. the already-certified ₹137.03 Cr Reliance figure (0.00 L variance, per PR #193's Reliance Control) — both are re-proving already-certified numbers through the new engine, not new business findings.
**Rollback plan:** Same as Phase 3 — no dashboard consumer yet, zero UI blast radius.
**Acceptance gate:** Both reconciliations pass at 0.00 L variance against the already-certified PR #193 figures.
**Files expected to change:** `scripts/canonical/primary.py` (or equivalent) and its tests.
**Files explicitly forbidden from changing:** Same as Phase 3's forbidden list, Primary-side equivalents (`primary_block()`, `apply_primary_channel_correction()` keep running for today's dashboard until Phase 5/6 migrate their consumers).

---

## Phase 5 — Executive Cockpit migration

**Scope:** The first dashboard-visible change. Migrate `buildExecutiveCockpit()` (per `docs/CANONICAL_METRIC_DEPENDENCY_MAP.md`'s consumer list) to read `CHANNEL_PRIMARY_NSV`/`PRIMARY_NSV` from the canonical engine instead of `primary.by_channel` directly.
**Source:** `dashboard/index.html`'s `buildExecutiveCockpit()`.
**Affected metrics:** `PRIMARY_NSV`, `CHANNEL_PRIMARY_NSV` (Executive Cockpit's specific consumption of them).
**Dependencies:** Phase 4 merged and reconciled.
**Regression tests:** The existing 44-state Playwright sweep (`tests/dashboard_sweep.js`) must stay green — this phase must not introduce a new crash/NaN/undefined state.
**Reconciliation tests:** Old-`buildExecutiveCockpit()`-output vs. canonical-engine-output, screenshotted or DOM-diffed before/after, using Phase 2's framework — block the PR on any unexplained variance, per this repo's own established discipline (matches PR #193's own screenshot-based before/after proof).
**Rollback plan:** Revert `buildExecutiveCockpit()`'s data source back to direct `primary.by_channel` reads — the canonical engine underneath is untouched and still correct, so rollback is a one-function revert, not a data rebuild.
**Acceptance gate:** 44-state sweep green; Executive Cockpit's displayed numbers are pixel/value-identical to the pre-migration baseline (or, if different, the difference is a *documented fix* like PR #193's, not an unexplained drift).
**Files expected to change:** `dashboard/index.html` (only `buildExecutiveCockpit()` and its direct call chain).
**Files explicitly forbidden from changing:** Every other `build*()` function in `dashboard/index.html`; `dashboard/data.js`'s schema (the canonical engine can be exposed to the browser via a new field alongside the old ones, or via a build-time injection — an implementation-PR decision, not fixed here — but existing fields must not be removed while other views still read them).

---

## Phase 6 — Comparison / Inventory / Alerts migration

**Scope:** Migrate the remaining Primary-side consumers (`buildComparison()`, `buildChannelDynamics()`, `renderChannelSubview()`'s Category & Pack Mix sub-view) and the Offtake-side consumers (`buildInventoryHealth()` — both the already-fixed KPI and the `KI-OFFTAKE-001` "Top Chains" table, which finally gets its UI-visible fix here, consuming Phase 3's canonical `CHAIN_OFFTAKE_NSV`), plus Operational Alerts if it independently recomputes any of these metrics (per the dependency map's noted gap — Operational Alerts' own alert-generation source was flagged in this session's earlier audit as a freshness question, not yet fully traced to a specific metric consumer; this phase's own dependency check should close that gap before migrating it).
**Source:** `dashboard/index.html`'s `buildComparison()`, `buildChannelDynamics()`, `renderChannelSubview()`, `buildInventoryHealth()`, and `buildAlerts()`/`AlertController` if applicable.
**Affected metrics:** `PRIMARY_NSV`, `CHANNEL_PRIMARY_NSV`, `CATEGORY_OFFTAKE_NSV` (still `NOT_AVAILABLE` — this phase does not invent a source), `OFFTAKE_NSV`, `CHAIN_OFFTAKE_NSV`.
**Dependencies:** Phase 5 merged (proves the migration pattern once before repeating it across more views).
**Regression tests:** 44-state sweep green.
**Reconciliation tests:** Same before/after discipline as Phase 5, per view. `CHAIN_OFFTAKE_NSV`'s migration specifically must show the "Top Chains by Offtake" table now rendering `–` for the chains `KI-OFFTAKE-001` affected, with a reconciliation report closing the loop from Phase 3's non-UI proof to this phase's UI-visible fix.
**Rollback plan:** Per-view revert, same pattern as Phase 5 — each view's migration is independently revertible without touching the canonical engine or any other view.
**Acceptance gate:** 44-state sweep green; every migrated view's reconciliation report shows either an exact match to pre-migration output or a documented, explained difference (never a silent one); `KI-OFFTAKE-001`/Issue #195 UI symptom confirmed fixed by screenshot, mirroring PR #193's own evidence standard.
**Files expected to change:** `dashboard/index.html` (the specific functions named above only).
**Files explicitly forbidden from changing:** Any `build*()` function not in this phase's named list; the canonical engine's own logic (Phases 1-4's files) — this phase consumes them, it does not modify them.

---

## Phase 7 — Reliance Brand Counter migration

**Scope:** Build the actual three-part "Primary + Offtake + Gap" Reliance Brand Counter view per ADR-003, replacing the current single-Primary-only `reliance` sub-view.
**Source:** `dashboard/index.html`'s `renderChannelSubview()`'s `reliance` branch, extended (or replaced) to render `RBC_PRIMARY_NSV`, `RBC_OFFTAKE_NSV`, and `RBC_GAP_NSV` as three distinct, clearly-labelled figures — never blended per ADR-003 rule 1.
**Affected metrics:** `RBC_PRIMARY_NSV`, `RBC_OFFTAKE_NSV`, `RBC_GAP_NSV`.
**Dependencies:** Phase 4 merged (both operand measures certified); Phase 6 merged (establishes the migration pattern for this tab's sibling sub-views under Channel & Chain Performance).
**Regression tests:** 44-state sweep green (the sweep's state count may need to grow if this becomes a new distinguishable state — an implementation-PR detail).
**Reconciliation tests:** `RBC_PRIMARY_NSV` vs. the pre-migration tab's output (should match exactly — this is the same data the tab already showed, just correctly labelled); `RBC_OFFTAKE_NSV` and `RBC_GAP_NSV` are new to the UI, so their "reconciliation" is against the canonical engine's own Phase 3/4 certified values, not against a prior UI state that didn't exist.
**Rollback plan:** Revert to the pre-Phase-7 single-Primary view — `RBC_PRIMARY_NSV`'s data is unaffected either way, so rollback loses only the newly-added Offtake/Gap visibility, not correctness of what remains.
**Acceptance gate:** All three measures render with correct, distinct labels; `RBC_SELL_THROUGH_PCT` is confirmed absent/disabled per ADR-003 rule 6 (a specific negative-assertion test: the UI must not compute or display a sell-through ratio at this phase).
**Files expected to change:** `dashboard/index.html` (`renderChannelSubview()`'s `reliance` branch and any new supporting card/chart functions it calls).
**Files explicitly forbidden from changing:** Everything outside that sub-view; `scripts/build_dashboard_data.py`'s `load_reliance_bc_data()` and `validate_offtake_partition()` (reused as-is, per ADR-003's sourcing — not modified by a UI migration phase).

---

## Phase 8 — PBIP / Power BI semantic model

**Scope:** Mirror the certified canonical metrics into the Power BI build kit (`PowerBI/`) as reusable DAX measures, so the dashboard and Power BI stop being two independently-maintained calculation surfaces.
**Source:** `PowerBI/DAX/`, `PowerBI/PowerQuery/`, per this repo's existing Power BI build-kit structure (see `PowerBI/docs/PageLayouts.md` for the existing web-dashboard-to-PowerBI mapping convention this phase extends).
**Affected metrics:** All 9, exposed as named DAX measures (`[Primary NSV]`, `[Offtake NSV]`, `[RBC Primary NSV]`, etc., per each contract's "Future semantic-model measure" field).
**Dependencies:** Phases 1-7 merged and reconciled — the canonical engine's Python implementation is the reference every DAX measure is checked against, not the other way around.
**Regression tests:** This repo's existing Power BI validation tooling (`PowerBI/QuickSetup/`, DAX validation scripts referenced in CLAUDE.md's CI check list — "Run Headless Tabular Editor & DAX Validation").
**Reconciliation tests:** Each DAX measure's output vs. the Python canonical engine's output, for a shared reference period — the two must agree within each metric's stated tolerance, or the phase is not complete.
**Rollback plan:** Power BI measures are additive to the existing build kit; a bad measure can be reverted independently of both the dashboard and the Python engine.
**Acceptance gate:** Every DAX measure reconciles against its Python canonical counterpart; existing Power BI CI checks stay green.
**Files expected to change:** `PowerBI/DAX/*`, `PowerBI/docs/*` (documentation of the new measures).
**Files explicitly forbidden from changing:** `dashboard/index.html`, `dashboard/data.js`, the Python canonical engine (this phase consumes its certified output as the reference, it does not modify it).

---

## Phase 9 — AI Insight Agent

**Scope:** An agent that explains certified canonical metrics in natural language (e.g. "Reliance Offtake declined 8.2% because Face Wash declined in X states") — it reads `RBC_OFFTAKE_NSV`/`RBC_PRIMARY_NSV`/`RBC_GAP_NSV` (and the other certified measures) as inputs. It never independently computes a metric value; every number in its output must be traceable to a canonical-engine call, never a re-derivation.
**Source:** New, TBD at this phase — not designed here.
**Affected metrics:** Consumes all; computes none.
**Dependencies:** Phases 1-8 merged, certified, and in production use for at least one full reporting cycle (an implementation-phase decision on exact duration, not fixed here) — this phase should not start against a canonical layer that hasn't yet proven stable in real leadership use.
**Regression tests:** TBD at implementation time.
**Reconciliation tests:** Every numeric claim the agent makes must be checked against the canonical engine's own value for that metric/period — an automated "does this sentence's number match a real canonical query result" check, not a manual spot-check.
**Rollback plan:** TBD.
**Acceptance gate:** TBD — not designed in this document. Named here only to keep this phase explicitly downstream and explicitly out of scope for every phase before it, per this repo's standing "no AI-generated financial truth" principle.
**Files expected to change:** TBD.
**Files explicitly forbidden from changing:** The canonical engine's calculation logic (Phases 1-4) — the agent is a consumer, never a second source of truth.

---

## Cross-phase invariants (apply to every phase above, not restated per-phase)

- No phase merges without its own reconciliation report, in the format established by `docs/PR_193_PRODUCTION_CERTIFICATION.md` (source, expected, actual, variance, tolerance, PASS/FAIL).
- No phase touches a file outside its own "expected to change" list — verified via `git diff --stat` against the prior phase's merge SHA, exactly as this design phase verified itself.
- No phase skips ahead (e.g. Phase 6 cannot start before Phase 3-4 are merged and reconciled) — each phase's Dependencies row is a hard gate, not a suggestion.
- Every phase that touches `dashboard/index.html` must keep the 44-state Playwright sweep (`tests/dashboard_sweep.js`) green, per this repo's existing "Validation before committing dashboard changes" rule in `CLAUDE.md`.
- `KI-OFFTAKE-001` (Issue #195) closes at the end of Phase 3 (engine-level fix, reconciliation-proven) but its UI-visible confirmation is Phase 6's acceptance gate — the issue should not be closed until both are done, to avoid declaring victory on a fix nobody can see yet.
