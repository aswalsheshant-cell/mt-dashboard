# KA-06 — Star Schema & Bridge Tables

| Field | Value |
|---|---|
| Topic_ID | KA-06 |
| Purpose | Model shape for facts, dimensions and genuine many-to-many assignments. |
| Applicable_Agents | mt-powerbi-dax, business-ai-automation |
| Trigger_Conditions | data model, star schema, bridge table, many-to-many, semantic model, grain |
| Source_Type | Official vendor / recognised industry body |
| Access_Date | 2026-09-11 |
| Last_Reviewed | 2026-09-11 |
| Review_By | 2027-03-11 |
| Internal_Approval_Required | No |
| Confidence | HIGH |

## Authoritative sources
- Microsoft Learn — Understand star schema and the importance for Power BI (bridge / factless fact for dimension-to-dimension many-to-many)

## Key principles
- Dimensions describe entities; facts record measurable events.
- Every fact table has ONE consistent grain, stated explicitly.
- A genuine many-to-many between two dimensions uses a bridge (factless fact) table, not a direct relationship.
- Avoid bi-directional filtering unless a specific need justifies it.
- Do not relate unrelated fact tables to each other.

## Recommended pattern
Dim_Employee, Dim_Role_Slab, Dim_Parameter, Dim_Date, Dim_Store, Dim_Account, Dim_Product; Bridge_Employee_Store (and Bridge_Employee_Account only if genuinely many-to-many); Fact_Target, Fact_Actual, Fact_Achievement, Fact_Incentive_Calc, Fact_Approval, Fact_Payout.

## Anti-patterns
- Relating Dim_Employee directly many-to-many to Dim_Store.
- Mixing two grains in one fact table.
- Turning on bi-directional filtering to make a visual work.

## Project application
Our store ownership is genuinely many-to-many (a store can be split across up to 3 officers with Cont% weights), so Bridge_Employee_Store with ContributionPct is the correct shape.

## Project limitations
The bridge must carry the allocation weight; a bare link would lose the Cont% split.

## Related project files
- `PowerBI/docs/DataModel.md`
