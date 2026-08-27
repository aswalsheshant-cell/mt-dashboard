# Sprint 5 Track 3: Promo Depth vs. Offtake Uplift Correlation

**Branch**: `feature/sprint5-offtake-correlation`  
**Base Commit**: a85bdee (v1.6.0-ci-automation)  
**Target Duration**: 4 days (Days 5–8)  
**Status**: KICKOFF

---

## Executive Summary

Model the commercial impact of promotional discount depth on secondary sales (offtake) uplift. Identify high-ROI promotional tiers and quantify dilution risk from excessive discounting across retail chains (DMart, Reliance Retail, Apollo, etc.).

**Key Question**: *For a given discount depth (30%, 50%, 70%), what is the expected offtake volume lift across key account segments?*

---

## Deliverables

### 1. Data Modeling Layer (`scripts/promo_offtake_correlation.py`)

**Input Data**:
- Promotional depth by chain/month (from `promo` block in data.js)
- Offtake volume by chain/month (from `offtake` block in data.js)
- Primary depth metadata (prior-month baseline for MoM comparison)

**Correlation Metrics**:
```
For each (chain, month, discount_tier):
  tier_1  = discount_depth >= 30% AND < 50%
  tier_2  = discount_depth >= 50% AND < 70%
  tier_3  = discount_depth >= 70%

  offtake_lift = (current_offtake - baseline_offtake) / baseline_offtake
  lift_elasticity = offtake_lift / discount_depth  [volume change per 1% discount]
  roi_index = offtake_lift / discount_depth  [return efficiency]
```

**Calculation Stages**:
1. **Baseline Offtake**: Compute rolling 3-month median offtake per chain (excludes spike months)
2. **Promotional Segments**: Classify months by discount depth tier
3. **Lift Quantification**: Compare current vs baseline; flag anomalies (>50% uplift = exceptional)
4. **Elasticity Coefficients**: Aggregate by chain and tier to derive lift curves

**Output Schema** (`correlations` block in data.js):
```json
{
  "correlations": {
    "by_chain": [
      {
        "name": "DMart",
        "elasticity_tiers": {
          "tier_1": { "avg_lift": 0.12, "std_dev": 0.08, "count": 24 },
          "tier_2": { "avg_lift": 0.28, "std_dev": 0.14, "count": 18 },
          "tier_3": { "avg_lift": 0.35, "std_dev": 0.22, "count": 8 }
        },
        "roc_index": 0.45  // Return on capital: tier_2 (50% discount) yields 28% uplift = 0.56x ROI
      }
    ],
    "summary": {
      "highest_roi_tier": "tier_2",  // 50% discounts most efficient
      "dilution_threshold": 0.70,     // 70%+ discount shows diminishing returns
      "optimal_depth_range": "45–55%"
    }
  }
}
```

---

### 2. UI Integration — Offtake Impact Tab (`dashboard/index.html`)

**New Tab**: "Offtake Impact" (tab 11 of 12, between Promo & Insights)

**Layout**:
```
┌─────────────────────────────────────────────────────┐
│  Offtake Impact — Promotional Elasticity Analysis   │
├─────────────────────────────────────────────────────┤
│ Filter Bar:  [Month] [Chain] [Discount Tier]        │
├─────────────────────────────────────────────────────┤
│ Charts Row 1:                                       │
│  1. Elasticity Curves (line chart)                  │
│     X: Discount Depth (0–100%)                      │
│     Y: Offtake Lift (0–60%)                         │
│     Series: By Chain (DMart, Reliance, Apollo, etc) │
│  2. Tier ROI Heatmap                                │
│     Rows: Chains  Cols: Depth Tiers (Tier1/2/3)     │
│     Color: Green (high ROI) → Red (dilution)        │
├─────────────────────────────────────────────────────┤
│ Charts Row 2:                                       │
│  3. Waterfall: Offtake Breakdown                    │
│     Stacked: Baseline + Promotional Uplift + Anomaly │
│  4. Scatter: Depth vs Lift (with trend line)        │
│     Identify outliers (exceptionally high/low lift) │
├─────────────────────────────────────────────────────┤
│ Summary Metrics (KPI Row):                          │
│  • Optimal Discount Range: 45–55%                   │
│  • Avg Lift @ Tier 2: +28%                          │
│  • Dilution Risk Chains: 3 (excessive 70%+ depth)   │
│  • High-ROI Chains: 12                              │
└─────────────────────────────────────────────────────┘
```

**Interaction**:
- Clicking a chain on Elasticity Curves highlights it
- Heatmap drill-down: Click cell → show detail months for that chain/tier
- Scatter outliers: Hover to show chain name, discount depth, offtake lift, and flags
- Filter synchronization: Changing Month filter updates all charts

**Export**: "Export Correlation Report" button → CSV with elasticity data + flags

