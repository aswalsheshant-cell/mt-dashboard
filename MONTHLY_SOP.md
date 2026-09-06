# Modern Trade 1-Pager PPT — Monthly Operating Procedure (SOP)

**Effective Date:** 2026-09-04  
**Audience:** MIS Analysts, Regional Planning Leads, MT Operations Leadership  
**Frequency:** Monthly (1st to 5th business day of each calendar month)

---

## 🎯 Objective

Automate the generation and distribution of executive Modern Trade (Primary vs. Offtake) snapshots to leadership, eliminating manual PowerPoint creation and enabling data-driven weekly RAG reviews.

---

## 📅 Monthly Timeline

| Business Day | Time (IST) | Activity | Owner | Deliverable |
|---|---|---|---|---|
| **WD 1–2** | — | Reconcile primary billing and secondary offtake files | MIS Analyst / Operations Lead | Normalized Excel (.xlsx) ready for data entry |
| **WD 3** | 09:00–16:00 | Fill Excel template with reconciled figures | Regional Planning Lead | Updated `MT_Primary_vs_Offtake_Analysis_Template.xlsx` |
| **WD 3** | 17:00 | **PUSH to GitHub** (triggers automation) | Regional Planning Lead | `git push origin main` |
| **WD 3** | 17:01–17:02 | GitHub Actions runs tests, generates PPTX/PDF/PNG | Automated CI/CD | Test coverage report, multi-format artifacts |
| **WD 3** | 17:02–17:03 | Slack webhook posts success notification | Automated CI/CD | Snapshot card with download links in Slack |
| **WD 4** | 09:00 | **Modern Trade RAG Review Meeting** | MT Commercial Director, Zone Heads, Sales Leads | Discussion, action items, zone accountability |
| **WD 4–5** | — | Follow-up actions on red/amber alerts | Zone Heads, Category Managers | Written closure emails, corrective action plans |

---

## 📋 Step-by-Step Execution Guide

### Step 1: Data Preparation (WD 1–2, Owner: MIS Analyst)

**Task:** Reconcile primary billing data with secondary offtake files to ensure accuracy.

1. Pull primary billing data from ERP system (SAP / NetSuite)
2. Fetch offtake data from all retail chains (Reliance, DMart, More Retail, etc.)
3. Reconcile line-by-line at zone + chain + category level
4. Flag any discrepancies and document assumptions
5. **Deliver:** Clean, reconciled data ready for Excel entry

**Checkpoint:** All zones' primary ≈ offtake (reconciliation variance <5%)

---

### Step 2: Excel Data Entry (WD 3, 09:00–16:00, Owner: Regional Planning Lead)

**Task:** Fill the Excel template with reconciled metrics.

**File:** `MT_Primary_vs_Offtake_Analysis_Template.xlsx`

**Steps:**

1. Open the template in Excel or Google Sheets
   ```bash
   open MT_Primary_vs_Offtake_Analysis_Template.xlsx
   ```

2. **Fill Executive Summary (Row 7–16):**

   | Cell | Metric | Example | Notes |
   |------|--------|---------|-------|
   | B7 | Primary NSV (₹ Cr) | 48.2 | National Primary Sales Value |
   | B8 | Primary MoM (%) | +4.2 | Month-over-month % change |
   | B11 | Offtake NSV (₹ Cr) | 44.6 | National Offtake Sales Value |
   | B12 | Offtake MoM (%) | +2.8 | Month-over-month % change |

3. **Fill Zone Breakdown (Rows 27–32):**

   | Column | Zone | Primary (₹ Cr) | Offtake (₹ Cr) | Gap (%) |
   |--------|------|---|---|---|
   | A27 | North | 12.4 | 11.1 | auto-calculated |
   | A28 | South-1 | 10.8 | 10.5 | auto-calculated |
   | A29 | South-2 | 11.2 | 9.8 | auto-calculated |
   | A30 | East | 6.5 | 6.2 | auto-calculated |
   | A31 | West | 4.1 | 4.0 | auto-calculated |
   | A32 | Central | 3.2 | 3.0 | auto-calculated |

4. **Fill Alert Bullets (Optional, Column F, Rows 8–11):**
   
   - F8: Custom alert 1 (e.g., "West Zone inventory exceeds 30 days; recommend freeze")
   - F9: Custom alert 2 (e.g., "Reliance shows 3% conversion dip vs prior month")
   - F10: Custom alert 3
   - F11: Custom alert 4
   
   *If empty, alerts auto-generate from data (gap thresholds + red zones)*

