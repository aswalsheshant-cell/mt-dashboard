# Modern Trade PPT Generator — Phase 4+ Roadmap

**Status:** Planned (Post-production deployment)  
**Target:** Q4 FY27 onwards

Once the production system runs smoothly for 3+ monthly cycles, these enhancements will expand capability and stakeholder value.

---

## 🎯 Phase 4: Advanced Analytics & Trend Intelligence

**Objective:** Add historical context and predictive signals to executive snapshots.

### 4.1 Month-over-Month (MoM) Trend Sparklines

**What:** Embed mini inline charts in the zone table showing 6-month trend (visual at-a-glance performance).

**Implementation:**
```python
# generate_1pager_ppt.py: add_sparklines_to_zone_table()

# For each zone, add 6-month moving average trend
# Green upward arrow if improving, red downward if declining
# Hover-able in PPTX (or visible as PNG with mini bar chart)
```

**Deliverable:** Each zone row shows:
| Zone | Primary (₹ Cr) | Offtake (₹ Cr) | 6M Trend | Gap Status |
|------|---|---|---|---|
| North | 12.4 | 11.1 | ↑↑↑ | 🟡 Amber |
| South-1 | 10.8 | 10.5 | ↑↓↓ | 🟢 Green |

**Effort:** ~8 hours (openpyxl trend calculation + chart embedding)

---

### 4.2 Year-over-Year (YoY) Performance Comparison

**What:** Side-by-side comparison: current month vs. same month last year.

**Implementation:**
- Add YoY tracking database (CSV archive: `/history/YYYY-MM/metrics.csv`)
- On PPT generation, fetch prior-year month metrics
- Display as comparison card: "Primary up 12% YoY, Offtake up 8% YoY"

**Slide Layout Enhancement:**
```
Executive Summary (Current Month)        |  Same Month Last Year
─────────────────────────────────────────────────────────────
Primary: ₹48.2 Cr (+4.2% MoM)           |  ₹43.0 Cr (↑12% YoY)
Offtake: ₹44.6 Cr (+2.8% MoM)           |  ₹41.2 Cr (↑8% YoY)
Gap: 3.6% (Amber)                       |  4.1% (Amber)
```

**Effort:** ~6 hours (CSV archiving + metric lookup + card layout)

---

### 4.3 Zone Performance Ranking (Heat Map)

**What:** Color-coded heat map showing which zones are performing best/worst.

**Implementation:**
- Rank all 6 zones by gap % (Green → Amber → Red)
- Highlight top 2 performers (bright green) and bottom 2 (bright red)
- Add ranking badges: 🥇 🥈 🥉

**Deliverable:**
```
Zone Scorecard (Ranked by Alignment Gap)

🥇 South-1: 2.8% gap (GREEN) — Best alignment
🥈 West: 2.4% gap (GREEN)
🥉 East: 4.6% gap (AMBER)
...
🔴 South-2: 12.5% gap (RED) — Requires immediate action
🔴 North: 10.5% gap (RED)
```

**Effort:** ~4 hours (sorting + badge rendering)

---

## 🎯 Phase 5: Mobile & Multi-Channel Distribution

**Objective:** Enable stakeholders to view and act on data without leaving their tools (Slack, email, mobile).

### 5.1 Responsive HTML Dashboard Version

**What:** Generate an interactive, mobile-friendly HTML version alongside PPTX/PDF/PNG.

**Use Case:** Executives viewing on phone during travel; Slack does not support interactivity.

**Implementation:**
```python
# New function: generate_interactive_html()
# Output: MT_Primary_vs_Offtake_1Pager.html
# 
# Contains:
#  - KPI cards (tap to expand into details)
#  - Sortable zone table
#  - Alert list (tap to expand root cause)
#  - Responsive CSS (mobile-first layout)
```

**Features:**
- 🔄 Swipe between Primary, Offtake, Gap tabs
- 📊 Tap KPI card to see MoM trend chart
- 🗂️ Sort zone table by Primary/Offtake/Gap
- 📱 Responsive design (iPhone, iPad, desktop)
- 🔗 Direct links to detailed PDF/PPTX

