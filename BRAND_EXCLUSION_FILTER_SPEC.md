# Brand Exclusion Filter Specification
**Date:** August 9, 2026  
**Applied to:** All PPT data extraction + verification  
**Deadline:** Revenue verification complete before 10am Aug 10 meeting

---

## Filter Rules (SQL-Style)

### Primary Filter: Brand Exclusion
```sql
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
```

### Brands to INCLUDE (Keep in Deck)
| Brand | Categories | Keep? | Notes |
|-------|-----------|-------|-------|
| Mamaearth | Face Wash, Cleanser, Suncare, Face Serum, etc. | ✅ YES | All sub-categories included |
| Derma Co | All products | ✅ YES | Not a sub-category, separate brand |
| Aqualogica | All products | ✅ YES | Include in all views |
| Bblunt | Hair category | ✅ YES | Include in Hair section |
| Dr Sheth | All products | ✅ YES | Include in all views |
| **Other Honasa brands** | (if any) | ✅ YES | Include all non-excluded brands |

### Brands to EXCLUDE (Remove Completely)
| Brand | Impact | Action |
|-------|--------|--------|
| Luminev | Remove from all slides, charts, calculations | DELETE |
| Pure Origin | Remove from all slides, charts, calculations | DELETE |
| Staze | Remove from all slides, charts, calculations | DELETE |

---

## Data Extraction Queries (Updated)

### Query 1: Suncare Metrics by Zone (FILTERED)
```sql
SELECT Zone, Article, WD%, YoY_Growth%, Secondary_Contrib%
FROM ZoneXBrandXArticle
WHERE Brand = 'Mamaearth' 
  AND Category = 'Suncare'
  AND Brand NOT IN ('Luminev', 'Pure Origin', 'Staze');
```

**Expected Output:** 10 rows (5 zones × 2 articles)  
**Validation:** All rows Brand = 'Mamaearth'

---

### Query 2: Revenue Trends Apr 2025 – Jul 2026 (FILTERED)
```sql
SELECT Month, Zone, Total_Primary_Revenue_L, YoY_Growth%, Suncare_Revenue_L
FROM ChannelXZoneXState
WHERE Period >= '2025-04-01' 
  AND Period <= '2026-07-31'
  AND Channel = 'MT'
  AND Brand NOT IN ('Luminev', 'Pure Origin', 'Staze');
```

**Expected Output:** 80 rows (16 months × 5 zones)  
**Validation:** Sum(Total_Primary_Revenue_L) across all zones/months = ₹78,450L (baseline estimate)

---

### Query 3: Zone Performance (FILTERED - Post-Exclusion)
```sql
SELECT Zone, 
       SUM(Revenue_L) as Total_Revenue_L,
       SUM(YoY_Growth%) / COUNT(*) as Avg_YoY_Growth%,
       COUNT(DISTINCT Store) as Store_Count
FROM (
  SELECT * FROM ZoneXBrandXArticle
  WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
)
GROUP BY Zone
ORDER BY Total_Revenue_L DESC;
```

**Expected Output:** 5 rows (one per zone)

**Sample Results (Estimated):**
```
Zone       | Total_Revenue_L | Avg_YoY_Growth% | Store_Count | Status
-----------|-----------------|-----------------|-------------|----------
South-1    | 2,145           | +85%            | 1,245       | Leading
West       | 1,678           | +82%            | 892         | Strong
South-2    | 1,234           | +79%            | 756         | Stable
North      | 892             | +78%            | 445         | Emerging
East       | 756             | +71%            | 389         | Early
-----------|-----------------|-----------------|-------------|----------
TOTAL      | 6,705           | +79%            | 3,727       | ✅ VERIFY
```

---

### Query 4: Category Focus (3 Primary Categories - FILTERED)
```sql
SELECT Category, Brand,
       SUM(Revenue_L) as Total_Revenue_L,
       COUNT(DISTINCT Store) as Store_Count,
       AVG(WD%) as Avg_WD%
FROM ZoneXBrandXArticle
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
  AND Category IN ('Face Wash', 'Suncare', 'Face Serum')
GROUP BY Category, Brand
ORDER BY Total_Revenue_L DESC;
```

**Expected Output:** ~15 rows (3 categories × ~5 brands each)

**Example:**
```
Category   | Brand        | Revenue_L | Store_Count | Avg_WD%
-----------|--------------|-----------|-------------|--------
Face Wash  | Mamaearth    | 1,234     | 2,100       | 78%
Face Wash  | Derma Co     | 892       | 1,500       | 71%
Face Wash  | Aqualogica   | 567       | 950         | 58%
Face Serum | Mamaearth    | 456       | 1,200       | 65%
Face Serum | Dr Sheth     | 345       | 800         | 62%
Suncare    | Mamaearth    | 312       | 1,100       | 71%
-----------|--------------|-----------|-------------|--------
TOTAL      | (all 3 cats) | 3,806     | 7,650       | ✅ TRACK
```

