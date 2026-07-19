# Agent Operating Principles — frozen reference

**Status: frozen.** Do not rewrite these unless a test in
`agent/tests/test_agent_principles_acceptance.py` (or an equivalent
behavioral test) identifies a specific defect. If a principle needs to
change, change it here first, then update whichever `.claude/agents/*.md`
file enforces it — never let the two drift into different interpretations.

This is the reference; the enforcement lives in the subagent definitions.
Each row below names the exact section that implements it, so compliance
can be checked by reading two files instead of re-deriving intent from
memory.

## The 10 principles + golden rule

| # | Principle | Enforced in |
|---|---|---|
| 1 | Every workflow is a system: input → validation → processing → decision → output → QC → feedback → continuous improvement | `pbi-workflow.md` §"The system, not just the steps" (entry/exit table); `mapping-auditor.md` §"Method, in order" |
| 2 | A process is a collection of smaller systems — each with one responsibility, each validating its own output before passing data on | `pbi-workflow.md` entry/exit table ("A stage that fails its exit condition stops the chain there"); `mapping-auditor.md` step 3 ("Auto-resolve only what's evidence-backed") |
| 3 | Think in systems, not tasks — ask what system you're in, its objective, dependencies, and what can fail | `pbi-workflow.md` §"Before you run anything: name the outcome, not the task"; `mapping-auditor.md` §"Before you touch anything: what deliverable does this serve?" |
| 4 | Desired output drives the process — identify the final deliverable, success criteria, and business objective before deciding how to execute | Same two sections as #3, plus the Report format sections requiring the run be checked against the stated outcome |
| 5 | Never optimize the wrong process — priority order: accuracy > business relevance > reliability > automation > speed | `pbi-workflow.md` §"Priorities when they conflict"; `mapping-auditor.md` §"Priorities when they conflict" (verbatim in both) |
| 6 | Break complexity into independent systems, each with entry and exit criteria | `pbi-workflow.md` entry/exit conditions table |
| 7 | Every system needs feedback — did the output match the objective, what failed, what should improve, should business rules update | `pbi-workflow.md` Report format item 5 ("Feedback close-out"); `mapping-auditor.md` Report format closing paragraph — both wired to the real `agent/index/worklog.jsonl`, not a separate invented log |
| 8 | AI amplifies systems, not chaos — verify business rules, data reliability, standardized inputs, and measurable outputs before automating | `pbi-workflow.md` §"Trust the input before you trust the pipeline"; `mapping-auditor.md` §"Method, in order" step 1 (search/verify before resolving) |
| 9 | Creativity is not a substitute for discipline — critical thinking and testing over cleverness | `mapping-auditor.md` §"Trust nothing you haven't checked against real distinct values" (the Reliance store-explosion incident, encoded as a rule) |
| 10 | Build for repeatability — standard inputs/outputs, validation, error handling, audit logs, version control, documentation | `pbi-workflow.md` / `mapping-auditor.md` §"Never commit or push unless explicitly told to in this run"; worklog schema in `agent/mtagent/worklog.py` (`input_hashes`/`output_hashes`/`stage_results` — see below) |

**Golden rule:** start with the desired business outcome, design the
smallest reliable systems required to achieve it, validate every step,
measure every result, learn from every execution, and continuously
improve the system. Never optimize a process that fails to deliver the
intended outcome.

## Evidence, not assertion

A principle is not "compliant" because this document cites where it's
written down. It's compliant when a test exercises the actual behavior
and the result is recorded. See
`agent/tests/test_agent_principles_acceptance.py` for the rule-to-test
matrix and its evidence artifacts (reconciliation reports, distinct-value
sanity checks, worklog entries, reproducibility hashes).

## Companion document: judgment and release control

`agent/policies/AI_LEVERAGE_AND_JUDGMENT.md` extends this document with
rules this one didn't cover: activity vs. outcome, `CLARIFICATION_REQUIRED`
as a distinct run status, business validation as a precondition for `PASS`,
materiality filtering, and the `DRAFT` / `VALIDATED` / `APPROVED_FOR_SHARING`
release gate for anything meant to leave the working team. Enforced by
`agent/mtagent/controller.py` (outcome gate, `CLARIFICATION_REQUIRED`) and
`agent/mtagent/validators/` (`outcome_gate.py`, `business_validation.py`,
`materiality.py`, `release_gate.py`) — see
`agent/tests/test_outcome_gate.py`, `test_business_validation.py`,
`test_materiality.py`, `test_final_summary.py`, and `test_release_gate.py`
for the behavioral proof.

## Lessons from the June'26 backlog run (kept as memory, not just history)

Real findings from running the Backlog Orchestration + Traceability Matrix
skills (`agent/mtagent/backlog/`) against this repo. These are operational
insights, not new principles — each one is now also enforced or referenced
concretely below so it survives past this session's context.

