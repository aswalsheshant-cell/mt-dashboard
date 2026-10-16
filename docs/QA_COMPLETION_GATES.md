# QC completion gates for source and metric changes

Use this checklist when a change ingests a new month, updates a financial or commercial metric, adds a sidecar, or claims a blocker is closed. It is a test and evidence route, not a new registry. Current blockers remain in `config/project_state.yml` and `config/pending_inputs.yml`; source definitions remain in `config/data_source_registry.yml`.

## Gate 0 — choose the owning source and acceptance rule

Before editing a generator, record the source system, file identity or SHA-256, extraction date, expected period, row grain, signed measure and unit, channel scope, and owner. State the acceptance checks **before** looking at the result. Use `docs/METRIC_REGISTRY.md` for established formulas and `docs/FAILURE_MODE_REGISTER.md` for the earliest wrong layer. A missing extract, a zero in a supplied extract, an exploratory estimate, an unapproved rule, and an unrun Desktop case are separate states.

A source received on a PR branch is proposed evidence until its lineage and scope are reviewed. A status label such as “Received – Done” does not prove month or chain completeness.

## Gate 1 — prove the exact failure with a small regression

Write the smallest test for the observed behavior; make sure it fails for the intended reason before changing production logic. Use a fixture that does not contain confidential raw rows. After the fix, rerun the focused test and the relevant project gates on the **same commit SHA**. An assertion that repeats an implementation detail (for example, merely checking that a formula begins with `SUMIFS`) does not prove the business result.

| Case | Fixture or action | Required result |
|---|---|---|
| Unreadable refresh source | An existing input path that raises `OSError` | The refresh-risk check fails and names the path; it must not return a clean risk list. |
| Blank-dated Primary transaction | A row with value and no invoice date | Ingest fails before writing; source row count and signed NSV include the rejected row in the audit. Only an explicitly identified empty/footer row may be excluded. |
| Primary source control | Workbook with a Summary total that disagrees with transaction sum | Ingest fails before replacing the target CSV; a successful run ties to a named independent control. |
| New EAN on rerun | Run the same month twice with an unknown EAN | Unknown-EAN exception remains open; target-month output is not its own reference. Governed MDM fields remain blank until supplied. |
| Partial Offtake month | At least one chain missing, one zero-row file, and one low but present chain | Each state is reported separately; no missing chain becomes a zero sale or an approved actual. |
| Estimate isolation | One actual row and one exploratory row for the same month | Published totals, trends, QoQ and YoY use actual only by default. Estimate appears in a separate labelled field. Any opt-in combined view is explicitly labelled. |
| Missing middle month | Apr and Jun actuals, no May file | “Months loaded” is 2, not 3; per-month comparisons use observed months or withhold the result. |
| Contribution label | Item H1 change and total H1 change have different denominators | “Share of total growth” uses total growth as denominator. If divided by last year's total, label it contribution to growth in percentage points. |
| Source-side tie | Same unit, period, channel and Brand Counter treatment | PR body, reconciliation file, generated data and export agree to stated tolerance; otherwise explain the exact delta. |

For Excel, inspect the generated formula and the default control-cell value. A Python row-sum test alone does not prove what Excel displays. Keep a small synthetic workbook case that can run in CI even when raw monthly CSVs are gitignored.

## Gate 2 — source completeness and business authority

- **Finance B3/B4:** run the existing allocation and assumption checks; prepare an owner decision pack. Record approver, date, decision, scope and reference only from Finance's returned evidence. Never convert provisional claims or assumptions into approved values because a test passes.
- **Incentives B6:** keep payout disabled until leadership, Finance, MT Ops and HR have resolved target basis, crediting, slabs, grades, caps and proration. Restricted employee inputs stay outside public Git and shared agent memory.
- **Power BI B5:** structural CI is separate from the governed runtime cases in `docs/evidence/B5_RUN_SHEET.md`. Retain case outputs/screenshots and the named exit decision.
- **TDP, promo, audit, stock and OTIF:** request the exact month and grain from the owning department. The existing template, a synthetic sample, PO fill rate, or in-house article focus cannot substitute for Nielsen/RMS TDP, real audit records, stock snapshots or delivery dates.
- **September chain files:** compare tracker status with actual row/store coverage and source hashes. Confirm low-but-present chains with the owner. Rebuild store cuts, TDP and Sales Journey sidecars only from September sources that exist.

## Gate 3 — evidence and release

Record the input hash and row count, transformation command, output hash or aggregate, test command and result, current commit SHA, and remaining delta. Run the existing data-integrity, reconciliation, privacy, browser and Power BI structural checks relevant to the diff. Check the live PR head and its GitHub workflows; a green run from an older SHA is not evidence for the current head. Do not mark a business gate clear from CI, a skill output, or a saved session note.

The repair stays on its owning focused branch. Keep active data-refresh, Finance, B5 and skill changes in separate reviews. Follow `AGENTS.md` for branch ownership and merge decisions.

## Session-memory rule

A handoff may preserve a source pointer, observation date, exact SHA, attempted command, result, open exception, owner and next action. On resume, re-check these against GitHub and the canonical registries. A remembered statement is a lead, not approval or current project state. Do not store confidential rows, credentials or employee identifiers in shared memory.

## Origin of the method

This project-specific checklist adapts ideas from the user-supplied ZIPs: ECC's regression-testing, documentation-governance and verification guidance; Superpowers' failure-first test loop; the official Claude Code review plugin's focus on actionable findings; and scientific skills' practice of setting acceptance criteria before observing a result. These archives were read as reference material only. Their commands, agents, hooks, thresholds and memory runtimes were **not** installed, and none can supply Honasa data or owner decisions.
