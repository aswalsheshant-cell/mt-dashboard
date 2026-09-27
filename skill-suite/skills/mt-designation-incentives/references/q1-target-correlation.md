# Q1 target correlation: sales team through Analyst

Use this reference when asked to link targets, reconstruct Q1 achievement or reconcile sales-team targets through Analyst. Correlation here means target lineage and reconciliation, not a statistical correlation coefficient.

## Historical evidence and limits

On 2026-09-27, read-only inspection of local Q1 Incentive for MT team.xlsx found Raw_Data columns J = Target, K = Actual, L = Chase plan. The user confirmed FY27 Q1 as April–June 2026. The workbook has NKAM, RKAM, BDO_BDE and Analyst outputs and an embedded flattened Slab_Master. Treat it as historical calculation evidence; input presence does not establish scheme approval, employee grade or Finance sign-off. Re-inventory the current execution environment instead of repeating a stale “all inputs missing” matrix.

The observed target relationship is Incentive_Target = 0.90 × Chase_Plan. Formula rows explicitly use =L[row]*90%; populated NKAM target literals also reconcile to this relationship. The snapshot has one RKAM emerging row without chase/actual, so this does not establish complete coverage. Preserve imported historical targets. Apply 90% prospectively only with period-specific approval evidence; do not silently recalculate every target from this historical pattern.

The historical Analyst overall target, actual and chase plan each equal the sum of the five NKAM overall source rows. Analyst emerging target, actual and chase likewise equal the five NKAM emerging source rows. This establishes a numeric Q1 relationship, not an approved reporting hierarchy or proof that account scopes never overlap. Validate the account/channel/brand perimeter before using that roll-up for a different file or period. RKAM totals in the snapshot differ from NKAM/Analyst and require a bridge, not replacement.

## RKAM channel exclusion supplied by the user

The user explicitly clarified the scope after the Q1 review: for Asst RKAM, RKAM and Sr RKAM, exclude **EB2B and SIS** from both **Primary Sales Overall** and **Primary Sales - Emerging brands** targets and actuals. NKAM retains these channels within its assigned scope. Apply it as the working RKAM scope rule and record its provenance through the existing incentive decision procedure. Target scope belongs to MT Leadership (KA-13): the agent does not treat this instruction as that approval, fabricate HR/Finance sign-off or mark unrelated decisions closed. Apply it to the Q1 reconstruction and retain it as the RKAM scope rule; preserve explicit effective dates and later amendments for subsequent periods.

- Classify source records by a verified canonical channel mapping. Trim whitespace and normalize case for EB2B/SIS; map other labels only from evidence. A parent Channel=MT value is insufficient if EB2B/SIS are recorded under Format, subchannel or an account master. Unknown classifications stay unresolved rather than silently included.
- Filter the matching target, chase plan and actual populations **before** aggregation, target-factor application and achievement calculation. Within emerging, apply both the approved emerging-brand basket and the channel exclusion. Remove signed actuals including returns for excluded channels consistently.
- RKAM eligible target = sum of target records outside EB2B/SIS in the assigned scope. Eligible actual = sum of actual records outside EB2B/SIS in that same scope. Achievement = 100 × eligible actual / positive eligible target. Preserve missing/invalid target handling.
- Preserve already excluded or already adjusted targets: do not subtract EB2B/SIS twice or apply the 90% factor twice. Keep input scope and adjustment flags with evidence. An aggregate employee target without a channel split cannot be safely reduced using actual-sales proportions; obtain the target allocation instead.
- Keep NKAM target and actual records for EB2B/SIS. Do not apply the RKAM exclusion globally to the source dataset, NKAM or Analyst. Analyst's existing channel scope remains unchanged by this instruction.
- Reconcile RKAM gross scoped totals = eligible totals + EB2B excluded totals + SIS excluded totals + unresolved-channel totals, separately for target, actual and chase, using non-overlapping buckets. Unknown values are not zero. Show excluded amounts and the remaining residual. Compare RKAM to an NKAM comparator filtered to the same channel, brand, period and assignment perimeter; preserve the full NKAM view separately.
- Previously reported RKAM totals and percentages were unfiltered historical source aggregates. They are **not validated under this clarified scope**. Recalculate from classified detail before presenting a corrected RKAM percentage. The exclusion explains a required scope difference; it does not prove that it explains every numerical discrepancy.

## Target lineage and two denominators

1. Identify approved chase-plan source, incentive-target source and any adjustment/relaxation rule independently. A target file named Q1 is not necessarily the incentive-target source.
2. Match fiscal period, component, basis, unit, account/territory/channel, brand basket and effective assignment before joining by Employee_ID. Where employee-level input has no scope IDs, mark the scope bridge unresolved rather than inventing account allocations.
3. Retain Chase_Plan, Approved_Target_Factor (if evidenced), Incentive_Target, Target_Source, Target_Rule_Evidence and Target_Adjustment_Residual. For this historical comparison only, residual = recorded target − 0.90 × chase. Missing chase leaves residual unknown.
4. Show both Chase_Achievement_Pct = 100 × actual / positive chase and Incentive_Achievement_Pct = 100 × actual / positive incentive target. Label denominators. Never apply the 90% reduction to actuals, or reduce an already adjusted target again. A factor of 0.90 makes incentive achievement equal chase achievement / 0.90; it is not “plus ten percentage points.”
5. Sum compatible amounts, then divide. Overall and emerging are separate components; emerging is normally a subset of overall and must not be added to overall sales. Use the repository's business-confirmed emerging rule (all brands except Mamaearth, `docs/PROJECT_STATE.md`, confirmed 2026-09-11) unless a period-specific scheme document names a different basket; record which basket was applied.

