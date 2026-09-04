# Operational Handoff Checklist
## MT Dashboard v1.1.0 — Executive & Governance Activation

**Status:** Phase 4 engineering complete, production live, operational procedures documented  
**Created:** 2026-09-04  
**Owner:** Operations Lead / Project Lead

---

## IMMEDIATE ACTIONS (This Week)

### 1. Push Release Tag v1.1.0 ⏳
**Objective:** Formalize the v1.1.0 release in GitHub.

**Status:** Tag created locally, ready to push.  
**Blocker:** Temporary organizational egress policy (403 on git push).  
**Action:**
- [ ] When network environment permits, execute:
  ```bash
  git push origin v1.1.0
  ```
- [ ] Verify success: Tag should appear in GitHub Releases page
- [ ] Expected URL: `https://github.com/aswalsheshant-cell/mt-dashboard/releases/tag/v1.1.0`

**Timeline:** As soon as egress policy lifts (typically within 24 hours).  
**Responsible Party:** Engineering Lead / DevOps

---

### 2. Distribute Executive Briefing 📧
**Objective:** Alert MT leadership to the new dashboard and activate adoption.

**Materials Ready:**
- ✅ `LEADERSHIP_BRIEFING.md` (6.4 KB, committed to main)
- ✅ Live URL: `https://aswalsheshant-cell.github.io/mt-dashboard/`

**Distribution Template:**

```
Subject: [MT Leadership] Modern Trade Dashboard v1.1.0 Now Live

Hi [Zone Head / Category Manager],

The MT Dashboard v1.1.0 is now live and ready for operational use.

LIVE DASHBOARD: https://aswalsheshant-cell.github.io/mt-dashboard/

WHAT'S NEW:
✓ Unified 25-tab analytics platform (replacing 5+ scattered reports)
✓ Real-time RAG alert system (9 critical KPIs: alignment, distribution, execution)
✓ Monthly Insights & Way Forward (strategic recommendations by zone/chain)
✓ Executive Summary tabs: Monthly Briefing, Channel Economics, Execution Excellence

GETTING STARTED:
1. Open the dashboard link above
2. Review the Overview tab (3 RAG summary cards at top)
3. Navigate to Monthly Briefing for month-on-month analysis
4. Check Insights & Way Forward → Alert Center for RED/AMBER alerts

NEXT STEP:
Join the weekly Monday RAG review (see governance section below for meeting details).

Questions? See the LEADERSHIP_BRIEFING.md guide attached for FAQ.

[Attached: LEADERSHIP_BRIEFING.md]
```

**Action Checklist:**
- [ ] Obtain distribution list: MT Leadership, Zone Heads, Category Managers
- [ ] Customize email with specific names/roles
- [ ] Attach `LEADERSHIP_BRIEFING.md`
- [ ] Send by EOD [Date]
- [ ] Log: Note distribution date and recipient count

**Responsible Party:** Business Lead / Communications

---

### 3. Lock Weekly Governance Cadence 📅
**Objective:** Establish recurring operational review to monitor dashboard health and RAG alerts.

**Meeting Details:**

| Item | Value |
|------|-------|
| **Frequency** | Weekly, every Monday |
| **Duration** | 30 minutes |
| **Time** | [Suggest 10:00 AM or per team preference] |
| **Attendees** | Zone Heads, Category Managers, Area Sales Managers |
| **Owner** | [Name] — MT Leadership |
| **Backup** | [Name] — if primary unavailable |

**Meeting Agenda (30 min total):**

1. **Dashboard Health Check (2 min)**
   - CI/CD status: All workflows green?
   - Last data refresh: Was it successful?
   - Any missing data or JS errors?

2. **Insights & Way Forward Review (15 min)**
   - Navigate to: Insights & Way Forward tab → Alert Center
   - Scan for 🔴 **RED alerts** (critical KPI breaches):
     - Alignment Gap % > 10%
     - Numeric Distribution % < 75%
     - Weighted Distribution % < 70%
     - On-Time Delivery % < 80%
     - Fill Rate % < 85%
     - Rotation Days > 35
     - Forecast Accuracy % < 65%
     - Promo ROI < 2.0x
     - Secondary YoY % < 5%
   - For each RED: Assign owner + 48-hour action plan

3. **Monthly Briefing Drill-Down (10 min)**
   - By zone: month-on-month trends
   - By chain: top performers, underperformers
   - By category: growth drivers, problem areas
   - Questions for data team if anomalies found

