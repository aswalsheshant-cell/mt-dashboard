# Repository verification map

Which command proves which claim in this repository. Run from the repo root on a fresh
checkout of the branch being verified. Every command below is the repo's own; this file
only indexes them — when a workflow changes, the workflow file wins.

## Claim → proving command

| Claim | Command | Pass looks like |
|---|---|---|
| Python pipeline compiles | `python -m py_compile scripts/build_dashboard_data.py` | exit 0 |
| Unit and integration tests | `python3 -m pytest tests/ -q` | `0 failed` |
| Script-level tests | `python3 -m pytest scripts/ -q` | `0 failed` (note any file excluded and why) |
| Canonical financial truth | `python3 -m pytest tests/canonical/ -q` and `python3 scripts/canonical_gate_checks.py <gate>` for each gate in `.github/workflows/canonical-financial-truth-gate.yml` | every gate prints PASS |
| Governed baselines unchanged | `python3 scripts/ci_validate_datajs.py` | `baseline invariants hold` |
| Historical baseline | `python3 scripts/validate_historical_baseline.py` | exit 0 |
| MT channel reconciliation | `python3 scripts/mt_channel_reconciliation.py dashboard/data.js` | exit 0 (exit 2 = BLOCKED; currently CB-01, non-blocking in CI by design) |
| Dashboard renders every tab × FY | serve `dashboard/`, then `node tests/dashboard_sweep.js` | `failing: 0`, `total JS errors: 0` |
| Smoke + governed baselines in browser | serve `dashboard/` on 8080, then `node tests/smoke_dashboard.js` | `SMOKE TEST PASSED` |
| Any JS regression test | `node tests/test_<name>.js` (dashboard served on 8899) | `0 failed` |
| Skill suite valid | `python3 skill-suite/scripts/validate_skills.py` | `VALIDATION PASSED` |
| Installed skills match canonical | `python3 skill-suite/scripts/sync_skills.py --check` | `OK` |
| Workbook sanity (read-only) | `python3 scripts/xlsx_qc.py <book.xlsx>` | exit 0 PASS / 1 FAIL / 2 named error |

Browser tests launch Chromium through `tests/browser_launch.js`
(`PW_CHROMIUM_PATH` > Playwright bundle > `$PLAYWRIGHT_BROWSERS_PATH/chromium`).

## "Nothing else changed" checks

```bash
git diff --name-only origin/main...HEAD             # scope of the change
git diff --quiet origin/main -- dashboard/data.js config/ PowerBI/ && echo unchanged
git diff --quiet <tested-head> origin/main && echo "merged tree == tested head"
```

## Known CI signatures (verify each time; do not assume)

| Check | Signature in the job log | Label |
|---|---|---|
| `github-advanced-security` | `CAPIError: 400 The requested model is not supported`, raised at session creation before any scan | BLOCKED_ENVIRONMENT (CB-09) |
| Production Acceptance Gate → MT channel reconciliation step | `VERDICT BLOCKED` with Rs 11.64 Cr eB2B+SIS | PRE_EXISTING, governed as CB-01; step is `continue-on-error` by design |

## Dependency matrix template (interacting PRs)

| Setup | Suite A | Suite B | data/config/PowerBI |
|---|---|---|---|
| current `main` | | | unchanged |
| `main` + PR-1 | | | |
| `main` + PR-2 | | | |
| `main` + PR-1 + PR-2 | | | |

Build each row in a scratch `git worktree` from `origin/main`; never push a trial merge.

## Attribution

The four disciplines in `SKILL.md` — evidence before claims, root cause before fix,
failing test first, and technical (not performative) handling of review feedback — are
adapted from the MIT-licensed *superpowers* skill collection by Jesse Vincent
(skills: verification-before-completion, systematic-debugging,
test-driven-development, receiving-code-review). They were rewritten for this
repository's commands, governance and status labels; no upstream file or script was
copied.
