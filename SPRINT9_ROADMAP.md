# Sprint 9 Roadmap: Automated Alerting, Anomaly Reporting & JBP Decks
## v2.0.1-alerting-automation (Planned)

**Planned Start Date**: 2026-09-01  
**Target Release**: 2026-09-30  
**Theme**: Operationalize compliance, fill-rate, and trade-spend insights through automated alerts, anomaly detection, and presentation automation

---

## Strategic Objectives

Sprint 9 bridges the gap between **visibility** (Sprint 8: audit scores, DOC, CFR/OTIF) and **action**. Three epics operationalize the metrics via:

1. **Automated Alerts** — Notify KAMs and supply chain when thresholds breach (DOC, PES, fill-rate targets)
2. **Anomaly Detection** — Flag inefficient trade spend and systemic supply issues
3. **Presentation Automation** — Export account snapshots into JBP decks without manual compilation

---

## Epic 1: Threshold Alert & Notification Dispatcher

**Objective**: Automated email/webhook dispatch when account execution or supply chain metrics breach defined thresholds.

### Features

#### 1.1 DOC Depletion Alerts
- **Trigger**: Account Days of Cover drops below 7 days (CRITICAL_OOS status)
- **Audience**: Supply Chain Director, Warehouse Manager, KAM
- **Delivery**: Email + dashboard notification + optional Slack webhook
- **Content**:
  ```
  🚨 CRITICAL: Account XYZ DOC Alert
  Account: Reliance Retail - New Delhi
  Current DOC: 5.2 days
  Risk: Stock-out in 5 days on current demand trajectory
  Recommendation: Pre-position 1,500 units (estimated 15-day cover) from nearest warehouse
  Action Link: [Dashboard DOC Guardrail] [Pre-Indent Form]
  ```

#### 1.2 PES Compliance Alerts
- **Trigger**: Account average PES drops below 60% (quality threshold breach)
- **Audience**: Merchandising Manager, Regional KAM
- **Delivery**: Email + dashboard notification
- **Content**:
  ```
  ⚠️ Alert: Account XYZ PES Dropped Below Target
  Account: DMart - Mumbai Metro
  Current PES: 58.5% (was 85% on 2026-08-20)
  Audit Dimension Breakdown:
    - Price Compliance: 72% (OK)
    - FSDU Compliance: 48% (ISSUE: End-cap not built; planogram not followed)
    - OSA Compliance: 55% (ISSUE: Shelf stockouts; rotation not maintained)
  Action Required: Field visit within 48 hours to correct FSDU and OSA
  ```

#### 1.3 Fill-Rate Target Misses
- **Trigger**: Account CFR or OTIF misses monthly target (CFR < 95%, OTIF < 90%)
- **Audience**: Supply Chain Lead, 3PL Partner Manager
- **Delivery**: Email + dashboard alert + escalation path
- **Content**:
  ```
  Supply Chain Alert: OTIF Miss — Account XYZ
  Account: Apollo Pharmacy - Chennai
  Target OTIF: 90% | Actual: 84% | Gap: -6%
  Estimated Lost Revenue: ₹2.8L (month-to-date)
  Root Cause Analysis: [Dashboard anomaly report] [3PL Performance]
  Action: Review SKU mix with 3PL; validate warehouse allocation
  ```

### Implementation Details

**Backend**:
- Add threshold configuration table: `alert_thresholds.json` (DOC < 7, PES < 60, CFR < 95%, OTIF < 90%)
- Implement alert rule engine: evaluate compliance/fillrate metrics against thresholds on dashboard load
- Webhook dispatcher: integrate with email service (SendGrid) and Slack API

**Frontend**:
- Toast notification on dashboard: "⚠️ Account XYZ DOC alert" with action link
- Alert summary widget on Overview tab: show count of active alerts by type
- Alert detail view: drill into each alert with drill-down anomaly data

**Testing**:
- E2E: Verify email dispatch on threshold trigger
- E2E: Verify Slack webhook POST on alert condition
- Load test: 5,000+ alerts/day scalability check

---

## Epic 2: Automated Joint Business Planning (JBP) Deck Builder

**Objective**: Export account-level insights into a single multi-slide presentation asset for account meetings, eliminating manual slide compilation.

### Features

#### 2.1 Deck Template & Slide Generation
- **Slide 1: Account Executive Summary**
  - Account name, chain, network size, YTD sales/volume
  - Key metrics: avg order value, fill-rate, PES score, DOC status
  - Traffic light KPI dashboard (green = on-target, yellow = at-risk, red = critical)

