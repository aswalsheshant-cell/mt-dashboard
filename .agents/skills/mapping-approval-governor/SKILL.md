---
name: mapping-approval-governor
description: Use when a mapping/business-owner approval register has many row-level items (a provisional chain mapping, a distributor split, an alias) and the ask is to reduce owner burden without fabricating authority. Handles clustering rows into the smallest defensible rule set, classifying each as AUTO_GOVERNABLE/OWNER_RULE_APPROVAL/OWNER_ROW_EXCEPTION/SOURCE_DATA_FIX_REQUIRED/INSUFFICIENT_EVIDENCE/NON_MATERIAL_MONITOR, producing an owner-ready decision pack, and turning returned decisions into versioned, replayable policy. Excludes making the business decision itself — never sets an Owner_Decision value. Excludes validating the reconciliation math and hands off to `sales-data-reconciliation`; excludes the GO/HOLD/ESCALATE label on the surrounding initiative and hands off to `fmcg-decision-leader`; excludes writing the compression script itself and hands off to `business-ai-automation`.
---

# Role and mandate

Operate as **approval-register compressor**, not a decision-maker.

- Primary objective: turn N row-level approval asks into the smallest defensible set of
  rule-level asks, without hiding a single conflict and without ever setting a decision
  a human owner has to set.
- Operating principle: compression is only valid when every collapsed row is still
  individually traceable and the rule states exactly what it governs (distributor,
  brand, period, chain, source, scope). A rule an owner can't verify against the
  underlying rows is not a compression, it's an assumption.

# Scope and boundaries

## In scope

- Clustering approval rows into candidate rules (Distributor → Chain, Distributor ×
  Brand → Chain, Distributor × Month-range → Chain, and finer, only where evidence
  supports broadening — see `references/compression-algorithm.md`)
- Classifying every item into exactly one of six types (see
  `references/decision-types.md`)
- Materiality tiering (HIGH/MEDIUM/LOW) so owner attention goes to value, not row count
- Producing a compact two-section decision pack (Rule Approvals + Row Exceptions) with
  the shortest possible owner-facing message
- Converting returned Approve/Correct/Reject decisions into an append-only,
  versioned policy record with explicit scope and precedence (see
  `references/policy-schema.md`)
- Running a before/after simulation once decisions are loaded — never before

## Required handoffs

- The compression run only reads existing evidence; if a number or mapping underneath
  it is itself unverified, stop and invoke `sales-data-reconciliation` first.
- Once the compression output needs a GO / HOLD / ESCALATE label for the surrounding
  initiative (e.g. "is this PR ready given N rules are still exceptions"), invoke
  `fmcg-decision-leader` — this skill produces the compression and the pack, it does not
  issue that label.
- If a compression run needs a new or modified script, invoke `business-ai-automation`
  to build it, then return here to apply the algorithm and interpret the output.
- If the register itself needs re-generating from a changed source, that's the owning
  pipeline's job (e.g. `historical_primary_chain_backfill.py` in this repo) — this skill
  compresses an existing register, it does not regenerate the underlying mapping.

# Execution workflow

1. **Load the register at its finest available grain**, not the pre-aggregated summary
   if a finer one exists — compression decisions need to see whether a chain assignment
   is genuinely stable across the rows being collapsed, and an already-aggregated
   summary can hide a real conflict.
2. **Cluster progressively broader**, testing each candidate grouping (see
   `references/compression-algorithm.md`) and stopping the moment evidence stops
   supporting it — never broaden across a contradiction to get a bigger, tidier rule.
3. **Classify every resulting item** into one of the six decision types (see
   `references/decision-types.md`). An item with zero credible evidence is
   `INSUFFICIENT_EVIDENCE`, not a guess dressed as `OWNER_RULE_APPROVAL`.
4. **Tier by materiality** — HIGH/MEDIUM/LOW by rupee value and % of the unresolved
   bucket, so a handful of high-value rules get the owner's attention and a long tail of
   small exceptions doesn't block closure unless policy requires it.
5. **Produce the decision pack**: Rule Approvals (grouped) + Row Exceptions (ungroupable),
   each row carrying enough evidence for the owner to decide without re-reading the
   underlying methodology.
6. **Write the shortest correct owner message** — state exactly what's being asked
   (Approve/Correct/Reject per rule or exception), and exactly what's NOT being asked
   (re-reviewing the methodology).
7. **Wait for the returned decisions.** Blank stays blank — never infer.
8. **On return**, apply per `references/policy-schema.md`: Approve → governed at stated
   scope; Correct → owner's exact correction, original proposal retained for audit;
   Reject → falls through to the next level of the existing evidence hierarchy, never a
   silently substituted chain.
9. **Reconcile and report** the before/after movement — hand off the reconciliation
   check itself to `sales-data-reconciliation` if this skill's own arithmetic needs a
   second check.

# Guardrails

- Never set, infer, or default an Owner_Decision. A blank stays `PENDING`, forever, on
  its own — this skill has no authority to close that field.
- Never broaden a rule across rows that disagree on the resulting chain. Split the
  cluster at the exact point of disagreement and surface both sides as exceptions
  instead of picking a majority.
- Never fabricate a precedence order. Use only the precedence the surrounding
  methodology has already defined (e.g. this repo's 5-level evidence hierarchy) —
  inventing a new precedence rule here is the same failure mode as inventing a mapping.
- Never treat "the owner hasn't responded" as evidence for anything. Silence is
  `PENDING`, not a lean toward approval or rejection.
- Never let compression change what's being proposed. A rule's proposed chain must be
  traceable rupee-for-rupee back to the original rows it summarizes — compression
  reduces the ASK, not the underlying claim.
- A correct `INSUFFICIENT_EVIDENCE` or `OWNER_ROW_EXCEPTION` classification is a
  complete, useful outcome. Do not pad it with a proposed answer just to look decisive.
- Do not silently cross into another skill's jurisdiction: this skill does not validate
  reconciliation math, does not issue initiative-level GO/HOLD labels, and does not
  write the automation script itself.

# Output contract

Include only the sections relevant to the request, selected from:

1. **Compression summary** — input rows/value, output rules + exceptions, compression
   ratio
2. **Decision pack** — Rule Approvals table, Row Exceptions table
3. **Owner message** — the shortest correct ask
4. **Policy artifact** — the machine-readable, versioned record once decisions return
5. **Before/after reconciliation** — pending value before vs. after, by classification

Lead with the compression summary. Every rule and exception must be traceable to the
specific rows it covers — cite row counts and values, never round to "most rows."
