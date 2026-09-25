# FY27 Incentive Platform — V1 Completion Scorecard

Tracks progress toward V1 closure for the FY27 Modern Trade incentive
platform. Updated at each phase-C milestone (decision closure, shadow
calculation, reconciliation, acceptance, sign-off). This file carries no
restricted data — no employee names, no compensation figures, no
approver identities. Those live only in `incentive_working/` (gitignored)
and in the operating-procedure doc's described channels.

## Definition of Done (V1)

V1 is complete only when every item below is true. None may be assumed,
inferred, or marked done by this session on its own authority.

- [ ] Required Leadership decisions = 100% closed
- [ ] Required Finance decisions = 100% closed
- [ ] Decision closure gate = `READY_FOR_SHADOW_CALCULATION`
- [ ] Real shadow calculation completes successfully
- [ ] Population reconciles: Total = Calculated + Approved Exclusions + Not Applicable + Blocked + Governed Unmapped, difference = 0
- [ ] Financial value reconciles: Approved Measurement Base = Calculated Base + Governed Exceptions, difference = 0 within an explicitly approved tolerance
- [ ] UNKNOWN financial logic = 0
- [ ] Silent missing-to-zero transformations = 0
- [ ] Unauthorized fallback paths = 0
- [ ] Unresolved material mapping issues = 0
- [ ] Critical tests = PASS
- [ ] Production acceptance gate = PASS
- [ ] Finance / Leadership review evidence recorded
- [ ] No restricted employee or compensation data committed to git
- [ ] V1 scope frozen (SHA, register version, data cutoff, calc/schema/test versions recorded)

## Current status (as of 2026-09-25, main @ `efce6239c2d8f55fa503db6dd62f79cad31355d5`)

| Metric | Value |
|---|---|
| Decision closure | 0/12 = 0% (0/10 Leadership, 0/2 Finance) |
| Population reconciliation | N/A — not started, gated behind decision closure |
| Financial reconciliation | N/A — not started, gated behind decision closure |
| Mapping completeness | N/A — evaluated only at shadow-calculation time |
| Test pass rate | 56/56 = 100% (`tests/incentive_control/`) |
| Critical blockers | 12 open decisions (0 technical blockers) |
| Controlled exceptions | 0 (exception register not yet created — Phase C6 not started) |
| Post-v1 items | 0 (see `docs/POST_V1_BACKLOG.md`) |
| **Overall status** | **RED — blocked on human decisions** |

Overall status legend: `RED` = blocked · `AMBER` = shadow validation in
progress · `GREEN` = V1 ready for signoff · `CLOSED` = signed off and frozen.

## Decision closure detail

Owner counts and gate state, read directly from
`incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json` via
`scripts/incentive_readiness_report.py` — never hand-transcribed.

- **Leadership:** 0/10 approved — NC-01, TG-01, TG-02, TG-03, TG-04, TG-05, GRAIN-01, DM-01, BASUP-01, D1A
- **Finance:** 0/2 approved — D1B, RES-01
- **Basis conflicts (D1A vs D1B):** 0 — neither side has answered yet
- **Clarifications outstanding:** 0
- **Gate state:** `BLOCKED_LEADERSHIP_DECISION` (readiness-report exit code 3)

The decision pack for Leadership and Finance is
`incentive_working/target_scope_decision_pack.md` (gitignored, sent
outside this repo).

## Phase status

| Phase | Status |
|---|---|
| Foundation (canonical truth, governance, CI, Phase 3A/3B) | COMPLETE — merged (`9dc011d`, `efce623`) |
| C1 — Human decision closure | IN PROGRESS — 0/12 |
| C2 — Real response activation | NOT STARTED (waiting on C1) |
| Gate C — Shadow calc authorization | BLOCKED |
| C3 — Real shadow calculation | LOCKED |
| C4 — Population reconciliation | LOCKED |
| C5 — Financial reconciliation | LOCKED |
| C6 — Exception register | LOCKED |
| C7 — Materiality / blocking review | LOCKED |
| C8 — Shadow output QA | LOCKED |
| C9 — Finance / business review pack | LOCKED |
| C10 — Final acceptance gate | LOCKED |
| C11 — Business signoff | LOCKED |
| C12 — V1 freeze | LOCKED |

## How to re-check this scorecard

```bash
python3 scripts/incentive_readiness_report.py \
  --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json
```

Update the "Current status" table above whenever that command's output
changes — never by assumption between runs.
