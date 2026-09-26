# Decision classification

Every recommendation this skill labels gets exactly one of these five. The label is the
answer; everything else is support for it.

| Label | Means | Requires |
|---|---|---|
| **GO** | Evidence is validated, owner has approved (or approval isn't required), no material risk is unaddressed | A validated number/mapping (governed, or PASS from `sales-data-reconciliation`), a named owner, a stated validation criterion |
| **GO WITH CONDITIONS** | Proceed, but a specific, named condition must hold or be tracked | The condition itself, who checks it, and by when |
| **HOLD** | The honest answer is "not yet" — an input is still provisional, a gate hasn't cleared, or the pre-mortem surfaced something unresolved | Naming exactly what is pending and what would clear it (never "more analysis needed" with nothing specific attached) |
| **ESCALATE** | Two required parties disagree, or the decision would cross a boundary this repo's own governance already drew | Naming both positions and the specific boundary or disagreement, not just "this is above my pay grade" |
| **REJECT** | Evidence contradicts the proposal, or the risk is unacceptable relative to the upside | The specific evidence or risk that rejects it, not a vague "too risky" |

## Worked calibration (from this repo's own history)

- **PROVISIONAL_BUSINESS_MAPPED_PRIMARY (₹9,455.1997L), pre-owner-sign-off** → **HOLD**.
  The methodology is validated (16/16 reconciliation, 25/25 tests), but the *mapping
  itself* has not cleared its own gate (owner approval). Calling this GO because the
  pipeline is clean would conflate "the code is right" with "the business number is
  approved" — exactly the failure mode this skill exists to prevent.
- **D-Mart-Offline ambiguity, before root-causing it** → looked like it needed
  **ESCALATE** (a material, ₹629.9L chain-identity question). After root-causing it to a
  script defect (Direct rows keyed off the wrong column), it became a **GO** — fix and
  ship, no owner alias decision needed. The label changes when the evidence changes, not
  when the stakes look high.
- **May'26's 86-row PO Type anomaly (₹1.4237L)** → **HOLD** on classifying those rows as
  Direct or Dist., permanently, until the source owner confirms — a small rupee amount
  does not justify inferring a business fact from a pattern. Correctly reconciling it into
  `UNALLOCATED_PRIMARY` was itself the GO (ship the honest classification).
- **The ₹9,455.51L transcription error** → the underlying run was a legitimate GO (all
  gates cleared); the *report* was not, because it wasn't reproducible from source. The
  fix was a control (`historical_primary_chain_backfill_report.py`), not a re-decision —
  a reminder that "GO" applies to the decision and its evidence, and a hand-typed number
  is not evidence.

## Anti-patterns to catch before labelling

- Labelling GO because the technical pipeline is clean, while a business approval is
  still open. These are two different gates — see CLAUDE.md's own note on this project:
  "provisional status must never leak into reporting as governed actuals."
- Labelling HOLD indefinitely with no named blocker, as a way to avoid a REJECT or an
  ESCALATE that would be uncomfortable to state.
- Labelling ESCALATE for something a five-minute root-cause check would resolve (see the
  D-Mart-Offline calibration above) — escalate the disagreement, not the unexamined
  symptom.
