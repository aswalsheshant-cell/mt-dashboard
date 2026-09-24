# Post-Merge Certification — PR #193

**PR:** [aswalsheshant-cell/mt-dashboard#193](https://github.com/aswalsheshant-cell/mt-dashboard/pull/193)
**Certified PR head SHA:** `19ddc709d894ae0b2f531bbe39ed9c63b0015467`
**Resulting `main` SHA:** `c83011b82d1f3b1e6f1c2a21c12aed91ea9c5cf7`
**Merge timestamp:** 2026-09-24T01:32:01Z
**Merge method:** standard merge commit (this repo's existing convention — matches PRs #182, #188, #190, #191, #192)
**Merged/certified by:** Claude Code session `01HrrHqs3z5s4zwcF6xhCAHs`, on explicit owner approval

This report certifies that `main` at `c83011b` is a known-good production baseline for the four business-number defects fixed in PR #193. It is the second of two auditable certification points for this change (`19ddc70` on the PR branch, then `c83011b` on `main`), per the "required checks apply to the latest applicable commit" principle applied at both the PR and the post-merge stage.

---

## Pre-merge verification (performed immediately before the merge action)

| Check | Result |
|---|---|
| PR #193 head SHA | `19ddc709d894ae0b2f531bbe39ed9c63b0015467` — confirmed, unchanged since certification |
| PR state | `open`, `draft: false`, `mergeable_state: clean` |
| Required status checks | All 6 green: `validate`, `Analyze (python)`, `Analyze (javascript-typescript)`, `Validate Dashboard Data & Schema`, `Validate HTML Structure & Fixes`, `Production Acceptance Gate` |
| New commits since certification | None (PR `updated_at` unchanged) |
| Unresolved review conversations | None (0 review threads, 0 reviews — repo has no second collaborator/CODEOWNERS; owner approval given directly) |
| Issue #194 (github-advanced-security infra) | Open, separately tracked, untouched |
| Issue #195 (KI-OFFTAKE-001) | Open, separately tracked, untouched |

Merge executed with `expectedHeadSha` pinned to `19ddc70` so the merge could only succeed against exactly the certified commit.

## Files merged into `main`

`git diff --stat cd8b033...c83011b` (base → merge commit):

| File | Change |
|---|---|
| `scripts/build_dashboard_data.py` | +89/-… — adds `apply_primary_channel_correction()` |
| `dashboard/data.js` | `primary.by_channel` (FY26) corrected; one pre-existing, unrelated cosmetic `mapping_health.note` string |
| `dashboard/index.html` | 3 `crc(x/100)` fixes; `buildInventoryHealth()` KPI fyR ordering fix; Store Audit Scorecard caption fix |
| `docs/PR_193_PRODUCTION_CERTIFICATION.md` | new — pre-merge certification |
| `tests/test_primary_channel_correction.py` | new — 5 tests |
| `tests/test_pr193_reconciliation.py` | new — 12 tests |

Verified via an explicit tracked-file-mutation check (below) that no file outside this list changed.

---

## Certification run against `main` @ `c83011b`

### A. Python compile
```
$ python -m py_compile scripts/build_dashboard_data.py
OK
```

### B/C. All reconciliation and unit tests
```
$ python -m pytest tests/test_primary_channel_correction.py tests/test_pr193_reconciliation.py -v
17 passed in 14.34s
```
Full repository test suite (broader regression check, not just the PR's own tests):
```
$ python -m pytest tests/ -q
191 passed, 1 skipped in 192.17s
```
The 1 skip is this repo's pre-existing, documented governed skip (unrelated to PR #193).

### D. `ci_validate_datajs.py`
```
OK  data.js -- FY27 zones: Central, East, North, Pan India, South 1, South 2, West
OK  dashboard/data.js is valid JSON
OK  detail_records value_coverage_pct: 100.0%
OK  baseline invariants hold (7 checked)
```

### E. Official 44-state Playwright dashboard sweep
```
$ bash scripts/run_dashboard_sweep.sh tests/dashboard_sweep.js
states swept: 44  |  failing: 0  |  total JS errors: 0
```

### F. Publication-boundary checks
| Check | Result |
|---|---|
| `dashboard/data.js` parses as valid JSON | PASS |
| No raw `NaN` token | PASS |
| No `Infinity` token | PASS |

### G. Git working-tree cleanliness
```
$ git status --short
(empty)
```
Local `main` fast-forwarded cleanly to `c83011b`; no local modifications.

### H. Unexpected tracked-file mutation check
```
$ git diff --stat cd8b033 HEAD -- . ':!dashboard/data.js' ':!dashboard/index.html' \
    ':!scripts/build_dashboard_data.py' ':!docs/PR_193_PRODUCTION_CERTIFICATION.md' \
    ':!tests/test_pr193_reconciliation.py' ':!tests/test_primary_channel_correction.py'
(empty)
```
No file outside the 6 expected ones changed.

---

## Business reconciliations, re-run against `main`

| Control | Source | Expected | Actual | Variance | Tolerance | Result |
|---|---|---|---|---|---|---|
| **FY26 Primary Channel**: MT+EB2B+SIS | `primary.by_channel` (fy26) | 32,900.36 L (certified FY26 baseline) | 30,684.99 + 1,965.20 + 250.17 = **32,900.36 L** | 0.00 L | ±0.01 L | **PASS** |
| — cross-check vs article-wise source | `detail_meta.channel_totals.FY26` | `{MT:30684.99, EB2B:1965.2, SIS:250.17}` | identical | 0.00 L | ±0.01 L | **PASS** |
| **Category/Pack**: displayed NSV | Sum of `detail_records` grouped by Category | 55,138.75 L (= sum of all `detail_records`) | **55,138.75 L** | 0.00 L | ±0.01 L | **PASS** |
| **Reliance**: sum of zone NSV | Sum of Reliance Retail records grouped by Zone | 13,702.51 L (= Reliance Retail total across all `detail_records`) | **13,702.51 L** | 0.00 L | ±0.01 L | **PASS** |
| **Inventory Health**: Total Offtake KPI | `offtake.total_fy27` vs `sum(offtake.monthly_fy27)` | 19,044.99 L | 19,044.99 L (monthly sum: `[3588.51, 4019.42, 3840.46, 3621.47, 3975.13]`) | 3.6×10⁻¹² L (float noise) | ±0.01 L | **PASS** |

All four reconciliations are numerically identical to the pre-merge certification (`docs/PR_193_PRODUCTION_CERTIFICATION.md`), confirming the merge carried the exact certified data through unchanged.

---

## Known limitations (unchanged, still governed separately — not re-litigated here)

- **Issue #195 — `KI-OFFTAKE-001`**: ~0.08% variance in the "Top Chains by Offtake" table from a stale-FY fallback on ~4 long-tail chains. Confirmed pre-existing, does not affect the certified Inventory KPI above. Target: the canonical financial-truth architecture work, not a standalone fix.
- **Issue #194**: `github-advanced-security` CI check fails on GitHub's own Copilot backend (`CAPIError: 400 The requested model is not supported`) — infrastructure, not a required check, not a dashboard defect. Reproduced identically on two separate CI runs before merge; not re-checked post-merge as it is orthogonal to `main`'s content.

No new limitations were found during post-merge certification.

## Unexpected behavior

None observed. Every check that passed pre-merge passed identically post-merge; every reconciliation is bit-for-bit consistent with the pre-merge run.

---

## Final verdict

```
POST-MERGE CERTIFICATION — PR #193
[PASS] Pre-merge verification (head SHA, state, required checks, no unresolved conversations)
[PASS] Merge executed against exact certified SHA (expectedHeadSha pinned)
[PASS] Python compile
[PASS] Full test suite (191 passed, 1 pre-existing governed skip)
[PASS] tests/test_pr193_reconciliation.py (12/12)
[PASS] ci_validate_datajs.py
[PASS] 44/44 browser sweep states, 0 JS errors
[PASS] Publication boundary (valid JSON, no NaN, no Infinity)
[PASS] Git working-tree clean
[PASS] No unexpected tracked-file mutation
[PASS] Channel reconciliation
[PASS] Category reconciliation
[PASS] Reliance reconciliation
[PASS] Inventory KPI reconciliation
[GOVERNED] Issue #194 (infrastructure, non-blocking)
[GOVERNED] Issue #195 (KI-OFFTAKE-001, non-blocking, targeted at future architecture work)

VERDICT: PRODUCTION BASELINE CERTIFIED
```

**`main` @ `c83011b82d1f3b1e6f1c2a21c12aed91ea9c5cf7` is the certified production baseline as of 2026-09-24T01:32:01Z.**

Per the fail-closed rule, no further action is taken automatically. No new feature work, dashboard UI change, or canonical-architecture work begins from this session until this report is reviewed.
