# Mock Power BI Dashboard — Sales & Operations Review

**File:** `PowerBI/PBIX_Build_Package/Modern_Trade_Dashboard.pbix` (142 KB)

**Data:** 6,619 rows of realistic sample Modern Trade data (Apr–Sep 2026)  
**Purpose:** Early UX feedback on layout, drill-down workflow, and new operational metrics  
**Status:** Production-ready structure; awaiting real data load post-Finance D1 approval

---

## What to Review

### Page 1: Executive Summary
- [ ] KPI strip reads clearly (Revenue, Forecast Accuracy, CM2 Amount, CM2 %, CM2 Status)
- [ ] Trend line + column chart shows actual vs forecast properly
- [ ] Variance waterfall visualizes gap clearly
- [ ] State contribution bar chart (top 5 states) is readable
- [ ] All slicers (Date, Chain, Category, State, Zone) filter correctly

**Feedback:** ________________

### Page 2: Forecast Accuracy
- [ ] Realization matrix (State rows × Chain columns) shows fill rate
- [ ] Scatter plot (45° reference line) shows forecast quality
- [ ] Forecast bias column chart identifies outliers
- [ ] Drill-down to State works (e.g., click Maharastra → filters accuracy data)

**Feedback:** ________________

### Page 3: Regional Performance
- [ ] State vs Chain matrix shows realization % by intersection
- [ ] Filled map heatmap (geographic saturation) displays correctly
- [ ] Logistics drag bar chart ranks states clearly
- [ ] Tooltip shows State, Realization %, Logistics Drag %

**Feedback:** ________________

### Page 4: Demand vs. Actuals
- [ ] Variance waterfall (Forecast → +Demand → +Actual → +Variance) flows logically
- [ ] Top 20 SKUs by variance table identifies biggest misses
- [ ] Confidence calibration table (Confidence Level → Actual Realization %) shows model quality

**Feedback:** ________________

### Page 5: P&L & Logistics
- [ ] ⚠️ Provisional banner appears (amber, sticky at top)
- [ ] Margin bridge waterfall (Revenue → -COGS → Gross → -P&L → CM2) shows flow
- [ ] Logistics costs by state table (sortable, drillable)
- [ ] P&L expense breakdown visible when CM2 = APPROVED

**Feedback:** ________________

### Page 6: Supply Chain & Operations (NEW)
- [ ] Fill Rate % card shows delivery performance
- [ ] Lost Sales (₹) card shows revenue leakage
- [ ] Trade Spend % card shows promotional intensity
- [ ] Days of Cover (average) shows inventory health
- [ ] SKU Distribution % card shows listing breadth
- [ ] Inventory matrix (Hub rows × SKU columns) with Days of Cover + status colors

**Feedback:** ________________

---

## Global Slicers (All Pages)

- [ ] **Date slicer:** Filters to single month (e.g., Apr-2026)
- [ ] **Chain slicer:** Multi-select (e.g., DMart, Reliance Retail)
- [ ] **Category slicer:** Multi-select (e.g., Beverages, Confectionery)
- [ ] **State slicer:** Multi-select (NEW in this version)
- [ ] **Zone slicer:** Buttons (North, South, East, West)
- [ ] **CM2 Logic slicer (Page 5 only):** Toggle between "Provisional" and "Finance Baseline"

**Feedback:** ________________

---

## New Operational Metrics to Validate

These metrics are new in this release. Please verify they answer the business question clearly.

| Metric | What It Shows | Expected Range | Page |
|--------|---------------|-----------------|------|
| **Fill Rate %** | Delivery completeness vs order | 90–98% | Supply Chain |
| **Lost Sales (₹)** | Revenue from unfulfilled demand | 5–15 Cr | Supply Chain |
| **Trade Spend %** | Promotional intensity | 3–8% of revenue | Supply Chain |
| **Promo Lift %** | Incremental sales from promotion | +15% to +25% | Supply Chain |
| **Days of Cover (DSI)** | Inventory health (7–45 days optimal) | 7–45 days | Supply Chain |
| **SKU Distribution %** | % of chains stocking SKU | >80% core SKUs | Supply Chain |
| **Weighted Distribution** | Sales reach across chains | >75% volume | Supply Chain |

**Do these metrics address your operational questions?** ________________

---

## Drill-Down Navigation

Test these workflows:

1. **Executive → Regional:**  
   Click a state in the State Contribution bar (Page 1) → filters to that state on Page 3

2. **Accuracy → Demand:**  
   Click a state in the realization matrix (Page 2) → shows that state's demand variance on Page 4

3. **Regional → Supply Chain:**  
   Click a chain in the State vs Chain matrix (Page 3) → shows that chain's operational health on Page 6

**Navigation smooth?** ________________

---

## Visual Design Feedback

- [ ] Dark-blue executive theme (primary: #0F4C81) feels appropriate
- [ ] Card styling with blue borders + drop shadows is clean
- [ ] Table headers (dark blue + white text) are readable
- [ ] Color coding (Green/Yellow/Red status) is intuitive
- [ ] Font sizes and spacing are comfortable on-screen
- [ ] Does the layout work on typical laptop screen (1920×1080)?

**Design feedback:** ________________

---

## Drill-Path Intuitiveness

When exploring data, do the filters cascade as expected?

- [ ] Selecting Date filters all pages to that month ✓/✗
- [ ] Selecting Chain filters all metrics to that chain ✓/✗
- [ ] Selecting State + Chain shows only that intersection ✓/✗
- [ ] Clearing slicers returns to "All" view ✓/✗

**Navigation improvements:** ________________

---

## Data Accuracy Check (Sample Validation)

Using the sample data, spot-check one calculation:

1. Pick a state + chain + month combination
2. Verify: Fill Rate % = Delivered_Qty / Ordered_Qty
3. Verify: Trade Spend % sums scheme + promo costs

**Validation results:** ________________

---

## Missing Features or Fields

Are there any metrics, dimensions, or drill-paths you expect but don't see?

**Missing features:** ________________

---

## Production Readiness Assessment

Based on your review:

- [ ] **GO** — Structure is solid, minor cosmetic tweaks acceptable
- [ ] **GO with Notes** — Structure good, please incorporate feedback before final sign-off
- [ ] **HOLD** — Significant structural changes needed before deployment

**Recommendation:** ________________

**Approver Name & Date:** ________________

---

## Next Steps (Post Finance D1 Approval)

Once Finance approves the CM2 formula:

1. Real expense data loads into `PL_Expense_Input.csv`
2. Dashboard connects to actual Modern Trade database (via Power BI Service)
3. All sample data replaced with live data (April–Sep 2026)
4. Provisional banner clears automatically
5. Dashboard publishes to Power BI Service (read-only for stakeholders)

**Estimated time to live:** 2–4 weeks post-approval (dependent on real data availability)

---

**Review Period:** Aug 27–29, 2026  
**Feedback Deadline:** Aug 29, 2026 EOD  
**Distribution:** Sales Leadership, Operations Leadership, Finance MIS  

---

*This is a mock review. Real data will follow Finance approval. No commitments made to UI changes until Design + Product review is complete.*