5. Save the file locally and **verify all required cells are numeric** (not text or formulas)

**Checkpoint:** 
- ✅ All required cells filled with numbers (no `[Enter Value]` placeholders)
- ✅ No error values (#DIV/0!, #N/A, etc.)
- ✅ Zone totals ≈ national totals (variance <5%)

---

### Step 3: Push to GitHub (WD 3, 17:00, Owner: Regional Planning Lead)

**Task:** Commit and push the updated Excel file to trigger automation.

**Steps:**

```bash
# Navigate to repository
cd ~/mt-dashboard

# Stage the Excel file
git add MT_Primary_vs_Offtake_Analysis_Template.xlsx

# Commit with clear message
git commit -m "data: update MT Primary vs Offtake for [MONTH-YEAR]

- Primary NSV: ₹48.2 Cr
- Offtake NSV: ₹44.6 Cr
- Alignment gap: 3.6% (Amber)
- Red zones: [zone names if any]"

# Push to main (triggers GitHub Actions)
git push origin main
```

**Expected output:**
```
To https://github.com/aswalsheshant-cell/mt-dashboard
   abc1234..def5678  main -> main
```

**Checkpoint:** Push succeeds without errors

---

### Step 4: Automated Generation (WD 3, 17:01–17:02, Owner: GitHub Actions)

**Task:** Automated (no human action required).

**What happens:**

1. ✅ GitHub Actions workflow triggered
2. ✅ Python environment set up (3.11)
3. ✅ Dependencies installed (python-pptx, openpyxl, LibreOffice, Poppler)
4. ✅ Data validation runs (31 pytest tests)
5. ✅ PPTX presentation generated
6. ✅ PPTX converted to PDF (headless LibreOffice)
7. ✅ PDF rendered to 300 DPI PNG (Poppler)
8. ✅ All artifacts committed and pushed
9. ✅ Slack webhook notification posted

**To monitor:**
1. Go to [GitHub Actions tab](https://github.com/aswalsheshant-cell/mt-dashboard/actions)
2. Find "Auto-Generate 1-Pager PPT" workflow
3. Watch for ✅ (success) or ❌ (failure)

**If it fails:**
- Click the failed run
- Check the logs for error message
- Common issues:
  - Missing/invalid Excel cell → Fix in Excel and push again
  - Non-numeric value in cell → Re-enter as number
  - Corruption in Excel file → Re-download template and fill fresh

---

### Step 5: Slack Notification (WD 3, 17:02–17:03, Automated)

**Task:** Automated (no human action required).

**What you receive in Slack:**

```
✅ Modern Trade Executive Snapshot
📊 Latest artifacts generated and committed.

📥 Download PPTX (editable)
📄 Download PDF (print-ready)
🖼️ View PNG (mobile-friendly)
```

**Action:** Click desired format link to download artifact

---

### Step 6: Executive RAG Review (WD 4, 09:00, Owner: MT Commercial Director)

**Task:** Weekly leadership meeting to discuss Modern Trade performance.

**Agenda (30 min):**

1. **Overview** (5 min)
   - National Primary vs. Offtake gap
   - MoM trends (Primary up/down, Offtake up/down)
   - Overall RAG status (Green/Amber/Red)

2. **Zone Performance** (15 min)
   - Identify red and amber zones
   - Root cause discussion (supply, demand, execution)
   - Action owner assignments

3. **Chain-Level Deep Dives** (5 min)
   - Top performers vs. laggards
   - Reliance, DMart, More Retail conversion rates

4. **Action Items & Owners** (5 min)
   - Assign follow-ups: zone heads, category managers, chain relations
   - Set closure dates (target: WD 5 COB)

**Participants:**
- MT Commercial Director (Chair)
- Zone Heads (6 regions)
- Category Managers (3 categories)
- Sales Operations Lead
- MIS Analyst (support)

**Materials:** 
- Printed or screenshared PDF/PNG from GitHub
- Backup: Open PPTX in PowerPoint for live edits if needed

---

### Step 7: Follow-Up & Accountability (WD 4–5, Owners: Zone Heads, Category Managers)

**Task:** Execute agreed action items and report closure.

**Timeline:**
- **WD 4 Evening:** Zone heads and category managers assign work to field teams
- **WD 5 Morning:** Field teams execute corrective actions (e.g., promotions, supply rebalancing, retailer outreach)
- **WD 5 EOD:** Written email to MT Commercial Director:
  - Issue and root cause
  - Action taken
  - Expected outcome
  - Closure confirmation

**Example Action Items:**
- "West Zone: Increase secondary distribution to DMart (Top 10 SKUs) by +5% via promotional support"
- "South-1: Reliance fill rate down 8% → Schedule joint inventory review with chain"
- "Central: Distributor stock-outs in Tier-3 → Rush deliver 5 days supply by EOW"

---

## 🚨 Troubleshooting

### Issue: Excel file is "locked" or "read-only"

**Solution:**
1. Close the file in Excel
2. Delete the hidden lock file (usually `.~filename.xlsx`)
3. Re-open and edit

### Issue: GitHub Actions workflow failed

**Steps:**
1. Go to [Actions tab](https://github.com/aswalsheshant-cell/mt-dashboard/actions)
2. Find the failed run and click it
3. Scroll to "Run Test Suite" or "Generate 1-Pager Presentation" step
4. Read error message (e.g., "Cell B7 contains invalid data: '[Enter Value]'")
5. Fix in Excel:
   - Replace text/placeholder with actual number
   - Re-save and push
6. Workflow auto-re-triggers

### Issue: Slack notification not received

**Diagnostic:**
1. Check that `SLACK_WEBHOOK_URL` secret is set in GitHub
2. Verify Slack channel still exists and bot has permission
3. Check GitHub Actions logs for curl error

**Fix:**
1. Go to [GitHub Secrets](https://github.com/aswalsheshant-cell/mt-dashboard/settings/secrets/actions)
2. Update or recreate `SLACK_WEBHOOK_URL` with fresh webhook from Slack
3. Push any file change to re-trigger (e.g., `echo "" >> README.md`)

### Issue: Generated PNG/PDF quality is low

**Solution:**
- Manually adjust in workflow (WD 4 morning, before commit):
  - Edit `.github/workflows/generate_ppt.yml`
  - Change `pdftoppm -r 300` to `pdftoppm -r 600` for higher DPI
  - Commit and next month's run will use new setting

---

## ✅ Pre-Launch Checklist

Before first production run (by WD 3, 17:00):

- [ ] Slack webhook URL configured in GitHub Secrets (`SLACK_WEBHOOK_URL`)
- [ ] Team trained on Excel template cell layout (B7, B11, zones 27–32)
- [ ] MIS analyst and regional planning lead notified of timeline
- [ ] Backup email distribution set up (if Slack unavailable)
- [ ] Stakeholders briefed: they will receive PDF/PNG every 1st Friday

---

## 📞 Support & Escalation

| Issue | Contact | Timeline |
|-------|---------|----------|
| Excel template questions | Data/Ops team | Same day |
| Data reconciliation gaps | MIS Analyst Lead | WD 1–2 |
| GitHub Actions failure | Engineering Lead | 30 min response |
| Slack webhook down | IT/Slack Admin | 1 hour response |
| Workflow/RAG meeting questions | MT Commercial Director | Weekly meeting |

---

## 📊 Monthly Success Metrics

Track these to ensure smooth operations:

| Metric | Target | Measure |
|--------|--------|---------|
| On-time Excel submission | WD 3, 17:00 | % pushed by deadline |
| Test pass rate | 100% | All 31 pytest pass |
| PDF generation success | 100% | No failed runs |
| Slack notification delivery | 100% | Message received in channel |
| RAG review attendance | 100% | All zone heads present |
| Action item closure rate | 100% | Closed by WD 5 EOD |

---

## 📝 Historical Archive

Each month's snapshot is automatically archived in the GitHub repository:

**To view past months:**
1. Go to [GitHub repository](https://github.com/aswalsheshant-cell/mt-dashboard)
2. Check commit history under "Data / Update MT Primary vs Offtake for [Month]"
3. Click commit to view PDF/PNG artifacts from that run
4. Optional: Add to a `/history/YYYY-MM/` folder for browsable archive (Phase 4 enhancement)

---

## 🚀 Launch Readiness

✅ **System Ready for Production**

- ✅ Workflow validated and tested
- ✅ Documentation complete
- ✅ Team trained (SOP distributed)
- ✅ Slack webhook configured
- ✅ First run scheduled for [MONTH/DATE]

**Approval for launch:** [Sign-off by MT Commercial Director]

---

**Document Version:** 1.0  
**Last Updated:** 2026-09-04  
**Maintained By:** Data & Operations Teams  
**Review Cycle:** Quarterly (or as needed)
