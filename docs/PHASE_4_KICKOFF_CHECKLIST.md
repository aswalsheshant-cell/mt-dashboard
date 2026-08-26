# Phase 4 Kickoff Checklist (Pre-Wired for Aug 13)

**Purpose:** Eliminate setup delays; ensure Phase 4 (PBIP Assembly) starts immediately upon Phase 3 sign-off  
**Timeline:** Prepare now (Aug 9–12); execute immediately upon Phase 3 approval (Aug 13)  
**Owner:** PBIP Lead + Analytics Engineering

---

## Phase 4 Scope (PBIP Assembly + Testing)

**Deliverable:** Power BI `.pbix` file for Modern Trade leadership analytics  
**Components:**
- 25 Power Query M scripts (extract from committed `.pq` files)
- 14 DAX measures (extract from committed `.dax` files)
- Seed data (CSVs committed in `PowerBI/SeedData/`)
- Theme and formatting (templates in `PowerBI/theme/`)

**SLA:** Build + test complete by Aug 20 (8 days)  
**Exit Criteria:** `.pbix` opens in Power BI Desktop, all 12 tabs load, KPIs match dashboard within tolerance

---

## Pre-Work (Aug 9–12): Environment Setup

### 1. Verify Power BI Prerequisites

- [ ] **Power BI Desktop installed (Windows only)**
  - Version: 2024.08 or later
  - License: Pro (for publishing)
  - Check: "Help → About" menu
  - If missing: Download from https://powerbi.microsoft.com/downloads/

- [ ] **Power BI local workspace ready**
  - Location: `~/PowerBI_Workspace/` (or C:\Users\[User]\PowerBI_Workspace\)
  - Subdirs:
    - `PQ_Scripts/` (Power Query M files)
    - `DAX_Scripts/` (DAX measures)
    - `SeedData/` (CSV inputs)
    - `Theme/` (theme files)
    - `Build/` (working .pbix during development)
  - Command (Linux/Mac): 
    ```bash
    mkdir -p ~/PowerBI_Workspace/{PQ_Scripts,DAX_Scripts,SeedData,Theme,Build}
    ```

- [ ] **Git repo accessible (clone in Windows if needed)**
  - Path: C:\Users\[User]\Documents\mt-dashboard\ (Windows) or ~/mt-dashboard/ (Linux/Mac)
  - Verify: Can access `.claude/skills/`, `scripts/`, `docs/`
  - Purpose: Reference Phase 2 skills (mt-powerbi-dax, mt-python-pipeline) while building

### 2. Extract & Stage Build Artifacts

- [ ] **Copy Power Query M files to workspace**
  - Source: `PowerBI/PowerQuery/*.pq`
  - Dest: `~/PowerBI_Workspace/PQ_Scripts/`
  - Verify: All 25 files present
  - Command (on Windows): 
    ```powershell
    Copy-Item "PowerBI/PowerQuery/*.pq" -Destination "~/PowerBI_Workspace/PQ_Scripts/" -Recurse
    ```

- [ ] **Copy DAX measure files to workspace**
  - Source: `PowerBI/DAX/*.dax`
  - Dest: `~/PowerBI_Workspace/DAX_Scripts/`
  - Verify: All 14 files present
  - Command:
    ```powershell
    Copy-Item "PowerBI/DAX/*.dax" -Destination "~/PowerBI_Workspace/DAX_Scripts/" -Recurse
    ```

- [ ] **Copy seed data CSVs to workspace**
  - Source: `PowerBI/SeedData/*.csv`
  - Dest: `~/PowerBI_Workspace/SeedData/`
  - Examples: GST_Rate_QC_Table.csv, CustCode_Chain_Map.csv, PL_Expense_Input.csv
  - Verify: All CSVs readable, no encoding issues
  - Command:
    ```powershell
    Copy-Item "PowerBI/SeedData/*.csv" -Destination "~/PowerBI_Workspace/SeedData/" -Recurse
    ```

- [ ] **Copy theme files to workspace**
  - Source: `PowerBI/theme/`
  - Dest: `~/PowerBI_Workspace/Theme/`
  - Files: theme.json, color palette, fonts
  - Command:
    ```powershell
    Copy-Item "PowerBI/theme/*" -Destination "~/PowerBI_Workspace/Theme/" -Recurse
    ```

