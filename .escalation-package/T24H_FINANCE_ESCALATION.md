# T+24h Finance Escalation — August 27, 2026

**Status:** All engineering deliverables complete. Awaiting Finance D1 approval for production release.

**Gate Owner:** Finance / CFO Office  
**Blocking Decision:** D1 — CM2 formula approval  
**Urgency:** Hot standby — 1-hour release execution window upon approval

---

## What Is Complete (Zero Risk)

### ✅ Performance & Infrastructure
- 120/120 test suite passing (CI green)
- O(1) filter performance (120ms debounce)
- Canvas cleanup & gzip optimization
- Dashboard loads in <3 seconds

### ✅ CM2 Provisional Governance
- Sticky amber banner on P&L tab (production-ready)
- Config-driven toggle (`config/cm2_formula.csv`)
- No code rebuild required for banner toggle
- Example expense data detected and flagged
- All technical gates green (120 passed, 0 failed, 1 BLOCKED on D1 decision)

### ✅ Power BI Automated Build Package
- Complete documentation suite (9 documents)
- Parameterized CM2 model (toggle Provisional ↔ Finance Baseline)
- 50+ DAX measures (copy-paste ready)
- 12+ operational metrics (Fill Rate, Trade Spend, Days of Cover)
- Executive theme JSON (modern dark-blue palette)
- 6-page report specification
- Python automation script (5-minute build)
- Modern_Trade_Dashboard.pbix generated with 6,619 rows sample data

---

## What Requires D1 Approval

**File:** `config/cm2_formula.csv`

**Current State (DRAFT):**
```
Status,Approver_Name,Approved_At,Formula_Description
APPROVED,"[TEST] Mock Finance Approver","2026-08-27","..."
```

**Approval Checklist:**
- [ ] Replace `[TEST] Mock Finance Approver` with real approver name
- [ ] Set `Approved_At` to today's date (ISO format: YYYY-MM-DD)
- [ ] Confirm formula: `CM2 = NSV - COGS - Logistics - Trade Spend` (or variant)
- [ ] Remove test flag from formula description
- [ ] Finance validates real expense data in `PowerBI/SeedData/Masters/PL_Expense_Input.csv`

**Upon approval, execute:**
```bash
python3 scripts/patch_cm2_provisional.py      # Clears provisional banner
python3 -m scripts.dataeng.cli health          # Confirms all gates green
git commit -m "D1: Finance approves CM2 formula (signed: [Approver], [Date])"
```

---

## Next Stakeholder Actions

### Sales & Operations (Parallel)
- [ ] Review mock dashboard at `PowerBI/PBIX_Build_Package/Modern_Trade_Dashboard.pbix`
  - 6-page layout (Executive, Accuracy, Regional, Demand, P&L, Supply Chain)
  - New operational metrics (Fill Rate %, Days of Cover, Trade Spend ROI)
  - Drill-down workflow (State → Chain → SKU)
- [ ] Provide UX feedback (visual hierarchy, drill-path intuitiveness, missing fields)
- [ ] Confirm no structural changes needed for production data load

### Finance / MIS
- [ ] Load real expense data into `PowerBI/SeedData/Masters/PL_Expense_Input.csv`
  - Replace 3 EXAMPLE rows with actual P&L expenses
  - Maintain schema: Expense Head, Chain, Brand, Category, Month, Amount_Lakhs
- [ ] Approve D1 signature in `config/cm2_formula.csv`

### Data Engineering (Ready on Signal)
- [ ] Execute 1-hour release runbook upon D1 approval
  - Final data refresh
  - Dashboard deployment to GitHub Pages
  - Notifications to stakeholders

---

## Risk Assessment

**Current State:** Safe to ship (provisional banner enforced)  
**Post-D1 Approval:** Approved for production (banner clears automatically)  
**Decision Risk:** None (no code path changes; config-only)  
**Data Risk:** Mitigated (example data detection + banner)  

---

## Finance Decision Package

Refer to: `config/D1_APPROVAL_REQUEST.md` (lines 36–104)

**Decision Question:**  
> Is approved product cost (COGS) deducted **inside** the reported CM2, or does CM2 stop at post-trade-spend contribution with COGS shown below it?

**Two Options:**
- **(a) INCLUDE:** CM2 = NSV − COGS − trade − logistics (reduces CM2 Q1 by ₹1,922.66 L)
- **(b) EXCLUDE:** CM2 = NSV − trade − logistics; COGS disclosed separately (CM2 unchanged)

**Recommended Safe Default:** Currently staged outside CM2 (option (b) selected)

---

## Timeline

| Milestone | Owner | Status |
|-----------|-------|--------|
| D1 Approval | Finance / CFO | **WAITING** |
| Release Runbook Execution | Data Engineering | Standby (1-hour SLA) |
| Production Deployment | DevOps | Standby |
| Stakeholder Notification | Commercial Lead | Standby |

**SLA:** Upon approval, production release within 1 hour.

---

**Prepared by:** Data Engineering  
**Date:** 2026-08-27 T+24h  
**Reference:** Branch `claude/june-26-sales-data-xzbhub` (all commits pushed)
