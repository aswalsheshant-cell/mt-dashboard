# Inputs, joins and tracker output

These are required logical fields, not an instruction to replace existing file schemas. Map existing headers explicitly and preserve raw inputs.

| Input | Key fields and checks |
|---|---|
| Scheme/slabs | Version, approval evidence, effective dates, Role Group, Designation, Frequency, Metric, Slab Name, Min Ach %, Max Ach %, Amount %, Payout Amount, Condition Type; normalized operators/precision and component-combination rules |
| Employee master | Employee_ID as text, HR designation, approved Incentive_Grade, role group, zone/account, joining/leaving dates, eligibility and effective dates |
| Targets | Period, basis, unit, component, scope/ownership key, target and allocation approval; compatible grain before attribution |
| Actuals | Transaction/store/account/product identifiers as text, business date, basis, signed value, unit and provenance; duplicates and returns controlled |
| Ownership | Employee_ID, role, store/account/territory, effective interval, mapping approval and approved full/shared-credit rule |
| Decision register | Current schema, decision owner, status, selected response, evidence, approval date and content integrity; use repository validator |
| Payment/approval | Employee-period-component or approved summary key, rule version, amount, approval ref and distinct payment ref |

The observed slab input is flattened, with Designation as a column. A matrix with designations as headers requires an explicitly validated mapping; do not guess a converter. Multiple local files with similar names may contain different subsets, so choose by scope and evidence, not by newest filename.

## Row key and reconciliation

Use (Employee_ID, effective assignment segment, period, component, scheme version). Aggregate compatible segments under the approved employee-period rule. Resolve duplicate identities or overlapping assignments before joining. Ensure join multiplicity cannot repeat the same target or actual within a role.

Source actual = attributed + each mutually exclusive unresolved/out-of-scope bucket, with an explicit residual. Reconcile within each role and source period. The same store can appear in several hierarchy roles; those are alternative role credit views, not additive company sales. Approved share percentages apply only inside the relevant policy-defined pool.

## Detail tracker fields

Run_ID; Source_As_Of; Fiscal_Year; Quarter; Period_Start; Period_End; Period_Completeness; Employee_ID; Incentive_Grade; Role_Group; Assignment_Scope; Component; Frequency; Measurement_Basis; Unit; Target; Actual; Achievement_Pct_or_Rate; Metric_Definition_ID; Gap_To_Target; Tracking_Status; Scheme_Version; Slab_Rule_ID; Rule_Source; Incentive_Readiness; First_Blocker; Other_Blockers; Shadow_Amount; Calculation_Trace; Approval_Status; Payment_Status; Evidence_Reference.

Add employee names only to restricted outputs when needed. Do not publish per-person achievement or payouts to the general dashboard. Export should preserve IDs as text, amounts as numbers, dates as dates and missing amounts as blank/null.

Track per-component statuses and coverage counts before aggregating. Designation summaries group only matching component/basis/unit/period scopes. Do not sum percentages, add different measures, or average individual achievement percentages. Show ready/blocked/not-eligible counts independently of valid-zero counts. Summary outputs may contain no private person-level information when shared broadly.

Store records in the existing restricted incentive_working area or approved private output path. Version source hashes, policy and calculation logic; reruns with identical inputs must be identical apart from run metadata. Changes to prior periods generate an amendment trail instead of rewriting the certified result.

## Channel scope evidence

For RKAM primary overall/emerging tracking retain Channel_Scope_Rule, Canonical_Channel, Source_Channel_Field, Target_Scope_Already_Filtered, Eligible_Target, Eligible_Actual, EB2B_Excluded_Target/Actual, SIS_Excluded_Target/Actual, Unresolved_Channel_Target/Actual and exclusion evidence. Apply the user’s RKAM EB2B/SIS exclusion symmetrically; preserve NKAM inclusion. These are logical fields mapped to the existing output contract, not permission to replace its schema.
