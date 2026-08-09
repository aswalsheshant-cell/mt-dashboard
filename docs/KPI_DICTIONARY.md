# MT KPI Dictionary

**Every metric used in the MT Analytics Platform — one definition, one formula, one source.**

---

| KPI | Definition | Formula | Grain | Unit | Source | Owner |
|---|---|---|---|---|---|---|
| **NSV** | Net Sales Value — what Honasa earns after all deductions | Gross Billing − Returns − Schemes − Damages | Month + Chain + Brand | ₹L | Primary XLSB | MT Analytics |
| **Gross Margin (GM)** | Revenue minus cost of goods | NSV − COGS | Month + Chain | ₹L | P&L workbook | Finance |
| **GM %** | Gross margin as a share of NSV | GM / NSV × 100 | Month + Chain | % | Calculated | Finance |
| **Trade Spend** | BTL investment at channel level | Scheme + Activation + Visibility costs | Month + Chain | ₹L | P&L workbook | Finance |
| **Trade Spend %** | Trade spend as a share of NSV | Trade Spend / NSV × 100 | Month + Chain | % | Calculated | Finance |
| **Channel EBITDA** | Net contribution from channel | GM − Trade Spend − Field Force Cost | Month + Chain | ₹L | Calculated | Finance |
| **Offtake Value** | Consumer sell-through at store level | Sum of store-level billed sales | Month + Chain + Store + EAN | ₹L | Offtake XLSB | MT Analytics |
| **Offtake Qty** | Units sold to consumers | Sum of units at store level | Month + Chain + Store + EAN | Units | Offtake XLSB | MT Analytics |
| **Primary-Offtake Gap** | Inventory build at trade | NSV − Offtake Value | Month + Chain | ₹L | Calculated | MT Analytics |
| **Numeric Distribution** | % stores stocking ≥1 relevant SKU | Stores stocking / Total stores × 100 | Month + Chain | % | Distribution | Sales Ops |
| **Weighted Distribution** | Distribution weighted by store potential | Offtake-potential-weighted store coverage | Month + Chain | % | Distribution | Sales Ops |
| **Days of Supply (DOS)** | Weeks of stock at trade | Closing Stock / (Avg Weekly Offtake) × 7 | Month + Chain | Days | Calculated | Supply |
| **Market Share** | Honasa share of category | Honasa Offtake / Total Category Offtake × 100 | Month + Channel | % | Market Share source | MT Analytics |
| **Same Store Growth (SSG)** | Growth from stores active in both periods | NSV (stores in both periods, current) / NSV (stores in both periods, prior) − 1 × 100 | YoY | % | Calculated | MT Analytics |
| **Target Achievement** | Actual vs target | Actual NSV / Target NSV × 100 | Month + Chain | % | Calculated | MT Analytics |
| **Return Rate** | Returns as % of gross billing | MRN Value / Gross Billing × 100 | Month + Chain | % | Primary XLSB | MT Analytics |
| **Trade Spend ROI** | Offtake generated per unit of spend | Offtake Value / Trade Spend | Month + Chain | ₹/₹ | Calculated | Finance |
| **SKU Velocity** | Average offtake per active store per month | Offtake Qty / Active Stores | Month + Chain + EAN | Units/Store | Calculated | Category |
| **Listing Rate** | % of target stores with SKU listed | Stores with SKU / Target stores × 100 | Month + Chain + EAN | % | Distribution | Sales Ops |

---

## Reporting Units

- All monetary values: **₹ Lakhs (L)**
- Percentages: one decimal place (e.g. 38.2%)
- Percentage point changes: stated as "pp" (e.g. "+3.2pp")
- Days: integer (e.g. "22 days")
- Units: actual count (cases / pieces as defined by pack)

---

## FY and Period Labels

- FY: "FY25", "FY26", "FY27" (two-digit year = end year of the Indian FY)
- Month: "Apr-26", "May-26", ... "Mar-27" (three-letter abbreviation + two-digit year)
- Quarter: "Q1 FY27" = Apr-26, May-26, Jun-26
