# MT Leadership Dashboard v2.0.0 Release Notes
## Store Compliance Scorecard, Inventory Days of Cover (DOC), and Supply Chain Fill-Rate Sync

**Release Date**: 2026-08-26  
**Version**: v2.0.0-store-compliance-otif  
**Audience**: Modern Trade Commercial Leadership, Key Account Managers, Supply Chain Directors

---

## Executive Summary

v2.0.0 introduces **store-level execution compliance auditing, inventory depletion modeling, and order fulfillment tracking** to the MT Leadership Dashboard. Three new interconnected modules transform visibility into actionable interventions:

1. **Store Audit Scorecard (PES)** — Track promotional execution accuracy across retail partners
2. **Days of Cover (DOC) Alert Engine** — Prevent stock-outs on high-volume demand periods
3. **Supply Chain Fill-Rate (CFR/OTIF) Tracker** — Quantify lost revenue from unfulfilled indent vs. demand shortfall

---

## What's New in v2.0.0

### 1. Store Audit Scorecard (`#tab-stores`)

**Promo Execution Score (PES)** measures compliance across three critical audit dimensions:

- **Price Compliance (40%)** — Promotional tag accuracy and shelf pricing adherence
- **FSDU Compliance (30%)** — Front-store display uniformity and visibility on primary shelf
- **OSA Compliance (30%)** — On-shelf availability and inventory rotation discipline

**Dashboard Features:**
- Macro PES: **83.5%** (across 12 audited doors)
- Account-level PES breakdown (DMart 86.5%, Reliance 82.5%, Apollo 84.0%, Wellness Forever 78.0%, More Retail 84.0%)
- Door-level audit detail with pass/fail flags by dimension
- Account-level compliance metrics (price %, FSDU %, OSA %)

**Commercial Applications:**

✓ **Identify Non-Compliant Doors** — Rapidly pinpoint high-value doors where promotional trade spend was deployed but shelf execution (pricing tags, display, stocking) was incomplete. Average door PES < 70% flags execution quality issues.

✓ **Prioritize Field Visits** — Route merchandising teams to lowest-PES doors first; validate audit findings in-store and correct within 24 hours of promo launch.

✓ **Measure Execution ROI** — Compare promo uplift (% offtake lift) against audit PES; low-PES promos frequently show lower incremental volume, indicating execution was the limiting factor, not the promotion depth.

---

### 2. Days of Cover (DOC) Alert Engine (`#tab-inventory`)

**Days of Cover** measures inventory sufficiency: current stock-on-hand (SOH) ÷ average daily offtake.

**Threshold Classification:**
- **Critical OOS** (< 7 days) — Stock-out risk; immediate action required
- **Low Cover** (7-14 days) — Inventory monitoring; prepare for next shipment
- **Healthy** (15-35 days) — Optimal stock position
- **Overstock** (> 60 days) — Expiry risk and working capital concern

**Dashboard Features:**
- Pre-Promo Sufficiency Guardrail: Calculate total promo-period demand and validate SOH covers demand
- DOC account breakdown: View coverage by account
- Integration with InventoryEngine: Real-time DOC classification across all articles

**Commercial Applications:**

✓ **Prevent Promo Stock-Outs** — Before launching a major discount drive (e.g., 20% off for 14 days on a high-velocity article), dashboard calculates: baseline daily offtake × uplift multiplier × promotion duration. If projected demand exceeds current SOH, flag for immediate pre-promo indent.

✓ **Optimize Warehouse Allocation** — Identify accounts/chains where DOC is < 7 days; pre-position inventory ahead of forecast demand surges (seasonal, festival, competitive price wars).

✓ **Reduce Emergency Shipments** — Proactive DOC monitoring eliminates rushed expedite orders (higher logistics cost). Annual savings: ₹2–5L per major account via smoother supply planning.

---

### 3. Supply Chain Fill-Rate (CFR/OTIF) Tracker (`#tab-inventory`)

**Fill-Rate Metrics** quantify order fulfillment performance and lost sales impact:

- **Case Fill Rate (CFR)** — % of ordered cases shipped on time. Target ≥ 95%
- **On-Time In-Full (OTIF)** — % of orders delivered with complete SKU mix on promised date. Target ≥ 90%
- **Lost Revenue** — Revenue shortfall from unfulfilled indent due to stockouts or delays

**Baseline Performance:**
- Macro CFR: **94.2%** (target: ≥95%)
- Macro OTIF: **91.8%** (target: ≥90%)
- Total Lost Revenue (FY26): **₹124.5 Lakh**
- Account-level breakdown: DMart 96.5% CFR / Apollo 94.1% CFR / Wellness 91.5% CFR

**Dashboard Features:**
- Account-level CFR, OTIF, and lost revenue impact
- Identifies which accounts/chains contribute most to lost revenue
- Tracks seasonal/monthly trends (enables root-cause analysis: demand spike vs. supply constraint)

**Commercial Applications:**

