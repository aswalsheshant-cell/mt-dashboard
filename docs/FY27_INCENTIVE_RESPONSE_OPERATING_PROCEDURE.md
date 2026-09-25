# FY27 Incentive — Response Operating Procedure

Generated 2026-09-25 (Phase 3B). This is the step-by-step procedure for turning
one real Leadership or Finance response into a governed, auditable record —
from the moment a reply arrives to the moment (if ever) the decision closure
gate reads `READY_FOR_SHADOW_CALCULATION`. It contains no real decisions and
is safe to read/share; the restricted register it describes lives only in the
gitignored `incentive_working/` directory.

**The one rule that governs everything below:**
**do not interpret an ambiguous response. If it's unclear, the outcome is
`CLARIFICATION_REQUIRED` — never a best guess.**

---

## The 10 steps

### 1. Receive the human response

A reply to `incentive_working/target_scope_decision_pack.md`'s outreach
email arrives — by email reply, in a meeting, or (least preferred, because
it's least durable) verbally reported by someone who attended. Save the
original: the email itself, a screenshot, or meeting minutes. **A response
that exists only in someone's memory or a chat message that later
disappears is not a governed response** — it needs a durable, referenceable
record before step 5.

### 2. Confirm sender / decision owner

Check the response came from the person actually named as `Decision_Owner`
(or `Consulted_Owner`, for Finance's D1B/RES-01 half) in
`incentive_working/FY27_INCENTIVE_DECISION_REGISTER.md` — not a delegate
replying on their behalf without an explicit handoff, and not a reply-all
from someone outside the decision chain. If the response comes from someone
other than the named owner, get explicit confirmation the owner has
delegated this specific decision before treating it as authoritative.

### 3. Map the response to the allowed enum

Every decision has a small, fixed set of allowed tokens (see the register
or `scripts/incentive_control/models.py`'s `REQUIRED_DECISIONS`). Read the
actual reply text and ask: does it map cleanly to exactly one of these
tokens?

- **Yes, unambiguously** → proceed to step 4 with that token.
- **No, or it could mean more than one thing** → do NOT guess. Record the
  decision as `CLARIFICATION_REQUIRED` (step 5's `--status
  CLARIFICATION_REQUIRED`, no `--selected-response`) and go back to the
  sender with the specific allowed tokens, asking them to pick one
  explicitly. This is not a failure of process — a reply like "yes, go
  ahead" against a 5-option enum is genuinely ambiguous and deserves a
  clarifying follow-up, not an inference.

### 4. Store the evidence reference

Before touching the register, decide what the `evidence_reference` string
will be — a short, stable pointer back to the original response (e.g. an
email subject + date, `"email-2026-10-01-nc01-response"`, or a meeting-notes
document link). This is what someone re-verifying the register a year from
now will follow back to the source. Never reuse one decision's evidence
reference for another — the validator treats identical evidence across
different decisions as a "duplicate approval record" smell and will refuse
to persist it (see `scripts/incentive_control/validator.py`).

### 5. Enter the decision in the restricted register

Run the ingestion helper — the **only** sanctioned way a response enters
the register. Never hand-edit the JSON directly.

```bash
python3 scripts/record_incentive_decision.py \
  --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json \
  --decision-id NC-01 \
  --status APPROVED \
  --selected-response H1_ONLY \
  --approved-by "<the real named approver>" \
  --approval-date 2026-10-01 \
  --evidence-reference "email-2026-10-01-nc01-response"
```

For an ambiguous reply (step 3's "no" branch):

```bash
python3 scripts/record_incentive_decision.py \
  --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json \
  --decision-id TG-03 \
  --status CLARIFICATION_REQUIRED \
  --notes "reply said 'probably fine' -- does not map to an allowed token, asked for clarification 2026-10-01"
```

The helper itself will refuse (exit code 4) if the response isn't one of
the decision's allowed tokens, the approval date is malformed, or any
required field is blank — so a mistake here fails immediately, not later.

### 6. The helper runs the validator automatically

`record_incentive_decision.py` re-validates the **entire** register (not
just the one row you changed) before writing anything to disk. If your
change would make the file schema-invalid, create a duplicate evidence
reference, or otherwise break consistency, it prints `FAIL_VALIDATION` (or
`FAIL_SCHEMA`) and the file on disk is **not modified** — you'll see the
exact problem printed and can fix the input and re-run. You do not need to
run `scripts/validate_incentive_decisions.py` separately as a normal part
of this flow; it's still there for a standalone spot-check any time.

### 7. The helper runs the closure gate automatically

After a successful write, the helper prints the current overall gate
state (`Closure gate: BLOCKED_LEADERSHIP_DECISION`, etc.) so you see
immediately whether this response changed the overall picture — without a
separate command. For a full multi-decision snapshot at any time (not just
right after one update), use:

```bash
python3 scripts/incentive_readiness_report.py \
  --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json
```

### 8. Resolve conflicts

If D1A (Leadership's intended basis) and D1B (Finance's source
confirmation) are both `APPROVED` but disagree, the gate reports
`BLOCKED_BASIS_CONFLICT`. **Do not pick a winner.** Go back to both parties
jointly — this needs a resolution conversation between MT Leadership and
Finance, not a unilateral call by whoever is recording decisions. Once they
agree, record the agreed value on whichever side needs to change, as a
normal approval (step 5) — or, if a side that was already `APPROVED` needs
to change, as an **amendment** (see below).

### 9. Preserve audit evidence — never silently overwrite an approval

If an already-`APPROVED` decision's response needs to change (a
correction, a follow-up call that reversed the earlier answer), the helper
requires **both** `--reason` and a **new** `--evidence-reference` (not the
original one reused):

```bash
python3 scripts/record_incentive_decision.py \
  --register incentive_working/FY27_INCENTIVE_DECISION_REGISTER.json \
  --decision-id NC-01 \
  --status APPROVED \
  --selected-response H2_PENDING \
  --approved-by "<approver>" \
  --approval-date 2026-10-05 \
  --evidence-reference "email-2026-10-05-nc01-correction" \
  --reason "corrected after follow-up call on 2026-10-04 -- original reply was based on an outdated plan"
```

Without `--reason` and a genuinely new evidence reference, the helper
refuses (`AMENDMENT_REQUIRED`, exit code 3) rather than silently changing
history. The prior approval is preserved in that decision's
`revision_history` array — nothing is deleted.

### 10. Determine whether shadow calculation is unlocked

Run the readiness report (step 7) after each new response. The overall
line reads one of:

```
READY_FOR_SHADOW_CALCULATION
BLOCKED_LEADERSHIP_DECISION
BLOCKED_FINANCE_INPUT
BLOCKED_BASIS_CONFLICT
BLOCKED_MAPPING
BLOCKED_BUSINESS_DEFINITION
```

Only `READY_FOR_SHADOW_CALCULATION` means every required decision is fully
approved and D1A/D1B agree. Anything else means the incentive engine
remains correctly blocked — not an error, the expected state until every
required decision lands. **Reaching `READY_FOR_SHADOW_CALCULATION` is not,
by itself, authorization to calculate a real payout** — that is Phase 3C's
own separate gate (shadow calculation → reconciliation → Business/Finance
review → only then payout readiness).

---

## What never happens in this procedure

- No script infers a Leadership or Finance decision from historical data,
  achievement percentages, or any other number.
- No script sets `current_status` to `APPROVED` on its own — every field
  in an approval comes from an explicit command-line value, supplied by a
  person.
- No ambiguous reply is ever silently mapped to "the closest-sounding"
  token.
- No approved decision's response is ever changed without a reason and new
  evidence.
- No partial set of approved decisions is ever handed to a calculation
  layer — `extract_approved_rules()` (in
  `scripts/incentive_control/business_rules.py`) refuses outright unless
  every required decision is fully approved and compatible.

## CI / branch-protection recommendation (Phase 3B, STEP 12)

The CI check introduced in Phase 3A — **"Incentive Decision Control Gate:
schema + validator + closure gate (synthetic)"**
(`.github/workflows/incentive-decision-gate.yml`) — is a good candidate for
a **required** GitHub branch-protection status check on `main`:

- Its job name is unique and stable.
- It runs only against synthetic fixtures (`tests/fixtures/incentive_decisions/`)
  and explicitly asserts `incentive_working/` is absent from the CI
  checkout before running anything — no secret or restricted data is ever
  required to pass it.
- It fails closed: a schema break, a validator regression, or a gate-logic
  regression in this framework makes the check fail, not silently pass.

Making it required needs repository Settings access this session doesn't
have. The exact manual step for a repo admin:

**Settings → Branches → branch protection rule for `main` → "Require
status checks to pass before merging" → add "Incentive Decision Control
Gate: schema + validator + closure gate (synthetic)".**

Optionally, enabling "Require branches to be up to date before merging"
(strict mode) on the same rule ensures this check always runs against the
PR's latest merge with `main`, not a stale base — consistent with how this
repo's other narrowly-scoped gates (`assumption-coverage-gate.yml`,
`canonical-financial-truth-gate.yml`) are already set up to run on every
relevant PR.
