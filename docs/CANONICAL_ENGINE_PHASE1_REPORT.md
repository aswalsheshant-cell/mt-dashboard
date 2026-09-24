# Canonical Engine — Phase 1 Report

**Status:** Phase 1 of `docs/CANONICAL_METRIC_IMPLEMENTATION_PLAN.md` (Canonical metric engine + reconciliation framework). No dashboard UI, `dashboard/data.js` schema, or existing `scripts/build_dashboard_data.py` logic changed — the engine runs in shadow mode only, alongside today's production dashboard, consumed by nothing yet.
**Depends on:** `main` @ `1b75257c35cd5eab47ffc34bfb5ae53755ae318d` (PR #197's merge — the canonical financial-truth architecture contract).
**Branch:** `architecture/canonical-metric-engine`
**Certification gate (this update):** the Phase 1 Certification Gate requested before PR #198 can be marked Ready for Review — a rigorous GOVERNED-reconciliation review (every governed row now traces to a reviewed `governance.py` registry entry, never a bare reason string), corrected Reliance availability reporting, an authorized documentation correction to `docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md`, a status update on Issue #195 (kept OPEN), a new "Canonical Financial Truth Gate" CI workflow, and source contracts for the Primary and Offtake inputs. See "Final verdict" at the bottom for the outcome.

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
scripts/canonical/governance.py          -- NEW (certification gate): approved-exceptions registry
scripts/canonical/availability.py        -- NEW (certification gate): ADR-003 RBC availability reporting
scripts/canonical/contract_validation.py -- NEW (certification gate): Primary/Offtake source contract validators
scripts/canonical_gate_checks.py         -- NEW (certification gate): CI entrypoint for the Canonical Financial Truth Gate

contracts/channel_contract.yaml          -- NEW (certification gate)
contracts/chain_contract.yaml            -- NEW (certification gate)
contracts/primary_contract.yaml          -- NEW (certification gate)
contracts/offtake_contract.yaml          -- NEW (certification gate)

.github/workflows/canonical-financial-truth-gate.yml  -- NEW (certification gate)

tests/canonical/__init__.py
tests/canonical/conftest.py
tests/canonical/test_fiscal.py
tests/canonical/test_units.py
tests/canonical/test_policies.py
tests/canonical/test_primary_metrics.py
tests/canonical/test_offtake_metrics.py
tests/canonical/test_reliance_metrics.py
tests/canonical/test_publication_boundary.py
tests/canonical/test_shadow_reconciliation.py    -- REWRITTEN (certification gate): PASS/APPROVED_GOVERNED/FAIL/UNKNOWN model
tests/canonical/test_governance.py               -- NEW (certification gate)
tests/canonical/test_availability.py             -- NEW (certification gate)
tests/canonical/test_contract_validation.py      -- NEW (certification gate)
tests/canonical/test_gate_checks.py              -- NEW (certification gate)
```

**Files changed by the certification gate, beyond what's listed above as new:**
- `scripts/canonical/reconcile.py` — added the `UNKNOWN` result state; `reconcile_one()` now routes every non-clean case through `governance.find_approved_exception()` instead of accepting a caller-supplied reason string at face value.
- `scripts/canonical/policies.py` — `is_available()` now also treats a bare `None` as unavailable (previously only `NotAvailable` instances were), fixing a real crash/false-pass this certification review surfaced (see "Errors found and fixed" below).
- `docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md` — one explicitly authorized correction (an implementation-discovery note, not a reversal of ADR-003; see that document's own note at the top and the RBC_OFFTAKE_NSV contract table).
- `requirements.txt` — added `PyYAML==6.0.1` (now a real, direct dependency via `contract_validation.py`, not just a transitive one).

**No existing dashboard/build file was touched.** Verified: `git diff --stat -- dashboard/index.html dashboard/data.js scripts/build_dashboard_data.py` is empty.

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
SHADOW RECONCILIATION SUMMARY  (post-certification-gate model)
Total comparisons:    48
PASS:                 38   (zero variance against the already-certified figures)
APPROVED_GOVERNED:    10   (each traces to a reviewed governance.py registry entry)
FAIL:                  0
UNKNOWN:               0

clean_population_pct: 100.0%   (PASS + APPROVED_GOVERNED, of total)
OVERALL: PASS
```

**"GOVERNED" is no longer a soft label.** Every one of the 10 non-PASS rows above now carries a full, reviewed record from `scripts/canonical/governance.py`'s `APPROVED_EXCEPTIONS` registry — `reconcile_one()` looks the row up by `(metric, scope)`; if no registry entry matches, the result is `UNKNOWN` (which fails the gate exactly like `FAIL`), never a bare `APPROVED_GOVERNED` string a caller could self-certify. `tests/canonical/test_governance.py` proves this both ways: an unregistered claim becomes `UNKNOWN` (`test_unregistered_exception_becomes_unknown_not_governed`), and a registered one becomes `APPROVED_GOVERNED` with the record attached (`test_registered_exception_becomes_approved_governed`).

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

### APPROVED_GOVERNED rows (10) — the full governance record for each

Every field below is a real, reviewed field on the `governance.ApprovedException` record attached to these rows — not a reason string invented at reconciliation time. Registry source: `scripts/canonical/governance.py`.

| Registry ID | Metric | Scope | Existing | Canonical | Reason not PASS | Evidence | Business impact | Financial impact | Owner | Temp/Perm | Resolution phase | Release blocker |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GOV-001` | `CHANNEL_PRIMARY_NSV` | MT/EB2B/SIS, FY27 (3 rows) | `NOT_AVAILABLE` | real FY27 value | `primary.by_channel` (Executive Cockpit's current source) carries no FY27 data at all | CLAUDE.md's documented "Coverage split": the pre-aggregated Primary workbook ends Mar'26 | Executive Cockpit's channel donut cannot show FY27 today; canonical engine already can | None — a display-source coverage gap, not a miscalculation | Engineering | TEMPORARY | Phase 5 (Executive Cockpit migration) | NO |
| `GOV-002` | `PRIMARY_NSV` | FY27 | `NOT_AVAILABLE` | real FY27 value | Same root cause as `GOV-001`, at the grand-total level | Same as `GOV-001` | Same as `GOV-001` | None | Engineering | TEMPORARY | Phase 5 (Executive Cockpit migration) | NO |
| `GOV-003` | `CHAIN_OFFTAKE_NSV` | CNC/EB2B/Others/Vijetha, FY27 (4 rows) | a real-looking number (e.g. Vijetha's stale `15.19`) or `0` | `NOT_AVAILABLE` | **`KI-OFFTAKE-001` (Issue #195) — this is the registry entry that proves the fix.** Canonical correctly reports no data; production's fallback chain reaches `offtake.by_chain[].value`, an all-months-combined field with no FY subscript | Verified: none of these 4 chains has a real `fy27`-keyed entry in the certified `data.js`; `test_shadow_reconciliation.py::test_shadow_reconciliation_includes_ki_offtake_001_proof` pins this | The "Top Chains by Offtake" table can show a stale or zero FY27 figure for these 4 chains today | Low — 4 of 35 chains, not majority | Engineering | TEMPORARY | Phase 6 (Comparison/Inventory/Alerts migration) | NO |
| `GOV-004` | `RBC_OFFTAKE_NSV` | FY26, FY27 (2 rows) | no existing consumer (`None`) | `NOT_AVAILABLE` | `D.reliance_brand_counters` is an empty availability stub in this build — no real BC extract has been sourced | `data.js`'s own block: `{"total": 0, "months": [], ..., "note": "Reliance Brand Counter data not available in current extracts."}` | The Reliance Brand Counter tab's Offtake-side view cannot be built yet; Primary-side and the tab's current Primary-only display are unaffected | None — nothing today reads this field | MT Leadership / Business (source onboarding — sourcing a real extract is not an engineering task) | TEMPORARY | Not yet scheduled — blocked on a real Reliance Brand Counter offtake extract being sourced | NO |

Acceptance condition met: **`FAIL = 0`, `UNKNOWN = 0`, `PASS + APPROVED_GOVERNED = 100%` of the reconciliation population** (`tests/canonical/test_shadow_reconciliation.py::test_shadow_reconciliation_meets_phase1_acceptance_criterion`).

## Reliance Brand Counter (ADR-003) — availability status, explicit and tested

Per the certification instruction, canonical availability is reported explicitly, per measure, never inferred or silently substituted:

| Measure | Status | Reason |
|---|---|---|
| `RBC_PRIMARY_NSV` | **AVAILABLE** | Real `detail_records` rows filtered to `Chain == 'Reliance Retail'` (13,702.51 L, all FYs combined — reconciled 0.00 L variance against PR #193's certified Reliance Control) |
| `RBC_OFFTAKE_NSV` | **NOT_AVAILABLE** | `D.reliance_brand_counters` is an empty stub in the certified `data.js` — no real Brand Counter offtake extract has been sourced for this build |
| `RBC_GAP_NSV` | **NOT_AVAILABLE** | Per ADR-003 rule 5, a derived measure requires both operands available; `RBC_OFFTAKE_NSV` is not, so no Gap is computed (there is no `rbc_gap_nsv()` function at all — see "Metrics implemented" above) |

Computed by `scripts/canonical/availability.py::rbc_availability_report()`, verified against the real certified `data.js` in `tests/canonical/test_availability.py` (5 tests, including a mutation test proving the Gap's derivation actually inspects both operands rather than being hardcoded). **No calculated substitute was created and no Reliance chain-level Offtake was allocated down to Brand Counter** — per the explicit instruction that such an allocation requires a business rule that does not currently exist.

## Test results

Re-run in full for the certification gate (all commands below are the actual final validation run, not the original Phase 1 numbers):

```
$ python -m py_compile scripts/build_dashboard_data.py scripts/canonical_gate_checks.py scripts/canonical/*.py
OK

$ python -m pytest tests/canonical/ -v
80 passed in ~12s     # 43 original + 37 new this gate (governance, availability,
                       # contract_validation, gate_checks test files)

$ python -m pytest tests/ -q          # full repository suite, not just canonical/
271 passed, 1 skipped in 203.77s      # 191 pre-existing (non-canonical) + 80 canonical, 0 regressions,
                                       # the 1 skip is the same pre-existing, already-governed skip as before

$ python scripts/ci_validate_datajs.py
OK  data.js -- FY27 zones: Central, East, North, Pan India, South 1, South 2, West
OK  dashboard/data.js is valid JSON
OK  detail_records value_coverage_pct: 100.0%
OK  baseline invariants hold (7 checked)

$ python scripts/canonical/shadow_report.py   # summary
{"total": 48, "pass": 38, "approved_governed": 10, "fail": 0, "unknown": 0,
 "clean_population_pct": 100.0, "overall": "PASS"}

$ python scripts/canonical_gate_checks.py     # the new Canonical Financial Truth Gate script, all 8 structural checks
PASS [reconciliation]
PASS [numeric-safety]
PASS [governance]
PASS [fallback-safety]
PASS [unit-isolation]
PASS [availability-metadata]
PASS [missing-never-zero]
PASS [source-contracts]
Canonical Financial Truth Gate: PASS

$ bash scripts/run_dashboard_sweep.sh tests/dashboard_sweep.js
states swept: 44  |  failing: 0  |  total JS errors: 0

$ git diff --stat -- dashboard/index.html dashboard/data.js scripts/build_dashboard_data.py
(empty — zero changes to any of the three forbidden files)
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

**Engine remediation = COMPLETE. Production consumer migration = PENDING. Issue status = OPEN — IMPLEMENTED IN SHADOW MODE.**

- `canonical.offtake.chain_offtake_nsv(data, 'FY27', 'Vijetha')` returns `NOT_AVAILABLE`, never `15.19` (Vijetha's stale FY26 figure) — proven by a dedicated test (`test_chain_offtake_nsv_ki_offtake_001_no_stale_fallback`) and by the shadow reconciliation's `GOV-003` registry row.
- The fix is structural, not a per-chain patch: `canonical.facts.offtake_chain_fy_values()` strips the `.value`/`.total` fields at the fact-loading layer itself, so no metric function built on top of it — now or in any future phase — can reach them, even by accident. Verified by `test_chain_offtake_nsv_never_reaches_the_value_field_even_when_present`, which asserts this for **every** chain currently lacking a real FY27 entry (4 found: CNC, EB2B, Others, Vijetha), not just the one example chain. `scripts/canonical_gate_checks.py`'s `fallback-safety` structural check additionally scans `facts.py`/`primary.py`/`offtake.py` on every CI run for the `.value` anti-pattern reappearing anywhere in those files, so this cannot silently regress in a later commit.
- A status comment was posted on [Issue #195](https://github.com/aswalsheshant-cell/mt-dashboard/issues/195) recording this exact state. **The issue was deliberately NOT closed** — closing it would claim the production bug is fixed for users, which is false until a real dashboard consumer (planned: `CHAIN_OFFTAKE_NSV` migration, the first production consumer migration once this PR is certified and merged) replaces the "Top Chains by Offtake" table's current fallback chain. That table is unchanged by this PR, per Phase 1's explicit no-UI-migration scope.

## Source contracts (Primary, Offtake)

Per the certification instruction, both canonical-engine inputs now have an explicit, checked contract — plain YAML + a Python validator, not a heavy framework:

| Contract | File | Covers |
|---|---|---|
| Primary | `contracts/primary_contract.yaml` | `detail_records`: required fields, datatypes, nullability, grain, FY pattern (THE ONE FY RULE), NSV unit/sign policy, full-row duplicate detection |
| Offtake | `contracts/offtake_contract.yaml` | `offtake.by_chain`: chain-row shape, duplicate chain-name detection, FY field naming (`fy<YY>`), NaN/Infinity/negative-value rejection, explicit note that `.value`/`.total` are legitimate fields to *have* but forbidden to use as an FY substitute |
| Channel mapping | `contracts/channel_contract.yaml` | Closed list (`MT`, `EB2B`, `SIS`) — referenced by the Primary contract |
| Chain mapping | `contracts/chain_contract.yaml` | Open list (chains legitimately grow) — shape-only validation, plus the known `"Unmapped Chain"` placeholder value |

Validator: `scripts/canonical/contract_validation.py` (`validate_primary_contract()`, `validate_offtake_contract()`, `validate_channel_contract()`, `validate_chain_contract()`, `validate_all()`). 14 tests in `tests/canonical/test_contract_validation.py`, including mutation tests proving each validator actually catches the defect it claims to (an unrecognized channel, a null chain, a full-row duplicate, a NaN NSV, a duplicate chain name, a negative/infinite offtake value).

**One real, pre-existing finding surfaced by writing this contract** (not introduced by this PR): exactly one `detail_records` row — `Article="TDC-FOC Product 18%"`, `Chain=Apollo`, FY27, negative NSV/MRP/Qty — has a null `Category`/`SubCategory`/`Range`/`PackSize`. This is a free-of-cost/scheme adjustment line, not a catalog SKU. It is recorded as a pinned, documented exception (`primary_contract.yaml`'s `known_exceptions` note; `test_primary_contract_has_exactly_one_known_category_null_exception` pins the count at exactly 1) rather than silently patched or silently ignored — if a second, different row ever violates this contract, the pinned test fails and the new finding must be reviewed, not absorbed. Offtake's contract is fully clean today (0 violations).

## Errors found and fixed during this certification review

Building the governance registry surfaced three real bugs in the reconciliation framework itself, each fixed and covered by a regression test before this report was finalized:

1. **An availability mismatch (`existing` has a real value, `canonical` says `NOT_AVAILABLE`, or vice versa) was briefly implemented as an automatic PASS.** This would have silently converted all 10 governed rows into unlabeled passes — the opposite of transparency. Fixed: an availability mismatch is never automatically clean; it must resolve through the governance registry (`APPROVED_GOVERNED`) or fail (`FAIL`/`UNKNOWN`).
2. **`is_available(None)` returned `True`.** `shadow_report.py` passes a bare `None` (not a `NotAvailable` instance) for `RBC_OFFTAKE_NSV`'s "no existing consumer" case, which then reached `float(None)` and crashed. Fixed: `policies.is_available()` now treats a bare `None` the same as an explicit `NotAvailable` — both mean "nothing to compare."
3. **After fixing #2, "both sides unavailable" was auto-passing even when a caller explicitly flagged the pair as a finding worth recording** (`expected_difference=True`) — which would have made `RBC_OFFTAKE_NSV`'s honest unavailability disappear into a generic, unlabeled PASS instead of surfacing as the reviewed `GOV-004` record. Fixed: an explicit `expected_difference=True` claim always routes through the governance lookup, even when both sides report unavailable.

All three are covered by `tests/canonical/test_governance.py` and `tests/canonical/test_shadow_reconciliation.py::test_shadow_reconciliation_rbc_offtake_not_available_is_governed_not_hidden`.

## Known limitations

1. **Negative-value policy is structurally satisfied but not test-covered** (see Test results table above) — a genuine gap to close in a later phase, not a finding of incorrect behavior.
2. **`PRIMARY_NSV`/`CHANNEL_PRIMARY_NSV`'s `detail_records` fallback path** (used only outside `channel_totals`'s FY coverage — not exercised for FY26/FY27 today) still carries the ~0.003% cumulative-rounding characteristic described in Source lineage above. This is fine as a documented fallback for FYs `channel_totals` doesn't cover, but should not become the primary path in a later phase without addressing the underlying pre-rounding-at-record-creation issue in `detail_records_real()` itself (out of scope for this engine — that function is on the forbidden-to-change list for Phase 1).
3. **`RBC_OFFTAKE_NSV` has no real data to reconcile against** in the certified baseline (empty BC stub) — Phase 1's reconciliation for this metric proves the engine *correctly reports the absence*, not that the metric produces correct real values, since none exist yet to check against.
4. ~~The design doc's claim that `D.reliance_brand_counters` "is real" (PR #197) needs a small clarifying note~~ — **RESOLVED by this certification gate.** `docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md` now carries an explicit "Implementation discovery — Phase 1" correction (an authorized, one-time exception to Phase 1's no-doc-change scope, since this is evidence discovered by implementation correcting the contract implementation follows, not scope creep) stating plainly: the code path and schema are real, the populated values in this certified `data.js` are not, and ADR-003's Option C decision is unchanged.
5. **`existing.py`'s replication of dashboard JS is a manual mirror**, not an executed/tested-against-the-real-browser comparison — the same technique `tests/test_pr193_reconciliation.py` already uses and this repo already trusts, but a future phase could strengthen this further (e.g. a Playwright-based extraction of the actual rendered DOM values) if desired.

## Rollback method

Phase 1 has zero dashboard or data consumers — nothing outside `scripts/canonical/` and `tests/canonical/` references any function in this package (verified: `grep -r "canonical\." dashboard/ scripts/build_dashboard_data.py` returns no matches). Rollback is deleting these two directories; no data rebuild, no dashboard change, no other file touched.

---

## Final verdict — Phase 1 Certification Gate

```
CANONICAL ENGINE — PHASE 1 CERTIFICATION GATE
[PASS] Architecture: fact layer -> metrics -> reconciliation, no second pre-aggregated blob
[PASS] 6 of 9 metrics implemented (2 correctly deferred as NOT_AVAILABLE per ADR-004/005,
       1 -- RBC_GAP_NSV -- correctly deferred pending a real RBC_OFFTAKE_NSV source)
[PASS] Governed reconciliation review: 38 PASS / 10 APPROVED_GOVERNED / 0 FAIL / 0 UNKNOWN
       -- every APPROVED_GOVERNED row traces to a reviewed governance.py registry entry
       (GOV-001..GOV-004), never a bare reason string
[PASS] Reliance Brand Counter availability corrected and tested:
       RBC_PRIMARY_NSV = AVAILABLE, RBC_OFFTAKE_NSV = NOT_AVAILABLE, RBC_GAP_NSV = NOT_AVAILABLE
       -- no calculated substitute, no chain-level-Offtake allocation to Brand Counter
[PASS] Authorized documentation correction applied to CANONICAL_FINANCIAL_TRUTH_DESIGN.md
       (implementation discovery, not a reversal of ADR-003)
[PASS] Issue #195 (KI-OFFTAKE-001): status comment posted, issue kept OPEN --
       "Engine remediation = COMPLETE, Production consumer migration = PENDING"
[PASS] New "Canonical Financial Truth Gate" CI workflow added (8 structural checks,
       does not weaken any existing gate)
[PASS] Source contracts added for Primary and Offtake inputs (contracts/*.yaml +
       contract_validation.py), 1 pinned pre-existing data finding documented, not hidden
[PASS] Full final validation: 80/80 canonical tests, 271/271 full repo suite (1 pre-existing
       governed skip, 0 regressions), py_compile clean, ci_validate_datajs.py PASS,
       44/44 browser sweep unaffected, zero tracked dashboard/data.js/build-script changes
[PASS] Acceptance condition met: FAIL=0, UNKNOWN=0, UNEXPLAINED=0,
       PASS+APPROVED_GOVERNED=100% of the reconciliation population

VERDICT: PHASE 1 READY FOR CONSUMER MIGRATION
```

**PR #198 may be marked "Ready for Review."** Per explicit instruction: this PR is **NOT** being merged automatically, and Phase 2 (production consumer migration) is **NOT** starting as part of this certification. The next planned step — a future task, not this one — is migrating `CHAIN_OFFTAKE_NSV` as the first live production consumer, which is what will actually close Issue #195.
