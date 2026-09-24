# Canonical Engine — Phase 1 Report

**Status:** Phase 1 of `docs/CANONICAL_METRIC_IMPLEMENTATION_PLAN.md` (Canonical metric engine + reconciliation framework). No dashboard UI, `dashboard/data.js` schema, or existing `scripts/build_dashboard_data.py` logic changed — the engine runs in shadow mode only, alongside today's production dashboard, consumed by nothing yet.
**Depends on:** `main` @ `1b75257c35cd5eab47ffc34bfb5ae53755ae318d` (PR #197's merge — the canonical financial-truth architecture contract).
**Branch:** `architecture/canonical-metric-engine`

---

## Architecture implemented

```
dashboard/data.js (certified baseline)
        │
        ▼
canonical.facts        -- fact accessors: primary_fact_rows(), offtake_chain_fy_values(),
                           channel_totals_for_fy(), reliance_bc_fy_total(). Deliberately
                           strips offtake.by_chain[]'s 'value'/'total' fields at this layer
                           (see KI-OFFTAKE-001 below) so no metric function above it can
                           reach them even by accident.
        │
        ▼
canonical.fiscal        -- normalize_fy()/data_key(), wrapping build_dashboard_data.py's
                           existing THE ONE FY RULE helpers (fy_tag_from_label, etc.) rather
                           than reimplementing FY derivation.
canonical.units          -- INR Lakh canonical storage, Crore conversion presentation-only
                           (ADR-006).
canonical.policies       -- NotAvailable sentinel + exact_fy_or_not_available(), the single
                           choke point every FY-keyed metric routes through (ADR-001,
                           ADR-007).
        │
        ▼
canonical.primary        -- primary_nsv(), channel_primary_nsv(), channel_primary_nsv_all_channels(),
                           rbc_primary_nsv(), rbc_primary_nsv_by_zone()
canonical.offtake         -- offtake_nsv(), chain_offtake_nsv(), chain_offtake_nsv_all_chains(),
                           rbc_offtake_nsv()
        │
        ▼
canonical.existing        -- replicates the CURRENT production JS expressions in Python
                           (Executive Cockpit's channel donut, the Total Offtake KPI, the
                           Top Chains table's exact fallback chain, the Reliance tab), so
                           "existing" and "canonical" can be compared on the same data
                           without executing JS.
        │
        ▼
canonical.reconcile        -- ReconciliationRow, reconcile_one(), summarize(): the shadow
                           comparison framework. Every unexplained variance is FAIL; a
                           named, reasoned exception is GOVERNED, never a silent PASS.
        │
        ▼
canonical.shadow_report     -- runs the full existing-vs-canonical comparison across all
                           6 metrics and both certified FYs, produces the table below.
```

No `canonical_data.js` or second pre-aggregated blob was created — per the design doc's explicit warning against that pattern. The engine reads `dashboard/data.js`'s own fact-grain fields (`detail_records`, `offtake.by_chain`, `detail_meta.channel_totals`) directly and computes each metric on demand; nothing is pre-computed and stored a second time.

## Files added

```
scripts/canonical/__init__.py
scripts/canonical/fiscal.py
scripts/canonical/units.py
scripts/canonical/policies.py
scripts/canonical/facts.py
scripts/canonical/primary.py
scripts/canonical/offtake.py
scripts/canonical/existing.py
scripts/canonical/reconcile.py
scripts/canonical/shadow_report.py

tests/canonical/__init__.py
tests/canonical/conftest.py
tests/canonical/test_fiscal.py
tests/canonical/test_units.py
tests/canonical/test_policies.py
tests/canonical/test_primary_metrics.py
tests/canonical/test_offtake_metrics.py
tests/canonical/test_reliance_metrics.py
tests/canonical/test_publication_boundary.py
tests/canonical/test_shadow_reconciliation.py
```

**Files changed:** none. Verified: `git diff --stat main -- . ':(exclude)scripts/canonical' ':(exclude)tests/canonical'` is empty — no existing tracked file was modified.

## Metrics implemented (6 of the design's 9)

| Metric | Function | Source |
|---|---|---|
| `PRIMARY_NSV` | `canonical.primary.primary_nsv(data, fy)` | `detail_meta.channel_totals[fy]` (preferred, full precision) or `detail_records` (fallback) |
| `CHANNEL_PRIMARY_NSV` | `canonical.primary.channel_primary_nsv(data, fy, channel)` | Same |
| `OFFTAKE_NSV` | `canonical.offtake.offtake_nsv(data, fy)` | `offtake.total_<fy>` |
| `CHAIN_OFFTAKE_NSV` | `canonical.offtake.chain_offtake_nsv(data, fy, chain)` | `offtake.by_chain[chain][<fy>]`, **never** `.value`/`.total` |
| `RBC_PRIMARY_NSV` | `canonical.primary.rbc_primary_nsv(data, fy)` | `detail_records` filtered to `Chain=='Reliance Retail'` |
| `RBC_OFFTAKE_NSV` | `canonical.offtake.rbc_offtake_nsv(data, fy)` | `D.reliance_brand_counters` |

**Not implemented, per the design's ADR-004/005** (and per instruction): `CATEGORY_OFFTAKE_NSV`, `STORE_OFFTAKE_NSV` — no authoritative source grain exists. **`RBC_GAP_NSV` also not implemented** in Phase 1 — no `rbc_gap_nsv()` function exists anywhere in `canonical.primary` or `canonical.offtake` (verified by `tests/canonical/test_reliance_metrics.py::test_rbc_gap_requires_both_operands_never_computed_from_one`), so there is no code path that could compute a Gap from only one operand by mistake. It is deferred to a later phase once `RBC_OFFTAKE_NSV` has a real, non-stub source.

## Source lineage (verified, not assumed)

- **`PRIMARY_NSV`/`CHANNEL_PRIMARY_NSV`**: while building this module, `detail_records`'s own raw NSV sum for FY26 (`32,901.28 L`) was found to differ from the certified `32,900.36 L` baseline by `0.92 L` (`~0.003%`). Root-caused, not hand-waved: every `detail_records` row's `NSV` field is independently pre-rounded to exactly 2 decimal places (verified: 0 of 160,834 rows have more than 2 decimal digits), so re-summing 113,535 FY26 rows reintroduces cumulative rounding noise that `detail_meta.channel_totals` (which sums the full-precision, row-level values once, before any per-record rounding) does not have. **Fix applied**: `primary_nsv()`/`channel_primary_nsv()` now prefer `detail_meta.channel_totals[fy]` whenever it covers the requested FY (it covers both FY26 and FY27), falling back to `detail_records` re-aggregation only outside that coverage. With the fix, `PRIMARY_NSV('FY26')` matches the certified baseline to `0.00 L`.
- **`RBC_OFFTAKE_NSV`**: `D.reliance_brand_counters` in the *certified baseline's actual `data.js`* is the **empty stub** — `{"months": [], "monthly": [], "total": 0, "fy_tags": [], ..., "note": "Reliance Brand Counter data not available in current extracts."}`. This is a correction to a claim in `docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md` (merged in PR #197), which described this block as "real" based on the loader code (`load_reliance_bc_data()`) and schema being real — true, but the *populated values* in this specific build are the "no source found" fallback, not real BC figures. `RBC_OFFTAKE_NSV` therefore honestly returns `NOT_AVAILABLE` for both certified FYs today. This does not change ADR-003's decision (Primary + Offtake + Gap remains the correct target architecture) — it means the Offtake side of that view has no real data to show yet, and must say so, not display a stale zero.

## Shadow reconciliation results

Full report: `python scripts/canonical/shadow_report.py` (JSON; the table below is a summary).

```
SHADOW RECONCILIATION SUMMARY
Total comparisons: 48
PASS:              38  (zero variance against the already-certified figures)
GOVERNED:          10  (named, reasoned, expected differences -- see below)
FAIL:               0

OVERALL: PASS
```

### Clean PASSes (representative — full list in the JSON output)

| Metric | Scope | Existing | Canonical | Variance |
|---|---|---|---|---|
| `PRIMARY_NSV` | FY26 | 32,900.36 | 32,900.36 | 0.00 |
| `CHANNEL_PRIMARY_NSV` | MT, FY26 | 30,684.99 | 30,684.99 | 0.00 |
| `CHANNEL_PRIMARY_NSV` | EB2B, FY26 | 1,965.20 | 1,965.20 | 0.00 |
| `CHANNEL_PRIMARY_NSV` | SIS, FY26 | 250.17 | 250.17 | 0.00 |
| `OFFTAKE_NSV` | FY26 | 31,119.87 | 31,119.87 | 0.00 |
| `OFFTAKE_NSV` | FY27 | 19,044.99 | 19,044.99 | 0.00 |
| `RBC_PRIMARY_NSV` | all FYs combined | 13,702.51 | 13,702.51 | 0.00 |
| `CHAIN_OFFTAKE_NSV` | DMart, FY27 | 7,046.26 | 7,046.26 | 0.00 |
| ... (30 more chain/channel-level rows, all 0.00 variance) | | | | |

### Governed rows (10) — every one named and reasoned, none silently passed

| # | Metric | Scope | Reason |
|---|---|---|---|
| 1-3 | `CHANNEL_PRIMARY_NSV` | EB2B/MT/SIS, FY27 | `primary.by_channel` (Executive Cockpit's source) carries **no FY27 data at all** — a pre-existing, documented architecture fact (CLAUDE.md's "Coverage split": the pre-agg workbook ends Mar'26), not discovered by this reconciliation. Canonical correctly computes a real FY27 value from `detail_meta.channel_totals`. |
| 4 | `PRIMARY_NSV` | FY27 | Same coverage gap as above. |
| 5-8 | `CHAIN_OFFTAKE_NSV` | CNC / EB2B / Others / Vijetha, FY27 | **`KI-OFFTAKE-001`'s exact proof case.** Canonical correctly reports `NOT_AVAILABLE` for each (no real `fy27`-keyed entry). The existing dashboard's fallback chain would reach `offtake.by_chain[].value` instead — for Vijetha this is a real-looking stale number (`15.19`, its FY26 figure); for CNC/EB2B/Others it happens to be `0`. Same underlying defect either way: a non-answer substituted for "no data this FY." |
| 9-10 | `RBC_OFFTAKE_NSV` | FY26, FY27 | No existing dashboard consumer (per `docs/CANONICAL_METRIC_DEPENDENCY_MAP.md`) to compare against; canonical honestly reports `NOT_AVAILABLE` (empty BC stub, see Source lineage above). |

Every governed row has `expected_difference=True` and a reason of substantive length — enforced by `tests/canonical/test_shadow_reconciliation.py::test_shadow_reconciliation_governed_rows_are_all_reasoned`, so a future change that silently governs away a real problem (an empty or generic reason) fails the test suite, not just this report.

## Test results

```
$ python -m py_compile scripts/canonical/*.py tests/canonical/*.py
OK

$ python -m pytest tests/canonical/ -v
43 passed in 2.58s

$ python -m pytest tests/ -q          # full repository suite, not just canonical/
234 passed, 1 skipped in 187.78s      # 191 pre-existing + 43 new canonical, 0 regressions

$ python scripts/ci_validate_datajs.py
OK  data.js -- FY27 zones: Central, East, North, Pan India, South 1, South 2, West
OK  dashboard/data.js is valid JSON
OK  detail_records value_coverage_pct: 100.0%
OK  baseline invariants hold (7 checked)

$ bash scripts/run_dashboard_sweep.sh tests/dashboard_sweep.js
states swept: 44  |  failing: 0  |  total JS errors: 0
```

Test categories per the instruction:

| Category | Test file / test(s) |
|---|---|
| Exact-FY selection | `test_policies.py::test_exact_fy_returns_the_real_value_when_present` |
| No-cross-FY-fallback | `test_policies.py::test_never_falls_back_to_a_different_fy`, `::test_never_falls_back_to_an_all_period_value_field` |
| Missing != zero | `test_policies.py::test_missing_fy_returns_not_available_not_zero`, `::test_real_zero_is_available_and_distinct_from_not_available` |
| Unit conversion | `test_units.py` (5 tests) |
| Negative-value handling | Not separately tested in Phase 1 — no negative-NSV row currently reaches a Phase-1 metric's aggregation boundary in a way that exercises a distinct code path; the policy (ADR: real, never floored) is structurally satisfied by plain summation (no `max(0, ...)` clamp exists anywhere in `canonical.primary`/`canonical.offtake`), but this is a **known test gap**, not a verified guarantee — see Known limitations. |
| Channel-total reconciliation | `test_primary_metrics.py::test_channel_primary_nsv_fy26_matches_pr193_control1`, `::test_channel_primary_nsv_sums_to_primary_nsv` |
| Chain-total reconciliation | `test_offtake_metrics.py` (7 tests) |
| Reliance reconciliation | `test_reliance_metrics.py` (3 tests) |
| Publication-boundary NaN/Infinity | `test_publication_boundary.py` (3 tests) |
| Full shadow reconciliation | `test_shadow_reconciliation.py` (4 tests) |

## KI-OFFTAKE-001 result

**Closed at the engine level, not yet at the UI level** — per `docs/CANONICAL_METRIC_IMPLEMENTATION_PLAN.md` Phase 3/6 split (engine fix + reconciliation proof now; UI-visible confirmation is a later phase's job, not this one's).

- `canonical.offtake.chain_offtake_nsv(data, 'FY27', 'Vijetha')` returns `NOT_AVAILABLE`, never `15.19` (Vijetha's stale FY26 figure) — proven by a dedicated test (`test_chain_offtake_nsv_ki_offtake_001_no_stale_fallback`) and by the shadow reconciliation's governed row.
- The fix is structural, not a per-chain patch: `canonical.facts.offtake_chain_fy_values()` strips the `.value`/`.total` fields at the fact-loading layer itself, so no metric function built on top of it — now or in any future phase — can reach them, even by accident. Verified by `test_chain_offtake_nsv_never_reaches_the_value_field_even_when_present`, which asserts this for **every** chain currently lacking a real FY27 entry (4 found: CNC, EB2B, Others, Vijetha), not just the one example chain.
- **Issue #195 should stay open** until Phase 6 lands the UI-visible fix (the "Top Chains by Offtake" table itself still uses the old fallback chain today — unchanged by this PR, per Phase 1's explicit no-UI-migration scope).

## Known limitations

1. **Negative-value policy is structurally satisfied but not test-covered** (see Test results table above) — a genuine gap to close in a later phase, not a finding of incorrect behavior.
2. **`PRIMARY_NSV`/`CHANNEL_PRIMARY_NSV`'s `detail_records` fallback path** (used only outside `channel_totals`'s FY coverage — not exercised for FY26/FY27 today) still carries the ~0.003% cumulative-rounding characteristic described in Source lineage above. This is fine as a documented fallback for FYs `channel_totals` doesn't cover, but should not become the primary path in a later phase without addressing the underlying pre-rounding-at-record-creation issue in `detail_records_real()` itself (out of scope for this engine — that function is on the forbidden-to-change list for Phase 1).
3. **`RBC_OFFTAKE_NSV` has no real data to reconcile against** in the certified baseline (empty BC stub) — Phase 1's reconciliation for this metric proves the engine *correctly reports the absence*, not that the metric produces correct real values, since none exist yet to check against.
4. **The design doc's claim that `D.reliance_brand_counters` "is real"** (PR #197) needs a small clarifying note in a future documentation pass — the code path and schema are real; the populated values in the current certified `data.js` are not. Not fixed here (Phase 1 is forbidden from modifying `docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md`; noted here as an accurate correction on record instead).
5. **`existing.py`'s replication of dashboard JS is a manual mirror**, not an executed/tested-against-the-real-browser comparison — the same technique `tests/test_pr193_reconciliation.py` already uses and this repo already trusts, but a future phase could strengthen this further (e.g. a Playwright-based extraction of the actual rendered DOM values) if desired.

## Rollback method

Phase 1 has zero dashboard or data consumers — nothing outside `scripts/canonical/` and `tests/canonical/` references any function in this package (verified: `grep -r "canonical\." dashboard/ scripts/build_dashboard_data.py` returns no matches). Rollback is deleting these two directories; no data rebuild, no dashboard change, no other file touched.

---

## Final verdict

```
CANONICAL ENGINE — PHASE 1
[PASS] Architecture: fact layer -> metrics -> reconciliation, no second pre-aggregated blob
[PASS] 6 of 9 metrics implemented (2 correctly deferred as NOT_AVAILABLE per ADR-004/005,
       1 -- RBC_GAP_NSV -- correctly deferred pending a real RBC_OFFTAKE_NSV source)
[PASS] Shadow reconciliation: 38 PASS / 10 GOVERNED (all reasoned) / 0 FAIL
[PASS] KI-OFFTAKE-001 closed at engine level, proven by dedicated + reconciliation tests
[PASS] 43/43 new canonical tests pass; 234/235 full repo suite (1 pre-existing governed skip)
[PASS] ci_validate_datajs.py PASS; 44/44 browser sweep unaffected
[PASS] Zero existing files changed; zero dashboard/data.js consumers of the new package

VERDICT: PHASE 1 READY FOR MIGRATION
```

Not started in this phase, per instruction: dashboard UI migration, PBIP/DAX measures, AI insight generation. Opening this PR as **draft** for review before any of that begins.