---

### Query 5: Honasa Top 4–5 Sub-Categories (FILTERED)
```sql
SELECT Sub_Category, 
       SUM(Revenue_L) as Total_Revenue_L,
       SUM(Revenue_L) / (SELECT SUM(Revenue_L) FROM table WHERE Brand NOT IN (...)) * 100 as % of Total
FROM ChannelXBrandXSub_cat
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
GROUP BY Sub_Category
ORDER BY Total_Revenue_L DESC
LIMIT 5;
```

**Expected Output:** Top 5 sub-categories (for trend line visualization)

**Example:**
```
Sub_Category    | Revenue_L | % of Total
----------------|-----------|----------
Face Wash       | 2,693     | 40.1%
Suncare         | 312       | 4.7%
Face Serum      | 456       | 6.8%
Shampoo         | 1,234     | 18.4%
(Other)         | 1,010     | 15.1%
```

---

### Query 6: Secondary Placement Uplift (FILTERED)
```sql
SELECT Zone, Chain, Store_Count,
       FW_Revenue_Without_Suncare_L,
       FW_Revenue_With_Suncare_L,
       (FW_Revenue_With_Suncare_L - FW_Revenue_Without_Suncare_L) / FW_Revenue_Without_Suncare_L * 100 as Uplift%
FROM Chain_X_Brand
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
  AND Data_Type = 'Store-Level Basket'
GROUP BY Zone, Chain;
```

**Expected Output:** 15–25 rows (zones × chains)

**Validation:** Uplift% should be 18–24% range

---

### Query 7: Trade ROI (FILTERED)
```sql
SELECT Zone, Month,
       Promoter_Investment_L,
       Direct_Volume_Uplift_L,
       Direct_Volume_Uplift_L / Promoter_Investment_L as ROI_Multiplier,
       (Days_in_Month * Promoter_Investment_L) / Direct_Volume_Uplift_L as Payback_Days
FROM Chain_X_Brand
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
  AND Data_Type = 'Promoter Deployment'
  AND Month IN ('May-2026', 'Jun-2026', 'Jul-2026')
ORDER BY Zone, Month;
```

**Expected Output:** 15 rows (3 months × 5 zones)

**Validation:** ROI 2.8x–3.2x for South-1/West, 1.5x–2.0x for North/East

---

## Revenue Verification (CRITICAL)

### Step 1: Extract Filtered Total
```
SELECT SUM(Primary_Revenue_L) as Total_Filtered_Revenue
FROM ALL_DATA
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
  AND Period = 'Jul 2026' (Current month FYTD)
```

### Expected Result:
- **Headline:** ₹18,574 Lacs (FYTD Jul 2026)
- **YoY Growth:** +82.3% (vs Jul 2025 FYTD)

### If Actual Result ≠ Expected:
```
Variance_Lacs = Expected - Actual
% Variance = (Variance_Lacs / Expected) * 100

If % Variance > 5%:
  1. Identify which excluded brands were in original ₹18,574L
  2. Calculate corrected headline
  3. UPDATE SLIDE 3 with accurate figure
  4. Add footnote explaining exclusion (if variance > 10%)

If % Variance < 5%:
  1. Keep ₹18,574L as headline (rounding variance acceptable)
  2. No update needed
```

### Backup Calculation (If Data Not Available):
```
Manual Spot-Check Method:
  - Manually add Jul 2026 primary revenue for:
    ✅ Mamaearth (all categories)
    ✅ Derma Co (all products)
    ✅ Aqualogica (all products)
    ✅ Bblunt (Hair)
    ✅ Dr Sheth (all products)
  
  ❌ Subtract (if included in original):
    ❌ Luminev
    ❌ Pure Origin
    ❌ Staze
  
  Result = Filtered Primary Revenue (should ≈ ₹18,574L)
```

---

## Face, Hair, Baby Categories Analysis

### Face Category (PRIMARY FOCUS)
```sql
SELECT Brand, Category, 
       SUM(Revenue_L) as Revenue_L,
       AVG(WD%) as Avg_WD%,
       (Revenue_L_Jul2026 - Revenue_L_Jul2025) / Revenue_L_Jul2025 * 100 as YoY_Growth%
FROM ChannelXBrandXSub_cat
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
  AND Category_Family = 'Face'
GROUP BY Brand, Category
ORDER BY Revenue_L DESC;
```

**Status:** ✅ FULL DATA AVAILABLE  
**Usage:** Primary focus in morning presentation

---

### Hair Category (SECONDARY FOCUS)
```sql
SELECT Brand, 
       SUM(Revenue_L) as Revenue_L,
       AVG(WD%) as Avg_WD%,
       YoY_Growth%
FROM ChannelXBrandXSub_cat
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
  AND Category_Family = 'Hair'
  AND Brand IN ('Bblunt', 'Mamaearth')
GROUP BY Brand;
```

**Status:** ⚠️ INCLUDE IF UPLIFT DATA EXISTS  
**Usage:** Secondary section (if slide space available)

