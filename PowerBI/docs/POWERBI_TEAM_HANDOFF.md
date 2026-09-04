# Power BI Team Handoff — August 2026 Release Implementation

**Release:** v2.4.0  
**Date:** August 30, 2026  
**Prepared By:** Claude Code Agent  
**Timeline:** 15-minute setup + testing  

---

## 🎯 Your Mission (15 Minutes)

Integrate the September 2026 promotional analytics dimension and 15 DAX measures into the production Power BI model. This unlocks planned-vs-actual trade spend variance tracking and incremental ROI reporting.

---

## 📋 Checklist (Execute in Order)

### **Phase 1: Data Load (3 minutes)**

- [ ] Open your existing `.pbix` file in Power BI Desktop
- [ ] **Transform Data** → **New Source** → **Text/CSV**
- [ ] Navigate to: `PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv`
- [ ] Click **Load**
- [ ] Rename query to: `Dim_PromoCalendar`
- [ ] Verify: 2,613 rows loaded, 18 columns present
- [ ] Click **Close & Apply**

**Expected:** Data pane shows `Dim_PromoCalendar` table with 2,613 rows

---

### **Phase 2: Relationships (3 minutes)**

- [ ] Click **Model** (left sidebar)
- [ ] Create **Relationship 1** (Promo → Fact):
  - From: `Dim_PromoCalendar[EAN Code]`
  - To: `Fact_Secondary_TOT_Hierarchy[EAN]`
  - Type: One-to-Many (1 → *)
  - Direction: Single
- [ ] Create **Relationship 2** (Promo → Brand):
  - From: `Dim_PromoCalendar[Brand]`
  - To: `Dim_Brand[Brand_Name]`
  - Type: One-to-Many
  - Direction: Single
- [ ] Create **Relationship 3** (Promo → Calendar):
  - From: `Dim_PromoCalendar[From ]`
  - To: `Dim_Calendar[Date]`
  - Type: One-to-Many
  - Direction: Single
- [ ] Verify all relationships are **active** (solid lines)
- [ ] Return to **Report View**

**Expected:** Model View shows 7 relationships total (4 existing + 3 new)

---

### **Phase 3: Paste Measures (5 minutes)**

- [ ] Open `PowerBI/QuickSetup/AllDAX_Consolidated.txt`
- [ ] Search for: `STEP 16: PROMOTIONAL ANALYTICS`
- [ ] Copy all 15 measures (from `[Actual NSV Lakh]` through `[Promo ROI Performance Band]`)
- [ ] In Power BI Desktop, go to **Report View**
- [ ] Locate your `_Measures` table in the Data pane
- [ ] Click **New Measure**
- [ ] Paste the first measure into the formula bar → Press **Enter**
- [ ] Repeat for remaining 14 measures

**Measures to Create (in order):**
```
1. [Actual NSV Lakh]
2. [Actual Promoted NSV Lakh]
3. [Baseline Non-Promoted NSV Lakh]
4. [Active Promo Offer Count]
5. [Promoted NSV Share %]
6. [Promoted SKU Breadth %]
7. [Planned Promo Discount %]
8. [Planned Company Trade Spend %]
9. [Planned Trade Spend Value Lakh]
10. [Actual Claim Expense Lakh]
11. [Promo Spend Variance Lakh]
12. [Promo Spend Variance %]
13. [Promo Execution Status]
14. [Incremental Promo NSV Lakh]
15. [Promo Volume Lift %]
16. [Promo Trade Spend ROI]
17. [Promo Net Margin ROI]
18. [Promo ROI Performance Band]
```

**Expected:** All 15 measures appear in Data pane without #ERROR

---

### **Phase 4: Format Measures (2 minutes)**

For each measure, apply formatting:

| Measure | Format String |
|---------|----------------|
| NSV Lakh columns, Spend Value, Claim Expense, Variance Lakh, Baseline, Incremental | `₹#,##0.00 "L"` |
| All % columns, Lift %, Margin ROI | `0.0%` |
| Offer Count | `#,##0` |
| Trade Spend ROI | `0.00 "x"` |
| Execution Status, ROI Band | **(Default)** |

**Steps:**
1. Click measure name in Data pane
2. Go to **Measure Tools** → **Formatting** (or right-click → **Format**)
3. Select format from dropdown or paste custom string
4. Press **Enter**

---

### **Phase 5: Build Variance Matrix Visual (3 minutes)**

- [ ] Create new page: "Trade Spend Variance Analysis"
- [ ] Insert **Matrix** visual
- [ ] Configure:
  - **Rows:** Drag `Dim_Brand[Brand_Name]`, then `Dim_Chain[Chain_Name]`, then `Dim_PromoCalendar[EAN Code]`
  - **Values:** 
    1. `[Actual Promoted NSV Lakh]`
    2. `[Planned Company Trade Spend %]`
    3. `[Planned Trade Spend Value Lakh]`
    4. `[Actual Claim Expense Lakh]`
    5. `[Promo Spend Variance Lakh]`
    6. `[Promo Execution Status]`