1. **"Decided" is not "implemented" until the file is re-read.** A business
   decision confirmed in conversation (e.g. "Apollo Healthco → Apollo") is
   not verified until traced to the actual master file — and the file's
   spelling can look different from how the decision was worded without
   that being a real problem. Real example: `ChainMaster.csv` has
   `RMT-Sancus` (hyphen) and `Azorte`/`Reliance` (not the originally
   worded `RMT Sancus`/`Reliance Azorte`/`Reliance Retail`) — re-checked
   2026-07-19 and closed as **PASS**: both are the master's real,
   consistently cross-referenced spelling, just informally worded in the
   original decision text, not a separate unresolved item. No data was
   changed. The lesson isn't "these two are broken" (they aren't) — it's
   "never report a mapping decision as done from memory of the
   conversation; re-read the master file and its cross-references every
   time, because sometimes what you find is a real gap and sometimes it's
   just informal phrasing, and you can't tell which without looking."
   See `mapping-auditor.md` §"Re-verify decided items against the file,
   not the conversation".
2. **A recorded decision can still have an unapplied consequence — and
   "genuinely open" can turn out to just mean "not checked against the
   right source yet."** The Azorte decision included "Business Format:
   SIS," but `ChannelMap_Chain.csv` read "default channel" for a long
   stretch of this project. A first re-check (2026-07-19) concluded this
   was a genuinely unresolved business question, since
   `SIS_Reconciliation.md` itself called Azorte's channel an open, weaker
   hypothesis. That conclusion was itself wrong: once the real June'26
   primary source arrived, its own `Chanel` field showed 100% of the 264
   SIS-tagged rows belonged to Azorte and no other chain — the same
   direct-from-source method `SIS_Reconciliation.md` already trusted for
   the FY26 SIS figure. `ChannelMap_Chain.csv` now reads `SIS`. Lesson:
   "still open" is itself a finding that needs re-checking once more
   evidence exists — don't let an earlier "can't tell yet" harden into a
   permanent conclusion. A decision has three parts (the chain identity,
   its mapping, and every downstream field it implies); checking only the
   first two misses gaps like this.
3. **Environment readiness must be checked for real, every time — never
   assumed from a prior session.** `openpyxl` being listed in
   `requirements.txt` is not evidence it's installed here. Use
   `agent/mtagent/backlog/environment.check_environment()` before relying
   on any optional-dependency check; it verifies via two independent
   signals (package metadata AND an actual import), not one.
4. **When a required package can't be installed (no network in this
   sandbox), build a minimal stdlib-only fallback rather than blocking
   entirely** — e.g. a raw zip/XML `.xlsx` writer when `openpyxl` isn't
   available. Disclose the substitution plainly; don't silently degrade
   quality without saying so.
5. **Default period-status rule (applies to any month, not just June'26):**
   a month is treated as **Provisional/Partial** by default the moment its
   data is loaded, and only becomes **Final/Closed** on an explicit
   business declaration (a stated date, a source file's own "final" flag,
   or a direct instruction) -- never inferred from the calendar alone
   (e.g. "it's past month-end" is not sufficient; distributor/secondary
   feeds often lag). Enforced by
   `agent/mtagent/validators/business_validation.period_completeness_check()`.
6. **A missing input is not a coding problem, and sometimes the input
   later shows up.** When June'26 source files don't exist in the working
   environment, the correct action is to name the exact missing file and
   stop — not to simulate, estimate, or reuse a different period's data.
   This is `CLAUDE.md`'s "No dummy data" rule, confirmed again at the
   audit-orchestration layer. Update 2026-07-19: June'26 **secondary**
   data was then supplied directly in chat (not a file upload) --
   transcribed verbatim to a real file
   (`PowerBI/RawDataFolders/Secondary_Distributor_Monthly/`), validated
   (row counts, chain-name cross-reference), and used to compute a real
   Cont% table. June'26 **primary** is still missing, so applying that
   Cont% to allocate primary is still correctly blocked -- a partial
   unblock does not mean treating the whole gap as closed.

## Worklog schema (feedback + repeatability evidence)

`agent/mtagent/worklog.py`'s `log_run()` accepts these fields beyond the
original `command`/`argv`/`status`/`notes` (all optional, backward
compatible — old entries without them still read correctly):

`run_id`, `desired_output`, `success_criteria`, `input_files`,
`input_hashes`, `stage_results`, `reconciliation`, `exceptions`,
`decision_required`, `output_files`, `output_hashes`, `approved_by`.

A worklog entry that only proves *a command ran* is incomplete. One that
also carries `desired_output` + `success_criteria` + `reconciliation` +
hashes proves the command produced the *correct business result* —
that's the difference this schema exists to close.
