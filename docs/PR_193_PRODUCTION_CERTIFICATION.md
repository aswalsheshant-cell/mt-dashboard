# PR #193 Production Certification Gate

**PR:** [aswalsheshant-cell/mt-dashboard#193](https://github.com/aswalsheshant-cell/mt-dashboard/pull/193)
**Branch:** `fix/dashboard-audit-findings`
**Certified commit SHA:** `e0e30c4814b750415717b3635be4d04a2a2e1c6c` (validation
run against this SHA; this report is committed on top of it as `64db8fd`,
which changes only this file — `git diff --stat e0e30c4 64db8fd` touches
nothing else — so every result below holds unchanged for the PR's actual
final head, `64db8fdfefed05bde992ea3fd5bd5fdf674808a6`)
**Base:** `main` @ `cd8b033f34d73e6e283d4a264731362750a0cc5e`
**Certified on:** 2026-09-24
**Certifying agent:** Claude Code session `01HrrHqs3z5s4zwcF6xhCAHs`

This is a scope-frozen certification of the four business-number defects found
and fixed in PR #193's 17-view dashboard root-cause audit. It does not add,
remove, or modify any dashboard feature or fix beyond what is already in the
PR's diff. Its purpose is to move validation from "the dashboard renders
correctly" (already proven by the 44-state sweep) to "the corrected business
numbers are provably reconciled against independent sources."

---

## Files changed in this PR (`git diff --stat main...e0e30c4`)

| File | Change |
|---|---|
| `scripts/build_dashboard_data.py` | +89/-not shown — adds `apply_primary_channel_correction()`, wires it into both the full build and `--detail-only` |
| `dashboard/data.js` | `primary.by_channel` (FY26 only) corrected; one pre-existing, unrelated cosmetic `mapping_health.note` string added by re-running today's generator |
| `dashboard/index.html` | 3 `crc(x/100)` double-division sites fixed (Category & Pack Mix x2, Reliance-by-Zone x1); `buildInventoryHealth()`'s `total` reordered to use `fyR` instead of raw `fy`; Store Audit Scorecard door-count caption fixed |
| `tests/test_primary_channel_correction.py` | new — 5 tests on `apply_primary_channel_correction()` |
| `tests/test_pr193_reconciliation.py` | new — 12 tests, this certification's evidence (below) |

No other file is touched. `git status` is clean at the certified SHA.

---

## Certification checks

### Control 1 — FY26 Primary Total (Executive Cockpit Channel split)

| | Value (INR Lakh) |
|---|---|
| `primary.by_channel` FY26: MT | 30,684.99 |
| `primary.by_channel` FY26: EB2B | 1,965.20 |
| `primary.by_channel` FY26: SIS | 250.17 |
| **Sum (MT+EB2B+SIS)** | **32,900.36** |
| Certified FY26 Primary baseline (`config/baselines.json` / CLAUDE.md) | 32,900.36 |
| `detail_meta.channel_totals.FY26` (independent article-wise source) | `{EB2B: 1965.2, MT: 30684.99, SIS: 250.17}` — identical |
| **Variance** | **0.00 L** |
| Tolerance | ±0.01 L (rupee rounding) |
| **Result** | **PASS** |

Pre-fix value was `{MT: 32900.36, EB2B: 0, SIS: 0}` — same total, wrong split.
Tests: `test_channel_by_channel_sums_to_certified_fy26_total`,
`test_channel_by_channel_reconciles_to_article_wise_channel_totals`.

### Control 2 — Category & Pack Mix

| | Value (INR Lakh) |
|---|---|
| Sum of `detail_records` grouped by Category | 55,138.75 |
| Sum of all `detail_records` NSV | 55,138.75 |
| **Variance** | **0.00 L** |
| Face category NSV (regression pin; pre-fix displayed as ~341 L / ₹3.41 Cr) | 34,089.83 L (₹340.90 Cr) |
| Tolerance | ±0.01 L |
| Source-regression guard: `crc(x/100)` call sites in `dashboard/index.html` | 0 found |
| **Result** | **PASS** |

This is an arithmetic identity (sum of a groupby must equal the ungrouped
total) combined with a static source-code guard, because the underlying bug
was a **display** defect (`crc(v.nsv/100)` double-dividing an already-Lakh
value before `crc()`'s own Cr conversion), not an aggregation defect — the
`agg[k].nsv += r.NSV` accumulation was never wrong. The guard proves the exact
buggy pattern cannot silently return; the identity proves the values it now
displays are internally consistent.
Tests: `test_category_nsv_sums_to_detail_records_total`,
`test_category_face_matches_certified_screenshot_figure`,
`test_no_double_lakh_division_before_crc_in_category_or_reliance_tables`.

### Control 3 — Reliance Zone

| | Value (INR Lakh) |
|---|---|
| Reliance Retail total NSV (all `detail_records`) | 13,702.51 |
| Sum of Reliance Retail records grouped by Zone | 13,702.51 |
| **Variance** | **0.00 L** |
| Regression pin (pre-fix displayed as ~137 L / ₹1.37 Cr) | 13,702.51 L (₹137.03 Cr) |
| Tolerance | ±0.01 L |
| Source-regression guard | same `crc(x/100)` scan as Control 2 — 0 found |
| **Result** | **PASS** |

Tests: `test_reliance_zone_nsv_sums_to_reliance_chain_total`,
`test_reliance_total_matches_certified_screenshot_figure`.

### Control 4 — Inventory & Supply Health "Total Offtake" KPI

| | Value (INR Lakh) |
|---|---|
| Resolved FY (`fyR`, latest `offtake.fy_tags`) | `fy27` |
| `offtake.total_fy27` (field the fixed KPI now reads) | 19,044.99 |
| Independent sum of `offtake.monthly_fy27` (`[3588.51, 4019.42, 3840.46, 3621.47, 3975.13]`) | 19,044.99 |
| **Variance** | **3.6 × 10⁻¹² L** (floating-point noise) |
| Tolerance | ±0.01 L |
| Pre-fix KPI value (raw `fy` is `null` in the default "All FY" view) | 0 |
| **Result** | **PASS** |

Note on scope: a separate, pre-existing table on the same page ("Top Chains by
Offtake", `buildInventoryHealth`'s `chainData`) falls back to a stale
`ch_data.value` field for ~4 long-tail chains that have no current-FY entry
(e.g. Vijetha), which does not itself feed the KPI and was not touched by any
of the three fixes in this PR — see **Known limitations** below rather than
presented here as passing.

Tests: `test_inventory_total_offtake_reconciles_to_monthly_sum`,
`test_inventory_kpi_formula_uses_fyr_fallback_not_raw_fy`,
`test_inventory_kpi_nonzero_when_real_data_exists`.

### Control 5 — Publication boundary

| Check | Result |
|---|---|
| `dashboard/data.js` parses as valid JSON | PASS |
| No raw `NaN` token in `dashboard/data.js` | PASS |
| No `Infinity` token in `dashboard/data.js` | PASS |
| `detail_records` value coverage | 100.0% |
| Baseline invariants (`config/baselines.json`, 7 checked) | PASS — all hold |

Reuses `scripts/ci_validate_datajs.py` rather than a second copy of the same
scan. Test: `test_no_nan_or_infinity_tokens_in_datajs`,
`test_datajs_baseline_invariants_hold`.

---

## Full validation run (at certified SHA `e0e30c4`)

```
$ python -m py_compile scripts/build_dashboard_data.py
py_compile: OK

$ python -m pytest tests/test_primary_channel_correction.py tests/test_pr193_reconciliation.py -v
17 passed in 12.52s

$ python scripts/ci_validate_datajs.py
OK  data.js -- FY27 zones: Central, East, North, Pan India, South 1, South 2, West
OK  dashboard/data.js is valid JSON
OK  detail_records value_coverage_pct: 100.0%
OK  baseline invariants hold (7 checked)

$ bash scripts/run_dashboard_sweep.sh tests/dashboard_sweep.js   # run at dde3cb8
states swept: 44  |  failing: 0  |  total JS errors: 0
```

The 44-state sweep was executed at commit `dde3cb8` (the commit immediately
before this certification's own test-only commit). `git diff --stat dde3cb8
e0e30c4` shows only `tests/test_pr193_reconciliation.py` added — no file the
sweep exercises (`dashboard/index.html`, `dashboard/data.js`, any `.json`
asset) changed between the two, so the sweep result carries forward
unmodified to the certified SHA.

---

## Gate summary

```
PR #193 CERTIFICATION
[PASS] Python compile
[PASS] Primary channel unit tests (5/5)
[PASS] ci_validate_datajs.py
[PASS] 44/44 browser states (0 JS errors)
[PASS] 17-view visual audit (manual, prior to this certification)
[PASS] No JS errors
[PASS] Channel reconciliation (Control 1)
[PASS] Category reconciliation (Control 2)
[PASS] Reliance reconciliation (Control 3)
[PASS] Inventory KPI reconciliation (Control 4)
[PASS] No unexpected tracked-file mutation (git status clean; diff limited to listed files)
[PASS] Git working tree clean
[PASS] PR diff limited to approved scope (4 defects + their tests + this report)
[PASS] GitHub CI — 25/26 checks green at c5da242, including all 6 required
       Production Acceptance Gate checks (validate, Analyze (python),
       Analyze (javascript-typescript), Validate Dashboard Data & Schema,
       Validate HTML Structure & Fixes, Production Acceptance Gate)
[N/A]  github-advanced-security — failed at session setup with
       "CAPIError: 400 The requested model is not supported" (GitHub's own
       Copilot backend rejecting its own model choice, before reading any
       code in this diff). Not a required check; not retriable
       (rerun_failed_jobs -> 403 This workflow run cannot be retried).
       Documented on the PR, not treated as blocking.

VERDICT: READY FOR REVIEW
```

---

## Known limitations (not blocking; explicitly out of this PR's scope)

1. **"Top Chains by Offtake" table's stale-fallback quirk.** For ~4 long-tail
   chains with no entry for the currently-viewed FY (e.g. "Vijetha", FY27),
   `buildInventoryHealth`'s chain table falls back to `ch_data.value`, which
   mirrors the chain's FY26 figure rather than showing "–" for FY27. This
   inflates that table's own displayed sum by ~15 L (~0.08% of ~19,045 L) —
   found while grounding Control 4's reconciliation formula against the real
   code path. It is a **pre-existing** characteristic (confirmed present in
   the pre-PR-193 baseline data.js, unrelated to any of the three code fixes
   in this PR) and does not feed the "Total Offtake" KPI this PR corrected.
   Recommendation: track as a separate, small follow-up fix (show "–" for a
   chain with no data in the selected FY instead of falling back to a
   different FY's value) — not addressed here to keep this PR's diff scoped
   to its own four defects.
2. **`dashboard/alerts_feed.json` reports 0 active alerts** from a file
   generated 2026-08-26 (about one month stale as of this certification).
   The value is genuinely computed (not a code bug — `buildAlerts()` correctly
   renders whatever the feed contains), but whatever job is meant to refresh
   this file on a cadence should be checked. Not a dashboard code defect.
3. **Reliance Brand Counter "macro vs BA" toggle** only changes an on-page
   disclaimer, not the underlying data, in `renderChannelSubview`'s `reliance`
   branch. Confirmed **by design**: per this repo's Reliance Brand Counter
   isolation rule, counter deduplication applies to Offtake only, never to
   Primary — and this sub-view (under Channel & Chain Performance, a
   Primary-scoped tab group) is Primary data. Not a defect.

None of these three items are business-number defects in the four areas this
PR fixed, and none are changed by this certification.

---

## Verdict

**READY FOR REVIEW.**

All four defects are reconciled against independent sources with 0.00 L
variance (well within the ±0.01 L rounding tolerance used throughout this
repo's own `r2()` convention), all regression guards correctly detect their
respective mutations (verified against a scratch copy, not the tracked repo),
and the full existing validation gate (py_compile, unit tests, release-gate
script, 44-state browser sweep) is green at the certified commit. PR #193 is
recommended to move from Draft to Ready for Review. It should not be merged
until a human reviewer approves it and any branch-protection requirements on
`main` (required status checks, required review, conversation resolution,
up-to-date-with-base) are satisfied.