- [ ] Apply conditional formatting to `[Promo Spend Variance Lakh]`:
  - **Rule Type:** Based on `[Promo Spend Variance %]`
  - **< -15%:** Background `#FCE8E6`, Font `#C5221F` (Red = Over-Spent)
  - **-15% to +15%:** Background `#E6F4EA`, Font `#137333` (Green = On-Plan)
  - **> +15%:** Background `#FEF7E0`, Font `#B06000` (Amber = Under-Utilized)

**Expected:** Matrix shows data with color coding

---

### **Phase 6: Build ROI Dashboard (2 minutes)**

- [ ] Create new visual: **Card (Multi-row)**
- [ ] Add cards:
  1. `[Actual Promoted NSV Lakh]` → Label "Promoted NSV"
  2. `[Actual Claim Expense Lakh]` → Label "Claim Spend"
  3. `[Incremental Promo NSV Lakh]` → Label "Incremental Lift"
  4. `[Promo Trade Spend ROI]` → Label "Trade ROI"
  5. `[Promo Net Margin ROI]` → Label "Margin ROI"

**Expected:** 5 cards display metrics

---

### **Phase 7: Add Slicers (2 minutes)**

- [ ] Create slicers for:
  1. `Dim_Calendar[Month_Label]` (default to Sep-2026)
  2. `Dim_Brand[Brand_Name]`
  3. `Dim_Chain[Chain_Name]`
  4. `Dim_PromoCalendar[Promo_Type]`
- [ ] Wire each slicer to all visuals (cross-filter enabled)

**Expected:** Slicers filter all visuals

---

### **Phase 8: Test & Validate (1 minute)**

- [ ] Click **Home** → **Refresh**
- [ ] Monitor Data Load Progress window
- [ ] Verify:
  - ✅ No errors in refresh
  - ✅ All measures display values (not #ERROR or blank)
  - ✅ Variance matrix shows Sep-2026 data
  - ✅ Cards display numeric values
  - ✅ Conditional formatting shows color bands
  - ✅ Slicers filter all visuals correctly

**Expected:** Refresh completes <5 seconds, zero errors

---

## 📊 Visual Reference

### Variance Matrix Expected Output
```
Brand              Chain              EAN         Promo NSV  Spend%  Planned   Actual    Variance  Status
Mamaearth          Apollo             8904417...  125.50     35%     43.93     42.50     1.43      On-Plan
Mamaearth          Reliance Retail    8904417...  89.75      40%     35.90     36.25     -0.35     On-Plan
The Derma Co       D-Mart             8904416...  78.30      32%     25.06     24.80     0.26      On-Plan
```

### ROI Dashboard Expected Cards
```
┌─────────────────┐ ┌──────────────────┐ ┌──────────────┐
│  Promoted NSV   │ │   Claim Spend    │ │ Incr. Lift   │
│   ₹2,840.50 L   │ │  ₹896.20 L       │ │ ₹450.75 L    │
└─────────────────┘ └──────────────────┘ └──────────────┘

┌─────────────────┐ ┌──────────────────┐
│   Trade ROI     │ │   Margin ROI     │
│    1.87x        │ │    0.36x         │
└─────────────────┘ └──────────────────┘
```

---

## 🆘 Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "No Actual Offtake" for all rows | EAN mismatch | Check `Dim_PromoCalendar[EAN Code]` ≠ blank, matches fact table |
| Measures show #ERROR | Circular dependency or syntax | Copy paste code again, ensure no typos |
| Variance doesn't calculate | Relationship inactive | Verify solid (not dashed) line in Model View |
| Refresh takes >10 sec | Too many rows or complex formula | Verify Dim_PromoCalendar is marked as **Dimension** (not Fact) |

---

## ✅ Sign-Off Checklist

After completing all steps:

- [ ] All 15 measures appear in Data pane
- [ ] Variance matrix displays data without errors
- [ ] Conditional formatting shows colors (Red/Green/Amber)
- [ ] ROI dashboard shows 5 numeric cards
- [ ] Slicers filter all visuals
- [ ] Refresh completes <5 seconds
- [ ] No #ERROR or blank values in any visual
- [ ] Month slicer defaults to Sep-2026

**Status:** Ready for production

---

## 📞 Support

- **Setup Guide:** `PowerBI/docs/Promo_Analytics_Power_BI_Setup.md` (detailed 7-step walkthrough)
- **Measure Definitions:** `PowerBI/DAX/15_Promo_Measures.dax` (annotated code)
- **Consolidated DAX:** `PowerBI/QuickSetup/AllDAX_Consolidated.txt` (ready to paste)
- **Promo Data:** `PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv` (2,613 records)

---

**Handoff Date:** August 30, 2026  
**Timeline:** 15 minutes  
**Status:** ✅ Ready for implementation