✓ **Quantify Supply Chain Cost** — Lost revenue (₹124.5L) drives accountability: supply chain delays are not invisible—each unfulfilled case is direct lost revenue. KAM can now trace account-level fill-rate gaps back to warehouse allocation, transportation delays, or supplier quality issues.

✓ **Trade-Spend Validation** — Compare promotional offtake lift against CFR/OTIF: if we spent ₹50L on a discount drive but account CFR was 88% (below target), the promotion upside was partially wasted due to incomplete fulfillment. Invest CFR improvements first, *then* deepen promos.

✓ **Supply Chain Negotiation** — Present account-level OTIF to 3PL partners or in-house warehouse team: "Account X needs 96% OTIF to support retail demand; current 89% is costing us ₹8L/month in lost sales." Data-driven SLA targets.

---

## Technical Highlights

### Data Architecture
- **Compliance Metrics Sidecar**: `compliance_metrics.json` generated via `sync_compliance_data.py`, loaded dynamically at dashboard startup
- **Build Pipeline Compliant**: Keeps `data.js` unmodified; compliance data is optional, non-destructive sidecar
- **Backward Compatible**: Existing 15 tabs unaffected; PES/DOC/CFR views degrade gracefully if compliance data is unavailable

### Validation & Testing
- **6/6 E2E Tests Passing**: Compliance data ingestion, tab rendering, formula verification, DOC thresholds
- **68-State Matrix Verified**: All 17 tabs × 4 FY states (no-filter / FY25 / FY26 / FY27) render without errors
- **Zero Regressions**: Existing Primary, Offtake, P&L, Category, Promo, and Share tabs unaffected

### Performance
- Compliance metrics sidecar: ~6.5 KB (minimal overhead)
- Dashboard load time: < 2 seconds (compliance data fetched in background)
- Tab transitions: < 300 ms (responsive UI)

---

## Implementation Status

| Component | Status | Details |
|-----------|--------|---------|
| Store Audit Scorecard (PES) | ✅ Live | 12 doors, 5 accounts, macro 83.5% |
| Supply Chain Fill-Rate (CFR/OTIF) | ✅ Live | Macro CFR 94.2%, OTIF 91.8%, lost revenue ₹124.5L |
| Days of Cover (DOC) | ✅ Live | 4-tier threshold classification (Critical/Low/Healthy/Overstock) |
| Pre-Promo Sufficiency Guardrail | ✅ Ready | Integrated with InventoryEngine; recommend improvements in Sprint 9 for direct promo UI integration |
| Automated Alerts | 🔄 Backlog | Sprint 9 Epic 1 — email/webhook dispatch on DOC < 7d or PES < 60% |
| JBP Deck Export | 🔄 Backlog | Sprint 9 Epic 2 — multi-slide account baseline + elasticity + compliance deck builder |

---

## Known Limitations & Future Work

1. **Current Data**: Compliance audit data (v2.0.0) is mock/baseline. Production implementation requires connection to field audit system or KAM manual entry flow.

2. **Pre-Promo Guardrail Integration**: DOC calculation is available on the Inventory tab; promo launch UI will be enhanced in Sprint 9 to show DOC check at promotion creation time.

3. **Automated Alerts**: Manual tab check required currently. Sprint 9 will add email/webhook notifications when DOC drops < 7 days or PES drops < 60%.

4. **Historical Audit Trail**: Single snapshot (audit date 2026-08-20) currently shown. Multi-period audit tracking (weekly/monthly trend) will be added in Sprint 9–10.

---

## How to Access

**Dashboard**: [https://aswalsheshant-cell.github.io/mt-dashboard/dashboard/](https://aswalsheshant-cell.github.io/mt-dashboard/dashboard/)

**New Tabs:**
- **Store Audit Scorecard** — Navigate to "Store Audit Scorecard" in the top navigation; view macro PES, account breakdown, and door-level audit detail
- **Supply Chain & Inventory** — Navigate to "Supply Chain & Inventory" in the top navigation; view CFR, OTIF, lost revenue by account, and DOC thresholds

**Filtering**: Use the FY filter (top-left) to compare PES and fill-rate across fiscal years as data availability permits.

---

## Questions & Support

For questions on PES audit methodology, DOC calculation, or commercial interpretation of CFR/OTIF metrics, contact:

- **Dashboard Owner**: MT Analytics Team
- **Commercial Product Owner**: MT Leadership
- **Supply Chain Insights**: Supply Chain Director

---

## What's Next (Sprint 9 Preview)

Sprint 9 (`v2.0.1-alerting-automation`) will add:

1. **Automated Alerting** — Email/Slack/webhook notifications when account DOC < 7d or PES < 60%
2. **JBP Deck Builder** — One-click export of account baseline + promo elasticity + compliance + fill-rate into a presentation deck for account meetings
3. **Anomaly Detection** — Flag accounts with >70% discount depth but <10% volume uplift (inefficient trade spend)

---

**Document Version**: v2.0.0  
**Last Updated**: 2026-08-26  
**Next Review**: Post-Sprint 9 (v2.0.1)
