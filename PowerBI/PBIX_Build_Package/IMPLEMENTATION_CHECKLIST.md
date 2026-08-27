# Power BI Build Package — Implementation Checklist
## Modern Trade Dashboard (Demand & Sales Forecasting)

**Quick reference:** Follow this checklist to build the complete Power BI dashboard in ~2-3 hours.

---

## Phase 1: Setup & Data Preparation (20 mins)

- [ ] **Download all documents** from `PowerBI/PBIX_Build_Package/`
- [ ] **Review README.md** (5 mins) — understand structure & features
- [ ] **Review SEMANTIC_MODEL_SCHEMA.md** (5 mins) — understand ER diagram & data grain
- [ ] **Run sample data generator:**
  ```bash
  cd PowerBI/PBIX_Build_Package/
  python3 05_SAMPLE_SEED_DATA_GENERATOR.py
  ```
  - [ ] Verify 6 CSV files created in `powerbi_data/` directory
  - [ ] Files: Dim_Date, Dim_Chain, Dim_Product, Dim_Geography, Fact_Sales, Fact_Forecast

---

## Phase 2: Create Power BI Model (40 mins)

### 2.1 Load Dimension Tables (10 mins)

- [ ] **Open Power BI Desktop** → New blank report
- [ ] **For each dimension** (Dim_Date, Dim_Chain, Dim_Product, Dim_Geography):
  - [ ] Home → Get Data → Text/CSV → Select file from `powerbi_data/`
  - [ ] Load table; rename query to exact table name (e.g., `Dim_Date`)
  - [ ] **Close & Apply**

- [ ] **Power Query (optional, recommended):**
  - [ ] For each table, open Power Query Editor
  - [ ] Copy-paste M code from `02_POWER_QUERY_TRANSFORMS.md` Section 1–2
  - [ ] Click OK (applies transformations: type casting, nullable handling, dedup)
  - [ ] Close & Apply

### 2.2 Load Fact Tables (10 mins)

- [ ] **Fact_Sales:**
  - [ ] Home → Get Data → Text/CSV → Select `Fact_Sales.csv`
  - [ ] (Optional) Apply Power Query code from `02_POWER_QUERY_TRANSFORMS.md` Section 2
  - [ ] Close & Apply

- [ ] **Fact_Forecast:**
  - [ ] Home → Get Data → Text/CSV → Select `Fact_Forecast.csv`
  - [ ] (Optional) Apply Power Query code
  - [ ] Close & Apply

### 2.3 Create Relationships (15 mins)

- [ ] **Open Model view** (left sidebar: Model icon)
- [ ] **Create 8 relationships** (per `02_POWER_QUERY_TRANSFORMS.md` Section 3):

| From Table | From Column | To Table | To Column | Relationship Type |
|---|---|---|---|---|
| Fact_Sales | DateKey | Dim_Date | DateKey | Many-to-One |
| Fact_Sales | ChainKey | Dim_Chain | ChainKey | Many-to-One |
| Fact_Sales | ProductKey | Dim_Product | ProductKey | Many-to-One |
| Fact_Sales | ZoneKey | Dim_Geography | ZoneKey | Many-to-One |
| Fact_Sales | State_Code | Dim_Geography | State_Code | Many-to-One |
| Fact_Forecast | DateKey | Dim_Date | DateKey | Many-to-One |
| Fact_Forecast | ChainKey | Dim_Chain | ChainKey | Many-to-One |
| Fact_Forecast | ProductKey | Dim_Product | ProductKey | Many-to-One |

  - [ ] Model → Manage Relationships → New → Create each relationship
  - [ ] Verify **no ambiguous paths** (red X on diagram = problem)
  - [ ] Verify all relationships are **Many-to-One** (not bidirectional)

- [ ] **Hide dimension table keys** (optional, for cleaner reporting):
  - [ ] Right-click each Key column → Hide → Confirm
  - [ ] Keep visible: descriptive columns only (Chain_Name, Product_Name, State, etc.)

---

## Phase 3: Create Measures (60 mins)

- [ ] **Create hidden `_Measures` table:**
  - [ ] Data → New Table → Name: `_Measures`
  - [ ] DAX: `_Measures = {"Placeholder"}`