- **Slide 2: Promo Elasticity (Historical)**
  - Chart: Promotional depth (₹ discount) vs. offtake lift (%) across past 6 months
  - Highlight: elasticity coefficient (e.g., "1% discount → 3.2% volume uplift")
  - Recommendation: "Based on elasticity, optimize next promo depth to 15% (target 4% uplift)"

- **Slide 3: Store Execution Scorecard (PES)**
  - Macro account PES score (account-level view)
  - Door-level heatmap: doors colored by PES (green/yellow/red)
  - Audit dimension breakdown: price/FSDU/OSA compliance by door
  - Recommendation: "Door XYZ: Address FSDU compliance (end-cap); ROI lift +8% post-correction"

- **Slide 4: Supply Chain Fill-Rate Tracking**
  - Month-by-month CFR/OTIF trend (6-month lookback)
  - Current month gap vs. target (CFR %, OTIF %)
  - Estimated lost revenue impact (₹L format)
  - Root cause: "OTIF gap due to SKU mix imbalance; recommend SKU concentration on top-5 articles"

- **Slide 5: Inventory Days of Cover (DOC) Alert**
  - Current DOC by key articles (top 5 by volume)
  - Pre-promo DOC projection: "If we launch 20% off for 14 days, SOH covers 11.2 days (safe)"
  - Recommendation: "Pre-position 2,000 units from warehouse before promo launch"

- **Slide 6: Trade Spend ROI Summary**
  - YTD trade spend (promotional discount + media support)
  - Incremental volume driven (units and revenue)
  - Implied ROI: (incremental revenue - trade spend) ÷ trade spend
  - Recommendation: "Shift ₹10L from inefficient deep-discount promos to FSDU investment; projected ROI +25%"

#### 2.2 Export & Presentation Format
- **Format**: PowerPoint (.pptx) with Mamaearth branding and theme
- **Trigger**: One-click "Export JBP Deck" button on account summary view
- **Output**: Slide deck auto-saved as `JBP_[AccountName]_[Date].pptx`, ready for download and in-person review
- **Optional**: Direct email delivery to account KAM and Regional Manager

### Implementation Details

**Backend**:
- Use `python-pptx` library to generate deck from account metrics
- Create template deck structure with branded placeholders
- Data source: window.DASH + compliance_metrics.json + historical trend aggregation

**Frontend**:
- Add "Export JBP Deck" button to account detail view (e.g., account drill-down on Overview tab)
- Show progress spinner during deck generation (typically < 5 seconds)
- Provide download link + optional email field

**Testing**:
- Generate deck for 5 test accounts; validate slide content accuracy
- Spot-check: promo elasticity calculation matches dashboard math
- Visual QA: check branding, layout, charts render correctly in PowerPoint

---

## Epic 3: Cross-Account Trade Spend & Margin Anomaly Engine

**Objective**: Automated statistical outlier detection to flag inefficient promos and systemic supply issues.

### Features

#### 3.1 Trade Spend Anomaly Detection
**Anomaly**: Account with >70% average discount depth but <10% volume uplift

- **Metric**: Trade Spend ROI = (incremental revenue - trade spend) ÷ trade spend
- **Threshold**: Flag accounts where ROI < 0 (trade spend generates negative return)
- **Example**: 
  ```
  Account: Wellness Forever (Mumbai)
  YTD Promos: 12 campaigns
  Avg Discount Depth: 22% (across 6-month promos)
  Avg Volume Uplift: 3.2% (below category average of 8%)
  Implied ROI: -15% (trade spend not yielding expected lift)
  → Recommendation: Shift ₹5L from deep discounts to FSDU + limited-time flash promos
  ```

**Anomaly Dashboard View**:
- List all accounts with negative trade-spend ROI
- Show depth vs. uplift scatter plot (highlight inefficient outliers)
- Drill-down: view individual promotions; identify which campaigns underperformed

#### 3.2 Supply Chain Anomaly Detection
**Anomaly**: Account with structural CFR or OTIF issues

- **Metric**: Seasonal fill-rate variance; flag accounts with >15% month-to-month OTIF swing
- **Example**:
  ```
  Account: Apollo Pharmacy (All branches)
  Monthly OTIF: [92%, 88%, 78%, 86%, 91%, 84%]
  Variance: 14% (high volatility)
  Pattern: OTIF dips in weeks 2–3 of each month (inventory depletes mid-cycle)
  → Root Cause: Insufficient safety stock; replenishment cycle too long
  → Recommendation: Increase pre-positioned inventory by 20%; reduce replenishment lead time to 5 days
  ```

