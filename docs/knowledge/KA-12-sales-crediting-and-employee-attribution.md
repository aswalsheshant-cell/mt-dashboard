# KA-12 — Sales Crediting & Employee Attribution

| Field | Value |
|---|---|
| Topic_ID | KA-12 |
| Purpose | Credit a store's sale to the right employee, without double counting and without treating a name match as an identity. |
| Applicable_Agents | fmcg-decision-leader, sales-data-reconciliation, business-ai-automation |
| Trigger_Conditions | sales credit, attribution, who owns this store, employee actuals, split credit |
| Source_Type | Recognised industry body (compensation governance) |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | Yes — identity approval and crediting policy are business decisions |
| Confidence | HIGH |

## Authoritative sources
- WorldatWork — sales compensation practice: account assignment, reassignment and sales
  crediting must be explicit, including split credit where more than one seller influences
  the sale.

## Key principles
- **Employee ID is the identity. A name is only a candidate.** Never promote a name match
  to a production identity without a named owner's approval.
- Credit flows `transaction -> store -> approved ownership -> employee -> role -> period`.
  Break the chain at the first missing link and say which link broke.
- **Never discard value you cannot attribute.** Unattributed value stays in the
  reconciliation under its own class, so the total still ties.
- A field hierarchy (advisor, supervisor, lead, regional manager) is several credit lines
  over the same store, not a split of one pot. Reconcile **within** a role; never add
  across roles — that multiplies the same sale by the number of levels.
- Whether a level earns full or shared credit is a **crediting policy**, set by the
  business. An analyst may model it; an analyst may not choose it.
- A population with no ownership row may be correct by design (a chain with no deployed
  staff) or a gap. Name the population and ask; do not assume either.

## Recommended pattern
Classify every unattributed amount, rather than dropping it:

| Class | Meaning |
|---|---|
| `ATTRIBUTED` | Approved Employee ID exists; credit posted |
| `UNATTRIBUTED_PENDING_APPROVAL` | One clean candidate, waiting on a signature |
| `AMBIGUOUS_IDENTITY` | More than one plausible person |
| `INVALID_SOURCE_PERSON` | Source value is not a usable person |
| `SOURCE_POPULATION_MISSING` | No candidate exists in the employee master |
| `ROLE_NOT_STAFFED` | Store covered, but that role is vacant |
| `STORE_NOT_IN_OWNERSHIP_SHEET` | Store has sales but no ownership record |

Attach a **value** to every pending approval. "Please approve 28 mappings" is ignorable;
"these 28 signatures release Rs 64.0 L of RKAM credit" is actionable.

## Anti-patterns
- Summing role credit lines into a company total.
- Auto-assigning the single candidate because there is only one.
- Dropping unmapped stores so the numbers look clean.
- Fuzzy-matching names across zones to raise the match rate.

## Project application
`scripts/build_actual_attribution.py` credits DMS store actuals (`TotalTertiaryValue`,
the established measure) through the WoA sheet. Apr-26 to Jul-26, Rs 14,118.82 L over
1,147 stores:

| Role | Pending approval (Rs L) | Ambiguous | Missing population |
|---|---:|---:|---:|
| RKAM | 6,398.95 | – | – |
| SO Name | 4,999.78 | 71.2 | 1,328.0 |
| BA Lead | 4,375.06 | – | 2,023.9 |
| BA Supervisor | 0.00 | 289.5 | 5,804.4 |

All four roles reconcile to the source total with a zero difference. **Zero identities are
approved**, so nothing is credited yet — every figure above is what a signature releases.

Largest single blocker is not identity: **Rs 7,535.62 L (53%) sits in 445 D-Mart stores
that have no WoA row at all**, plus Rs 184.25 L in 164 stores with no client type.

## Project limitations
Contribution/split percentages are not set. Credited actual is only produced for an
approved identity, and `Contribution_Pct` reads `CREDITING_POLICY_REQUIRED` until Finance
and MT Leadership set the rule.

## Related project files
- `scripts/build_actual_attribution.py`
- `incentive_working/employee_actual_attribution.csv`
- `incentive_working/actual_attribution_reconciliation.csv`
- `incentive_working/woa_approval_value_at_stake.csv`
- `incentive_working/actuals_outside_woa_coverage.csv`