**GitHub Actions Update:**
```yaml
- Upload HTML to gh-pages branch → Live at: https://mt-dashboard.github.io/monthly/FY27-Jul.html
```

**Effort:** ~20 hours (HTML + CSS + responsive layout + interactivity)

---

### 5.2 Direct Email Dispatch via SendGrid

**What:** Automatically email PDF to a distribution list (no Slack required).

**Use Case:** Executives who prefer email; international stakeholders outside Slack.

**Implementation:**
```yaml
# .github/workflows/generate_ppt.yml: Add step

- name: Email PDF to Distribution List
  env:
    SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
    RECIPIENTS: "leadership@company.com,zones@company.com"
  run: |
    # Use SendGrid API to attach PDF and send
    python scripts/email_ppt.py \
      --pdf MT_Primary_vs_Offtake_1Pager.pdf \
      --recipients $RECIPIENTS
```

**Email Template:**
```
Subject: [MT] Modern Trade Snapshot — [MONTH YEAR]

Hi Leadership,

Attached is this month's Modern Trade executive snapshot:
- Primary: ₹XX.X Cr (MoM: +X%)
- Offtake: ₹XX.X Cr (MoM: +X%)
- Alignment Gap: X.X% (Status: 🟡 AMBER)

Key Alerts:
- Red zones: [Zone names]
- Action Required: [Top 3 items]

GitHub Link: https://github.com/.../MT_Primary_vs_Offtake_1Pager.pdf

[Signature]
```

**Setup:**
1. Create SendGrid API key
2. Add to GitHub Secrets: `SENDGRID_API_KEY`
3. Configure `RECIPIENTS` email list
4. Next run auto-emails PDF

**Effort:** ~6 hours (SendGrid integration + template + auth)

---

### 5.3 QR Code & Deep Links in Slack

**What:** Add scannable QR code in Slack card; tap links to open specific views.

**Implementation:**
```python
# In Slack notification payload:
{
  "text": "Modern Trade Snapshot Generated",
  "image_url": "https://github.com/.../MT_1Pager.png",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "<https://github.com/.../MT_1Pager.pdf|📄 View PDF>\n" +
                "<https://mt-dashboard.github.io/latest.html|📱 Mobile View>\n" +
                "<https://github.com/.../commit/abc123|🔗 View in GitHub>"
      }
    }
  ]
}
```

**QR Code Feature:** Tap QR in Slack → Opens latest HTML dashboard in mobile browser (no download).

**Effort:** ~3 hours (QR generation + deep link routing)

---

## 🎯 Phase 6: Executive Intelligence & Auto-Escalation

**Objective:** Proactive alerting based on thresholds; escalate critical issues without waiting for the weekly meeting.

### 6.1 Threshold-Based Alert Escalation

**What:** Auto-escalate to leadership if any zone gap exceeds red threshold (>5%).

**Implementation:**
```python
# generate_1pager_ppt.py: check_escalation_thresholds()

if gap_pct > 5.0:
    # Post urgent message to #mt-escalations Slack channel
    escalation_alert = {
        "text": "🚨 CRITICAL ALIGNMENT GAP DETECTED",
        "zone": zone_name,
        "gap_pct": gap_pct,
        "action": "Immediate zone head review required",
        "contact": "@zone_head_slack_handle"
    }
    # POST to Slack webhook
```

**Notification Format:**
```
🚨 CRITICAL: [Zone Name] alignment gap at X.X% (threshold: 5%)
Action required: Zone head [Name] to review by EOD
Link: [PDF] [HTML] [GitHub]
```

**Escalation Chain:**
- Gap >5%? → Alert Zone Head (immediate Slack DM)
- Gap >10%? → Alert MT Commercial Director + CFO
- Gap >20%? → Auto-schedule emergency call (Calendly API)

**Effort:** ~12 hours (threshold logic + escalation routing + integration)

---

### 6.2 Predictive Red Zone Detection

**What:** Use 3-month trend data to predict zones at risk of falling into RED status next month.

**Forecast Logic:**
```python
# If zone has declining 3-month trend AND current gap approaching 5%
# Predict likelihood of RED next month

zones_at_risk = [
    {"zone": "South-2", "current_gap": 4.8, "trend": "↓↓", "risk": "85% → RED next month"},
    {"zone": "North", "current_gap": 5.2, "trend": "↓", "risk": "CRITICAL"}
]
```

