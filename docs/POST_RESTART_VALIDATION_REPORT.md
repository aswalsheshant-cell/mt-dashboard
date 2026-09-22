# Post-Restart Validation Report

Run: 2026-09-21, after a container restart. Per the resume notification, the
restart terminated only in-flight background wait-loops (pytest/build runs
already reported and acted on before the restart) — no committed work was
lost. This report independently re-verifies that claim rather than trusting
it.

## Repository State

- **Branch:** `feat/account-chain-yoy-intelligence`
- **HEAD SHA:** `ea1f753e6af9cf606b82ba110964e1155a429c00`
- **Upstream SHA:** `ea1f753e6af9cf606b82ba110964e1155a429c00`
- **HEAD matches upstream:** Yes (identical SHA — 0 ahead, 0 behind)
- **Working tree before validation:** Clean, 0 untracked files
- **Working tree after validation:** Clean, 0 untracked files (confirmed after every command below, not just at the end)

No discrepancy from the expected state was found, so no history investigation, reset, or checkout was needed.

## Validation Executed

| Suite | Command | Passed | Failed | Skipped | Warnings |
|---|---|---|---|---|---|
| Python syntax | `python -m py_compile scripts/build_dashboard_data.py` | ✅ Clean | 0 | — | 0 |
| Backend full suite | `python3 -m pytest scripts/ tests/ -q --ignore=scripts/test_json_serialization.py --ignore=tests/smoke_dashboard.js` | 450 | 0 | 30 | 1 (pre-existing pytest deprecation warning, unrelated to this repo's logic) |
| Baseline invariants | `python3 scripts/ci_validate_datajs.py` | 7/7 checks | 0 | — | 1 (pre-existing, documented — see below) |
| E2E / browser (CI-authoritative) | `npx playwright test tests/e2e_v1.1.0_consolidation.spec.js --project=chromium` | 13 | 0 | 0 | 0 |
| Browser sweep (supplementary, not CI) | `SWEEP_PORT=8899 node tests/dashboard_sweep.js` | 44/44 states | 0 | — | 0 JS errors |

**Explicitly not run**, and why: `scripts/sync_data_js.py` / `scripts/ci_validate_master.py` (the `validate-data.yml` workflow) — that workflow's own header comment states it validates a retired, non-production pipeline (`data_master.json` → `sync_data_js.py`) that is not how `dashboard/data.js` is actually generated (`build_dashboard_data.py` is the sole generator per `CLAUDE.md`). Running it would validate the wrong pipeline and risk a false finding.

**No `data.js` rebuild was performed.** Nothing changed since PR #167's certified build; rebuilding would only introduce non-deterministic noise (timestamps, float rounding) for no informational gain.

### Two apparent problems, both investigated and resolved as non-issues

1. **Backend suite initially reported "failed, exit code 1."** Investigated: the pytest run itself completed with "450 passed, 30 skipped" (visible in its own output); the exit code 1 came from a `grep -i "skills_loader"` I chained after it, which found no match in the quiet-mode (`-q`) log (individual test names aren't printed in `-q` mode) and returned its own exit 1 — the last command in the chain, so its exit code was what got reported for the whole background task. Confirmed via `pytest --collect-only` that `tests/unit/test_skills_loader.py` (21 tests) is real, collected, and included in the "450 passed" count. **Classification: ENVIRONMENTAL (my own command chaining), not a test failure.**
2. **E2E suite initially failed all 13 tests** with `browserType.launch: Executable doesn't exist at /opt/pw-browsers/chromium_headless_shell-1243/...`. Investigated: this repo's `@playwright/test@1.63.0` expects browser revision `1243`; only revision `1194` (`chromium`, `chromium_headless_shell`) is pre-installed in this environment. Per this repo's own environment guidance ("if a project pins a different @playwright/test version, launch with executablePath instead of downloading"), re-ran with a temporary out-of-repo config (`/tmp/pw_override.config.js`, never committed) pointing `launchOptions.executablePath` at `/opt/pw-browsers/chromium`. Result: 13/13 passed. **Classification: ENVIRONMENTAL (browser-binary/Playwright-version skew in this container), not a product regression.** No `npx playwright install` was run (network-download path, explicitly disallowed here).

## Certification Comparison

Baseline: `docs/PR167_PHASE1_CERTIFICATION.md`, certified 2026-09-20 at this exact same HEAD SHA (`ea1f753`) — this is not a different commit to reconcile against, it is the same commit, re-verified after the restart.

| Area | Previous Certified State | Current State | Difference | Classification |
|---|---|---|---|---|
| HEAD SHA | `ea1f753` | `ea1f753` | None | EXPECTED |
| Backend suite | 450 passed, 0 failed, 30 skipped | 450 passed, 0 failed, 30 skipped | None | EXPECTED |
| Mutation guard | Clean | Clean | None | EXPECTED |
| Browser sweep (`dashboard_sweep.js`) | 44/44, 0 JS errors | 44/44, 0 JS errors | None | EXPECTED |
| Baseline invariants (`ci_validate_datajs.py`) | Not run in PR #167 certification | 7/7 hold, run for the first time this pass | New coverage, not a prior result to diverge from | EXPECTED (coverage addition) |
| `metadata`/`meta` divergence WARN | Not surfaced in PR #167 cert (that pass didn't run this script) | WARN present | Pre-existing, already documented in `docs/DATA_AVAILABILITY_MATRIX.md` before either certification pass; unrelated to PR #167's or #166's changes | ENVIRONMENTAL / pre-existing, not new |
| E2E Playwright suite (`e2e_v1.1.0_consolidation.spec.js`) | Not run in PR #167 certification (that pass used only `dashboard_sweep.js`) | 13/13 passed, after an environment browser-binary workaround | New coverage; the one hiccup along the way was container-specific, not code | EXPECTED (coverage addition), workaround classified ENVIRONMENTAL |
| `github-advanced-security` GitHub check | Failed — confirmed platform-side model-routing crash before reading the diff (job id `106137808424`) | Not re-checked in this pass (no new commit pushed; same PR, same head) | None expected — would need a fresh GitHub API check to confirm it re-fired cleanly on a later push, not applicable here since nothing was pushed | ENVIRONMENTAL, unchanged since no new commit exists to re-trigger it |

No REGRESSION, DATA CHANGE, or unresolved UNKNOWN entries.

## Root Cause Classification

Every difference above traces to one of: intentional new validation coverage this pass added (`ci_validate_datajs.py`, the real E2E suite), a pre-existing and already-documented data hygiene note, or an artifact of how I chained shell commands / this container's browser-binary version — never a code or business-logic change, since none was made in this session.

## Governance Checks

- Unexplained failure: **NO**
- Unexplained error: **NO**
- UNKNOWN root cause: **NO**
- Unexpected tracked-file mutation: **NO**
- Silent parser/load failure: **NO**
- Duplicate financial truth: **NO**
- Uncontrolled baseline duplication: **NO**
- Unexplained KPI drift: **NO**
- Invalid JSON: **NO** (`ci_validate_datajs.py` confirms `dashboard/data.js` parses as valid JSON)
- NaN/Infinity at publication boundary: **NO** (44-state sweep asserts this explicitly; found none)
- Silent missing-as-zero financial treatment: **NO** (this is the specific governance property `same_period_block()`'s `comparability` flag exists to prevent — see PR #167's own certification for the edge-case tests proving it)
- Ungoverned Primary allocation: **NO** (not touched this session; `allocate_dist_primary()` and its governance CSVs were untouched by this pass — confirmed via the mutation guard)
- Unauthorized destructive change: **NO** (no reset, force-push, checkout, or history rewrite performed; only diagnostic reads and non-destructive test runs)

## Governed Blockers

None newly introduced by this pass. Two pre-existing, already-documented items carried forward unchanged (not new findings):

1. **ID:** `GB-01`
   **Description:** `data.js`'s `metadata` block diverges from `meta` (the block `index.html` actually reads); `metadata` is written by a deprecated, workflow_dispatch-only pipeline (`scripts/sync_data_js.py`).
   **Evidence:** `ci_validate_datajs.py` WARN, this pass; documented previously in `docs/DATA_AVAILABILITY_MATRIX.md`'s "Known data.js hygiene issue."
   **Owner:** MT Analytics (repo maintainer).
   **Dependency:** None blocking — `meta` is authoritative and correct; `metadata` should eventually be retired per `docs/PROJECT_STATE.md`'s recommendation.
   **Business impact:** None currently (no UI reads the stale block).
   **Next action:** Out of scope for this pass; tracked in `docs/PROJECT_STATE.md`.

2. **ID:** `GB-02`
   **Description:** `github-advanced-security` check on PR #167 shows `failure`, confirmed to be a GitHub-side Copilot model-routing crash (`SessionModelError: 400 The requested model is not supported`) that occurred before the diff was ever read.
   **Evidence:** Job log for job id `106137808424` (see `docs/PR167_PHASE1_CERTIFICATION.md` §9).
   **Owner:** GitHub platform (external dependency, not this repo).
   **Dependency:** Will re-fire automatically on the next push to the branch; a manual re-run was attempted and rejected by GitHub's API (`403 This workflow run cannot be retried`).
   **Business impact:** None — the other 16 required checks on PR #167 are green, and this check never evaluated the code either way.
   **Next action:** No action needed unless it recurs after a future push; if so, re-investigate rather than assume it's the same transient cause.

## Verdict

**`BASELINE CONFIRMED WITH GOVERNED BLOCKERS`**

Evidence: HEAD matches upstream exactly; working tree clean before and after every validation command; backend suite, baseline invariants, and both browser test suites all pass with zero unexplained failures; every apparent problem along the way (the grep exit code, the browser-binary mismatch) was investigated to a specific, non-code root cause rather than dismissed. The two governed blockers (`GB-01`, `GB-02`) are pre-existing, already documented, and non-blocking to any current deliverable — they do not represent new risk introduced by this pass, which is why the verdict is "confirmed with blockers" rather than "not confirmed."