### 3. Prepare PBIP Master Build Guide

- [ ] **Create Phase 4 BUILD_GUIDE.md**
  - Location: `docs/PHASE_4_BUILD_GUIDE.md`
  - Content:
    - Step-by-step instructions for assembling .pbix in Power BI Desktop
    - Power Query M import process
    - DAX measure definition process
    - Seed data loading
    - Theme application
    - Tab structure mapping (12 tabs from dashboard)
    - Testing checklist (all tabs load, KPIs match, no errors)
    - Deployment instructions (save to version control)
  - Reference: Use `mt-powerbi-dax` skill (DAX patterns) and `PowerBI/docs/RefreshGuide.md`
  - Save to repo: Commit before Aug 13

- [ ] **Pre-wire .pbix skeleton (optional but recommended)**
  - If Power BI supports it: Create blank `.pbix` file with basic data model structure
  - Add: Placeholder tables for Primary, Offtake, P&L, Universe
  - Purpose: Reduce Aug 13 setup time (just add queries + measures)
  - Location: `~/PowerBI_Workspace/Build/MTDashboard_Skeleton.pbix`

### 4. Prepare Testing Artifacts

- [ ] **Create Phase 4 Testing Checklist**
  - Location: `docs/PHASE_4_TESTING_CHECKLIST.md`
  - Content:
    - Tab load tests (all 12 tabs open without errors)
    - KPI verification (Primary NSV, Offtake, GM%, etc. match dashboard ±tolerance)
    - Visual rendering (charts, cards, slicers work as expected)
    - Filter behavior (chain, month, category filters work)
    - Drill-through tests (if applicable)
    - Performance (queries complete in <5s)
    - Error logging (no red X marks, no #ERROR)
  - Save to repo: Commit before Aug 13

- [ ] **Prepare KPI comparison spreadsheet**
  - Purpose: Compare dashboard KPIs to Power BI KPIs for validation
  - Columns: KPI Name | Dashboard Value | Power BI Value | Variance | Status (PASS/FAIL)
  - Pre-fill: Use FY26 data from current `data.js`
  - Save: `~/PowerBI_Workspace/KPI_Comparison_Template.xlsx`
  - Use during Phase 4 testing to validate build accuracy

### 5. Staging Checklist Document

- [ ] **Create PHASE_4_STAGING_STATUS.md**
  - Location: `docs/PHASE_4_STAGING_STATUS.md`
  - Content (to be filled in before Aug 13):
    - [ ] Power BI Desktop version + license verified
    - [ ] Workspace directory created and accessible
    - [ ] 25 PQ scripts copied and verified (count)
    - [ ] 14 DAX files copied and verified (count)
    - [ ] Seed CSVs copied and verified (count)
    - [ ] Theme files copied and verified
    - [ ] BUILD_GUIDE.md created and reviewed
    - [ ] TESTING_CHECKLIST.md created
    - [ ] KPI comparison template prepared
    - [ ] Skeleton .pbix created (if applicable)
    - [ ] All tools accessible (no permissions issues)
  - Use: Daily checklist on Aug 13 morning before starting build

---

## Aug 12 (Day Before Phase 4) — Final Preparations

### Morning (8am–11am)

- [ ] **Verify Phase 3 Sign-Off Received**
  - Check: Email from Finance Controller with signed approval form
  - Verify: Signature, date, certification checkboxes checked (not just form sent)
  - Archive: Save approval form to `docs/PHASE_3_SIGNOFFS/`
  - Notify: Send "Phase 3 APPROVED" email to team + leadership

### Midday (11am–2pm)

- [ ] **Finalize Phase 4 Staging Checklist**
  - Review each item in `PHASE_4_STAGING_STATUS.md`
  - Mark complete/incomplete for each
  - If incomplete: Resolve immediately (download files, install software, fix permissions)
  - Re-test: Verify each artifact one more time before Aug 13

- [ ] **Create Aug 13 Kickoff Document**
  - Location: `docs/PHASE_4_AUG13_KICKOFF.md`
  - Content:
    - Morning: Verify all staging items ✓, open Power BI Desktop
    - 9am: Review BUILD_GUIDE.md, understand 12-tab structure
    - 10am: Begin Power Query M import (start with one query, test, iterate)
    - 12pm: Add DAX measures to model
    - 2pm: Load seed data, apply theme
    - 4pm: Add remaining queries and measures
    - Next day (Aug 14): Full testing against TESTING_CHECKLIST
  - Include: Escalation contacts, troubleshooting guide, rollback procedure

- [ ] **Commit Final Staging Docs**
  - Add to git:
    - `docs/PHASE_4_STAGING_STATUS.md` (current status)
    - `docs/PHASE_4_AUG13_KICKOFF.md` (execution plan)
    - Updates to any other Phase 4 docs
  - Commit message: "docs: Pre-wire Phase 4 environment (ready for Aug 13 kickoff)"
  - Push: `git push origin claude/primary-pipeline-allocation-fy27-l9bdf6`

### Late Afternoon (by 5pm)

- [ ] **Send Team Notification**
  - Email to: PBIP Lead, Analytics Engineer, stakeholders
  - Subject: "Phase 3 APPROVED → Phase 4 Begins Tomorrow (Aug 13)"
  - Content:
    ```
    Phase 3 Business Validation is COMPLETE and APPROVED by Finance Controller.
    
    Phase 4 (PBIP Assembly) begins tomorrow, Aug 13.
    
    All staging is complete:
    ✓ Power BI environment ready
    ✓ Source scripts staged
    ✓ Build guide prepared
    ✓ Testing checklist ready
    
    Timeline: Aug 13–20 (8 days to complete .pbix build + testing)
    Target: Power BI .pbix ready for stakeholder review by Aug 20
    
    Kickoff meeting: Aug 13, 8:30am
    
    See: docs/PHASE_4_AUG13_KICKOFF.md for detailed execution plan
    ```
  - Attach: PHASE_4_STAGING_STATUS.md (proof of readiness)

---

## Aug 13 (Phase 4 Day 1) — Immediate Execution

### Pre-Flight Check (8am–8:30am)

- [ ] **Run through PHASE_4_STAGING_STATUS.md**
  - Verify every item is complete
  - If any item is incomplete: Fix before proceeding
  - Time limit: 30 minutes; escalate if longer needed

### Kickoff (8:30am–9am)

- [ ] **Review PHASE_4_AUG13_KICKOFF.md as a team**
  - Understand day-by-day timeline
  - Clarify responsibilities (who does PQ import, who adds DAX, etc.)
  - Q&A on BUILD_GUIDE.md

### Execution (9am–5pm)

- [ ] **Begin Power Query M Import**
  - Reference: `mt-powerbi-dax` skill (Power Query M patterns)
  - Start with: One simple query (e.g., GST_Rate_QC_Table)
  - Test: Verify data loads, preview looks correct
  - Iterate: Add next query, test, repeat

- [ ] **Create Data Model Star Schema**
  - Reference: `docs/DATA_JS_SCHEMA.md` (data structure)
  - Primary fact table: Primary sales
  - Secondary fact table: Offtake
  - Dimension tables: Chain, Brand, Category, Date
  - Relationships: One-to-many (no circular)

- [ ] **Add DAX Measures (as queries complete)**
  - Reference: `mt-powerbi-dax` skill (10 core measures)
  - Examples:
    - NSV total, YTD NSV, YoY growth
    - GM%, Market Share%
    - Rank, running totals
  - Test each: Verify correctness before moving to next

- [ ] **Document Progress**
  - Log at end of day (5pm):
    - How many PQ scripts added
    - How many DAX measures added
    - Any blockers encountered
    - Plan for Aug 14
  - Save to: `~/PowerBI_Workspace/AUG13_PROGRESS.txt`

---

## Aug 14–20 (Phase 4 Build Week) — Accelerated Timeline

### Daily Structure

**Morning (8am–11am):** Continue Power Query + DAX implementation  
**Midday (11am–2pm):** Test newly added components  
**Afternoon (2pm–5pm):** Troubleshoot issues, document learnings  

### Aug 14 (Day 2)
- [ ] Complete remaining PQ scripts (~50% done by EOD)
- [ ] Add 50% of DAX measures
- [ ] Begin seed data loading

### Aug 15 (Day 3)
- [ ] Complete all PQ scripts
- [ ] Complete all DAX measures
- [ ] Finish seed data + theme application
- [ ] Build should be ~90% complete

### Aug 16–17 (Days 4–5)
- [ ] Full regression testing (TESTING_CHECKLIST)
- [ ] KPI validation vs dashboard (use KPI_Comparison_Template.xlsx)
- [ ] Fix any errors or discrepancies

### Aug 18–19 (Days 6–7)
- [ ] Performance tuning (query optimization, measure calculation time)
- [ ] Documentation (tooltips, labels, navigation guide)
- [ ] Stakeholder walkthrough (demo to Finance, leadership)

### Aug 20 (Day 8 — Delivery)
- [ ] Final QC pass
- [ ] Commit .pbix to version control (if decision made to store it)
- [ ] Or: Package for distribution to Power BI Service / Sharepoint
- [ ] Archive all artifacts (scripts, measures, seed data, theme)
- [ ] Final handoff to business stakeholders

---

## Success Criteria (Phase 4 Completion)

**By Aug 20, the .pbix file must:**

- ✅ Open in Power BI Desktop without errors
- ✅ All 12 tabs load (Data Explorer, Overview, Primary, Offtake, P&L, Category, Forecast, Promo, Market Share, Distribution, Performance, Insights)
- ✅ All KPIs reconcile to dashboard within ±0.5% (or documented tolerance)
- ✅ Filters work (chain, month, category, FY)
- ✅ Visualizations render correctly
- ✅ No #ERROR, #DIV/0!, or N/A values in KPI fields
- ✅ Query refresh completes in <5 seconds
- ✅ Theme applied consistently (colors, fonts, logos)
- ✅ Stakeholder can navigate all tabs and drill down without issues
- ✅ All source code committed (PQ, DAX, seed data) to git

---

## Blockers & Escalation

**If any blocker occurs during Phase 4:**

| Blocker | Mitigation | Escalation |
|---------|-----------|-----------|
| Power BI crashes during import | Restart Power BI, load scripts one at a time | IT + PBIP Lead |
| Data type mismatch (e.g., text vs number) | Cast column in Power Query, test | Data Team |
| DAX measure calculation incorrect | Review formula vs mt-powerbi-dax skill | Analytics Lead |
| Seed data CSV missing or corrupted | Use backup from git history | Data Owner |
| Theme files incompatible | Apply theme manually or create new | Design Lead |
| Performance issue (slow queries) | Optimize PQ fold operations, check relationships | Analytics Engineer |
| Can't reach data source | Verify firewall, VPN, connection string | IT |

---

## Archive & Handoff (Aug 20)

- [ ] **Archive Power BI workspace**
  - Compress: `~/PowerBI_Workspace/` → `PowerBI_Build_Aug20_2026.zip`
  - Store: `docs/archives/` or shared drive

- [ ] **Commit final .pbix to git** (if organization policy allows)
  - Or: Save to OneDrive / SharePoint for distribution
  - Ensure: File is accessible to all stakeholders

- [ ] **Create Phase 4 Completion Report**
  - Location: `docs/PHASE_4_COMPLETION_REPORT.md`
  - Content: Timeline (met/missed dates), testing results, known issues, stakeholder feedback, lessons learned

- [ ] **Handoff to Business Stakeholders**
  - Email: "Modern Trade Power BI Dashboard Ready for Use"
  - Attachment: .pbix file (or link to distribution location)
  - Include: User guide (how to filter, drill down, export)
  - Schedule: Training session for end users (Finance, Marketing, Supply Chain)

---

## Timeline Summary

| Date | Milestone | Owner | Status |
|------|-----------|-------|--------|
| Aug 9–12 | Pre-wire Phase 4 environment | Analytics | 📅 This week |
| Aug 13 | Phase 4 Kickoff (Day 1) | PBIP Lead | 📅 Queued |
| Aug 14–19 | Build + Test (Days 2–7) | PBIP Lead + Eng | 📅 Queued |
| Aug 20 | Final QC + Handoff (Day 8) | Analytics | 📅 Queued |
| Aug 21+ | User Training + Support | Business Operations | 📅 Post-delivery |

---

## Success = Zero Setup Delays on Aug 13

**All pre-work completed before Aug 13 ensures:**
- No "waiting for files" delays
- No "let me install Power BI" delays
- No "where are the scripts?" delays
- August 13 can start building immediately upon Phase 3 sign-off

**Target:** .pbix complete and in stakeholders' hands by Aug 20 (delivered on time).