**Anomaly Dashboard View**:
- Time-series chart: monthly OTIF by account (highlight volatility)
- Statistical flagging: accounts with >2 standard deviations variance
- Correlation analysis: if account OTIF is low, check warehouse allocation % and 3PL SLA compliance

### Implementation Details

**Backend**:
- Calculate trade-spend ROI per account-month
- Perform statistical outlier detection: Z-score > 2 on ROI distribution
- Build CFR/OTIF trend analysis: month-over-month variance calculation
- Flag accounts for review; log anomaly with root cause hypothesis

**Frontend**:
- New "Anomaly Report" tab or section on Analytics tab
- Scatter plot: trade spend depth vs. volume uplift (with outlier annotations)
- Time-series: CFR/OTIF by account (sortable by variance)
- Action links: drill into account, view promo history, access supply chain detail

**Testing**:
- Validate trade-spend ROI formula: confirm against manual calculation
- Verify outlier detection: seed test data with known anomalies; confirm flagged correctly
- Performance: anomaly detection should complete in < 2 seconds for full dataset

---

## Implementation Timeline

| Phase | Week | Deliverable | Status |
|-------|------|-------------|--------|
| **Epic 1: Alerts** | W1–W2 | Alert rule engine + email/webhook dispatcher | Planned |
| | W2–W3 | Dashboard notifications + alert summary widget | Planned |
| | W3 | E2E testing + load testing | Planned |
| **Epic 2: JBP Decks** | W1–W2 | Deck template design + Slide 1–3 generation | Planned |
| | W2–W3 | Slide 4–6 generation + export logic | Planned |
| | W3 | E2E deck generation + visual QA | Planned |
| **Epic 3: Anomalies** | W1–W2 | Trade-spend ROI calculation + outlier detection | Planned |
| | W2–W3 | Supply chain anomaly detection + correlation analysis | Planned |
| | W3 | Anomaly dashboard UI + drill-down views | Planned |
| **Integration & Release** | W4 | E2E testing across all 3 epics + documentation | Planned |
| | W4 | Release candidate (RC1) deployment | Planned |
| | W4 | v2.0.1 tag + release notes + commercial rollout | Planned |

---

## Success Criteria

✓ All 3 epics implemented and integrated  
✓ E2E tests passing for each epic (alerts, deck generation, anomaly detection)  
✓ Load testing: 5,000+ alerts/day without performance degradation  
✓ Deck generation: < 5 seconds per account  
✓ Anomaly detection accuracy: >95% precision (low false-positive rate)  
✓ Commercial rollout: Release notes + KAM training completed  

---

## Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| Alert fatigue (too many false positives) | Threshold tuning post-launch; start conservative (DOC < 5d not <7d) |
| Deck generation performance (slow PDF/PPTX rendering) | Use lightweight python-pptx; cache template structures; test with 1,000+ deck generations |
| Anomaly detection accuracy (false anomalies) | Validate formulas against 6-month historical data; get commercial sign-off on thresholds before launch |
| Integration risk (new epics conflict with existing tabs) | Separate namespacing; add feature flags to disable anomaly/alert features if needed |

---

## Definitions of Done

1. **Code**: All features coded, tested, and merged to `main`
2. **Testing**: E2E + load tests passing; zero regressions on existing 17 tabs
3. **Documentation**: RELEASE_NOTES_v2.0.1.md + internal architecture docs
4. **Commercial Readiness**: KAM training, account rollout plan, support guide
5. **Tag & Deploy**: v2.0.1 tag created and pushed; GitHub Pages live

---

## Open Questions for Commercial & Supply Chain Leadership

1. **Alert Recipients**: Should DOC < 7 days trigger supply chain team, KAM, or both? Escalation path?
2. **PES Thresholds**: Is 60% the right floor for PES alerts? Or should it be 70% (higher bar)?
3. **JBP Deck Frequency**: Monthly deck export, or on-demand for account meetings?
4. **Trade Spend ROI Target**: What is the acceptable floor (breakeven, 10% ROI, 25% ROI)?
5. **Anomaly Review Cadence**: Weekly anomaly review meeting, or monthly?

---

## References

- Sprint 8 Scope: `SPRINT8_IMPLEMENTATION_REPORT.md`
- Sprint 8 Release Notes: `RELEASE_NOTES_v2.0.0.md`
- Dashboard Architecture: `CLAUDE.md` (project guidance)
- InventoryEngine: `dashboard/inventory_engine.js` (DOC calculation reference)

---

**Document Version**: Draft v1.0  
**Author**: MT Analytics & Product Team  
**Status**: Ready for Leadership Review  
**Target Approval**: 2026-08-28