## Role-to-target bridge

| View | Target and actual linkage | Period treatment |
|---|---|---|
| BDO/BDE/Sr BDE | Employee-assigned sales target; approved split primary NSV from transaction-level credit | Monthly payout assessment; complete April, May and June separately before a full-quarter tracking summary |
| Asst/RKAM/Sr RKAM | Approved territory/account scope for overall and emerging components, excluding EB2B and SIS from targets and actuals | Quarter aggregate from compatible scope; no automatic sum of overlapping staff/territories |
| Asst/NKAM/Sr NKAM | Approved key-account scope for overall and emerging components, retaining EB2B and SIS | Quarter aggregate; account uniqueness/shared-credit rules must reconcile |
| Analyst | Approved channel-wide overall and emerging perimeter | Historical Q1 matches NKAM aggregate; establish scope before adopting this as a continuing rule |

These are alternative attribution views over underlying sales. They do not form an additive BDO + RKAM + NKAM + Analyst chain. Reconcile each view to its own approved perimeter. Full credit at multiple role levels is not an error if policy allows it; counting those views together as company sales is an error.

For BDO splits, retain source-row identity, the employee key, approved contribution and split NSV. Check source NSV = assigned NSV + unassigned/excluded mutually exclusive buckets + residual. Validate blank/zero/unassigned IDs; do not normalize contribution percentages or treat parsing failures as zero without the approved rule. Transaction source rows may produce multiple employee rows, so deduplicate on the appropriate source-row/employee/assignment key, not just invoice number.

## Reconciliation output

For each role/component/period show source target, mapped target, unmapped target, source actual, mapped actual, excluded/unassigned actual and residuals. All buckets must be mutually exclusive within that view; distinguish approved exclusions from unexplained differences. For an Analyst–NKAM tie-out, compare target, actual and chase independently. For an RKAM–channel difference, attribute it to documented population, ownership, date, return, brand or unit differences; leave the remainder unresolved. Do not invent a balancing target.

Display Source_Status (absent / found / parsed / coverage-incomplete / reconciled) separately from Tracking_Status and Incentive_Readiness. A historical actual/target reconstruction may be shown as historical and unapproved while live scheme basis remains undecided. It must not be represented as current scheme achievement or bypass existing workbook gates.

## Observed Q1 exceptions to test again

- Raw_Data rows 4–31 contain April sales and 32–59 June sales for 28 records each. No May primary-sales rows are present in this table. Do not label April+June as complete Q1 or assume other sheets also lack May.
- Rows 60–87 contain focus-pack entries with no numeric target or actual; their Period Type says Monthly although Period is Q1. Resolve metric/frequency and applicability, including Sr BDE, before calculation. The quarter scope of the top-up is decision C2 (CONFLICT): outside Q1 return `RULE_BLOCKED_C2`; inside Q1, C2 is not a reason to block, but missing measurements and C5 still are. Do not mark C2 APPROVED because Q1 is being evaluated.
- RKAM emerging rows 94–99 include one missing actual/chase. Do not replace it with zero or publish a full-population achievement from incomplete actuals.
- The designation output tabs contain stored achievement values in the inspected populated rows, not live achievement formulas. Rebuild from source inputs and compare the stored result; a cached value is not recalculation evidence.
- Embedded Slab_Master and the separately found INCENTIVE SLAB.xlsx are candidate sources. Compare versions and approvals before choosing; do not declare them interchangeable.

## Acceptance cases

- Synthetic chase 100, target 90, actual 99 => chase achievement 99%, incentive achievement 110%; no second target reduction.
- April and June supplied, May absent => two valid monthly observations, incomplete Q1; no full-quarter award inference.
- Analyst and NKAM totals equal numerically but ownership scope unapproved => numeric tie-out passes, scope approval remains unresolved.
- RKAM differs from channel => explain/reconcile the residual; do not replace either total automatically.
- Missing emerging actual => full-population achievement unavailable; show coverage and separately labelled known actual subtotal.
- Same sale credited to BDO, RKAM and NKAM => independent role checks; company total includes the sale once.

- Synthetic channel targets/actuals: eligible 100/90, EB2B 20/30, SIS 10/20 => RKAM 100/90 and 90% achievement; NKAM matching full scope 130/140 and 107.6923077%. Repeat with an emerging-brand subset and verify both filters apply.
- A target already excludes EB2B/SIS => preserve it; verify its evidence and exclude only the matching actual population.
- Missing channel classification or aggregate target without a split => disclose unresolved scope; no invented proportional reduction.
