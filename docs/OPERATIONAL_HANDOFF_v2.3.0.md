# Operational Handoff Checklist — v2.3.0 → v2.4.0

**Status:** v2.3.0 Published & Ready for Integration  
**Target Date:** Power BI model live by Sep 3  
**Next Milestone:** v2.4.0 (Windows CI/CD + North distributor data + Finance sign-off)

---

## 📋 Phase 1: Power BI Desktop Model Integration (User Action)

**Owner:** Power BI Team  
**Estimated Time:** 45–60 minutes  
**Dependencies:** Power BI Desktop 2024.09+, repo access

### Checklist

- [ ] **Step 1: Open Power BI Desktop Model**
  - [ ] Locate `.pbix` file (shared model location: TBD)
  - [ ] Open in Power BI Desktop

- [ ] **Step 2: Add Power Query Tables**
  - [ ] Click Transform Data → Home Ribbon
  - [ ] New Query → Blank Query
  - [ ] Click Advanced Editor
  - [ ] Copy entire code from: `PowerBI/PowerQuery/44_Fact_SecondarySales.pq`
  - [ ] Paste → Click Done
  - [ ] Right-click query → Rename to: `Fact_SecondarySales`
  - [ ] Repeat for: `PowerBI/PowerQuery/45_Fact_ClaimMaster.pq`
  - [ ] Rename to: `Fact_ClaimMaster`
  - [ ] Verify folder path parameter (`pRootFolder`) points to repo root

- [ ] **Step 3: Establish Model Relationships** (Model View)
  - [ ] Click Model icon (left sidebar)
  - [ ] Create relationships (all single-direction `1 → *`, inner join):
    - [ ] `Dim_Calendar[Date]` → `Fact_SecondarySales[MonthStart]`
    - [ ] `Dim_Chain[Chain_Name]` → `Fact_SecondarySales[Chain]`
    - [ ] `Dim_Brand[Brand_Name]` → `Fact_SecondarySales[Brand]`
    - [ ] `Dim_Chain[Chain_Name]` → `Fact_ClaimMaster[Chain]`
    - [ ] `Dim_Brand[Brand_Name]` → `Fact_ClaimMaster[Brand]`
  - [ ] Mark as Active relationships (all 5)

- [ ] **Step 4: Add DAX Measures**
  - [ ] Return to Report View
  - [ ] Select a measures table (or create `_SecondaryMeasures`)
  - [ ] Copy all 16 measures from: `PowerBI/DAX/14_SecondarySales_Measures.dax`
  - [ ] Or: Open `PowerBI/QuickSetup/AllDAX_Consolidated.txt` → Copy Step 15 section
  - [ ] Paste into New Measure dialog (one by one, or bulk-paste if supported)
  - [ ] Verify all measures are named and documented:
    - [ ] `[Secondary NSV Lakh]`
    - [ ] `[Secondary NSV Cr]`
    - [ ] `[Sell-Through %]`
    - [ ] `[Sell-Through Signal]`
    - [ ] (+ 12 others — see DAX file)

- [ ] **Step 5: Validate Data Load**
  - [ ] Click Home → Refresh (full model refresh)
  - [ ] Wait for load to complete (should <5 seconds for CSVs)
  - [ ] Check status bar for errors/warnings → Should be zero
  - [ ] Verify in Data View or Power Query:
    - [ ] `Fact_SecondarySales`: 291 rows (78 distributor + 192 chain + 21 brand)
    - [ ] `Fact_ClaimMaster`: 47 rows (23 chain + 5 brand + 19 distributor)
  - [ ] Create test card with `[Secondary NSV Label]` measure → Should show "₹33.54 Cr"
  - [ ] Create test card with `[Sell-Through Signal]` → Should show "On-Track" (if primary data available)

- [ ] **Step 6: Save Model**
  - [ ] File → Save (or Ctrl+S)
  - [ ] Confirm no unsaved changes remain
  - [ ] Note: DO NOT publish to Power BI Service yet (Windows CI/CD will handle v2.4.0 automated .pbix generation)

**Success Criteria:**
- ✅ All 5 relationships created and marked Active
- ✅ All 16 DAX measures compile without errors
- ✅ Refresh loads 6 CSVs with zero schema breaks
- ✅ Test cards display correct formatted values (₹33.54 Cr, ₹4.50 Cr)

