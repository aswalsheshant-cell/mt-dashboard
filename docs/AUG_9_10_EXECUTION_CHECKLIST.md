# August 9–10 Execution Checklist

**Purpose:** Ensure smooth hand-off from Phase 2 (Finance Decisions) to Phase 3 (Business Validation)  
**Critical Path:** Aug 9 EOD → Aug 10 EOD → Aug 11 Reconciliation  
**Owner:** Analytics Lead + Finance Coordinator

---

## AUGUST 9 (TODAY) — Finance Decision Finalization

### Morning (by 10am)

- [ ] **Verify Finance has FINANCE_DECISION_PACK.md**
  - Location: `docs/FINANCE_DECISION_PACK.md` (311 lines)
  - Check: Finance received email link or PDF export
  - Contact: CFO/Finance Controller if not received
  - Action: Re-send if needed

- [ ] **Confirm Finance Decision Timeline**
  - Ask: "When will Decision 1 (A/B/C) and Decision 2 (RETAIN/ZERO-FLOOR) selections be submitted?"
  - SLA: Due by 5pm today (Aug 9)
  - Contact: finance@honasa.com or direct call to Finance Controller
  - Escalation: If no response by 2pm, escalate to leadership

### Afternoon (by 2pm)

- [ ] **Monitor Finance Decision Email**
  - Watch inbox for: "Finance Decision Approval Form" or similar subject
  - Expected content: Decision 1 choice (A/B/C), Decision 2 choice (RETAIN/ZERO-FLOOR), approver name, date
  - Flag: If form is incomplete or ambiguous, request clarification immediately

- [ ] **Review Decision Selections Against FINANCE_DECISION_PACK**
  - Compare Finance choices to business impact summary in pack
  - Verify: Selections align with stated rationale and risk appetite
  - If mismatch: Confirm with Finance (may indicate misunderstanding)

### Late Afternoon (by 4pm)

- [ ] **Prepare Phase 2 Implementation Script**
  - Script location: `scripts/phase2_finance_decision_implementation.py`
  - Pre-test: Run a dry-run with dummy selections to verify no issues
  - Command: 
    ```bash
    python scripts/phase2_finance_decision_implementation.py \
      --decision1 A \
      --decision2 RETAIN \
      --approver-email test@example.com \
      --approval-date 2026-08-09
    ```
  - Verify: No errors, correct exit code (0)

### End of Day (by 5pm)

- [ ] **Execute Phase 2 Implementation (Upon Finance Approval)**
  - Once Finance email received with Decision 1 and Decision 2:
    ```bash
    python scripts/phase2_finance_decision_implementation.py \
      --decision1 <A|B|C> \
      --decision2 <RETAIN|ZERO-FLOOR> \
      --approver-email <finance-email> \
      --approval-date 2026-08-09
    ```
  - Capture: Screenshot or log of successful execution (exit code 0)
  - Artifacts: Check for `docs/PHASE_2_IMPLEMENTATION_*.txt` report

- [ ] **Verify Release Gate G10 Configuration Updated**
  - Check: `scripts/release_gate.py` line 192 shows updated approval status
  - Verify: `jun26_allocation_status` = APPROVED or PROVISIONAL (per Decision 1)
  - Verify: `negative_frac_treatment_status` = PROVISIONAL or ZERO-FLOOR (per Decision 2)

- [ ] **Verify data.js Rebuilt Successfully**
  - Check: `dashboard/data.js` timestamp is current (same as execution time)
  - Verify: File size is reasonable (~9MB, not corrupted)
  - Confirm: Release Gate validation passed (no G1–G10 failures)

- [ ] **Commit Phase 2 Implementation Results**
  - Git status: Should show modified `release_gate.py` and `dashboard/data.js`
  - Commit message: "Phase 2 Implementation: Finance Decisions 1 & 2 Approved"
  - Push: `git push origin claude/primary-pipeline-allocation-fy27-l9bdf6`
  - Verify: Remote branch is up to date

- [ ] **Notify Finance Controller of Phase 2 Completion**
  - Email to: CFO/Finance Controller
  - Subject: "Phase 2 Complete: Data.js Rebuilt with Approved Allocation Logic"
  - Content: Brief summary—decisions implemented, G10 gate now APPROVED, ready for Phase 3
  - Attach: `docs/PHASE_2_IMPLEMENTATION_*.txt` report

