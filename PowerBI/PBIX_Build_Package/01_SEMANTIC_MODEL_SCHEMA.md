# Power BI Semantic Model & Star Schema
## Modern Trade Dashboard — Demand & Sales Forecasting

**Version:** 1.0  
**Last Updated:** 2026-08-27  
**Status:** Production-Ready

---

## 1. Data Model Relationships Diagram

```
                      +-------------------+
                      |     Dim_Date      |
                      | PK: DateKey       |
                      | - Date            |
                      | - Month           |
                      | - Quarter         |
                      | - FY              |
                      | - Week            |
                      +-------------------+
                               | 1
                               |
                               | *
        +-------------------+  |  +-------------------+
        |    Dim_Chain      |--+--|    Dim_Product    |
        | PK: ChainKey      |     | PK: ProductKey    |
        | - Chain_ID        |     | - SKU_Code        |
        | - Chain_Name      |     | - Brand           |
        | - Zone            |     | - Category        |
        | - Region          |     | - Subcategory     |
        | - Status          |     | - Pack_Size       |
        +-------------------+     +-------------------+
                 | 1                       | 1
                 |                         |
                 | *                       | *
        +------------------------------------------------------------+
        |    Fact_Sales (Actuals / Offtake)                          |
        | PK: SalesKey                                               |
        | FK: DateKey, ChainKey, ProductKey, ZoneKey                 |
        | - Actual_Qty (volume)                                      |
        | - Actual_Revenue (₹)                                       |
        | - Base_COGS                                                |
        | - CM2_Provisional (flag)                                   |
        | - Metric_Type (Actual/Offtake)                             |
        +------------------------------------------------------------+
                 | *
                 |
                 | 1
        +------------------------------------------------------------+
        |    Fact_Forecast (Demand / Targets)                        |
        | PK: ForecastKey                                            |
        | FK: DateKey, ChainKey, ProductKey, ZoneKey                 |
        | - Forecast_Qty (volume)                                    |
        | - Forecast_Revenue (₹)                                     |
        | - Target_Revenue (₹)                                       |
        | - Forecast_Type (Rolling/Seasonal)                         |
        +------------------------------------------------------------+
                         | *
                         |
                         | 1
                      +-------------------+
                      |   Dim_Geography   |
                      | PK: ZoneKey       |
                      | - Zone            |
                      | - Region          |
                      | - State           |
                      | - Territory       |
                      +-------------------+

        +-------------------+
        |    _Measures      |
        | (Hidden Table)    |
        | - All DAX         |
        | - Calculations    |
        | - KPI Logic       |
        +-------------------+
```

---

## 2. Dimension Tables Schema

### Dim_Date
```
DateKey (PK)          | Text     | yyyyMM (202608)
Date                  | Date     | 2026-08-01
Month                 | Text     | August
Month_Num             | Integer  | 8
Quarter               | Text     | Q3
Quarter_Num           | Integer  | 3
FY                    | Text     | FY27 (Apr–Mar)
FY_Num                | Integer  | 27
Year                  | Integer  | 2026
Week_Num              | Integer  | 34
Is_Current_Month      | Boolean  | TRUE/FALSE
```

### Dim_Chain
```
ChainKey (PK)         | Text     | CHAIN_001
Chain_ID              | Text     | C001
Chain_Name            | Text     | Reliance Retail / Aditya Birla / DMart
Zone                  | Text     | North / South / East / West
Region                | Text     | Delhi / Mumbai / Chennai / Bangalore
Status                | Text     | Active / Inactive
Chain_Type            | Text     | Modern Trade / E-comm
Last_Updated          | Date     | 2026-08-27
```

### Dim_Product
```
ProductKey (PK)       | Text     | SKU_MAMAEA001
SKU_Code              | Text     | MAMAEA001
Product_Name          | Text     | Mamaearth Face Wash
Brand                 | Text     | Mamaearth / Honasa / Arata
Category              | Text     | Personal Care / Home Care
Subcategory           | Text     | Face Wash / Body Lotion
Pack_Size             | Text     | 150 ml / 500 ml
Price_Tier            | Text     | Premium / Mass / Economy
Status                | Text     | Active / Discontinued
Is_Seasonal           | Boolean  | TRUE/FALSE
```

### Dim_Geography (Expanded Multi-Tier Hierarchy)
```
ZoneKey (PK)          | Text     | ZONE_NORTH
Zone                  | Text     | North / South / East / West
State                 | Text     | Delhi / Punjab / Haryana / Maharashtra / Gujarat / Karnataka / Tamil Nadu / West Bengal
State_Code            | Text     | DL / PB / UP / MH / GJ / KA / TN / WB
Key_City              | Text     | Delhi / Chandigarh / Lucknow / Mumbai / Ahmedabad / Bengaluru / Chennai / Kolkata
Region                | Text     | Northern / Southern / Eastern / Western
Operating_Region      | Text     | North-1 / North-2 / West-1 / West-2 / South-1 / East-1
Territory             | Text     | NCR / Mumbai / Chennai (optional: Cluster ID for dense metros)
PIN_Range             | Text     | 100000-110000
Geography_Type        | Text     | Urban / Semi-Urban / Rural
Depot_Warehouse       | Text     | DC_DL_01 / WH_MH_02 (optional: warehouse node for logistics)
```