4. **Next Steps & Escalations (3 min)**
   - Confirm action owners and deadlines
   - Flag any data quality issues for Data team
   - Schedule follow-up if RED alerts unresolved

**Meeting Materials:**
- Dashboard link: `https://aswalsheshant-cell.github.io/mt-dashboard/`
- RAG threshold reference: See `LEADERSHIP_BRIEFING.md` table
- Insights template: Print or screenshot the Insights & Way Forward tab each week

**Action Checklist:**
- [ ] Send calendar invite to all Zone Heads
- [ ] Include meeting agenda above in the invite description
- [ ] Designate primary owner and backup for meeting facilitation
- [ ] Add to company calendar as recurring (every Monday, indefinitely)
- [ ] Share dashboard link in meeting description
- [ ] Confirm attendance: Target 8+ participants

**Responsible Party:** Operations Lead

**First Meeting:** Next Monday (within 7 days)

---

## MONTH-END PREPARATION (Weeks 2–4)

### 4. Stand By for Data Refresh 📊
**Objective:** Prepare operations to execute monthly offtake refresh when data arrives.

**Timeline:**
- **Data Arrival:** Expected within first week of each month
- **Refresh Execution:** Same day or next business day
- **Dashboard Update:** Automatic via CI/CD (within 2 minutes of push)

**Pre-Refresh Preparation:**

**Data Team Responsibilities:**
- [ ] Confirm offtake files collected and ready
- [ ] Place files in: `PowerBI/RawDataFolders/offtake_monthly/`
- [ ] Notify Data Pipeline Operator: "Offtake files ready for refresh"

**Data Pipeline Operator Responsibilities:**
- [ ] Receive notification of file arrival
- [ ] Follow: `MONTHLY_REFRESH_PROCEDURE.md` (7-step process)
  1. Verify files
  2. Backup current data.js
  3. Run offtake-patch rebuild
  4. Validate data integrity
  5. Commit and push to main
  6. Monitor CI/CD (3 workflows)
  7. Verify live dashboard
- [ ] Estimated duration: 15–30 minutes
- [ ] Notify leadership when complete: "Dashboard updated with [month] data"

**Leadership/Operations Responsibilities:**
- [ ] Schedule weekly RAG review for the Tuesday after refresh (to review new month data)
- [ ] Mark calendar: "Dashboard updates expected by [date]"
- [ ] Be ready to review Insights & Way Forward for new month

**Responsible Party:** Data Lead (oversight), Data Pipeline Operator (execution)

---

## OPERATIONAL DOCUMENTATION INVENTORY

### Reference Materials (All Committed to `main`)

