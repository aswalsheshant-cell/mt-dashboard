# Downloadable Templates & Analysis Tools
## MT Dashboard v1.1.0

All templates and analysis tools are ready for download and operational use.

---

## Primary vs Offtake Analysis

### 📊 Excel Template (Recommended for Data Entry)
**File:** `MT_Primary_vs_Offtake_Analysis_Template.xlsx`

**What's Included:**
- Executive Summary (Primary, Offtake, Alignment Gap)
- National Level Comparison (variance analysis, MoM/YoY)
- Zone-Level Breakdown (6 zones, gaps, trends)
- Top 5 Chains Analysis (Primary, Offtake, status)
- Rotation Analysis (Days on Hand tracking)
- Conversion Rate Analysis (Offtake/Primary %)
- RED/AMBER/GREEN Alert Sections
- Sign-off and approval section

**How to Use:**
1. Download the Excel file
2. Fill in current month data from the MT Dashboard
3. Use formulas for calculations (Variance % = (Offtake - Primary) / Primary × 100)
4. Highlight RED/AMBER alerts for discussion
5. Share with Zone Heads and Category Managers
6. Track action owners and deadlines

**File Size:** ~50 KB  
**Format:** .xlsx (Excel 2007+)  
**Sheets:** 1 (Monthly Analysis)  
**Ready to Use:** ✅ Pre-formatted with styles, headers, borders

---

### 📄 Markdown Template (For Documentation/Version Control)
**File:** `MONTHLY_PRIMARY_vs_OFFTAKE_ANALYSIS.md`

**What's Included:**
- Same structure as Excel template
- Additional sections: Category Waterfall, Data Quality Checks
- Interpretation guides and insights
- Recommendations and next steps

**How to Use:**
1. Copy the markdown file as a base
2. Update monthly data sections
3. Add insights and analysis
4. Commit to version control (git)
5. Share with team for review and discussion

**File Size:** ~20 KB  
**Format:** .md (Markdown)  
**Ready to Use:** ✅ Complete template with examples

---

## Operational Documentation

### 📖 Core Handoff Documents

| Document | Purpose | Download | Size |
|----------|---------|----------|------|
| **LEADERSHIP_BRIEFING.md** | Executive overview for MT Leadership | `/LEADERSHIP_BRIEFING.md` | 6.4 KB |
| **RUNBOOK.md** | Complete operations manual | `/RUNBOOK.md` | 13 KB |
| **MONTHLY_REFRESH_PROCEDURE.md** | Step-by-step data refresh guide | `/MONTHLY_REFRESH_PROCEDURE.md` | 12 KB |
| **OPERATIONAL_HANDOFF.md** | Governance activation checklist | `/OPERATIONAL_HANDOFF.md` | 8 KB |
| **PROJECT_COMPLETION_SIGN_OFF.md** | Final project sign-off | `/PROJECT_COMPLETION_SIGN_OFF.md` | 10 KB |

**Access:** All files in the GitHub repository root  
**URL:** https://github.com/aswalsheshant-cell/mt-dashboard/

---

## How to Download from GitHub

### Option 1: Download Individual Files
1. Open GitHub repository: https://github.com/aswalsheshant-cell/mt-dashboard
2. Click on the file you want (e.g., `MT_Primary_vs_Offtake_Analysis_Template.xlsx`)
3. Click "Download raw file" (button on the right side)
4. File downloads to your Downloads folder

### Option 2: Clone the Entire Repository
```bash
git clone https://github.com/aswalsheshant-cell/mt-dashboard.git
cd mt-dashboard
```
All files are now available locally.

### Option 3: Download as ZIP
1. Click "Code" (green button)
2. Select "Download ZIP"
3. Extract the ZIP file
4. All templates and documentation are included

---

## Monthly Workflow Using Templates

### Week 1: Data Refresh
1. Receive offtake files from Data team
2. Run monthly refresh: `python3 scripts/build_dashboard_data.py --offtake-patch ...`
3. Download fresh data from MT Dashboard

### Week 2: Analysis & Documentation
1. Open Excel template: `MT_Primary_vs_Offtake_Analysis_Template.xlsx`
2. Fill in data from the Dashboard (Primary, Offtake, by Zone/Chain/Category)
3. Highlight RED/AMBER alerts
4. Draft action plans for each alert

### Week 3: Weekly Review Meeting
1. Share the completed analysis
2. Present to Zone Heads and Category Managers
3. Assign owners for RED alerts (<48h response)
4. Track AMBER alerts (next review follow-up)

### Week 4: Monthly Sign-Off
1. Finalize analysis with approvals
2. Document actions taken and results
3. Archive for reference

---

## Quick Start

### For Executives
→ Read: `LEADERSHIP_BRIEFING.md`  
→ Access: https://aswalsheshant-cell.github.io/mt-dashboard/

### For Operations Team
→ Read: `RUNBOOK.md`  
→ Download: `MT_Primary_vs_Offtake_Analysis_Template.xlsx`

### For Data Pipeline Operator
→ Read: `MONTHLY_REFRESH_PROCEDURE.md`

### For Weekly RAG Review
→ Use: `MT_Primary_vs_Offtake_Analysis_Template.xlsx`  
→ Follow agenda in: `OPERATIONAL_HANDOFF.md`

---

## Support & Questions

**For analysis questions:**
- Check: `MONTHLY_PRIMARY_vs_OFFTAKE_ANALYSIS.md` (interpretation guide)
- Escalate: Category Manager or Zone Head

**For operational questions:**
- Check: `RUNBOOK.md` (Sections 1–5)
- Escalate: Operations Lead

**For dashboard access:**
- URL: https://aswalsheshant-cell.github.io/mt-dashboard/
- Contact: Engineering Lead (if broken)

---

**Last Updated:** 2026-09-04  
**Version:** v1.1.0 Phase 4 Complete

