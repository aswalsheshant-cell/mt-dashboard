# Forecast Engine — Quick Start

Get a 3-month demand forecast in 5 minutes.

## 1. Verify Setup

```bash
# Check Python version (3.8+)
python --version

# Check dependencies
pip list | grep pandas
pip list | grep numpy
pip list | grep xlsxwriter
```

Install if missing:
```bash
pip install pandas numpy xlsxwriter
```

## 2. Prepare Data

The engine consumes:

- **Margin Repository** — Published data from `margin_repository/Release_v1.0.0_RC1/`
- **Primary Sales CSV** — Monthly primary sales by article
- **Offtake Sales CSV** — Monthly store offtake by article

Example CSV structure (Primary):

```csv
chain,ean,article,brand,category,date,quantity,nsv
CAN,889789123,Ubtan_Face_Wash,Mamaearth,Skincare,2026-07-01,1000,10000
```

Example CSV structure (Offtake):

```csv
chain,ean,article,brand,store,date,quantity
CAN,889789123,Ubtan_Face_Wash,Mamaearth,Store_123,2026-07-15,50
```

## 3. Run Forecast

### CLI (Recommended)

```bash
cd /path/to/mt-dashboard

python -m forecast_engine.cli \
  --margin-repo margin_repository \
  --primary-data PowerBI/RawDataFolders/Primary_Article_Monthly/primary_*.csv \
  --offtake-data PowerBI/RawDataFolders/Offtake_Monthly/offtake_*.csv \
  --out forecast_outputs/2026-08-01 \
  --months 3 \
  --verbose
```

### Python API

```python
from forecast_engine import ForecastEngine
from scenario_planner import ScenarioPlanner
import pandas as pd

engine = ForecastEngine("margin_repository")
margin_data = engine.load_margin_repository()
primary_df, offtake_df = engine.load_historical_demand(
    "primary_sales.csv", "offtake_sales.csv", months_back=12
)

article_catalog = []
for _, row in margin_data.iterrows():
    article_catalog.append({
        "ean": row["ean"],
        "article": row["article"],
        "brand": row["brand"],
        "chain": row["chain"],
    })

forecast_df = engine.run_forecast(
    margin_data, primary_df, offtake_df, article_catalog,
    num_forecast_months=3
)

planner = ScenarioPlanner()
scenarios = planner.generate_scenarios(forecast_df)
```

## 4. Review Outputs

In `forecast_outputs/2026-08-01/`:

### Excel Planning Workbook

```
Forecast_Planning_Workbook.xlsx
├── Forecast
│   └── Base forecast: Chain, Article, Qty, NSV, Confidence %, Risk Level
├── Expected
│   └── Baseline scenario (1.0x volume, 1.0x margin)
├── Best_Case
│   └── Upside scenario (+20% qty, +10% margin, -5% spend)
├── Worst_Case
│   └── Downside scenario (-25% qty, -10% margin, +20% spend)
└── Exceptions
    └── Risk-flagged articles: low confidence, high variance, low distribution
```

### Executive Summary

`Forecast_Summary.json`:

```json
{
  "forecast_rows": 5000,
  "articles": 250,
  "total_forecast_qty": 150000,
  "avg_confidence_pct": 82.5,
  "articles_at_risk": 45,
  "scenario_expected_qty": 150000,
  "scenario_best_case_qty": 180000,
  "scenario_worst_case_qty": 112500
}
```

### Report

`Forecast_Report.md` — Executive summary with key metrics and top drivers.

### Power BI Ready

`PowerBI/`:

```
├── fact_demand_forecast.csv  (all articles, all 3 months)
├── fact_demand_expected.csv  (baseline scenario)
├── fact_demand_best_case.csv (upside)
├── fact_demand_worst_case.csv (downside)
├── fact_exceptions.csv       (risk-flagged articles)
├── dim_article.csv           (EAN master)
├── dim_chain.csv             (chain master)
├── dim_date.csv              (forecast months)
└── MEASURES.dax              (copy-paste into Power BI)
```

## 5. Load into Power BI

1. Open Power BI Desktop
2. New → Blank Report
3. Get Data → Folder
4. Select `forecast_outputs/2026-08-01/PowerBI/`
5. Load all CSV files
6. Create relationships (EAN → dim_article, chain → dim_chain, month → dim_date)
7. Copy MEASURES.dax content into DAX editor
8. Create visualizations:
   - Card: Forecast Total Qty
   - Card: Forecast Total NSV
   - 100% Stacked Bar: Scenario comparison
   - Matrix: Risk level × Exception count

## 6. Make Adjustments (Optional)

Planners can override forecasts:

```python
adjustment = {
    "chain": "CAN",
    "brand": "Mamaearth",
    "article": "New_Face_Wash",
    "ean": "999999999",
    "adjustment_type": "NEW_LISTING",
    "adjustment_qty": 500,  # Add 500 units to forecast
    "adjustment_reason": "New launch in CAN stores"
}

adjusted_forecast = planner.apply_business_adjustment(forecast_df, adjustment)
```

Supported adjustment types:
- `NEW_LISTING` — Add quantity
- `DELISTING` — Remove quantity
- `PROMOTION` — Add % + increase spend
- `BOGO` — Add % + heavy discounting
- `PRICE_CHANGE` — Adjust by % elasticity
- `EVENT_SALES` — Add one-time quantity

## 7. Common Queries

### "How confident is this forecast?"

Look at `confidence_pct` column (50-95%). <60% = investigate.

### "Why is this article at risk?"

Check `exception_flag` and `exception_reason`:
- `LOW_CONFIDENCE` — High volatility, few historical samples
- `RISK_FLAGGED` — High variance from base
- `HIGH_GROWTH_SKU` — >20% YoY growth
- `LOW_DISTRIBUTION` — <50% chain coverage
- `NPI_WATCHLIST` — New article <3 months old

### "Which warehouse gets how much?"

Check `warehouse_gurgaon`, `warehouse_mumbai`, `warehouse_bangalore`, `warehouse_kolkata` columns.

### "What's the best/worst case?"

See `fact_demand_best_case.csv` and `fact_demand_worst_case.csv`.
- Best Case: +20% volume, improved margins
- Expected: baseline (most likely)
- Worst Case: -25% volume, margin pressure

### "How does this compare to target?"

Join forecast with `PowerBI/RawDataFolders/TDP_Monthly/target_*.csv` in Power BI.

## 8. Troubleshooting

| Issue | Solution |
|-------|----------|
| `FileNotFoundError: Margin file not found` | Check `margin_repository/Release_v1.0.0_RC1/04_Business_Outputs/` exists |
| `Empty offtake data` | Ensure CSVs have columns: `chain`, `ean`, `date`, `quantity` |
| `Low confidence (all <60%)` | Need more historical data (12+ months minimum) |
| `All articles flagged HIGH_RISK` | Review input data quality; likely data issue |
| Memory error with 1M+ rows | Reduce `months_back=12` or filter by chain first |

## 9. Next Steps

1. **Review** — Open Excel workbook, spot-check forecasts
2. **Validate** — Compare with your domain knowledge
3. **Adjust** — Apply business rules (new listings, promos)
4. **Share** — Export to Power BI or send planning workbook to stakeholders
5. **Monitor** — Track forecast accuracy monthly

## 10. Help

- **README.md** — Full architecture & features
- **INTEGRATION_GUIDE.md** — How to wire into broader ecosystem
- **selftest.py** — Run tests to verify setup

```bash
python forecast_engine/selftest.py
```

All 16 tests passing = ready to go.

---

**Questions?** See README.md § "Support & Maintenance"
