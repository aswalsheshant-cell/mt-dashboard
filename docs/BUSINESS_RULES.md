# MT Business Rules Registry

**Single source of truth for every business calculation, KPI, and allocation rule.**
Every implementation must match these definitions. Changes require approval.

---

## Financial Year (FY) Definition

```
Indian FY: April 1 – March 31
Apr–Dec of calendar year Y → FY(Y+1)  e.g. Apr-26 → FY27
Jan–Mar of calendar year Y → FY(Y)    e.g. Mar-26 → FY26

Quarter mapping:
  Q1: Apr, May, Jun
  Q2: Jul, Aug, Sep
  Q3: Oct, Nov, Dec
  Q4: Jan, Feb, Mar
```

---

## Primary Sales Rules

| Rule | Definition |
|---|---|
| NSV | Gross Billing − Returns (MRN) − Scheme Deductions − Damage Credits |
| GST | NSV is always ex-GST; never include GST in NSV |
| Grain | Month + Chain Name + Brand Name + Pack Size |
| Return timing | MRN reduces NSV in the month the credit note is issued, not original billing |
| Reliance BC | Reliance Brand Counter rows MUST be excluded (exact match: Data Status = "brand counter", not contains) |
| Currency unit | All NSV values reported in ₹ Lakhs (L) |

---

## Offtake Rules

| Rule | Definition |
|---|---|
| Grain | Month + Chain Name + Site Code + EAN |
| Source | Store-level XLSB files (one per chain or period) |
| FY gating | Offtake checks o['total_'+fy] independently — not governed by Primary FY coverage |
| Pre-agg coverage | FY25 and FY26 from pre-aggregated workbooks (ends Mar-26) |
| FY27 coverage | Via --offtake-patch only (idempotent — include all months collected) |
| Double-count prevention | --offtake-patch recomputes each touched FY; never run incremental without all prior months |

---

## Allocation Rules

| Level | Rule |
|---|---|
| Distributor → Chain | Geography + channel type mapping (priority column resolves conflicts) |
| Chain → Brand | Brand-chain relationship table (owned by build script) |
| Brand → Article/EAN | Product master mapping |
| Missing records | All unmapped records logged to alloc.missing_mapping — NEVER silently dropped |
| Conflict resolution | Priority chain wins when store maps to multiple chains |
| Effective dates | Historical mapping changes apply from effective_from month only |

---

## Key Metrics Definitions

| Metric | Formula | Grain | Unit |
|---|---|---|---|
| NSV | Gross Billing − Returns − Schemes − Damages | Month + Chain + Brand + Pack | ₹L |
| Gross Margin (GM) | NSV − COGS | Month + Chain | ₹L |
| GM % | GM / NSV × 100 | Month + Chain | % |
| Trade Spend % | BTL Trade Spend / NSV × 100 | Month + Chain | % |
| Channel EBITDA | GM − Trade Spend − Field Force Cost | Month + Chain | ₹L |
| Offtake Value | Sell-through at store level | Month + Chain + Store + EAN | ₹L |
| Primary-Offtake Gap | NSV − Offtake Value | Month + Chain | ₹L |
| Numeric Distribution | % stores stocking at least 1 relevant SKU | Month + Chain | % |
| Weighted Distribution | Distribution weighted by store offtake potential | Month + Chain | % |
| Days of Supply (DOS) | (Closing Stock at Trade / Avg Weekly Offtake) × 7 | Month + Chain | Days |
| Market Share | Brand Offtake / Category Total Offtake × 100 | Month + Channel | % |
| Same Store Growth | NSV from stores active in both current and prior period | YoY | % |
| Target Achievement | Actual NSV / Target NSV × 100 | Month + Chain | % |
| Return Rate | Returns / Gross Billing × 100 | Month + Chain | % |

---

## Tolerance Thresholds

| Check | Acceptable Tolerance | Action if Exceeded |
|---|---|---|
| Distributor vs Chain total | ±0.5% | Investigate before release |
| Primary vs Offtake gap | ≤10% of Primary | Document and explain |
| P&L vs Primary delta | ±2pp GM% | Flag to Finance |
| QC Health Score | ≥95 for release | Block release; document exceptions at 85–94 |
| Rounding | ±0.01L | Acceptable |
| Regression (prior FY) | 0.00L (zero tolerance) | Block release |

---

## Mapping Priority Rules

When a store or record maps to multiple chains, apply this priority order:
1. Exact site_code match in priority mapping table
2. Chain name from source file (if unambiguous)
3. Geographic hierarchy (State → City → Pincode)
4. Default to UNMAPPED and log to alloc.missing_mapping

---

## Data Governance Contacts

| Domain | Owner |
|---|---|
| Business rules (Primary/Offtake) | MT Analytics Lead |
| Allocation mapping | Sales Operations |
| P&L / Financial | Finance Business Partner |
| Master data (Chain/Store/EAN) | Data Governance |
| Dashboard / technical | Engineering (Claude/Sheshant) |