**End-of-Day Status:** Phase 2 complete ✅, Release Gate G10 APPROVED ✅, Data.js rebuilt ✅

---

## AUGUST 10 (TOMORROW) — Finance Control Submission & Preparation

### Morning (8am–10am)

- [ ] **Send Finance Control CSV Template Reminder**
  - Email to: Finance team, CFO/Controller
  - Subject: "URGENT: FY27 KPI Controls Due Today (EOD) — Please Use Template"
  - Attachment: CSV template (exact format) from `docs/PHASE_3_DRY_RUN_REPORT.md`
  - Content:
    ```
    Dear Finance Team,
    
    Please provide FY27 control values for these 9 KPIs by end of business today (Aug 10):
    1. primary_nsv (₹ Lakh)
    2. offtake_qty (units)
    3. pnl_gross_margin (₹ Lakh)
    4. pnl_gm_pct (%)
    5. pnl_expense_ratio (%)
    6. cm2_pct (%)
    7. tdp_distribution (%)
    8. market_share (%)
    9. forecast_target (₹ Lakh)
    
    Use the attached CSV template (exact format, exact KPI names).
    Send to: analytics-team@honasa.com
    
    We'll run reconciliation on Aug 11 and have results to you by 2pm.
    
    Thank you,
    Analytics Team
    ```
  - Follow-up: If no response by 11am, send reminder email + direct call

- [ ] **Verify Staging Directory is Ready**
  - Create: `~/finance_controls_staging/` (if not exists)
  - Permissions: Writable by current user
  - Command:
    ```bash
    mkdir -p ~/finance_controls_staging
    ls -la ~/finance_controls_staging
    ```

- [ ] **Pre-Stage Phase 3 Script & Fixtures**
  - Copy: `scripts/phase3_business_validation.py` to staging
  - Copy: `test/fixtures/finance_controls_fy26_*.csv` (for reference)
  - Verify: All files accessible and executable
  - Command:
    ```bash
    cp scripts/phase3_business_validation.py ~/finance_controls_staging/
    cp test/fixtures/finance_controls_fy26_*.csv ~/finance_controls_staging/
    ```

### Midday (11am–1pm)

- [ ] **Monitor Incoming Finance Controls**
  - Watch inbox for: Email subject containing "FY27", "Control", "KPI"
  - Expected: CSV file attachment `Finance_Controls_FY27_*.csv`
  - Save to: `~/finance_controls_staging/Finance_Controls_FY27.csv`
  - Verify: File opens in Excel or text editor without corruption
  - Check: 9 rows of data + 1 header row (10 total)

- [ ] **Validate CSV Format (Manual QC)**
  - Open file in text editor (not Excel, to preserve format)
  - Verify: Exactly 6 columns: `fy, kpi_name, value, unit, control_date, source`
  - Verify: No extra spaces, quotes, or special characters in KPI names
  - Verify: All 9 KPI names match template exactly:
    - `primary_nsv` (not `primary_nsv_lakhs` or `Primary NSV`)
    - `offtake_qty` (not `offtake_quantity`)
    - `pnl_gm_pct` (not `pnl_gm_percent` or `GM%`)
    - etc.
  - If format issues: Email Finance immediately with corrected template
  - If correct: Proceed to next step

- [ ] **Validate CSV Data (Sanity Check)**
  - Verify: All numeric values are reasonable
    - Primary NSV: ~1,000–1,500 ₹ Lakh (similar to FY26 ~900L)
    - Offtake Qty: 2–4 million units
    - GM%: 10–20%
    - Market Share: 3–8%
  - Flag: Any outliers (e.g., NSV = 0, Market Share = 150%) for Finance review
  - If outliers: Email Finance with "Data Quality Check" note

### Afternoon (1pm–4pm)

- [ ] **Prepare Environment Variables**
  - Set: `FINANCE_CONTROLS_PATH=~/finance_controls_staging/Finance_Controls_FY27.csv`
  - Set: `PHASE_3_OUTPUT_DIR=~/phase3_output/` (create if needed)
  - Verify: Paths are accessible
  - Command:
    ```bash
    export FINANCE_CONTROLS_PATH=~/finance_controls_staging/Finance_Controls_FY27.csv
    export PHASE_3_OUTPUT_DIR=~/phase3_output/
    mkdir -p $PHASE_3_OUTPUT_DIR
    ls -la $FINANCE_CONTROLS_PATH
    ```