---

### 3. Data Quality Enhancements

**Outlier Flagging** (`correlations.anomaly_flags`):
```json
{
  "anomaly_flags": [
    {
      "chain": "Apollo",
      "month": "Jul-26",
      "discount_depth": 65,
      "offtake_lift": 3.2,  // 320% lift at 65% discount = extremely high
      "flag": "exceptional_uplift",
      "severity": "high"
    },
    {
      "chain": "Modern Retail",
      "month": "Jun-26",
      "discount_depth": 72,
      "offtake_lift": 0.08,  // Only 8% lift at 72% discount = dilution
      "flag": "dilution_risk",
      "severity": "high"
    }
  ]
}
```

**Baseline Anomaly Detection**:
- Offtake change >50% month-over-month (isolated to promotional months)
- Discount depth > 75% with lift < 15% (negative ROI signal)
- Elasticity coefficient > 1.0 (super-elastic: more than 1% lift per 1% discount)

---

## Implementation Roadmap

### Day 5: Data Modeling & Correlation Engine

**Tasks**:
1. Create `scripts/promo_offtake_correlation.py`
   - Load `promo` and `offtake` blocks from data.js
   - Compute baseline offtake (rolling 3-month median per chain)
   - Calculate lift and elasticity for each depth tier
   - Detect anomalies (exceptional uplift, dilution risk)

2. Extend `scripts/build_dashboard_data.py`
   - Add `--correlations-only` flag for partial rebuild
   - Generate `correlations` block to data.js
   - Merge with existing data (non-destructive)

