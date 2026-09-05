# Day 1 Assembly Pack — Tuesday, September 8, 2026

**Objective:** Execute the full PBIP Desktop Assembly Phase 1 (4 hours) with zero rework.

**Audience:** Analytics Engineer (Executor)  
**Duration:** 9:00 AM – 5:00 PM IST (with breaks)  
**Success Metric:** PBIP Tabular Data Model (TDM) compiles, all DAX measures load, Power Query flows validate

---

## Pre-Kickoff Ritual (9:00 AM – 9:30 AM)

### 1. Environment Validation (10 min)

```powershell
# Run full pre-flight check again
powershell -ExecutionPolicy Bypass -File .\Verify-Preflight.ps1

# Expected: All 9 checks PASS [PASS] with exit code 0
```

If any check fails → **STOP. Call IT Lead immediately. Do not proceed to step 2.**

### 2. Repository State Check (5 min)

```bash
# Confirm you're on the correct branch
git status
# Expected: "On branch claude/proactive-intelligence-engine-skill-jldjlg"

# Confirm PR #99 is merged to main (or has Finance approval for merge)
git log --oneline -5 main
# Expected: Latest commit includes "Proactive Intelligence Engine skill" message

# Pull latest from remote
git fetch origin
git pull origin main
```

### 3. Dependency Validation (10 min)

```bash
# Activate venv
.\venv\Scripts\Activate.ps1

# Confirm all Python dependencies load
python -c "import openpyxl, lxml, pptx, pandas, numpy, pytest; print('All dependencies loaded.')"

# Run PyTest suite (should pass in < 30 sec)
pytest tests/test_business_validation_dax.py -v

# Expected output:
# test_business_validation_dax.py::TestGAP01AllocationWeighting::test_weights_sum_to_100 PASSED
# test_business_validation_dax.py::TestGAP01AllocationWeighting::test_allocated_total_matches_pool PASSED
# test_business_validation_dax.py::TestGAP02NegativeContributionMargin::test_negatives_preserved PASSED
# test_business_validation_dax.py::TestGAP02NegativeContributionMargin::test_status_badges_align PASSED
# test_business_validation_dax.py::TestBaselineReconciliation::test_variance_within_tolerance PASSED
# ============ 5 passed in 0.XX seconds ============
```

If PyTest fails → Debug error; escalate to Analytics Lead with screenshot.

---

## Phase 1: Power BI Desktop Assembly (9:30 AM – 2:00 PM)

**Reference Document:** `PowerBI/docs/DEPLOYMENT_RUNBOOK.md` (Sections 1–3)

### Checkpoint 1: PBIP Project Initialization (30 min)

```
1. Launch Power BI Desktop
2. Create new PBIP project:
   - File → New → Power BI Project
   - Project location: C:\Projects\mt-dashboard\
   - Project name: MT_Dashboard_v2.0.1
3. Connect to data source:
   - Home → Get Data → Folder
   - Source folder: \\data-server\MT\Primary\, \\data-server\MT\Offtake\, etc.
   - Load all CSV files
4. Save project:
   - Ctrl + S
   - Filename: MT_Dashboard_v2.0.1
```

**Validation:** PBIP folder appears in file explorer; `.pbip` file exists in project root.

### Checkpoint 2: Power Query Setup (1 hour)

```
1. Paste 25 Power Query (M language) definitions from PowerBI/QuickSetup/PQ_AllQueries.txt
   - In Power Query Editor: Home → New Source → Blank Query
   - Paste each M code block; click "Done"
   - Repeat for all 25 queries
2. Validate all queries:
   - Home → Close & Apply
   - Check Data Explorer tree for 25 queries (no errors in red)
3. Confirm refresh:
   - Right-click any query → Refresh
   - Should load data in < 30 seconds
```

**Validation:** All 25 queries visible in Data Explorer; zero errors; data preview shows row counts > 0.

### Checkpoint 3: DAX Measures & Calculated Columns (1.5 hours)

```
1. Open Semantic Model view (Model tab)
2. Paste all 9 DAX measures from PowerBI/docs/DAX_GAP01_GAP02_MEASURES.md
   - Copy TMDL measure definitions
   - Import into _Measures table via TMDL or manual entry
3. Paste 4 calculated columns from DAX_MEASURES.md
4. Validate each measure:
   - Click on each measure → Check Formula Bar syntax
   - No RED squiggly lines = syntax OK
5. Test DAX calculation:
   - Create a simple Matrix visual: rows = Category, values = [NSV_Jun26_Allocated]
   - Verify numbers populate (no #ERROR or blanks)
```

**Validation:** All 9 measures + 4 columns created; Matrix visual shows data; no #ERROR.

### Checkpoint 4: Relationship & Time Intelligence (30 min)

```
1. Model tab → Manage relationships
   - Confirm all 8 relationships exist (Fact → Dim tables)
   - Verify cardinality (1:M correct)
2. Time dimension:
   - Calendar table present (Date, Month, FY, Quarter columns)
   - Relationships: Fact[Date] → Calendar[Date] (1:M)
3. Test time-based formula:
   - Create measure: [NSV_YTD] = CALCULATE([NSV_Actual_INR], DATESYTD(Calendar[Date]))
   - Create Matrix: rows = Calendar[FY], values = [NSV_YTD]
   - Verify FY25, FY26, FY27 populate correctly
```