**Slide Addition:** "⚠️ Zones at Risk (3-Month Forecast)"

**Effort:** ~16 hours (trend analysis + regression model + visualization)

---

### 6.3 Chain-Level Deep Dive Auto-Generation

**What:** Extend PPT to include a second slide with top 10 retail chains (DMart, Reliance, More Retail, etc.).

**Slide 2 Content:**
```
Chain Performance (National Level)

Chain Name      | Primary (₹ Cr) | Offtake (₹ Cr) | Gap % | Status | MoM
─────────────────────────────────────────────────────────────────────
Reliance (Top)  | 15.2           | 14.1           | 7.2%  | 🔴 RED | ↓
DMart           | 12.8           | 12.1           | 5.5%  | 🟡 AMBER | ↑
More Retail     | 8.5            | 8.2            | 3.5%  | 🟢 GREEN | ↑
[... 7 more]
```

**Implementation:**
- Add chain-level extraction from offtake data
- Loop through top 10 chains
- Generate second slide with table
- Paging: "Slide 1 of 2" indicator

**Effort:** ~10 hours (data extraction + table formatting + multi-slide layout)

---

## 📋 Phase 4–6 Effort Estimate

| Phase | Feature | Effort | Dependencies |
|-------|---------|--------|--------------|
| **4.1** | MoM Sparklines | 8h | Data archiving |
| **4.2** | YoY Comparison | 6h | Historical CSV |
| **4.3** | Zone Heat Map | 4h | None |
| **4 Total** | — | **18h** | Complete by Month 3 |
| **5.1** | Mobile HTML | 20h | None (parallel to 4) |
| **5.2** | Email via SendGrid | 6h | SendGrid account |
| **5.3** | QR Codes | 3h | HTML dashboard (5.1) |
| **5 Total** | — | **29h** | Q4 FY27 (parallel) |
| **6.1** | Auto-Escalation | 12h | Slack webhook (working) |
| **6.2** | Predictive Forecast | 16h | 3-month data archive |
| **6.3** | Chain Deep Dive | 10h | Offtake data structure |
| **6 Total** | — | **38h** | Q4 FY27 + (depends on 4/5) |
| **Grand Total** | — | **85h** | ~3 weeks dev + 2 weeks QA |

---

## 🗓️ Recommended Timeline

| Period | Milestone |
|--------|-----------|
| **Sep 2026** | ✅ Phase 1–3 production go-live |
| **Oct–Nov 2026** | Run 2–3 monthly cycles, gather feedback |
| **Dec 2026** | Kick off Phase 4 (Advanced Analytics) |
| **Jan 2027** | Phase 4 complete; Phase 5 (Mobile) kickoff |
| **Feb 2027** | Phase 5 + 6 development & QA |
| **Mar 2027** | Phase 4–6 production rollout (Q4 FY27 end) |

---

## 💡 Decision Criteria for Prioritization

Evaluate each phase based on:

1. **Stakeholder Demand:** Do zone heads request this feature?
2. **ROI:** Does it reduce manual work or improve decision speed?
3. **Dependencies:** Are upstream systems (data, APIs) ready?
4. **Resource Availability:** Can team commit time without impacting operations?

**Current Priority:** 
- ✅ Phase 5.1 (Mobile HTML) — Highest ROI, independent of others
- ⏳ Phase 4.2 (YoY Comparison) — High demand, moderate effort
- ⏳ Phase 6.1 (Auto-Escalation) — High impact for red zones

---

## 📞 Feedback & Requests

To propose Phase 4+ features:
1. Submit GitHub issue in [mt-dashboard repo](https://github.com/aswalsheshant-cell/mt-dashboard/issues)
2. Label: `enhancement` + `phase-4`, `phase-5`, or `phase-6`
3. Include: Use case, estimated impact, required data/APIs
4. Tag: MT Commercial Director for prioritization

---

**Document Version:** 1.0  
**Last Updated:** 2026-09-04  
**Status:** Planning  
**Next Review:** After 3rd monthly production cycle (Nov 2026)
