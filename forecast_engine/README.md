# Dynamic Forecast & Demand Planning Engine

Production-grade demand forecasting system for Modern Trade, consuming published Margin Repository data to generate 3-month rolling forecasts at the Chain × Brand × Article level.

## Architecture

### Core Modules

1. **forecast_schema.py** — Data model, validation, hierarchy definition
2. **forecast_drivers.py** — Trend computation (MoM, YoY, weighted MA, seasonality)
3. **forecast_engine.py** — Core forecasting orchestration
4. **scenario_planner.py** — Scenario generation (Best/Expected/Worst) + business adjustments
5. **powerbi_export.py** — Power BI dataset export + DAX measures
6. **cli.py** — Command-line interface

### Forecast Hierarchy

```
Channel (Modern Trade, General Trade)
└── Chain (retail chains)
    └── Zone (sales zones)
        └── State (geography)
            └── Brand (product brand)
                └── Category
                    └── Article (EAN)
```

## Forecast Drivers

The engine considers:

- **Historical Demand** — 12-month offtake + primary history
- **Trends** — Month-over-month %, Year-over-year %
- **Moving Averages** — Weighted 3-month average (50%, 30%, 20%)
- **Seasonality** — Month-specific factors vs. annual average
- **Growth Factors** — Festival uplift, NPI launch curve, distribution expansion
- **Price Impact** — Margin change elasticity (-0.5)
- **Business Events** — New listings, delistings, promotions, BOGO, bulk orders

## Forecast Outputs

### Tables

| Table | Level | Columns |
|-------|-------|---------|
| fact_demand_forecast | Chain × Brand × Article | Qty, NSV, Primary, Offtake, Trade Spend, CM2, Confidence %, Risk Level |
| fact_demand_scenario | By scenario (Best/Expected/Worst) | Qty, NSV, Trade Spend, CM2, scenario name |
| fact_exceptions | Exception-flagged rows | Chain, Article, exception type, reason, risk level |
| dim_article | EAN-deduplicated | EAN, Brand, Category, Article |
| dim_chain | Chain-deduped | Chain, Zone, State |
| dim_date | By forecast month | Forecast Month, Forecast FY |

### Executive Summary

```json
{
  "forecast_rows": 5000,
  "articles": 250,
  "chains": 15,
  "total_forecast_qty": 150000,
  "total_forecast_nsv": 15000000,
  "total_trade_spend": 750000,
  "total_cm2": 1200000,
  "avg_confidence_pct": 82.5,
  "articles_at_risk": 45,
  "exception_count": 23,
  "scenario_expected_qty": 150000,
  "scenario_best_case_qty": 180000,
  "scenario_worst_case_qty": 112500
}
```

## Risk Scoring

| Level | Criteria | Action |
|-------|----------|--------|
| NORMAL | % variance ≤ 1% | Approve forecast |
| WARNING | % variance ≤ 3% | Review confidence |
| HIGH_RISK | % variance ≤ 5% | Investigate driver |
| BLOCKED | % variance > 5% | Escalate to planner |

## Exception Types

- **UNDER_FORECAST** — Actual > Forecast by >3%
- **OVER_FORECAST** — Forecast > Actual by >3%
- **INVENTORY_RISK** — Low stock vs. high demand
- **HIGH_MARGIN_OPPORTUNITY** — High margin SKU, low distribution
- **LOW_DISTRIBUTION** — <50% chain coverage
- **HIGH_GROWTH_SKU** — >20% YoY growth
- **NPI_WATCHLIST** — New article <3 months old

## Business Adjustments

Planners can override forecasts via:

- **NEW_LISTING** — Add quantity for new SKU
- **DELISTING** — Subtract quantity for discontinued SKU
- **EXTRA_VISIBILITY** — Uplift from store signage/display
- **PROMOTION** — % uplift + increased trade spend
- **BOGO** — Buy-One-Get-One uplift + heavy discounting
- **PRICE_CHANGE** — % demand change from price
- **DISTRIBUTOR_CHANGE** — Flag for manual review
- **EVENT_SALES** — One-time event quantity
- **BULK_ORDER** — Anticipated large order

## Usage

### Command-Line