**Validation:** Relationships error-free; time hierarchies work; YTD calculation matches baseline.

---

## Phase 2: PBIP Compilation & Validation (2:00 PM – 3:30 PM)

### Build & Compile

```
1. Home → Publish (or File → Publish)
2. Wait for compilation (typically 2–5 minutes)
3. Monitor the Output pane for errors:
   - Green checkmark = Success
   - Red X = Compilation error (details in Output)
```

**If Compilation Fails:**
- Read error message carefully (usually points to bad DAX syntax or circular reference)
- Go back to Model tab; fix the measure
- Re-publish

### Post-Compilation Validation

```
1. Model Browser pane (right-side):
   - Confirm all tables visible
   - Expand each table → verify columns & measures listed
2. Test each of the 9 GAP-01/02 measures:
   - Create report page with Matrix visual
   - Drag [NSV_Jun26_Allocated], [Cont_Margin_Pct], [Cont_Margin_Status] to fields
   - Verify no #ERROR, no blanks, numbers are reasonable
3. Run one full report:
   - Create page with 3–5 charts (column chart, matrix, KPI card)
   - Interact with filters
   - Verify drill-down works
```

**Validation:** PBIP compiles error-free; all 9 measures calculate; sample report interactive.

---

## End-of-Day Handoff (3:30 PM – 5:00 PM)

### Documentation

```
1. Screenshot PBIP folder structure (left pane)
2. Screenshot Semantic Model diagram (all tables visible)
3. Screenshot compilation output ("Success" message)
4. Screenshot sample Matrix visual with GAP-01/02 measures
5. Save all screenshots to: \\data-server\MT\Deployment\Sept8_Screenshots\
```

### Final Checklist

- [ ] Pre-flight validation passed (9/9 checks)
- [ ] PyTest suite passed (5/5 tests)
- [ ] PBIP project created and saved
- [ ] All 25 Power Query definitions loaded
- [ ] All 9 DAX measures created and syntax-validated
- [ ] Relationships configured (8 total, no errors)
- [ ] PBIP compiled successfully (no errors in Output pane)
- [ ] Sample Matrix visual with [NSV_Jun26_Allocated] populates correctly
- [ ] Screenshot package saved to deployment folder
- [ ] Handoff email sent to BI Admin (ready for Phase 2: Service Publication)

### Handoff Email Template

```
From: Analytics Engineer
To: BI Admin, Project Lead
Subject: PBIP Assembly Complete — Ready for Phase 2 Publication (Sept 9)

Day 1 PBIP Assembly (Phase 1) is complete and validated:

Deliverables:
  ✓ PBIP project created: MT_Dashboard_v2.0.1
  ✓ 25 Power Query definitions loaded
  ✓ 9 DAX measures (GAP-01/02) created and validated
  ✓ 8 relationships configured
  ✓ Compilation: SUCCESS (zero errors)
  ✓ Sample visuals: tested and interactive

Handoff:
  - PBIP file location: C:\Projects\mt-dashboard\MT_Dashboard_v2.0.1\
  - Semantic model ready for Service publication
  - Zero blockers for Phase 2

Next Steps:
  - BI Admin: Publish to Power BI Service (Phase 2, ~30 min)
  - Configure refresh schedule + credentials
  - Test in Service environment

Screenshots attached.

Timeline on track for Sept 15 publication target.
```

---

## Troubleshooting Quick Reference

| Issue | Symptom | Root Cause | Fix |
|-------|---------|-----------|-----|
| Pre-flight check fails | `[FAIL] Check 2: Python Version (>= 3.10)` | Python not installed or wrong version | Install Python 3.10+ from python.org; add to PATH |
| PyTest fails | `FAILED test_*.py::TestClass::test_method` | Dependency missing or data issue | Run `pip install -r requirements.txt`; re-run |
| PBIP won't compile | Red X in Output pane; error message | DAX syntax error or circular reference | Fix DAX formula in Model tab; re-publish |
| Measure shows #ERROR | Matrix visual cell shows `#ERROR` | DIVIDE by zero or invalid function | Add `DIVIDE(..., BLANK())` guard; use IFERROR wrapper |
| Data not loading in visual | Matrix visual shows blank cells | Query not refreshed or relationship broken | Right-click table → Refresh; check relationship cardinality |
| Service publication fails | 403 Forbidden or workspace not found | Wrong credentials or workspace permission | Verify Service Principal role (Admin); regenerate token |

---

## Success Criteria for Day 1

**PASS**: PBIP compiles error-free + All 9 measures calculate + Sample report interactive  
**FAIL**: Any P0 blocker unresolved (missing dependency, syntax error, service outage)

---

**Document Version:** 1.0  
**Prepared:** Sept 5, 2026  
**Executor:** [Analytics Engineer Name]  
**Approval Gate:** Sept 7 PM (Finance sign-off + IT handoff)
