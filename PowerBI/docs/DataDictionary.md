# Data Dictionary — Standard Columns

These are the canonical column names used across the model. **Do not rename**
the ones marked 🔒 — Power Query matches by name and renaming breaks refresh.
Column → table → type → meaning.

## Identity / time
| Column | Type | Meaning |
|---|---|---|
| 🔒 Month | text | `MMM'YY` e.g. `May'26`. Converted to `MonthStart` date in M. |
| MonthStart | date | First of month (derived). Relationship key to Date Table. |
| FY Year | text | Indian financial year e.g. `26-27`. |
| Quarter | text | `Q1`–`Q4` on Apr–Mar basis. |
| 🔒 Week Start Date | date | Monday of the week (Primary only). |
| Refresh Date | datetime | Stamped automatically on every loaded row. |
| 🔒 Data Source Name | text | e.g. `Chain POS`, `SAP Primary`, `Nielsen MS Val Urban`. |

## Geography & account
| Column | Type | Meaning |
|---|---|---|
| 🔒 Chain | text | Retail chain (Reliance Retail, Lulu, Wellness Forever, More, Apollo…). |
| Account | text | Parent account / group. |
| 🔒 Zone | text | East, North, South-1, South-2, West, Pan India. |
| 🔒 State | text | Indian state. |
| City | text | City. |
| 🔒 Store Code | text | Unique store id (= `Cust-SAP Code` in the team-mapping file). |
| Store Name | text | Store display name. |

## Product
| Column | Type | Meaning |
|---|---|---|
| 🔒 Brand | text | Mamaearth, The Derma Co., Aqualogica, Dr. Sheth's, BBlunt, Emerging Brands. |
| 🔒 Category | text | Internal category (Face Care, Hair Care, Sun Care…). |
| Sub-category | text | Face Wash, Shampoo, Sunscreen, Face Serum… |
| Nielsen Category | text | Facewash, Shampoo, Sunscreen, Face Serum (maps internal→Nielsen). |
| Range | text | Product range (Rice, Onion, Ultra Light…). |
| Pack Size | text | `150 g/ml`, `100 g/ml`, `50 g/ml`, `30 g/ml`… |
| 🔒 Article Code | text | SKU code. Master key. |
| Article Description | text | Full SKU name. |
| 🔒 EAN Code | text | Barcode. Keep as text (leading zeros). |

## Sales measures (numbers)
| Column | Type | Meaning |
|---|---|---|
| 🔒 Primary NSV | number | Primary net sales value (₹). |
| 🔒 Primary Qty | number | Primary units. |
| 🔒 Offtake NSV | number | Offtake / secondary net sales value (₹). |
| 🔒 Offtake Qty | number | Offtake units. |
| MRP Sales | number | Sales at MRP (gross proxy). |

## P&L (from Assumption Table, or actuals when available)
| Column | Type | Meaning |
|---|---|---|
| Gross Margin % | number | 0–1 decimal (0.52 = 52%). |
| Trade Spend % | number | % of NSV. |
| Visibility Spend | number | ₹ absolute. |
| Scheme Spend | number | ₹ absolute. |
| Other Spend | number | ₹ absolute. |
| Contribution Margin % | number | 0–1 decimal. |
| Remarks | text | assumption note. |

## Distribution / market share
| Column | Type | Meaning |
|---|---|---|
| 🔒 ACV % | number | All-Commodity-Volume reach of a SKU (0–100). TDP = Σ ACV %. |
| AIC | number | Average Items Carried. |
| Numeric Distribution | number | 0–1 store-count basis. |
| Weighted Distribution | number | 0–1 ACV-weighted basis. |
| Market Value Sales | number | Total category value (₹) — Nielsen. |
| Our Brand Sales | number | Our value in category (₹) — Nielsen. |
| Value Market Share % | number | 0–1 decimal. |
| Volume Market Share % | number | 0–1 decimal. |

## Derived in DAX (not in source files)
TDP, Sales per TDP, Offtake per TDP, MoM/YoY Growth %, L3M/L6M Average,
Contribution %, Total Spend, CM %, Forecast NSV, Final Forecast,
Forecast Accuracy %, Market Share BPS Change, etc. — see the `DAX/` files.

---
### Units & formatting convention
- All ₹ amounts stored in **absolute rupees**; display measures convert to
  **Lacs** (÷100,000) and **Cr** (÷10,000,000). `NSV Label` auto-picks Cr/L.
- Percentages stored as **decimals** (0.12 = 12%).
- Market-share movements shown in **bps** (1% = 100 bps).