---

## 🌐 Phase 2: Live Web Dashboard Verification (Local Validation)

**Owner:** QA / Deployment Team  
**Status:** ⚠️ GitHub Pages blocked by org proxy (local validation passed)

### Online Verification (when proxy allows)

- [ ] **Open GitHub Pages Dashboard**
  - [ ] URL: `https://aswalsheshant-cell.github.io/mt-dashboard/dashboard/`
  - [ ] Wait for page load (should <3 seconds)
  - [ ] Check page title: "Modern Trade (MT) Leadership Dashboard"

- [ ] **Console Check** (F12 → Console)
  - [ ] No errors in console (filter red 🔴)
  - [ ] window.DASH object populated
  - [ ] window.DASH.secondary_sales exists with ₹33.54 Cr total

- [ ] **Tab-by-Tab Validation**
  - [ ] Distribution tab → Secondary Sales MoM section displays (78 rows)
  - [ ] Promo & Trade Spend tab → Not impacted
  - [ ] CM2 & Claim Analysis → Brand-wise Claim Distribution shows 5 brands with ₹504.38 L total

- [ ] **Data Accuracy Checks**
  - [ ] Secondary Sales: ₹33.54 Cr across 26 distributors
  - [ ] Claims: ₹4.50 Cr (chain-level), ₹4.50 Cr (brand-level)
  - [ ] No NaN / undefined / [object Object] in visible UI text

### Local Validation (Current — Passed ✅)

**Completed in this session:**
- ✅ data.js loads correctly (17.88 MB, valid JSON)
- ✅ Secondary sales block: 26 distributors, 64 chains, 7 brands
- ✅ Claims block: 23 chains, 5 brands, 19 distributors
- ✅ No undefined strings in output
- ✅ Dashboard renders without JS errors (tested on local HTTP server)

**When proxy restrictions lift:**
- Perform full live verification against GitHub Pages URL
- Confirm GitHub Actions CI passed on commit `824ee8a`

---

## 🔄 Phase 3: Operational Standby — v2.4.0 Pipeline

**Owner:** Data Engineering + Finance + Sales Ops  
**Timeline:** Sep 3–Sep 30

### 3.1 North Distributor Data Intake

**Trigger:** When Sales Operations provides missing North distributor registers (Q1 FY27, `.xlsx` format)

**Process:**
```bash
# Step 1: Ingest new North data
python scripts/ingest_claims_and_secondary.py \
  --secsale <north_file.xlsx> \
  --datajs dashboard/data.js

# Step 2: Export updated CSVs to watch folders
python scripts/automate_pbi_refresh.py --mode primary-only --no-qc

# Step 3: Verify data
python scripts/eval_harness.py

# Step 4: Commit & push
git add PowerBI/RawDataFolders/
git commit -m "data: add North distributor secondary sales (Q1 FY27)"
git push origin main
```

**Expected Outcome:**
- Secondary sales watch-folder CSVs updated with North data
- Power BI model: Refresh auto-picks up new rows
- Dashboard: Secondary sales MoM section expands to include North chains/distributors

**Responsibility:** Data Eng (trigger: Sales Ops notification)

### 3.2 Finance Sign-Off: Zero-Claim Account Reclassification

**Items Pending Approval:**

| Account | Q1 FY27 Amount | Status | Decision Required |
|---------|---|---|---|
| AirPlaza | ₹0 L | Pending Finance | Close or reclassify? |
| Combined Charge | ₹0 L | Pending Finance | Consolidate into another category? |
| Fleet Labs | ₹0 L | Pending Finance | Merged/inactive? |
| Transportation | ₹0 L | Pending Finance | Allocated to DMart? |
| Beauty & Nutrition | ₹0 L | Pending Finance | Portfolio decision? |

**Sign-Off Checklist:**
- [ ] Finance confirms 5 accounts (reclassification / closure / allocation)
- [ ] Update `PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv` if needed
- [ ] Re-run ingest pipeline to reflect decision
- [ ] Commit to main with decision gate reference (e.g., "Finance D1 signed off Sep 5")