```bash
python -m forecast_engine.cli \
  --margin-repo /path/to/margin_repository \
  --primary-data /path/to/primary_sales.csv \
  --offtake-data /path/to/offtake_sales.csv \
  --out /output/directory \
  --months 3 \
  --verbose
```

### Python API

```python
from forecast_engine import ForecastEngine
from scenario_planner import ScenarioPlanner

engine = ForecastEngine("/path/to/margin_repository")
margin_data = engine.load_margin_repository()
primary_df, offtake_df = engine.load_historical_demand(...)

forecast_df = engine.run_forecast(
    margin_data, primary_df, offtake_df, article_catalog,
    num_forecast_months=3
)

planner = ScenarioPlanner()
scenarios = planner.generate_scenarios(forecast_df)
```

## Outputs

Generated files:

- **Forecast_Planning_Workbook.xlsx** — Multi-sheet Excel with base + scenario forecasts
- **Forecast_Report.md** — Executive summary and key insights
- **Forecast_Summary.json** — Full metadata and metrics
- **PowerBI/** — Clean fact/dimension tables + MEASURES.dax

### Power BI Integration

1. Open Power BI Desktop
2. New Data Source → Folder
3. Navigate to `PowerBI/` output directory
4. Load CSV files
5. Copy-paste MEASURES.dax content into Calculation Group or DAX formula bar
6. Create visualizations using:
   - Forecast Total Qty (card)
   - Forecast Total NSV (card)
   - Scenario comparison (column chart)
   - Risk breakdown (pie)
   - Top articles by forecast (table)
   - Warehouse allocation (100% stacked bar)

## Testing

```bash
python selftest.py
```

16 tests covering:
- Data model validation
- Forecast drivers (trends, seasonality, uplift)
- Scenario generation and variance
- Business adjustments

## Quality Gates

- ✅ All articles > 60% confidence (or flagged)
- ✅ No articles with >5% unexplained variance (or documented)
- ✅ Forecast reconciles to source data
- ✅ All scenarios generated successfully

## Integration with Margin Repository

The forecast engine:

1. **Consumes** — Published fact_margin + dim_article from MarginRepository v1.0.0
2. **Preserves** — All repository validation rules and quality gates
3. **Extends** — With demand planning, scenario analysis, warehouse allocation
4. **Produces** — Clean Power BI datasets ready for dashboard/reporting

## Data Lineage

```
DMS Upload
    ↓
Margin Repository v1.0.0 (validated, published)
    ↓
Forecast Engine (reads fact_margin + dim_article)
    ↓
Forecast tables + scenarios + exceptions
    ↓
Power BI (visualizations + dashboards)
```

## Configuration

Optional calendar files (CSV):

- **festival_calendar.csv** — Name, date, uplift %
- **npi_calendar.csv** — EAN, launch date, category
- **event_calendar.csv** — Event name, date, forecast impact

## Known Limitations

1. **Historical depth** — Requires minimum 12 months offtake history (shorter = lower confidence)
2. **New articles** — NPI curve applies to FY27+ launches only
3. **Price elasticity** — Fixed -0.5 (not category-specific, yet)
4. **Distribution** — Must have Store Master data for allocation
5. **Scenarios** — Fixed factors (Best +20%, Worst -25%); custom scenarios via API only

## Deployment

### Phase A: One-Click Refresh (Priority 1)
```bash
python refresh_forecast.py  # orchestrates full pipeline
```

### Phase B: Leadership Dashboard (Priority 2)
- Real-time scenario comparison
- Risk heatmap
- Top growth/risk SKUs
- Warehouse utilization forecast

### Phase C: Planner Portal (Priority 6)
- Interactive adjustment UI
- Confidence visualization
- History + audit trail
- Scenario export

### Phase D: Forecast Accuracy Tracking (Priority 9)
- Monthly actual vs. forecast comparison
- Driver attribution (which factors drove accuracy gains/losses)
- Model refinement recommendations

## Support & Maintenance

- **Model retraining** — Quarterly (as FY27/28 data accumulates)
- **Scenario factors** — Annual review (festive % by category, NPI curves)
- **Exception thresholds** — As business context changes (new categories, channels)

## Version

1.0.0 — Initial production release
- Core forecasting engine
- Three scenarios (Best/Expected/Worst)
- Exception detection
- Power BI export

See CHANGELOG.md for updates.