- [ ] **Create Backup of Finance Controls**
  - Destination: `~/finance_controls_staging/BACKUP_Finance_Controls_FY27.csv`
  - Reason: Prevent accidental loss if original is modified
  - Command:
    ```bash
    cp ~/finance_controls_staging/Finance_Controls_FY27.csv \
       ~/finance_controls_staging/BACKUP_Finance_Controls_FY27.csv
    ```

- [ ] **Dry-Run Phase 3 Script (with Real Finance Data)**
  - Purpose: Verify script works with actual Finance controls before Aug 11
  - Command:
    ```bash
    python ~/finance_controls_staging/phase3_business_validation.py \
      --finance-controls ~/finance_controls_staging/Finance_Controls_FY27.csv \
      --data-js dashboard/data.js \
      --fy FY27 \
      --validation-date 2026-08-10
    ```
  - Verify: Exit code is reasonable (0 = all pass, 4 = some fail, 2–6 = errors)
  - Verify: Three output files generated in `docs/`
  - Check: Validation report shows all 9 KPIs with PASS/FAIL/MISSING status
  - Save: A screenshot or log of the dry-run for reference tomorrow

### Late Afternoon (by 4pm)

- [ ] **Prepare Aug 11 Reconciliation Briefing**
  - Create: Quick summary document showing Finance control values received
  - Content: 
    - Summary table: 9 KPIs + their control values
    - Expected reconciliation status: Predict which KPIs might fail (if any)
    - Preliminary root causes: If you anticipate failures, note likely causes
  - Save to: `~/phase3_output/AUG_11_RECONCILIATION_BRIEF.txt`

- [ ] **Send Aug 11 Kickoff Email (FYI)**
  - Email to: Finance Controller, CFO
  - Subject: "Phase 3 Reconciliation Kickoff — Aug 11, 8am"
  - Content:
    ```
    Finance controls received ✓
    Phase 3 script ready ✓
    Environment staged ✓
    
    Tomorrow (Aug 11) at 8am, we will:
    1. Run Phase 3 business validation script
    2. Generate validation report + sign-off form
    3. Send results to Finance Controller for review
    
    Expected timeline: Results by 2pm Aug 11.
    
    Next: Please review and sign off (due Aug 12).
    ```

- [ ] **Commit Any Aug 10 Preparation Work**
  - If any docs or checklists were created: Add to git
  - Commit message: "chore: Prepare Phase 3 environment for Aug 11 reconciliation"
  - Push: `git push origin claude/primary-pipeline-allocation-fy27-l9bdf6`

**End-of-Day Status:** Finance controls received ✓, Format validated ✓, Dry-run successful ✓, Aug 11 ready ✓

---

## GO/NO-GO Decision (End of Aug 10)

**Proceed to Aug 11 Reconciliation IF:**

- ✅ Finance Decisions 1 & 2 received and implemented (Phase 2 complete)
- ✅ Finance control CSV received (9 KPIs, correct format)
- ✅ Phase 3 script dry-run successful (exit code 0 or 4)
- ✅ All output files generated correctly
- ✅ No blocking data quality issues identified

**If ANY condition is NOT met:**
- HOLD and investigate
- Escalate to Finance Controller + leadership
- Revise timeline accordingly

---

## Escalation Contacts

| Role | Email | Phone | When |
|------|-------|-------|------|
| Finance Controller | [TBD] | [TBD] | Finance Decision delayed, Controls missing |
| CFO | [TBD] | [TBD] | Critical blocker, Timeline at risk |
| Analytics Lead | [TBD] | [TBD] | Technical issue, Script failure |
| IT/Data Team | [TBD] | [TBD] | Environment/infrastructure issue |

---

## Summary

**Aug 9 Success:** Phase 2 implementation complete, Release Gate G10 APPROVED, data.js rebuilt  
**Aug 10 Success:** Finance controls received + validated, Phase 3 environment ready, dry-run passed  
**Aug 11 Kickoff:** Run real reconciliation, generate validation report, send to Finance Controller  
**Aug 12 Decision:** Finance Controller signs off (or escalates if variances need investigation)  
**Aug 13+:** Phase 4 (PBIP Assembly) proceeds upon Phase 3 sign-off  

**No delays expected. All systems GO for Aug 11 reconciliation.**
