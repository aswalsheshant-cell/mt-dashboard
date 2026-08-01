# Forecast Engine Integration Guide

How to integrate the Forecast Engine into the broader Modern Trade analytics ecosystem.

## Phase A: One-Click Refresh (Priority 1)

**Goal**: Single command to refresh forecast from latest DMS + margin repo.

### Implementation

Create `/refresh_forecast.py` at project root:

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""One-click forecast refresh orchestration."""
import os
import json
import datetime as dt
from forecast_engine.cli import run_forecast_pipeline

def main():
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    MARGIN_REPO = os.path.join(PROJECT_ROOT, "margin_repository")
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, "forecast_outputs", dt.date.today().isoformat())
    
    # Primary & Offtake paths (from last PowerBI refresh)
    PRIMARY_PATH = os.path.join(PROJECT_ROOT, "PowerBI", "RawDataFolders", "Primary_Article_Monthly", "*.csv")
    OFFTAKE_PATH = os.path.join(PROJECT_ROOT, "PowerBI", "RawDataFolders", "Offtake_Monthly", "*.csv")
    
    summary = run_forecast_pipeline(
        margin_repo_path=MARGIN_REPO,
        primary_data_path=PRIMARY_PATH,
        offtake_data_path=OFFTAKE_PATH,
        output_dir=OUTPUT_DIR,
        forecast_months=3,
        verbose=True
    )
    
    print(json.dumps(summary, indent=2, default=str))

if __name__ == "__main__":
    main()
```

### Usage

```bash
python refresh_forecast.py
```

### Output

```
forecast_outputs/
└── 2026-08-01/
    ├── Forecast_Summary.json
    ├── Forecast_Planning_Workbook.xlsx
    ├── Forecast_Report.md
    └── PowerBI/
        ├── fact_demand_forecast.csv
        ├── fact_demand_expected.csv
        ├── fact_demand_best_case.csv
        ├── fact_demand_worst_case.csv
        ├── fact_exceptions.csv
        ├── dim_article.csv
        ├── dim_chain.csv
        ├── dim_date.csv
        └── MEASURES.dax
```

## Phase B: Leadership Dashboard (Priority 2)

**Goal**: Real-time Power BI dashboard showing forecast, scenarios, exceptions, warehouse allocation.

### Power BI Setup

1. **Data Source** — Refresh from `forecast_outputs/YYYY-MM-DD/PowerBI/`
2. **Model**
   - Load 8 CSVs (fact_* + dim_*)
   - Create relationships (EAN → dim_article, chain → dim_chain, forecast_month → dim_date)
   - Import MEASURES.dax content
3. **Dashboard Pages**
   - **Overview** — Total Qty (card), NSV (card), Trade Spend (card), CM2 (card)
   - **Scenarios** — Side-by-side comparison (Best vs Expected vs Worst)
   - **Risk Heatmap** — Articles by risk level + exception type
   - **Warehouse** — Allocation to 4 warehouses (100% stacked bar)
   - **Top SKUs** — High growth (top 10), high risk (top 10)
   - **Details** — Drill into article-level forecast + drivers

### Report Sample

| Page | Visuals |
|------|---------|
| Overview | KPI cards (Qty, NSV, Spend, CM2, Confidence %), exception count |
| Scenarios | Clustered column (Best/Expected/Worst qty), line (NSV delta) |
| Risk | Matrix (exception type × risk level), drill to article |
| Warehouse | 100% stacked bar (chain or zone on axis, warehouse color-coded) |
| Top 10 | High growth YoY % (table), low distribution % (table) |
| Details | Article grid + filters (chain, brand, category, risk level) |

## Phase C: Self-Service Planner Portal (Priority 6)

**Goal**: Web UI for planners to view forecasts and make adjustments.

### Architecture

```
/planner_portal/
├── app.py (Flask/FastAPI)
├── static/
│   ├── js/ (React or vanilla JS)
│   └── css/
├── templates/ (HTML)
└── data/
    └── cache/ (forecast CSVs)
```

### Pages

1. **Search** — Find article by EAN/name/category
2. **Forecast View** — Base + 3 scenarios, confidence, risk level
3. **Adjustment** — Apply NEW_LISTING, PROMOTION, etc.
4. **History** — Previous forecasts + actuals
5. **Audit** — Who adjusted what, when, why
6. **Download** — Export workbook or Power BI refresh

### API Endpoints

```
GET  /api/forecast/search?q=<ean or name>
GET  /api/forecast/<ean>
GET  /api/forecast/<ean>/history
POST /api/adjustment/ (new listing, promo, etc.)
GET  /api/warehouse-allocation
```

## Phase D: Forecast Accuracy Tracking (Priority 9)

**Goal**: Monthly actuals vs. forecast comparison; model refinement.

### Process

1. **Load Actual** — Latest offtake CSVs from PowerBI
2. **Compare** — Actual vs. forecast by article
3. **Compute Accuracy** — MAPE (Mean Absolute % Error), RMSE
4. **Attribute Drivers** — Which factors (trends, seasonality, events) explain variance?
5. **Recommend Refinements** — Retrain scenario factors, adjust confidence thresholds

### Output

```json
{
  "forecast_month": "2026-09",
  "total_articles": 250,
  "overall_mape": 12.3,
  "by_category": {
    "Skincare": {"articles": 100, "mape": 9.5, "top_miss_articles": [...]},
    "Personal Care": {"articles": 150, "mape": 14.1, "top_miss_articles": [...]}
  },
  "top_drivers_of_error": [
    {"driver": "Festival Uplift", "impact": "+8.2%"},
    {"driver": "Seasonality", "impact": "-5.1%"},
    {"driver": "Listing Change", "impact": "+2.3%"}
  ],
  "recommended_actions": [
    "Increase Diwali uplift factor from 35% → 42%",
    "Investigate Q3 seasonality (higher than baseline)",
    "Track NPI launch adoption more closely (curve too steep)"
  ]
}
```

## Phase E: CM2 Model Integration (Priority 4)

**Goal**: Feed demand forecast into profitability model.

### Inputs from Forecast Engine

- Chain × Article forecast quantity
- Forecast NSV
- Forecast trade spend

### Outputs to CM2

```
CM2 = (Forecast NSV × Margin %) - Forecast Trade Spend - Logistics Cost - Admin Overhead
```

### Connection

```python
# In cm2_model.py
from forecast_engine import load_latest_forecast

forecast_df = load_latest_forecast()
article_forecast = forecast_df[(forecast_df['chain'] == 'ChainX') & (forecast_df['ean'] == 'EAN123')]

nsv = article_forecast['forecast_nsv'].iloc[0]
trade_spend = article_forecast['forecast_trade_spend'].iloc[0]
margin_pct = load_margin_data(article_forecast['ean'])['margin_pct'].iloc[0]

cm2 = (nsv * margin_pct / 100.0) - trade_spend - logistics_cost - overhead
```

## Phase F: MT Analyst Work Desk (Priority 7)

**Goal**: Forecast module in broader analyst portal.

### Integration Points

Forecast Engine would be **one of 7 modules** in Modern Trade analyst workspace:

1. **Store Master QC** ✅ (existing)
2. **Margin Repository** ✅ (existing)
3. **Dynamic Forecast Engine** ← this
4. **Forecast Accuracy** (Phase D)
5. **CM2 & Profitability**
6. **Executive Dashboard** (Phase B)
7. **Meeting Assistant** (AI-powered insights)

### Navigation

```
MT Analyst Workdesk
├── Store Master QC
│   ├── Search
│   ├── Validation Rules
│   └── Audit Trail
├── Margin Repository
│   ├── Article Master
│   ├── Margin Versioning
│   └── Issue Log
├── Forecast Engine ← NEW
│   ├── Search & View
│   ├── Make Adjustments
│   ├── Scenario Analysis
│   └── Exception Management
├── CM2 & Profitability
│   ├── Article Profitability
│   ├── Trade Spend Impact
│   └── Margin vs. Forecast
└── ...
```

## Data Flow Across Ecosystem

```
PowerBI Refresh (monthly)
         ↓
DMS Upload ←─→ Offtake CSV, Primary CSV
    ↓
Margin Repository (v1.0) ✅
    │
    ├─→ CONSTRAINT: Quality Gate (BLOCKED=0, WARNING≈0)
    │
    ├─→ PUBLISHED: fact_margin, dim_article
    │
    ↓
Forecast Engine ← NEW
    │
    ├─→ Run 3-month rolling forecast
    ├─→ Generate scenarios
    ├─→ Export to Power BI
    │
    ↓
Leadership Dashboard (Power BI) ← Phase B
    ├─→ Scenario comparison
    ├─→ Risk heatmap
    ├─→ Warehouse allocation
    │
    ↓
Planner Adjustments ← Phase C
    │
    ├─→ NEW_LISTING, PROMO, etc.
    ├─→ Audit trail + approval workflow
    │
    ↓
CM2 & Profitability Model ← Phase E
    │
    ├─→ Compute CM2 per article
    ├─→ Trade spend impact
    │
    ↓
Forecast Accuracy Tracking ← Phase D
    │
    ├─→ Monthly actual vs. forecast
    ├─→ MAPE, driver attribution
    ├─→ Model refinement recommendations
    │
    ↓
MT Analyst Workdesk ← Phase F
    │
    └─→ Unified interface for all 7 modules
```

## Deployment Checklist

### Development ✅
- [x] Core forecast engine (16 tests, all pass)
- [x] Scenario planner (Best/Expected/Worst)
- [x] Power BI export (8 tables + 18 measures)
- [ ] Phase A: One-click refresh script
- [ ] Phase B: Power BI dashboard
- [ ] Phase C: Planner portal UI
- [ ] Phase D: Accuracy tracking
- [ ] Phase E: CM2 integration
- [ ] Phase F: Workdesk integration

### Testing
- [x] Unit tests (16 scenarios)
- [ ] Integration tests (with real margin repo)
- [ ] UAT (with business users)
- [ ] Performance (5000+ articles, 3 months)

### Deployment
- [ ] Release notes
- [ ] Runbook (how to refresh monthly)
- [ ] Training (for planners + analysts)
- [ ] Monitoring (job status, data quality)
- [ ] Rollback plan

## Next Steps

1. **Phase A** — Create `refresh_forecast.py` and test with real data (1 week)
2. **Phase B** — Build Power BI dashboard from CSV exports (2 weeks)
3. **Phase C** — Prototype planner portal UI (3 weeks)
4. **Phase D** — Implement accuracy tracking (2 weeks)
5. **Phase E** — Wire CM2 model integration (1 week)
6. **Phase F** — Assemble unified workdesk (4 weeks)

**Timeline**: ~3 months to full production ecosystem.

## Support & Maintenance

- **Monthly refresh** — Automatic (scheduled job)
- **Quarterly retraining** — As FY27/28 data accumulates
- **Annual audit** — Scenario factors, exception thresholds, business rules
- **Continuous improvement** — Based on forecast accuracy feedback