- [ ] **Paste all measures from `03_DAX_MEASURE_LIBRARY.md`:**
  - [ ] For each measure (30+):
    - [ ] Home → New Measure
    - [ ] Paste DAX code from document
    - [ ] Set **Format** (Currency ₹, Percentage %, etc.)
    - [ ] Set **Decimal Places** (2 for currency, 1 for %)
    - [ ] Hit Enter

  - [ ] **Measure categories to create:**
    - [ ] Base Aggregations (8 measures): Total Actual Revenue, Total Forecast Revenue, etc.
    - [ ] Variance & Realization (6 measures): Forecast Variance ₹, Realization %, etc.
    - [ ] Accuracy & Bias (4 measures): Forecast Accuracy %, Bias %, MAPE %, etc.
    - [ ] State Analytics (5 measures): **NEW** State Contribution %, Logistics Drag %, etc.
    - [ ] KPI Signals (3 measures): Status badges (🟢 🟡 🔴)
    - [ ] Supporting Calcs (5+ measures): Margins, per-chain averages, etc.

- [ ] **Quick measure test:**
  - [ ] Report view → Insert blank page
  - [ ] Insert → Card visual
  - [ ] Drag [Total Actual Revenue] onto card
  - [ ] Verify value displays (not NaN, not Infinity, not `undefined`)
  - [ ] Delete test page

---

## Phase 4: Design Report Pages (60 mins)

- [ ] **Page 1: Executive Summary** (15 mins)
  - [ ] Insert → Slicer → Dim_Date[DateKey] (top-left)
  - [ ] Insert → Slicer → Dim_Chain[Chain_Name] (multi-select)
  - [ ] Insert → Slicer → Dim_Product[Category] (multi-select)
  - [ ] Insert → Slicer → Dim_Geography[State] (NEW, multi-select)
  - [ ] Insert → Slicer → Dim_Geography[Zone] (buttons)

  - [ ] Insert → **Card visuals (KPI strip):**
    - [ ] [Total Actual Revenue] (format: ₹ 0.0 Cr)
    - [ ] [Forecast Realization %] (format: 0.0%; status color)
    - [ ] [Budget Realization %]
    - [ ] [Forecast Accuracy %]
    - [ ] [CM2 Governance Flag] (text)

  - [ ] Insert → **Line + Column Combo:**
    - [ ] X-axis: Dim_Date[Month]
    - [ ] Line series: [Total Actual Revenue]
    - [ ] Column series: [Total Forecast Revenue]
    - [ ] Title: "Trend: Actual vs. Forecast"

  - [ ] Insert → **Waterfall Chart:**
    - [ ] X-axis: Waterfall steps (Forecast → +Variance → Actual → -Variance → Target)
    - [ ] Y-axis: [Forecast Variance ₹]
    - [ ] Title: "Variance Breakdown"

  - [ ] Insert → **Horizontal Bar Chart:**
    - [ ] Y-axis: Top 5 States (sorted by [Total Actual Revenue])
    - [ ] X-axis: [State Contribution %]
    - [ ] Title: "State Contribution"

- [ ] **Page 2: Forecast Accuracy** (15 mins)
  - [ ] Add same slicers as Page 1
  - [ ] Insert → Card visuals: [Forecast Accuracy %], [Forecast Bias %], [MAPE %]
  - [ ] Insert → **Table visual:**
    - [ ] Rows: Dim_Geography[State]
    - [ ] Columns: [Forecast Realization %], [Forecast Status] (conditional color)
    - [ ] Title: "Realization by State"

  - [ ] Insert → **Scatter Chart:**
    - [ ] X-axis: [Total Forecast Revenue]
    - [ ] Y-axis: [Total Actual Revenue]
    - [ ] Legend: Dim_Geography[State]
    - [ ] Size: [Total Forecast Qty]
    - [ ] Color: [Confidence Weighted Forecast]
    - [ ] Reference line: 45° (perfect forecast)
    - [ ] Title: "Accuracy Scatter Plot"

  - [ ] Insert → **Column Chart:**
    - [ ] X-axis: Top 10 States (by [Forecast Bias %])
    - [ ] Y-axis: [Forecast Bias %]
    - [ ] Color: Red if negative, Green if positive
    - [ ] Title: "Forecast Bias by State"