**Responsibility:** Finance (trigger: email sign-off to data team)

### 3.3 Windows CI/CD for Automated PBIX Compilation (v2.4.0)

**Goal:** Hands-off Power BI model compilation & validation on every main branch push  
**Target:** Sep 5–12  
**Owner:** DevOps / Data Eng

**Setup Steps:**
1. **Provision Windows Self-Hosted Runner**
   - VM spec: Windows Server 2022+, 8GB RAM, Power BI Desktop 2024.09+
   - GitHub Actions runner installed & registered to org

2. **Create `.github/workflows/pbi-compile.yml`**
   - Trigger: On push to main
   - Steps:
     - Checkout repo
     - Install/update Power BI Desktop CLI (pbitool or COM API)
     - Compile `.pbix` from QuickSetup + data CSVs
     - Validate DAX measures (TMDL export → schema check)
     - Upload `.pbix` artifact to releases

3. **Set Up Power BI Gateway** (optional, for scheduled cloud refreshes)
   - Install On-Premises Data Gateway
   - Link to Power BI Service
   - Schedule weekly/daily refresh from watch-folder CSVs

**Success Criteria:**
- [ ] Windows runner online & healthy
- [ ] CI/CD pipeline runs on every main push
- [ ] Compiled `.pbix` available as release artifact
- [ ] DAX validation passes (zero formula errors)

**Responsibility:** DevOps (trigger: infrastructure approval)

---

## 📅 Timeline & Milestones

| Date | Milestone | Owner | Status |
|------|-----------|-------|--------|
| **2026-08-30** | v2.3.0 Released | ✅ Complete | Published |
| **2026-09-01** | PBI Model Integration (Phase 1) | Power BI Team | ⏳ Pending |
| **2026-09-03** | Web Dashboard Live (Phase 2) | QA / Deployment | ⏳ Pending (blocked by proxy) |
| **2026-09-05** | Windows Runner Provisioned | DevOps | ⏳ Pending |
| **2026-09-08** | CI/CD Pipeline Active | DevOps | ⏳ Pending |
| **2026-09-12** | Automated PBIX Compilation Online | DevOps | ⏳ Pending |
| **2026-09-15** | North Distributor Data (if received) | Sales Ops | ⏳ Pending |
| **2026-09-30** | Finance Sign-Off on Zero Accounts | Finance | ⏳ Pending |
| **2026-10-15** | v2.4.0 Release Ready | Data Eng | ⏳ Pending |

---

## 📞 Escalation Path

| Issue | Owner | Contact | Escalation |
|-------|-------|---------|------------|
| **Power BI Model Errors** | PBI Admin | TBD | Data Eng Lead |
| **Missing North Distributor Data** | Sales Ops | TBD | Commercial Manager |
| **Finance Sign-Off Delayed** | Finance | TBD | CFO / Controller |
| **Windows CI/CD Setup** | DevOps | TBD | Infra Lead |
| **GitHub Pages Access** | IT / Security | TBD | Org Admin |

---

## 📎 Attached Resources

1. **Release Notes** → `docs/RELEASE_v2.3.0.md`
2. **Power Query Templates** → `PowerBI/PowerQuery/44_*.pq`, `45_*.pq`
3. **DAX Measures** → `PowerBI/DAX/14_SecondarySales_Measures.dax`
4. **QuickSetup Consolidated** → `PowerBI/QuickSetup/AllPowerQuery_Consolidated.txt`, `AllDAX_Consolidated.txt`
5. **Watch Folder READMEs** → `PowerBI/RawDataFolders/SecondarySales_Monthly/_README.txt`, `ClaimMaster_Quarterly/_README.txt`
6. **Governance Config** → `PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv`

---

## ✅ Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Data Engineering | MT Automation | 2026-08-30 | ✅ |
| Power BI Team | TBD | — | — |
| Finance | TBD | — | — |
| Sales Operations | TBD | — | — |
| DevOps | TBD | — | — |

---

**Questions or blockers?** Contact MT Data Team or refer to `CLAUDE.md` for architecture & troubleshooting.

**Next steps:** Power BI team to begin Phase 1 integration. Notify data team when complete for Phase 3 pipeline activation.
