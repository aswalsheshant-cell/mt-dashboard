# Modern Trade Retail Execution — Operations Manual

**Reference Period:** Q3 FY27 | Field Operations Standard SOP  
**Version:** 1.0 | September 1, 2026  

---

## Table of Contents

1. [KPI Dictionary & Benchmarks](#kpi-dictionary)
2. [In-Store Audit Workflow](#audit-workflow)
3. [Status Triage & Escalation](#escalation-matrix)
4. [Field Quick Reference Cheat Sheet](#quick-reference)
5. [Export & Reporting](#exports)

---

## <a name="kpi-dictionary"></a> KPI Dictionary & Benchmarks

### Planogram Adherence

**Formula:** (Compliant Shelf Placements / Total Contracted Facings) × 100  
**Target:** ≥ 85.0%  
**Warning Threshold:** < 85%  
**Business Interpretation:**  
Measures whether SKUs match agreed visual placement and eye-level blocking. Scores below 85% require visual audits by merchandisers.

**Immediate Action:** Correct shelf eye-level blocking and missing facings

---

### On-Shelf Availability (OSA)

**Formula:** (SKUs In-Stock on Shelf / Total Active Core Assortment) × 100  
**Target:** ≥ 90.0%  
**Warning Threshold:** < 88%  
**Business Interpretation:**  
Evaluates phantom inventory and backroom-to-shelf replenishment. If OSA falls below 88%, trigger priority replenishment from store backrooms.

**Immediate Action:** Pull backroom inventory to shelf; report phantom stock

---

### Share of Shelf (SoS)

**Formula:** (Brand Linear Facing Length / Total Category Facing Length) × 100  
**Target:** Category Dependent (Avg ≥ 25%)  
**Warning Threshold:** < 20%  
**Business Interpretation:**  
Tracks actual shelf space occupied versus competitive brands against contracted Trade Terms.

**Immediate Action:** Verify linear shelf space against contracted Trade Terms

---

### Promoter Productivity Index

**Formula:** Store Offtake Growth Rate / Promoter Deployment Cost Index  
**Target:** ≥ 1.00x  
**Warning Threshold:** < 0.85x  
**Business Interpretation:**  
Values ≥ 1.00x indicate positive ROI on in-store demonstrators (ISDs). Values below 0.85x prompt re-allocation to higher-footfall doors.

**Immediate Action:** Review promoter attendance, pitch script, and door footfall

---

### Overall Audit Status

**Composite heuristic** combining Planogram score and OSA rate:

| Status | Planogram | OSA | Action |
|--------|-----------|-----|--------|
| **COMPLIANT** (Green) | ≥ 85% | ≥ 90% | Maintain regular audit cadence; review ISD productivity for volume optimization |
| **WATCH** (Amber) | < 85% OR | < 90% | Single-point failure; inspect backroom or correct shelf arrangement |
| **CRITICAL GAP** (Red) | < 85% AND | < 90% | Escalation required; open Account Drill Modal for store-level gaps |

---

## <a name="audit-workflow"></a> In-Store Audit Workflow (4-Step Standard)

### Step 1: Scan Floor & Backroom

- Check front-of-store end-caps and eye-level secondary displays
- Verify backroom pallet stock levels and date-coded inventory
- Photograph any out-of-stock (OOS) bays or damaged stock
- Record promotional setup status (end-caps, floor displays)

### Step 2: Audit & Log Data

1. Open the **Retail Execution Tab** in MT Dashboard
2. Search your target Chain name or Zone designation
3. Review active Compliance % and current Status pill
4. Click the chain row to view store-level drill-down modal

### Step 3: Resolve Bottlenecks

**If stock exists in backroom but NOT on shelf:**
- Coordinate immediate pallet pull with store floor supervisor
- Verify pallet is not reserved for other locations
- Log replenishment time and SKU count in the modal

**If shelf space cut by competition:**
- Document with date-stamped photo
- Log under Account Drill modal
- Flag for RKAM JBP review

**If Planogram non-compliant:**
- Restack to eye-level in contracted configuration
- Verify no price-point merchandising blocking eye-level
- Photograph corrected planogram for audit trail

### Step 4: Export Daily Deliverables

- **CSV Export:** Download for daily operational store lists (to field supervisors)
- **Excel Multi-Tab:** For buyer review decks and JBP submission

---

## <a name="escalation-matrix"></a> Status Triage & Escalation Hierarchy

### Level 1: Store Floor Manager
**Trigger:** OSA drops below 88% with backroom stock available  
**Action:** Same-day physical stock transfers from backroom to bay  
**Timeline:** Within 4 hours of audit detection  

### Level 2: Field Sales Supervisor
**Trigger:** Planogram non-compliance across 2 consecutive audit cycles  
**Action:** Conduct in-store re-training on visual standards with store team  
**Timeline:** Within 7 days of second failure  

### Level 3: RKAM / National Account Lead
**Trigger:** Systemic supply fill-rate drops OR contractual display space disputes  
**Action:** Escalate to buyer category manager; review space allocation agreement  
**Timeline:** Within 14 days of detection; coordinate with Buyer Negotiations  

### Level 4: VP Commercial Operations
**Trigger:** Chain-wide compliance < 70% OR revenue impact > ₹50 Lakh  
**Action:** Account-level recovery program; executive stakeholder review  
**Timeline:** Immediate (within 24 hours)  

---

## <a name="quick-reference"></a> Field Quick Reference Cheat Sheet

### KPI Benchmarks & Action Matrix

| Metric | Target | Warning | Immediate Action |
|--------|--------|---------|------------------|
| Planogram Adherence | ≥ 85% | < 85% | Correct shelf eye-level blocking and missing facings |
| On-Shelf Availability (OSA) | ≥ 90% | < 88% | Pull backroom inventory to shelf; report phantom stock |
| Share of Shelf (SoS) | ≥ 25% | < 20% | Verify linear shelf space against contracted Trade Terms |
| Promoter Productivity | ≥ 1.00x | < 0.85x | Review promoter attendance, pitch script, and door footfall |

### Status Triage

- **COMPLIANT (Green):** Planogram ≥ 85% AND OSA ≥ 90%. Assortment is healthy; maintain standard audit rhythm.
- **WATCH (Amber):** Planogram < 85% OR OSA < 90%. Single-point failure; inspect backroom or correct shelf arrangement.
- **CRITICAL GAP (Red):** Planogram < 85% AND OSA < 90%. Escalation required; open Account Drill Modal for store-level gaps.

### Standard Operating Procedures (SOP)

**OSA Failure with In-Stock DC:**
If store OSA < 85% while regional DC stock cover > 15 days, instruct the field team to:
1. Verify backroom inventory physically
2. Coordinate pallet drops with store floor managers
3. Log replenishment timestamp in dashboard

**Chronic Planogram Gaps:**
If an account scores < 80% across two consecutive audit cycles:
1. RKAM must cross-reference space agreements against buyer category master grids
2. Schedule bi-weekly account reviews during JBP cycles
3. Provide merchandiser re-training materials

---

## <a name="exports"></a> Export & Reporting

### CSV Export (Instant Operational Dispatch)

**Use When:** Daily operational reporting to field supervisors, store lists, quick ad-hoc queries  
**Content:** Chain name, Store Counts (Total & Compliant), Compliance %, Status, Last Audit, Top Issues  
**Format:** RFC-4180 compliant; UTF-8 BOM for Excel compatibility  
**File Naming:** `MT_Dashboard_Retail_Execution_Compliance_Matrix_<date>.csv`

**Example Usage:**
```bash
# Filter for "DMart" stores and export
1. Click "Retail Execution" tab
2. Type "DMart" in search bar
3. Click "Export CSV"
4. Share with field supervisors via WhatsApp/Email
```

### Excel Multi-Tab Export (Executive & JBP Reviews)

**Use When:** Joint Business Planning (JBP) reviews, buyer deck submissions, historical trend analysis  
**Sheets:**
1. **Executive Summary:** KPI aggregates and chain compliance table
2. **Chain Details:** Compliance %, status, store gaps, trend sparklines
3. **Zone Health:** Zone aggregates, average compliance %, store counts

**Format:** `.xlsx` with formula-driven totals; color-coded status badges  
**File Naming:** `MT_Dashboard_Retail_Execution_Compliance_Multi_Tab_<date>.xlsx`

**Example Usage:**
```bash
# Generate board-ready workbook
1. Click "Retail Execution" tab (no filters if wanting full portfolio view)
2. Click "Export Excel"
3. Open in Excel → adjust column widths
4. Email to Buyer or present in JBP review
```

---

## Troubleshooting

### "Compliance data not loading"
- Check that `dashboard/compliance_metrics.json` is present
- Verify browser dev tools (F12) for HTTP 404 on `/dashboard/compliance_metrics.json`
- Clear browser cache and refresh page (`Ctrl+Shift+Del`)

### "Search filter not working"
- Ensure exact chain name or zone spelling
- Try searching partial name (e.g., "DMart" instead of "D-Mart")
- Reload tab and retry

### "Export buttons inactive"
- Verify XLSX library loaded: check browser console for errors
- If Excel export fails, CSV export will be offered as fallback
- Ensure no browser add-ons blocking file downloads

### "Modal not opening for store details"
- Click on a visible table row (not the header)
- Wait 1-2 seconds for modal to animate open
- If modal appears blank, refresh page and retry

---

## Contact & Escalation

**Dashboard Support:** aswal.sheshant@gmail.com  
**Field Operations Lead:** [Regional Lead Contact]  
**Buyer Escalations:** [Buyer Category Lead Contact]  

---

**Last Updated:** September 1, 2026  
**Document Version:** 1.0  
**Approval:** MT Leadership Finance & Operations