- [ ] **Page 3: Regional Performance** (15 mins)
  - [ ] Add same slicers
  - [ ] Insert → Card visuals: [State Contribution %], [State Logistics Drag %], [State Forecast Bias %]
  - [ ] Insert → **Matrix visual:**
    - [ ] Rows: Dim_Geography[State]
    - [ ] Columns: Dim_Chain[Chain_Name]
    - [ ] Values: [Forecast Realization %] (color by status)
    - [ ] Title: "State vs. Chain Performance"

  - [ ] Insert → **Filled Map:**
    - [ ] Location: Dim_Geography[State]
    - [ ] Color saturation: [Forecast Realization %]
    - [ ] Tooltip: State, Realization %, Logistics Drag %
    - [ ] Title: "Geographic Heatmap"

  - [ ] Insert → **Bar Chart:**
    - [ ] Y-axis: Dim_Geography[State] (sorted by [State Logistics Drag %])
    - [ ] X-axis: [State Logistics Drag %]
    - [ ] Title: "Logistics Drag % by State"

- [ ] **Page 4: Demand vs. Actuals** (10 mins)
  - [ ] Add same slicers
  - [ ] Insert → Card visuals: [Forecast Variance ₹], [Forecast Variance %], "Top Missing Chain"
  - [ ] Insert → **Waterfall:** (Forecast → +Demand → +Actual → +Variance → +Target)
  - [ ] Insert → **Table:** Top 20 SKUs by variance (Dim_Product[SKU_Code], [Forecast Variance %])
  - [ ] Insert → **Calibration Table:** Confidence Level → Realization % (shows model quality)

- [ ] **Page 5: P&L & Logistics** (5 mins)
  - [ ] Add same slicers
  - [ ] Insert → **Text Box:** [CM2 Governance Flag] (⚠️ amber if provisional)
  - [ ] Insert → Card visuals: [Gross Margin %], [Contribution Margin %], [Total CM2 Amount]
  - [ ] Insert → **Waterfall:** Revenue → -COGS → Gross → -P&L → CM2
  - [ ] Insert → **Table:** Logistics costs by state
  - [ ] Insert → **Stacked Column:** P&L expense breakdown (only visible if CM2 = APPROVED)

---

## Phase 5: Testing & Validation (20 mins)

### Unit Tests (per measure)

- [ ] **No data → returns 0 (not NaN):**
  - [ ] Slicer: Date = "202512" (future, no data)
  - [ ] Card: [Total Revenue] = 0 ✓

- [ ] **Single state → State Contribution % = 100%:**
  - [ ] Slicer: State = "MH"
  - [ ] Card: [State Contribution %] = 100% ✓

- [ ] **Forecast = 0 → Realization % handled gracefully:**
  - [ ] Create card: [Forecast Realization %]
  - [ ] Verify: 0 or blank displayed (not Infinity) ✓

- [ ] **Color coding works:**
  - [ ] Card: [Forecast Realization %] with conditional formatting
  - [ ] Verify: Green if 95-105%, Yellow if 80-95%, Red if <80% ✓

### Integration Tests

- [ ] **Slicers cascade correctly:**
  - [ ] Select State = "DL" → All visuals update to Delhi only ✓
  - [ ] Select Chain (multi) → Visuals aggregate across chains ✓
  - [ ] Select Date = "202608" → Trends show Aug-26 data ✓

- [ ] **Drill-downs work:**
  - [ ] Click State in State Contribution bar → Page 2 filters to that state ✓
  - [ ] Click Chain in State vs. Chain matrix → Regional Performance page updates ✓

- [ ] **CM2 flag toggles:**
  - [ ] If CM2_Provisional = TRUE → ⚠️ flag visible, P&L Expense chart hidden ✓
  - [ ] If CM2_Provisional = FALSE → ✓ flag visible, P&L Expense chart shown ✓

### Performance Tests