| Document | Purpose | Audience | Link | Status |
|----------|---------|----------|------|--------|
| **LEADERSHIP_BRIEFING.md** | Executive overview + getting started | MT Leadership, Zone Heads | [`repo/LEADERSHIP_BRIEFING.md`](https://github.com/aswalsheshant-cell/mt-dashboard/blob/main/LEADERSHIP_BRIEFING.md) | ✅ Distribute |
| **RUNBOOK.md** | Full operations manual (25 sections) | Operations Team, Operators | [`repo/RUNBOOK.md`](https://github.com/aswalsheshant-cell/mt-dashboard/blob/main/RUNBOOK.md) | ✅ Ready |
| **MONTHLY_REFRESH_PROCEDURE.md** | Step-by-step monthly refresh guide | Data Pipeline Operator | [`repo/MONTHLY_REFRESH_PROCEDURE.md`](https://github.com/aswalsheshant-cell/mt-dashboard/blob/main/MONTHLY_REFRESH_PROCEDURE.md) | ✅ Ready |
| **PHASE_4_COMPLETION.txt** | Engineering completion report | Project Archive, Stakeholders | [`repo/PHASE_4_COMPLETION.txt`](https://github.com/aswalsheshant-cell/mt-dashboard/blob/main/PHASE_4_COMPLETION.txt) | ✅ Archived |
| **OPERATIONAL_HANDOFF.md** | This document: transition checklist | Operations Lead | [`repo/OPERATIONAL_HANDOFF.md`](https://github.com/aswalsheshant-cell/mt-dashboard/blob/main/OPERATIONAL_HANDOFF.md) | ✅ This file |

---

## ESCALATION MATRIX

### Who to Contact for What

| Issue | Contact | Response Time | Action |
|-------|---------|----------------|--------|
| **RED Alert on Dashboard** | Zone Head / Category Manager | Immediate | Assign 48-hour action plan |
| **Data Quality (NaN, undefined, missing month)** | Data Team Lead | 1–2 hours | Investigate source, re-run refresh |
| **Dashboard Won't Load** | Engineering Lead | 30 minutes | Check GitHub Pages status, CI/CD logs |
| **CI/CD Pipeline Failed** | DevOps Lead | 1 hour | Review Actions logs, trigger fix |
| **Questions on TAB functionality** | Business Analyst | 1 hour | Reference RUNBOOK.md sections 1–5 |
| **Questions on Monthly Refresh** | Data Pipeline Operator | 30 minutes | Reference MONTHLY_REFRESH_PROCEDURE.md |
| **General Support / FAQ** | Project Lead | 2–4 hours | Direct to LEADERSHIP_BRIEFING.md |

---

## SUCCESS CRITERIA

✅ **Phase 4 handoff is complete when:**

1. **v1.1.0 tag pushed** → Visible in GitHub Releases page
2. **Leadership briefing distributed** → 8+ recipients confirmed receipt
3. **Weekly cadence scheduled** → First Monday meeting confirmed on calendar
4. **Procedures documented** → All 4 operational documents in `main` branch
5. **First month-end refresh executed** → October data loaded and verified
6. **Weekly RAG reviews launched** → 2+ consecutive Mondays completed
7. **Zero critical blockers** → Dashboard fully operational, no unresolved RED alerts

---

## TRACKING & SIGN-OFF

### Action Items Checklist

| # | Action | Owner | Due Date | Status | Sign-Off |
|---|--------|-------|----------|--------|----------|
| 1 | Push v1.1.0 tag | DevOps | [TBD] | ⏳ Pending | |
| 2 | Distribute LEADERSHIP_BRIEFING.md | Comms | [Date] | ⏳ Pending | |
| 3 | Schedule weekly Monday RAG review | Ops Lead | [Date] | ⏳ Pending | |
| 4 | Confirm Zone Head attendance | Ops Lead | [Date] | ⏳ Pending | |
| 5 | Data team prepared for Oct refresh | Data Lead | [Date] | ⏳ Pending | |
| 6 | Operator trained on MONTHLY_REFRESH_PROCEDURE.md | Data Lead | [Date] | ⏳ Pending | |

---

## TRANSITION NOTES

**What's Already Working:**
- ✅ Dashboard is live and accessible on GitHub Pages
- ✅ All 25 tabs functional with FY25/FY26/FY27 data
- ✅ RAG alert system active across all 9 metrics
- ✅ CI/CD pipeline fully automated (validate → ui-smoke → deploy-pages)
- ✅ Monthly refresh idempotent and tested
- ✅ All operational documentation written and committed

**What Needs Leadership Attention:**
- Weekly RAG review cadence (scheduling)
- Executive adoption and communication (briefing distribution)
- Monthly refresh execution coordination (data arrival → operator → deployment)

**What Needs Operator Training:**
- MONTHLY_REFRESH_PROCEDURE.md walkthrough
- CI/CD monitoring and troubleshooting
- Basic dashboard troubleshooting (cache clear, browser refresh)

**Zero Known Blockers:**
- No outstanding bugs or unresolved issues
- Network egress policy delay on tag push is temporary, not a blocker
- All test suites passing, all validations green

---

## APPENDIX: Quick Reference Links

**Live Dashboard:**  
https://aswalsheshant-cell.github.io/mt-dashboard/

**GitHub Repository:**  
https://github.com/aswalsheshant-cell/mt-dashboard

**GitHub Actions (CI/CD Status):**  
https://github.com/aswalsheshant-cell/mt-dashboard/actions

**Latest Release (once tag pushed):**  
https://github.com/aswalsheshant-cell/mt-dashboard/releases/tag/v1.1.0

**Documentation in Repo:**
- Leadership Briefing: `/LEADERSHIP_BRIEFING.md`
- Operations Runbook: `/RUNBOOK.md`
- Monthly Refresh Guide: `/MONTHLY_REFRESH_PROCEDURE.md`
- Completion Report: `/PHASE_4_COMPLETION.txt`

---

**Ready for Executive Handoff.**  
**Engineering Team Transition: Complete.**  
**Operations Team: Stand by for monthly cadence launch.**

