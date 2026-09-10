# Governed policy schema

Once an owner decision returns, encode it as a record in an append-only, versioned
policy file — never overwrite a prior record, never bury the decision back inside a
spreadsheet as the only record of it.

## Fields

| Field | Meaning |
|---|---|
| `RULE_ID` | Stable identifier for this rule or exception |
| `STATUS` | `APPROVED` / `CORRECTED` / `REJECTED` |
| `DISTRIBUTOR`, `BRAND`, `CHAIN` | Scope of the rule. `BRAND` may be `ALL` if the rule was approved at Distributor→Chain scope |
| `VALID_FROM`, `VALID_TO` | The period this rule governs. Never open-ended into the future unless the owner explicitly said so (see Scope, below) |
| `SOURCE`, `SOURCE_HASH` | Where the original evidence came from, fingerprinted (SHA-256) so the record is tied to a specific version of the source |
| `DECISION_OWNER`, `DECISION_DATE` | Who decided, when |
| `DECISION_SCOPE` | One of: THIS_ROW_ONLY / THIS_MONTH_ONLY / THIS_MONTH_RANGE / THIS_DISTRIBUTOR_BRAND / THIS_DISTRIBUTOR_GENERALLY / FUTURE_PERIODS_ALSO |
| `PRECEDENCE` | The evidence-hierarchy level this rule now occupies once governed (use only a precedence order the surrounding methodology already defines) |
| `SUPERSEDES_RULE_ID` | Set when a correction replaces an earlier rule — the earlier record is never deleted, only superseded |
| `COMMENT` | Free text, including the owner's own correction wording verbatim where `STATUS = CORRECTED` |

## Scope defaults to narrowest

`DECISION_SCOPE` defaults to the narrowest reading of what was actually approved. An
approval covering Apr'25-Jul'26 for one distributor does not, by itself, license
applying the same chain to that distributor's Aug'26 primary — `FUTURE_PERIODS_ALSO`
requires the owner to say so explicitly, not an inference from "they'll probably want
the same thing."

## Applying decisions (once, not iteratively)

- **Approve** → the rule's rows move to `GOVERNED` at the stated scope; `PRECEDENCE` is
  set per the existing evidence hierarchy (this repo's methodology: Direct billing >
  approved business mapping > approved single-chain field > approved workbook split >
  secondary-derived fallback > unallocated) — never a precedence invented for this
  policy alone.
- **Correct** → apply the owner's exact correction; retain the original proposed
  mapping in the record (as `COMMENT` or a linked prior `RULE_ID`) so the audit trail
  shows both what was proposed and what was decided.
- **Reject** → the rule's rows do not move to governed. They fall through to the next
  level of the existing evidence hierarchy exactly as if no rule had ever been proposed
  — never silently substituted with a different chain chosen by this skill.

## Precedence discipline

Only use a precedence order the surrounding methodology has already defined. If none
exists for a given context, that absence is itself something to surface to the owner
(as `INSUFFICIENT_EVIDENCE` at the policy level) rather than a gap this skill fills in.
