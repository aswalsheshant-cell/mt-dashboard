# Dashboard unit integrity and shared-agent handoff — design

Date: 2026-10-03. Status: design for owner review; no implementation or blocker clearance is asserted.

## Intended outcome

The HTML dashboard and Power BI model must report the same value when they use the same source rows, metric, FY/month, channel scope, and unit. Primary, distributor secondary, and Offtake are different business measures and must not be forced to equal one another. No source row, file, historical mapping, or approved value may be removed or altered to make a reconciliation pass. A corrected display number may change only with a source-to-output explanation. Differences are recorded with lineage and left visible until explained.

This design also gives Claude Code and ChatGPT/Codex one shared, durable handoff contract. Git and the live PR/CI state remain authoritative; a human owns merge and business approvals.

## Evidence already observed

- The main branch is 84864ce4076164aee5cbc79493bb7f086743eb90. The Claude branch claude/youthful-carson-vzv9hh is four commits ahead at 853e01d1d450dab11e4ce34e7c2c4ebfd96d8132, with no PR. It changes HTML FY filtering, Power Query FY derivation, DAX, QuickSetup, and tests. The attachment ends during an unfinished Offtake NSV unit investigation.
- PowerBI/docs/DataDictionary.md says model currency amounts are stored in absolute rupees. PowerBI/PowerQuery/11_Fact_OfftakeSales.pq currently renames source NSV to Offtake NSV without scaling. PowerBI/DAX/01_CoreMeasures.dax divides that measure by 100,000 or 10,000,000 for lakh/crore display. The attachment's sampled source-to-MRP ratio suggests the Offtake source NSV is in lakhs; this is a hypothesis until source-level reconciliation confirms it.
- PowerBI/PowerQuery/43_SecondarySalesEfficiency.pq divides Offtake NSV by Primary NSV and labels both lakh, but Primary Article is treated as rupees. PowerBI/DAX/14_SecondarySales_Measures.dax divides Secondary NSV Lakh by Total Primary Article NSV. These ratios require same-unit proof.
- PR #291 is a draft B5 runner PR. Its Windows runner has not been proven against a live Desktop engine. B5 remains BLOCKED_PENDING_DESKTOP_EVIDENCE. Any model-affecting fix requires fresh Desktop evidence for the resulting model.
- PR #119 is frozen at 51487b6, pending the #120 owner mapping register; PR #267 is a draft HOLD pending Finance's formal reference and seven alias decisions. Neither is a vehicle for this work.

## Chosen approach and rejected alternatives

Normalize each imported currency column at a documented Power Query boundary after proving its source unit. Keep dashboard/data.js on its existing lakh contract, and compare against Power BI after explicit unit conversion. Correct DAX ratios only where one operand has a different declared unit. This preserves one semantic contract for model values in rupees.

Do not change display divisors to conceal an import mismatch, relabel rupees as lakhs, scale a source CSV in place, or change source totals. Do not merge the Claude FY branch wholesale before reviewing its four commits and validating the generated QuickSetup and dashboard outputs.

## Work sequence and gates

### 1. Prove source units and reconcile

Build a read-only matrix for each relevant source and metric: source file/column, row count, raw sum and unit, transformed sum and unit, HTML value, Power BI query/measure, FY/month, channel scope, and delta after unit alignment. Use at least one row-level NSV-to-MRP plausibility check and complete month totals for available overlapping months. Verify the source file hashes and row counts before and after. Check Offtake, Primary Article, Primary ShipTo, distributor secondary, and all unit-bearing sell-through or gap calculations. Record any missing period or unmatched scope as NOT_COMPARABLE, never as zero.

Acceptance: every comparison on the same basis reconciles to the documented reporting precision (normally 0.01 lakh), or is listed as an unresolved discrepancy with source and cause. Raw-source totals and row counts remain unchanged. Do not proceed to a scaling edit on a plausibility ratio alone.

### 2. Correct the minimal boundary and dependent consumers

From fresh main, create a focused worktree/branch for the proven correctness fix. Scale only columns demonstrated to be lakh-valued when entering the rupee-valued Power BI model. Make the transformation explicit and idempotent for each supported input format; fail clearly when the input unit cannot be established. Review dependent ratios, percent labels, expected baselines, and QuickSetup generation. Preserve the Reliance Brand Counter Offtake-only exclusion and the existing FY rule. Keep the HTML pipeline's current unit convention unless stage 1 finds an independent HTML defect. Do not alter approved mappings, source data, or historical evidence.

Acceptance: regression checks pin source-to-model totals, consistent units in every numerator/denominator, unchanged source hashes/row counts, and matching same-basis HTML/Power BI reporting values. A changed number must have a source-to-output explanation; no unexplained difference is accepted.

### 3. Validate and publish evidence without clearing B5

Run targeted unit and reconciliation tests, full affected CI gates, generated-file consistency checks, and browser FY-state checks. Open the resulting model in Power BI Desktop, refresh it, and capture live B5 evidence using the governed run sheet and approved runner state. Keep failures and NOT_RUN rows visible. A screenshot, raw results, exact SHA, Desktop version, and evidence file belong to the review record. B5 remains blocked until its documented exit condition and human decision are met.

### 4. Add the shared handoff protocol separately

Create root AGENTS.md with agent-neutral instructions and keep docs/PROJECT_STATE.md as the existing narrative state file. config/project_state.yml remains the machine-readable blocker/PR state. If a root PROJECT_STATE.md is needed for discovery, it is a pointer only; it must not duplicate status values.

Each handoff records repository, branch/worktree, full HEAD SHA, clean/dirty state and checkpoint, PR/issue, exact scope, files allowed/forbidden, unresolved decisions, tests/evidence and their SHA, next authorized action, and merge restriction. One agent writes to a branch/worktree at a time. On return, the agent fetches and reconciles Git, PR, CI, and state files before editing. All PRs start as drafts under the feature-freeze classification. Business approvals cannot be inferred from code or CI. No merge without the owner's explicit instruction.

## Older PR disposition

PR #119 remains frozen; do not rebase, rewrite, cherry-pick, or modify its evidence. Its provisional Rs 9,455.1997 lakh mapping bucket needs the #120 owner register before governance promotion. PR #267 remains HOLD; its source amount and received treatment decision do not supply the missing formal approval reference or seven alias decisions. Do not merge or reuse its provisional monthly allocation as governed CM2.

## Isolation, review, and rollback

Use separate branches/PRs for the unit correction and the handoff protocol. Do not add either to PR #291, #119, or #267. Review the Claude FY branch independently before selecting any of its changes. The unit fix PR must show before/after same-basis totals and a file-level no-deletion report. A rollback reverts only its code commit; it never rewrites source data or frozen evidence.