- [ ] **Page load:** <3 seconds (all slicers + visuals loaded)
- [ ] **Slicer change:** <2 seconds (visuals refresh)
- [ ] **Drill-down:** <1 second (navigate to detail page)

---

## Phase 6: Deployment (10 mins)

- [ ] **Save Power BI file:**
  - [ ] File → Save As → Name: `Modern_Trade_Dashboard.pbix`
  - [ ] Location: Preferred path (e.g., OneDrive, SharePoint)

- [ ] **Publish to Power BI Service:**
  - [ ] File → Publish → Select workspace
  - [ ] Wait for upload (may take 1-2 mins for 100M+ rows)

- [ ] **Configure refresh schedule:**
  - [ ] Power BI Service → Dataset settings → Scheduled refresh
  - [ ] Fact_Sales: Daily at 6 AM IST
  - [ ] Fact_Forecast: Weekly (Sunday 10 AM)
  - [ ] Dimensions: Monthly (1st of month)

- [ ] **Share with stakeholders:**
  - [ ] Power BI Service → Workspace → Grant access (Viewer/Editor roles)
  - [ ] Send report link to end-users

- [ ] **Enable mobile layout (optional):**
  - [ ] Power BI Service → Edit → Mobile layout
  - [ ] Design mobile-friendly view for each page
  - [ ] Test on phone/tablet

---

## Phase 7: Documentation & Handoff (10 mins)

- [ ] **Create user guide (optional):**
  - [ ] Explain each page's purpose
  - [ ] Document slicer usage
  - [ ] List common queries & how to answer them

- [ ] **Train end-users:**
  - [ ] Demo each page (5 mins)
  - [ ] Show drill-down navigation (2 mins)
  - [ ] Explain measure meanings (status colors, variance signs) (3 mins)

- [ ] **Monitor dashboard health:**
  - [ ] Check refresh logs weekly (Power BI Service → Dataset → Refresh history)
  - [ ] Alert if refresh fails or slow query detected

---

## ✅ Final Verification

Run this before declaring "done":

```
☐ All 6 tables loaded (Data → Refresh to verify no errors)
☐ All 8 relationships created (Model view → no red X's)
☐ All 30+ measures created and formatted
☐ All 5 pages have slicers + visuals
☐ KPI cards show correct status colors (Green/Yellow/Red)
☐ CM2 flag toggles between ⚠️ and ✓
☐ Drill-downs navigate between pages
☐ No NaN / undefined / [object Object] visible in any visual
☐ Tooltip shows on hover (all visuals)
☐ Dark mode tested (text readable)
☐ PDF/Excel export works
☐ Refresh schedule configured
☐ Shared with stakeholders
☐ User guide created (optional)
```

---

## 📞 Troubleshooting

| Issue | Fix |
|-------|-----|
| "Measure not found" | Verify measure is in `_Measures` table (not Dim_ or Fact_) |
| KPI shows NaN | Check DIVIDE() has 3rd parameter: `DIVIDE(a, b, 0)` |
| Slicer doesn't filter visuals | Check relationships exist in Model view |
| Forecast Realization % always 0% | Verify [Total Forecast Revenue] measure exists |
| Report loads slowly | Enable incremental refresh (Power Query settings) or pre-aggregate facts |
| CM2 flag not showing | Verify CM2_Provisional column exists in Fact_Sales CSV |

---

## 🎉 Success Criteria

You've completed this build when:

1. ✅ All 5 report pages display without errors
2. ✅ All slicers (Date, Chain, State, Category, Zone) filter visuals correctly
3. ✅ KPI cards show realistic values (not 0, not NaN)
4. ✅ Drill-downs work (State → Accuracy page, Chain → Regional Performance)
5. ✅ CM2 governance flag visible on P&L page
6. ✅ Measures pass unit tests (State Contribution % = 100% when single state selected)
7. ✅ Report published to Power BI Service with scheduled refresh
8. ✅ End-users can access and interact with the dashboard

---

**Time estimate:** 2–3 hours (first build); 30 mins (refresh from CSV updates)

**Questions?** See README.md or detailed document sections (01–04).

**Good luck! 🚀**