---

## 3. Fact Tables Schema

### Fact_Sales (Actuals / Offtake)
```
SalesKey (PK)         | Integer  | Auto-increment
DateKey (FK)          | Text     | yyyyMM
ChainKey (FK)         | Text     | CHAIN_001
ProductKey (FK)       | Text     | SKU_MAMAEA001
ZoneKey (FK)          | Text     | ZONE_NORTH
State_Code (FK)       | Text     | DL / PB / MH / GJ / KA / TN / WB (NEW: enables State drill-down)

Actual_Qty            | Decimal  | Volume in units
Actual_Revenue        | Decimal  | ₹ Revenue
Base_COGS             | Decimal  | ₹ Cost of goods
CM2_Amount            | Decimal  | ₹ CM2 contribution
CM2_Provisional       | Boolean  | TRUE (if D1 DRAFT) / FALSE (if D1 APPROVED)
Logistics_Cost        | Decimal  | ₹ (NEW: State-level freight, warehousing, distribution)
Metric_Type           | Text     | Actual / Offtake
Data_Source           | Text     | Primary / Offtake / Blend
Is_Blended            | Boolean  | TRUE if blended across sources
Load_Date             | Date     | Data load timestamp
```

### Fact_Forecast (Demand / Targets)
```
ForecastKey (PK)      | Integer  | Auto-increment
DateKey (FK)          | Text     | yyyyMM
ChainKey (FK)         | Text     | CHAIN_001
ProductKey (FK)       | Text     | SKU_MAMAEA001
ZoneKey (FK)          | Text     | ZONE_NORTH

Forecast_Qty          | Decimal  | Demand forecast (units)
Forecast_Revenue      | Decimal  | ₹ Forecasted revenue
Target_Revenue        | Decimal  | ₹ TY target
Forecast_Type         | Text     | Rolling / Seasonal / ML_Model
Confidence_Level      | Decimal  | 0.0–1.0 (model confidence)
Forecast_Method       | Text     | Statistical / ML / Expert
Update_Frequency      | Text     | Weekly / Monthly / Ad-hoc
Last_Updated          | Date     | Forecast refresh timestamp
```

---

## 4. Relationship Configuration

| From Table | From Column | To Table | To Column | Relationship Type | Active |
|---|---|---|---|---|---|
| Fact_Sales | DateKey | Dim_Date | DateKey | Many-to-One | Yes |
| Fact_Sales | ChainKey | Dim_Chain | ChainKey | Many-to-One | Yes |
| Fact_Sales | ProductKey | Dim_Product | ProductKey | Many-to-One | Yes |
| Fact_Sales | ZoneKey | Dim_Geography | ZoneKey | Many-to-One | Yes |
| Fact_Forecast | DateKey | Dim_Date | DateKey | Many-to-One | Yes |
| Fact_Forecast | ChainKey | Dim_Chain | ChainKey | Many-to-One | Yes |
| Fact_Forecast | ProductKey | Dim_Product | ProductKey | Many-to-One | Yes |
| Fact_Forecast | ZoneKey | Dim_Geography | ZoneKey | Many-to-One | Yes |

---

## 5. Data Grain & Validation Rules

### Fact_Sales Grain
- **Lowest Grain:** [DateKey] × [ChainKey] × [ProductKey] × [ZoneKey]
- **Typical Aggregation:** Monthly (not daily)
- **Duplicate Check:** No exact duplicates on PK combination
- **Null Policy:** Actual_Qty/Revenue may NOT be null; CM2_Provisional defaults to TRUE

### Fact_Forecast Grain
- **Lowest Grain:** [DateKey] × [ChainKey] × [ProductKey] × [ZoneKey]
- **Future-dated:** DateKey ≥ current month
- **Duplicate Check:** Only latest forecast per grain kept (historical archive separate)
- **Null Policy:** Forecast_Qty/Revenue may NOT be null; Confidence_Level defaults to 0.5

---

## 6. Dimension Table Row Counts (Expected)

| Table | Row Count | Refresh Frequency |
|---|---|---|
| Dim_Date | 120 (10 years) | Annual (static) |
| Dim_Chain | 450–500 | Monthly |
| Dim_Product | 8,000–12,000 SKUs | Weekly |
| Dim_Geography | 50–60 zones | Quarterly |
| Fact_Sales | 50M–100M rows | Daily |
| Fact_Forecast | 5M–10M rows | Weekly |

---

## 7. Cardinality & Performance Notes

- **Fact_Sales ↔ Dim_Product:** 1 SKU × 500 Chains × 60 Zones × 36 months = ~1M rows per year
- **Fact_Forecast:** Similar grain, rolling 24-month window
- **Indexing:** Create clustered index on `Fact_Sales(DateKey, ChainKey, ProductKey)`
- **Compression:** Enable column-level compression on Fact tables (₹ values compress 70%+)

---

**Next Step:** Implement Power Query transformations (see `02_POWER_QUERY_TRANSFORMS.md`)
