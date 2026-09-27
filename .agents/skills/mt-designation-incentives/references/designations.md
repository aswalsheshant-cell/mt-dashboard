# Designation and component map

Observed in local INCENTIVE SLAB.xlsx, Sheet1, header row 3, data rows 4–88: 85 rows and 13 designation keys. This is a dated routing map, not a certification or a permanent rate table. Read the current approved slab workbook each cycle. Source fingerprints: [provenance](source-provenance.json).

| Exact designation keys | Frequency | Components observed |
|---|---|---|
| Analyst | Quarterly | Primary Sales Overall; Primary Sales - Emerging brands |
| Asst RKAM, RKAM, Sr RKAM | Quarterly and Annual | Primary Sales Overall; Primary Sales - Emerging brands; annual rules separate from quarterly rules |
| Asst NKAM, NKAM, Sr NKAM | Quarterly and Annual | Primary Sales Overall; Primary Sales - Emerging brands; annual rules separate from quarterly rules |
| BDO, BDE, Sr BDE | Monthly | Primary Sales |
| BDO, BDE, Sr BDE | Quarterly | Any 1 Focus Pack WoA L3M avg; quarter scope is decision C2 (CONFLICT: text says Q1 only, table annualises four quarters) — outside Q1 return `RULE_BLOCKED_C2` until C2 is approved |
| Sr National BA Ops | Quarterly | MT manned stores offtake target L3M avg; MT - Any 1 Focus Pack WoA L3M avg; MT - BA and Promoter attrition L3M absolute |
| BA Lead - Sr Exec, BA Lead - Asst Mgr | Monthly | GT Secondary target - LM; MT - Outlets above 2 lakhs MRP L3M avg; MT - BA Attrition LM absolute |

## Identity and applicability

Employee_ID is the identity. HR Designation, Role_Group, WoA role column and Incentive_Grade are different fields. An approved mapping connects them for an effective date range. For example, BA_Ops is a group label, not proof that the employee belongs to the Sr National BA Ops slab. BA Supervisor appears in ownership attribution but not as a designation in this observed slab: route it through the BASUP-01 decision instead of borrowing a BA Lead rate.

RKAM territory and NKAM account ownership must come from approved scope mappings. Asst RKAM/RKAM/Sr RKAM overall primary and emerging-brand targets and actuals exclude EB2B and SIS; NKAM retains those channels. Apply the [channel-exclusion procedure](q1-target-correlation.md) before computing achievement. Do not assign company totals to either role by default. The Analyst communication describes channel-level performance, but its exact target perimeter and emerging-brand set still need period-specific evidence. The communication names particular emerging brands; a general dashboard definition is not automatically the same incentive basket.

The absence of an annual component in this snapshot means no annual rule was found, not proof of an employee's permanent ineligibility. Confirm the applicable scheme and eligibility master.

## Metric definitions needing explicit resolution

- Focus pack: approved EAN list, eligible outlet denominator, WoA definition, three-month window, pack selection and the meaning of "any 1". Do not sum every qualifying pack or automatically choose the highest payout.
- L3M average: confirm whether the source intends an arithmetic average of monthly rates, ratio of three-month totals, or another defined measure. Do not substitute one for the other.
- Outlets above the MRP threshold: validate MRP-valued sales, outlet eligibility and whether thresholding happens before or after the three-month average. Do not use NSV in place of MRP sales.
- Attrition: approved leaver categories, headcount denominator, period and thresholds. Lower is better; it is not an ordinary sales actual/target percentage.
- Promotions/transfers/joiners/leavers: use effective-dated eligibility and target/credit assignment. Segmenting a period for audit does not authorize prorating payout.