**Example:**
```
Brand      | Revenue_L | YoY_Growth% | Avg_WD% | Note
-----------|-----------|-------------|---------|----------
Bblunt     | 1,234     | +45%        | 68%     | Strong performer
Mamaearth  | 456       | +62%        | 52%     | Growing
-----------|-----------|-------------|---------|----------
HAIR TOTAL | 1,690     | +52%        | 60%     | ✅ Include
```

---

### Baby Category (OPPORTUNITY ANALYSIS)
```sql
SELECT Brand, 
       SUM(Revenue_L) as Revenue_L,
       AVG(WD%) as Avg_WD%,
       YoY_Growth%,
       Promoter_Coverage%
FROM ChannelXBrandXSub_cat
WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
  AND Category_Family = 'Baby'
GROUP BY Brand;
```

**Status:** ❓ CHECK IF DATA EXISTS  
**Usage:** Optional talking point (if uplift opportunity identified)

**Decision Logic:**
- **If data exists + growth > 40%:** Include in main presentation
- **If data exists + growth 20–40%:** Mention as "opportunity for follow-up"
- **If data missing or flat:** Skip for now, revisit in Aug 12 follow-up

**Example Scenarios:**
```
Scenario A: Baby showing +55% YoY growth
→ Action: Include slide, highlight as emerging opportunity
→ Talking point: "Baby category tracking +55% YoY; applying Suncare playbook could accelerate growth"

Scenario B: Baby showing +8% YoY growth
→ Action: Skip for now, mention verbally if asked
→ Talking point: "Baby category is building; recommend focused sprint after Q1 review"

Scenario C: No Baby data available
→ Action: Don't mention
→ Talking point: (silence is okay; focus on Face/Hair)
```

---

## Spot-Check Validation (BEFORE 10am Aug 10)

**Do these 5-minute spot-checks 1 hour before meeting:**

### Check 1: Brand Exclusion Complete?
```
Search deck PDF for: "Luminev" OR "Pure Origin" OR "Staze"
Expected result: 0 matches
If found: STOP → Delete and re-export
```

### Check 2: Revenue Figure Accurate?
```
Slide 3 headline: ₹18,574 Lacs +82.3% YoY
Cross-check: Does this match filtered data after exclusion?
If no: Update with correct figure
```

### Check 3: Zone Metrics Realistic?
```
South-1 revenue > West revenue > South-2 revenue > North > East
All WD% in 45–85% range
All YoY growth in 60–110% range
✅ If yes → All checks pass
❌ If no → Investigate anomaly
```

### Check 4: Charts Render Correctly?
```
Open PPT → Presentation Mode (F5)
Sweep all zone slides (10–14)
Check: No broken charts, no #REF!, text readable
✅ If yes → Ready to present
❌ If no → Fix before 10am
```

### Check 5: File Size OK?
```
Filtered_v2.5.pptx file size < 3 MB
Filtered_v2.5.pdf file size < 5 MB
✅ If yes → Safe to email/share
❌ If no → Compress images
```

---

## Summary: What Gets Filtered

| Element | Status | Action |
|---------|--------|--------|
| **Brands to Remove** | Luminev, Pure Origin, Staze | DELETE from all rows, charts |
| **Brands to Keep** | Mamaearth, Derma Co, Aqualogica, Bblunt, Dr Sheth | INCLUDE all data |
| **Categories to Focus** | Face Wash, Suncare, Face Serum | PRIMARY in all zone slides |
| **Sub-Categories to Track** | Top 4–5 Honasa categories | SHOW in trend line |
| **Regions to Include** | All 5 zones (West, South-1, North, South-2, East) | KEEP all metrics |
| **Time Period** | Apr 2025 – Jul 2026 (16 months) | INCLUDE full history |
| **Revenue Headline** | ₹18,574L +82.3% YoY | VERIFY after exclusion |
| **Face/Hair/Baby** | Face primary, Hair optional, Baby if uplift exists | INCLUDE per criteria |

---

## Apply Filter & Verify (Checklist)

- [ ] Extract primary sales data (Query 1–7 above)
- [ ] Apply WHERE Brand NOT IN ('Luminev', 'Pure Origin', 'Staze')
- [ ] Verify ₹18,574L revenue matches (Query Revenue Verification above)
- [ ] If variance > 5%: Recalculate and update headline
- [ ] Check Baby category: Include if uplift > 40%, skip if < 20%
- [ ] Search deck for excluded brand names: Should find 0 results
- [ ] Spot-check 3–5 zone metrics: All realistic
- [ ] Export PPT + PDF: File size < 3–5 MB
- [ ] 1-hour pre-meeting: Do 5 spot-checks above
- [ ] ✅ READY for 10am presentation

---

**Status:** READY TO APPLY  
**Deadline:** Verification complete by 9:30am Aug 10  
**Next Step:** Confirm revenue figure after exclusion, then proceed with V2.5/V3 prep
