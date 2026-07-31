# MT Demand Forecast & S&OP Model — Honasa / Mamaearth Modern Trade

An enterprise, fully **formula-driven** Excel model for a rolling 3-month demand
forecast (Month **M / M+1 / M+2**) and S&OP planning, plus a separate
**Business Event Engine** that turns planned activities into incremental demand
on top of the baseline.

**Deliverable:** [`MT_Demand_Forecast_SOP_Model.xlsx`](MT_Demand_Forecast_SOP_Model.xlsx)
· 30 worksheets · every forecast is a live Excel formula.

> **No dummy data.** All history comes from the real Honasa MT primary and
> offtake files under `PowerBI/RawDataFolders/` (primary Apr'25–May'26, offtake
> Apr'26–May'26). Only planner assumptions (stock, service metrics, promo/NPI
> plans) are example inputs — every one is a **blue cell** you overwrite.

---

## Open & drive it

1. Open the workbook in **Excel** (it recalculates on open).
2. Go to **Control Panel** — every blue cell drives the model. The two that
   matter most:
   - **Last Actual Month** — the latest month present in Primary Sales History.
   - **Forecast Month (M)** — the first month to forecast (M+1, M+2 follow).
3. Read the **Executive Dashboard** and **Scenario Summary**.

Change nothing else and the model already produces a real, reconciled forecast.

## Refresh each month

1. Paste the new month's primary into **Primary Sales History** (add a column)
   and offtake into **Offtake History**.
2. On the **Control Panel**, set *Last Actual Month* to the new month and
   *Forecast Month (M)* to the next month. The whole workbook rolls forward.
3. Update **Promotion Calendar**, **NPI & EPD Planning** and
   **Business_Event_Master** for the new horizon.
4. Capture manual changes in the **Demand Planner Workbench** (with a reason —
   the audit trail is preserved).

Or regenerate everything from the raw sources:

```bash
python scripts/build_demand_forecast.py
python scripts/verify_demand_forecast.py   # asserts 0 formula errors
```

---

## What's inside (30 tabs)

**Forecasting core**
- **Executive Dashboard** — one-page S&OP view (scenario, forecast vs target, accuracy).
- **Control Panel** — all assumptions, method weights, scenarios, capacities.
- **Forecast Engine** — per Brand×Category: 7 statistical methods → Statistical →
  Business → AI ensemble → Base/Optimistic/Conservative/Selected, for M/M+1/M+2.
- **Forecast Plan Article-Chain** — the rolling forecast cascaded to
  **Article × Brand × Chain × Region** by real contribution % (filterable;
  reconciles exactly to the engine).
- **Scenario Summary** — Base/Optimistic/Conservative side by side vs target.
- **AI Business Insights** / **Demand Planner Workbench** (overrides + audit trail).

**Business Event Engine (separate module)**
- **Business_Event_Master** — one row per activity; only **Approved** rows affect
  the forecast; baseline is never overwritten.
- **Event Impact Engine** — Baseline + Events = Final, shown separately. Overlapping
  % events combine **multiplicatively** (1−∏(1+uᵢ)), absolute events are added.
- **Event Impact Dashboard**, **Event AI Recommendations**, **Event Calendar**,
  **Event Simulator** (instant what-ifs), and the editable
  **Chain / Article / Demand Driver** libraries + **Event Settings** (ramp-up &
  decay curves, priority weights, confidence, ₹/unit).

**Planning & supply**
- **Target Distribution** (company target → Zone/Chain/State/Article by real
  contribution %, with overrides that reconcile), **Primary Planning**,
  **Distributor Intelligence** (auto-classification), **Warehouse Optimization**
  (Gurgaon/Mumbai/Bangalore/Kolkata capacity check), **Forecast Accuracy**
  (MAPE/WMAPE/Bias/Tracking Signal back-test on real primary).

**Inputs / masters** — Monthly Target Upload, Primary Sales History, Offtake
History, Distributor Master, NPI & EPD Planning, Promotion Calendar, Seasonality
Matrix, Calendar, and full **Documentation**.

## Forecast methodology (summary)

Statistical = weight-normalised blend of WMA, Exponential Smoothing, Linear Trend,
Seasonal Index, CAGR, Rolling Average and YoY, each reseasonalised by the editable
Seasonality Matrix. Business = Statistical × (1 + adjustment % + promo uplift).
AI = weighted blend of Statistical, Business and a driver-adjusted Statistical
(brand momentum + promo response). Final (scenario) = AI × scenario multiplier +
NPI loading. Events then add on top via the Event Engine. Full formulas are on the
**Documentation** tab.

## Colour legend

Blue text on pale-yellow fill = **editable input** · black = formula · green =
cross-sheet link.
