# Phase 2A — Post-Merge Certification

**This is the exact rollback and comparison point for Phase 2A**, recorded as a
documentation commit rather than a git tag/GitHub Release — CLAUDE.md's "ZERO GitHub
Releases or Git Tags" rule (merging to `main` is this repo's sole deployment step)
applies here, so this file is the durable marker instead.

```
PR:                #199 (Phase 2A: CHAIN_OFFTAKE_NSV canonical consumer migration)
Merge commit:       de386b50f94b20eba181ccd2748ca56c7fe1a484
Merged into:        main (previously at cafd28def8d5ee3880d6a3b5b2051363b4bdd8c4, Phase 1 / PR #198)
Merged:             2026-09-24
Rollback:            git revert de386b50f94b20eba181ccd2748ca56c7fe1a484
                     (single merge commit; the legacy JS expression is also kept
                     commented in place at dashboard/index.html:1618 for a
                     same-file, no-revert rollback if only that is needed)
```

## Certification result

```
PHASE 2A POST-MERGE CERTIFICATION
Branch: main @ de386b5

Canonical Financial Truth Gate      PASS   (8/8 structural checks, verified locally --
                                             this workflow triggers on pull_request, not
                                             push, so it does not re-run on the merge
                                             commit itself; it was green on the exact
                                             PR HEAD SHA (28ae852) immediately before merge,
                                             with zero code changes introduced by the merge)
Production Acceptance Gate          PASS   (same basis as above -- green on 28ae852,
                                             merge introduced no code changes)
Canonical tests                     96/96 PASS
Full pytest                         287 passed / 1 skipped (pre-existing governed skip)
Browser regression                  44/44 PASS, 0 JS errors
Top Chains validation               FY27 = 31 rankable chains
                                     FY26 = 27 rankable chains
                                     (verified live in a real browser render against
                                     main's actual dashboard/data.js, not just the
                                     automated sweep)
Financial missing-data behaviour    NOT_AVAILABLE != 0                    HOLDS
                                     No fallback substitution (.value/.total/0)  HOLDS
                                     No NaN / Infinity in any canonical value    HOLDS
                                     No UNKNOWN governance state                 HOLDS (0/70)
Push-triggered CI on de386b5        13/13 checks green, including
                                     Deploy to GitHub Pages = success
                                     (this repo's actual production deployment step)

VERDICT: PHASE 2A CERTIFIED ON MAIN
```

## Governance exceptions active in production as of this merge

| ID | Metric | Scope | Status |
|---|---|---|---|
| `GOV-003` | `CHAIN_OFFTAKE_NSV` | CNC/EB2B/Others/Vijetha, FY27 (KI-OFFTAKE-001) | APPROVED_GOVERNED |
| `GOV-005` | `CHAIN_OFFTAKE_NSV` | 8 newly-onboarded chains, FY26 | APPROVED_GOVERNED |

Both fully approved per `scripts/canonical/governance.py`'s self-approval guard
(`approval_status="APPROVED"`, real `approver`/`approval_reference`/`approved_at` on
each entry) — see `docs/CANONICAL_ENGINE_PHASE1_REPORT.md` and
`docs/PHASE2A_CHAIN_OFFTAKE_LINEAGE.md` for full evidence.

## Known, separately tracked items

- **Issue #194** — `github-advanced-security` check failure. Pre-existing, GitHub-side
  infrastructure issue, unrelated to this repo's code. Not a blocker for this
  certification.
- **Issue #200** — `computeChannelHealth()` (`dashboard/index.html:3761`) independently
  exhibits the same class of fallback-to-`.value` defect KI-OFFTAKE-001 documents, in a
  different feature (Operational Alerts' stock-health scoring). Deliberately **not**
  migrated by Phase 2A (scope: exactly one consumer, the "Top Chains by Offtake"
  table). Tracked separately; does not block this certification since it does not
  affect the financial truth this cutover produces.

## Stabilization window

Per plan: the legacy `CHAIN_OFFTAKE_NSV` expression stays in `dashboard/index.html`,
commented but not deleted, for one full monthly reporting cycle after this merge before
any removal is considered. No removal work should start before that window closes
without a specific reason (a reconciliation, UI, or leadership issue surfacing) to act
on early.

## What's deliberately not started by this certification

Per instruction, this record closes out Phase 2A's evidence trail. It does **not**
start Phase 2B (canonical truth enforcement across remaining consumers) or any other
new engineering phase — those begin only on separate, explicit instruction.
