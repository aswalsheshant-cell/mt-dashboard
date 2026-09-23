# Post-Merge Certification — Design

**Created:** 2026-09-23, Phase 17.2 of "Production Acceptance & Certified Baseline
Lock." **This is a design document only.** No workflow file is created by this
document; implementation requires explicit human authorization and a separate PR,
per this phase's own rule ("Do not implement until the design and impact analysis
are complete").

## Why this is needed

Today, certification happens **on the PR head SHA**, before merge. The actual
`main` SHA that results from the merge is a *different* commit (a merge commit, or a
fast-forward) that has never itself been directly certified — only inferred to be
safe because its parents were. This session's own Phase 13 ("final main
certification") had to be done **manually**, by checking out `main`, re-running every
gate by hand, and writing up the result in conversation — a one-off, human-triggered
reconstruction, not a repeatable, automated control. That is the gap this design
closes.

## Trigger

```yaml
on:
  push:
    branches: [main]
```

Fires on every commit that lands on `main` — merge commits from PRs and (if ever
used) direct pushes alike. This is deliberately **not** `pull_request` — a
post-merge gate must certify what's actually on `main`, not a PR's speculative merge
preview.

## What it must run (mapped to this session's actual 17-point gate)

| # | Check | Existing implementation to call | New code needed? |
|---|---|---|---|
| 1 | Clean checkout / repository integrity | `git status --short` (trivially always clean on a fresh Actions checkout — retained for symmetry with the manual gate, not because it can fail in CI) | No |
| 2 | Zero conflict markers | `grep -rn '^<<<<<<<$|^=======$|^>>>>>>>'` over tracked text files | No — a 3-line shell step |
| 3 | Valid JSON | `python3 -c "..."` extracting `window.DASH` and `json.loads()` — already the exact logic in `scripts/ci_validate_datajs.py:load_datajs equivalent` and `scripts/validate_historical_baseline.py:load_datajs` | No, reuse `scripts/validate_historical_baseline.py`'s `load_datajs()` |
| 4–5 | No NaN / Infinity | Not currently a standalone script — this session ran an inline recursive scan in Python each time | **Yes — extract this session's inline NaN/Infinity scan into a small reusable script** (e.g. `scripts/ci_check_no_nan_inf.py`), the one piece of genuinely new code this design calls for |
| 6 | Required financial structures present | `scripts/ci_validate_datajs.py` | No |
| 7–8 | Primary / Offtake reconciliation | `scripts/ci_validate_datajs.py`'s baseline-invariant check against `config/baselines.json` | No |
| 9–10 | FY coverage / historical baseline integrity | `scripts/validate_historical_baseline.py` | No |
| 11 | No silent missing-as-zero | `pytest answer_governance/` (TD-01/03/04/05's own regression coverage IS this check) | No |
| 12 | No duplicate financial truth | `scripts/ci_validate_datajs.py`'s `metadata`-vs-`meta` WARN (already present, already zero on current main) | No |
| 13 | Allocation governance | `alloc.governance` fields already read by `scripts/ci_validate_datajs.py`; FM-19's "not force-applied" invariant has no dedicated automated check today — **documented gap, not fabricated as covered** | Partially — no dedicated script exists; recommend `tests/test_chain_allocation_no_fabrication.py` (already exists, already in `pytest tests/`) as the closest real coverage, not a new invention |
| 14 | Failure-mode register integrity | `grep -c '^| FM-' docs/FAILURE_MODE_REGISTER.md` + conflict-marker check (same as #2) | No |
| 15 | No accidental tracked-file mutation | `git diff --stat <previous-certified-SHA>..HEAD` — **requires storing the previous certified SHA somewhere the workflow can read it** (see "Open design question" below) | Small — needs a state store |
| 16 | Publication contract validity | `grep -c 'window\.DASH\s*=' dashboard/data.js` (already in `validate-promo-data.yml`'s `validate-dashboard` job) | No |
| 17 | Full required test suite | `pytest tests/ answer_governance/` | No — **this is the single highest-value addition**, since (per the Phase 17.1 audit) neither suite runs in any CI workflow today |

## Output contract

The job's final step prints and uploads (as a workflow summary and a JSON artifact)
exactly the fields the prompt specifies:

```json
{
  "CERTIFICATION_STATUS": "CERTIFIED | BLOCKED",
  "CERTIFIED_SHA": "<git rev-parse HEAD>",
  "TEST_RESULT": "<passed>/<skipped>/<failed> from the pytest run",
  "FINANCIAL_DRIFT_STATUS": "NONE | <n> unexplained",
  "GOVERNANCE_STATUS": "<count of FM-NN rows still OPEN, informational only>",
  "BLOCKED_ITEMS": ["<list, empty if CERTIFIED>"],
  "CERTIFICATION_TIMESTAMP": "<UTC ISO8601>"
}
```

`FINANCIAL_DRIFT_STATUS` is the one field that cannot be fully automated without the
open design question below being resolved first — see next section.

## Open design question: what does a post-merge run compare against?

Item #15 and `FINANCIAL_DRIFT_STATUS` both require a **known-good previous SHA** to
diff against. Three options, not decided here (this is exactly a
"genuine business/engineering decision" this design should surface, not silently
pick):

1. **Compare against the immediate parent commit** (`HEAD~1` for a fast-forward, or
   the merge base for a merge commit). Simple, always available, but only proves "no
   drift versus the last commit" — a slow drip of small, individually-explained
   changes could still accumulate unnoticed over many merges.
2. **Compare against a persisted "last certified SHA" value** (e.g. a file such as
   `config/certified_baseline.json` containing `{"sha": "...", "certified_at": "..."}`,
   updated by this same workflow on every CERTIFIED result). This directly answers
   "has anything drifted since the last time we called this certified?" — closer to
   what this session's own Phase 14 did (`95fcfb5` → `e0d4ceb`). Requires the workflow
   to have write access to commit that file back to `main` after a successful run, or
   to a separate branch/artifact.
3. **No stored baseline; report absolute state only** (JSON validity, NaN/Infinity,
   baseline invariants, etc.) without a diff-based drift check at all. Simplest,
   weakest — loses the "explain every line that changed" property this session's own
   certification pass relied on most heavily.

**Recommendation (not authorized to implement): option 2**, using a new
`config/certified_baseline.json` file as the state store, written only by this
post-merge job on a CERTIFIED result — mirroring `config/baselines.json`'s existing
pattern of "declared, versioned, reviewable in a diff" rather than inferred.

## Non-negotiables this design preserves

- **No git tags or releases** — the JSON artifact and workflow summary are the
  record; nothing here proposes a tag.
- **Fails closed** — any BLOCKED item stops the `CERTIFICATION_STATUS` at BLOCKED;
  no partial-credit "CERTIFIED WITH WARNINGS" state.
- **No silent override** — if this job is ever red on `main`, it does not
  auto-revert, auto-fix, or auto-retry; it reports and stops, exactly like every
  other gate in this session's own governing rules.

## Implementation is NOT authorized by this document

This is a design and impact analysis only. Turning it into
`.github/workflows/post-merge-certification.yml` requires a separate PR, explicit
human sign-off on the open design question above, and — if option 2 is chosen — a
decision on write-back permissions (a workflow that commits back to `main` is a
meaningfully bigger change to this repo's governance surface than anything else in
this certification pass, and should be reviewed as such).
