# MT Dashboard v1.1.0 — Executive Briefing

**Release Date:** September 4, 2026  
**Status:** Production Live ✅  
**Access:** https://aswalsheshant-cell.github.io/mt-dashboard/

---

## What's New in v1.1.0

### 🎯 Unified 25-Tab Dashboard
A single, comprehensive analytics platform replacing 5+ scattered reports. All tabs accessible from a single navigation bar with consistent filtering and drill-down.

**New Executive Tabs:**
- **Monthly Briefing** — Executive summary with zone/chain/category drill-down and YoY comparison
- **Insights & Way Forward** — Alert center + strategic recommendations
- **Channel Economics** — Distributor profitability, rotation velocity, engagement metrics
- **Execution Excellence** — On-time delivery, fill rates, strike rates, ZDS tracking
- **Demand vs Supply** — Primary/secondary alignment analysis with WAPE and bias metrics
- **Market Research** — ND/WD positioning quadrant, macro drivers, seasonal patterns

### 🟢 RAG Alert System (9 Metrics)
Real-time operational status indicators across all tabs:

| Metric | GREEN | AMBER | RED |
|--------|-------|-------|-----|
| **Alignment Gap %** | <5% | 5–10% | >10% |
| **Numeric Distribution %** | >85% | 75–85% | <75% |
| **Weighted Distribution %** | >80% | 70–80% | <70% |
| **On-Time Delivery %** | >90% | 80–90% | <80% |
| **Fill Rate %** | >95% | 85–95% | <85% |
| **Rotation Days** | <25 | 25–35 | >35 |
| **Forecast Accuracy %** | >80% | 65–80% | <65% |
| **Promo ROI** | >3.0x | 2.0–3.0x | <2.0x |
| **Secondary YoY %** | >15% | 5–15% | <5% |

**Action:** Visit **Insights & Way Forward** → **Alert Center** each week. Any RED alerts require immediate escalation.

### 📊 14-Layer Monthly Insights Engine
Automatically pre-calculated metrics flowing into every tab:
- Alignment & distribution analysis (3 layers)
- Secondary sales velocity & profitability (3 layers)
- Execution & supply chain (3 layers)
- Demand planning & forecasting (2 layers)
- Strategic insights & risks (3 layers)

All metrics update monthly without manual intervention.

---

## Getting Started

### Step 1: Open the Dashboard
Navigate to: **https://aswalsheshant-cell.github.io/mt-dashboard/**

### Step 2: Review the Overview Tab
- **3 RAG Summary Cards** at the top show alignment health, ND%, and WD%
- **Filters** (FY, Zone, Chain) control the entire dashboard

### Step 3: Explore the Monthly Briefing Tab
- Executive summary with month-on-month changes
- Drill down by zone, chain, category
- YoY comparison for trend analysis

### Step 4: Check Insights & Way Forward Tab
- **Alert Center** shows all RED and AMBER metrics
- **Strategic Recommendations** section lists top 3 opportunities per zone
- Use for weekly operational review

---

## Weekly Operations Checklist

**Every Monday (or desired cadence):**

1. ☐ Open: https://aswalsheshant-cell.github.io/mt-dashboard/
2. ☐ Go to **Insights & Way Forward** → **Alert Center**
3. ☐ Check for 🔴 RED alerts:
   - If found: Escalate to Zone Head + Category Manager
   - Action plan required within 48 hours
4. ☐ Check for 🟡 AMBER alerts:
   - If found: Plan corrective action in next commercial review
5. ☐ Review **Monthly Briefing** tab:
   - Scan top 3 challenges
   - Note YoY trends vs prior year

---

## Monthly Refresh Cycle

**When:** First week of month (once new offtake data arrives from stores)

**What Happens:**
1. Monthly store×article offtake data collected
2. Pipeline refreshes dashboard automatically
3. RAG thresholds re-evaluated
4. New insights generated
5. Live dashboard updated within 2 hours

**No action required from you** — automated refresh via CI/CD pipeline.

---

## Key Operational Metrics to Monitor

### Supply Chain Health
- **On-Time Delivery %:** Monitor for drops below 85% (RED)
- **Fill Rate %:** Target >95%; <85% indicates inventory gaps
- **Rotation Days:** <25 days = healthy velocity; >35 days = stale stock risk

### Market Reach
- **Numeric Distribution %:** Target >85%; gaps indicate coverage shortfalls
- **Weighted Distribution %:** Target >80%; indicates value concentration
- **Alignment Gap %:** <5% shows good primary/secondary sync

### Growth & Efficiency
- **Secondary YoY %:** Target >15% growth; <5% triggers strategy review
- **Promo ROI:** Target >3.0x; <2.0x indicates trade spend inefficiency
- **Forecast Accuracy %:** Target >80%; <65% shows demand planning gaps

---

## Frequently Asked Questions

**Q: What if I see a RED alert?**  
A: This indicates a critical KPI breach. Escalate immediately to the zone head and category manager. Corrective action is required within 48 hours.

**Q: Can I filter by specific zones or chains?**  
A: Yes. Use the **Filter Bar** at the top. All 25 tabs respect the filters you set.

**Q: How often does the data refresh?**  
A: Monthly, when new offtake data arrives. The dashboard is updated automatically — no manual steps required.

**Q: What's the difference between AMBER and RED?**  
A: 🟡 AMBER = Warning zone (plan action in next review). 🔴 RED = Critical breach (immediate action required).

**Q: Can I export data from the dashboard?**  
A: Yes. Use the **Download** buttons in the tab footers to export CSV or Excel files for further analysis.

---

## Support & Questions

For technical issues, operational guidance, or data questions:
- Check the **RUNBOOK.md** file in the repository for troubleshooting steps
- Review the **dashboard/index.html** source for code-level details
- Consult the **Insights & Way Forward** tab for strategic recommendations

---

## Timeline & Milestones

| Date | Milestone | Status |
|------|-----------|--------|
| **Sep 4, 2026** | Phase 4 Release (v1.1.0) | ✅ LIVE |
| **Sep 4, 2026** | 25-Tab Dashboard + RAG System | ✅ LIVE |
| **Sep 4, 2026** | GitHub Pages Deployment | ✅ LIVE |
| **Sep 4, 2026** | CI/CD Validation Pipeline | ✅ LIVE |
| **Sep 2026 (Monthly)** | Offtake Data Refresh Cycles | Ready |
| **Q4 2026** | Advanced Domain Skills Integration | Planned |

---

## Contact & Escalation

**Dashboard Technical Issues:**  
Review RUNBOOK.md or create an issue in the GitHub repository.

**Operational Questions:**  
Escalate through your zone head or category manager.

**Strategic Insights:**  
Use the **Insights & Way Forward** tab recommendations or schedule a data deep-dive session.

---

**Ready for executive briefing and operational use.**

🚀 **Next Step:** Share this link with your team: https://aswalsheshant-cell.github.io/mt-dashboard/