3. Validation
   - Elasticity coefficients should be 0.2–1.0 for healthy channels
   - Coefficients > 1.0 indicate market saturation or supply constraints
   - Test with mock data (Jul–Sep '26 promos)

**Test Coverage**:
- [ ] Baseline computation doesn't regress when data.js updates
- [ ] Elasticity for tier_1 (30–50% discount) should average ~0.15–0.25
- [ ] Anomaly flags catch dilution cases (>70% discount, <15% lift)
- [ ] No NaN/undefined in output (per CLAUDE.md)

### Day 6: UI Integration & Chart Rendering

**Tasks**:
1. Add "Offtake Impact" tab to `dashboard/index.html`
   - Tab structure: `<section id="tab-offtake-impact"></section>`
   - Filter bar: [Month] [Chain] [Discount Tier] dropdowns
   - Update `show()` function to render this tab

2. Implement chart functions:
   - `buildOfftakeImpact()`: Main rendering orchestrator
   - `renderElasticityCurves()`: Line chart (discount depth vs lift)
   - `renderROIHeatmap()`: Heatmap (chains × tiers)
   - `renderWaterfall()`: Stacked breakdown
   - `renderScatterTrend()`: Outlier detection chart

3. Integrate filters
   - `offtakeImpactFilters` state object (Month, Chain, Tier)
   - Event listeners on filter dropdowns
   - Chart re-render on filter change

**Chart Configuration**:
- Elasticity Curves: `chart.js` line chart, multiple series per chain
- ROI Heatmap: Custom canvas gradient heatmap (green=high ROI, red=dilution)
- Waterfall: Stacked bar chart, colors: baseline (gray), uplift (green), anomaly (orange)
- Scatter: Bubble chart with trendline (LOESS smoothing)

### Day 7: Polish & Cross-Tab Validation

**Tasks**:
1. Drill-down wiring
   - Clicking chain on Elasticity Curves filters Promo tab to that chain
   - Clicking heatmap cell shows detail months in drill table
   - Scatter outliers link to Promo tab for detail review

2. Export functionality
   - `exportOfftakeCorrelations()`: CSV with elasticity data + flags
   - Filename: `offtake_impact_YYYY-MM-DD.csv`

3. Mobile/responsive testing
   - Heatmap scales responsively
   - Charts don't overlap on smaller screens
   - Filter bar wraps gracefully

4. Error handling
   - No uplift data for a chain → show "–" (not NaN)
   - Insufficient historical data for baseline → flag and skip
   - Elasticity coefficient anomalies logged to console (no UI crash)

### Day 8: Documentation & Final QA

**Tasks**:
1. Inline documentation
   - JSDoc comments for `promo_offtake_correlation.py` functions
   - HTML template comments explaining filter logic
   - README: "Offtake Impact Tab — User Guide"

2. Final QA sweep
   - All 12 tabs (including new Offtake Impact) functional
   - No console errors or warnings
   - Elasticity curves render smoothly for 30+ chains
   - Anomaly flags properly classified and colored

3. Prepare PR
   - Title: `feat(analytics): Promo depth vs. offtake uplift correlation engine`
   - Body: Summary, test results, elasticity coefficients, anomaly flags

---

## Code Architecture

### New Functions

```javascript
// Offtake Impact orchestrator
function buildOfftakeImpact()         → void (renders entire tab)
function renderElasticityCurves(data) → Chart.js line chart
function renderROIHeatmap(data)       → Canvas heatmap
function renderWaterfall(data)        → Chart.js stacked bar
function renderScatterTrend(data)     → Canvas bubble chart with trendline

// Data processing
function computeOfftakeBaseline(chains, months)     → {chainName: baseline}
function calculateElasticity(promo, offtake)        → {chain: {tier: elasticity}}
function detectAnomalies(promo, offtake, elast)     → [flags]
function wireOfftakeImpactFilters()                 → void (event listeners)
function getCorrelationFilteredData()               → {curves, heatmap, scatter}
function exportOfftakeCorrelations()                → CSV download

// Chart utilities
function LOESS(x, y, bandwidth = 0.3)  → trendline coefficients
function heatmapColor(roi_value)       → CSS color (green ↔ red)
```

### Data Dependencies

```
Input:
  - D.promo.by_chain[].avg_offer_pct (discount depth)
  - D.promo.by_chain[].promos (SKU count, proxy for volume)
  - D.offtake.by_chain[].volume (monthly offtake data)
  - D.primary.by_chain[].prior_depth (baseline for comparison)

Output (new):
  - D.correlations.by_chain[].elasticity_tiers
  - D.correlations.anomaly_flags[]
  - D.correlations.summary.optimal_depth_range
```

---

## Testing Strategy

### Unit Tests (Day 5–6)
- [ ] Baseline computation: median of non-spike months
- [ ] Elasticity calculation: lift / discount_depth ∈ [0.1, 1.5]
- [ ] Anomaly detection: flags raised for dilution (>70% discount, <15% lift)
- [ ] No NaN/undefined in output

### Integration Tests (Day 7)
- [ ] Tab rendering: Offtake Impact tab loads without errors
- [ ] Filters: Changing Month/Chain/Tier re-renders charts
- [ ] Drill-down: Clicking chart element filters Promo tab
- [ ] Export: CSV valid and opens in Excel/Sheets

### Cross-Tab Validation (Day 8)
- [ ] All 12 tabs functional (no regressions)
- [ ] Elasticity data visible in new tab
- [ ] Links to Promo tab don't break existing filter state
- [ ] Performance: Chart render <500ms for 30+ chains

---

## Acceptance Criteria

✓ Elasticity engine computes lift per discount tier  
✓ Offtake Impact tab renders with 4 chart types  
✓ Filters (Month, Chain, Tier) functional and sync  
✓ Anomaly flags identify dilution and exceptional uplift  
✓ Export to CSV working  
✓ No console errors or NaN/undefined in UI  
✓ 12-tab dashboard functional (no regressions)  
✓ Performance: Chart re-render <500ms  

---

## Success Metrics

1. **Commercial**: Identify top-3 high-ROI tiers per chain (e.g., "DMart: 45–55% discount yields 24% uplift")
2. **Risk Mitigation**: Flag dilution-at-risk chains (e.g., "Apollo: 70% discount shows only 8% lift")
3. **Usability**: Elasticity curves are discoverable and interactive
4. **Data Integrity**: No regressions to FY25/FY26 baseline metrics

---

## Known Limitations & Future Work

1. **Elasticity Assumptions**: Linear model; actual elasticity may be non-linear at extremes
2. **Seasonal Factors**: Correlation does not account for holiday/festival seasonality
3. **Causality**: Offtake lift attributed to discount, but external factors (supply, competitor actions) could influence
4. **Real-Time Updates**: Correlation snapshot at merge time; doesn't auto-update if new offtake data arrives
5. **Mobile UX**: Charts optimized for desktop; mobile heatmap may be cramped

---

## Review Checklist

- [ ] Python correlation engine syntax validated
- [ ] Chart rendering tested in Chrome, Firefox, Safari
- [ ] All 12 tabs pass smoke test (12 × 4 FY states = 48 state matrix)
- [ ] Baseline FY25/FY26 metrics unchanged
- [ ] No hardcoded FY25/FY26; uses dynamic FY derivation
- [ ] CSV export valid and opens cleanly
- [ ] PR description includes elasticity coefficients and anomaly flags

---

## Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| **Phase 1** | Data modeling & correlation engine | Day 5 | NEXT |
| **Phase 2** | UI integration & chart rendering | Day 6 | PENDING |
| **Phase 3** | Polish & cross-tab validation | Day 7 | PENDING |
| **Phase 4** | Documentation & final QA | Day 8 | PENDING |

**Estimated Completion**: End of Day 8 (2026-08-29)

---

**Spec Owner**: Claude Haiku 4.5  
**Last Updated**: 2026-08-26  
**Status**: Ready for Development Kickoff
