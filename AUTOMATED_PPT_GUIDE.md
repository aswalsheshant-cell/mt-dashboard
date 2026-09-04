# Automated 1-Pager PPT Generator Guide

## Overview

The automated PowerPoint generator transforms your **MT Primary vs. Offtake Analysis Excel template** into a professional executive presentation in seconds.

**What it does:**
- Reads metrics from the Excel template (Primary NSV, Offtake NSV, gap %, zone breakdown)
- Applies RAG status logic (Green/Amber/Red based on variance thresholds)
- Generates a 16:9 single-slide executive presentation
- Auto-updates whenever the Excel template is modified

**When to use:**
- Weekly leadership briefings on Primary vs. Offtake alignment
- Monthly zone and chain performance reviews
- Executive presentations to stakeholders
- Quick circulation to sales and commercial teams

---

## Quick Start

### Option 1: Run Locally (Recommended for Drafts)

**Prerequisites:**
```bash
pip install python-pptx openpyxl
```

**Generate the presentation:**
```bash
python generate_1pager_ppt.py
```

**Output:** `MT_Primary_vs_Offtake_1Pager.pptx` in the current directory.

**Download and open:**
- Mac/Windows: Double-click the `.pptx` file
- Cloud: Upload to Google Drive and open with Google Slides
- Share: Email the file directly to stakeholders

---

### Option 2: Auto-Generate via GitHub Actions (Recommended for Production)

**How it works:**
1. Update the Excel template with new month's data
2. Push the file to the `main` branch
3. GitHub Actions automatically regenerates the PPT
4. Updated presentation is committed back to the repository

**To download the auto-generated PPT:**

**From GitHub Web:**
1. Open [https://github.com/aswalsheshant-cell/mt-dashboard](https://github.com/aswalsheshant-cell/mt-dashboard)
2. Navigate to: `MT_Primary_vs_Offtake_1Pager.pptx`
3. Click **Download raw file** (top-right corner)

**From Command Line:**
```bash
git pull origin main
# File: MT_Primary_vs_Offtake_1Pager.pptx
```

---

## Step-by-Step: Fill Excel → Generate PPT

### Step 1: Open Excel Template

```bash
# Open locally (Mac/Windows)
open MT_Primary_vs_Offtake_Analysis_Template.xlsx
# or on Linux/WSL
libreoffice MT_Primary_vs_Offtake_Analysis_Template.xlsx
```

### Step 2: Enter Your Data

**Executive Summary Section (Row 7–16):**
| Cell | Metric | Example |
|------|--------|---------|
| B7 | Primary NSV (₹ Cr) | `48.2` |
| B8 | Primary MoM (%) | `+4.2` |
| B9 | Primary YoY (%) | `+12.5` |
| B11 | Offtake NSV (₹ Cr) | `44.6` |
| B12 | Offtake MoM (%) | `+2.8` |
| B13 | Offtake YoY (%) | `+8.3` |
| B15 | Alignment Gap (%) | `3.6` |
| B16 | Status | `Amber` |

**Zone Breakdown (Rows 27–32):**
| Zone | Primary (B) | Offtake (C) | Gap % (D) |
|------|----------|----------|-------|
| North | 12.4 | 11.1 | 10.5 |
| South-1 | 10.8 | 10.5 | 2.8 |
| South-2 | 11.2 | 9.8 | 12.5 |
| East | 6.5 | 6.2 | 4.6 |
| West | 4.1 | 4.0 | 2.4 |
| Central | 3.2 | 3.0 | 6.3 |

**Alert Bullets (Optional, Column F, Rows 8–11):**
If you want custom alerts instead of auto-generated ones:
- F8: Custom alert 1
- F9: Custom alert 2
- F10: Custom alert 3
- F11: Custom alert 4

### Step 3: Generate the PPT

**Option A — Local Generation:**
```bash
python generate_1pager_ppt.py
# Output: MT_Primary_vs_Offtake_1Pager.pptx
```

**Option B — Auto-Generate via Push:**
```bash
git add MT_Primary_vs_Offtake_Analysis_Template.xlsx
git commit -m "data: update Primary vs Offtake for [Month]"
git push origin main

# GitHub Actions automatically regenerates the PPTX
# Check status: GitHub > Actions > Auto-Generate 1-Pager PPT workflow
```

### Step 4: Download & Share

**From GitHub:**
1. [Open repository](https://github.com/aswalsheshant-cell/mt-dashboard)
2. Find `MT_Primary_vs_Offtake_1Pager.pptx`
3. Click **Raw** or **Download raw file**

**Via Git CLI:**
```bash
git pull origin main
open MT_Primary_vs_Offtake_1Pager.pptx
```

---

## PPT Slide Layout

### Single-Slide Structure (16:9 Widescreen)

**Top Section (Header):**
- Title: "Monthly Modern Trade Primary vs. Offtake Snapshot"
- 3 KPI Cards:
  - **Primary Sales** (₹ X.X Cr, MoM trend)
  - **Offtake Sales** (₹ X.X Cr, MoM trend)
  - **Alignment Gap** (X.X%, RAG status)

**Bottom-Left (Zone Performance Table):**
- 6 zones (North, South-1, South-2, East, West, Central)
- Columns: Zone | Primary (Cr) | Offtake (Cr) | Gap Status (🟢/🟡/🔴)

**Bottom-Right (Executive Action & Alerts):**
- Critical alerts (🔴 Red, 🟡 Amber, 🟢 Green)
- Generated or custom alerts from Excel
- Action items and recommendations

**Footer:**
- Source attribution: "MT Dashboard Primary vs Offtake Analysis"
- Timestamp: Auto-generated timestamp

---

## RAG Status Logic (Automatic)

The script automatically evaluates gap percentages and assigns colors:

| Gap Range | Status | Color | Meaning |
|-----------|--------|-------|---------|
| **< 2%** | 🟢 GREEN | Green | Strong alignment; secondary sales on pace |
| **2–5%** | 🟡 AMBER | Orange | Needs attention; mild inventory buildup or secondary lag |
| **> 5%** | 🔴 RED | Red | Critical; immediate action required |

**Example:**
- Primary = ₹48.2 Cr, Offtake = ₹44.6 Cr → Gap = 3.6% → 🟡 **AMBER**
- Primary = ₹48.2 Cr, Offtake = ₹42.0 Cr → Gap = 12.9% → 🔴 **RED**

---

## GitHub Actions Automation

### How It Works

**File:** `.github/workflows/generate_ppt.yml`

**Triggers on:**
- Any push to `main` that modifies:
  - `MT_Primary_vs_Offtake_Analysis_Template.xlsx`
  - `generate_1pager_ppt.py`
- Manual trigger via **Actions** tab

**Process:**
1. Checkout code
2. Install Python dependencies (`python-pptx`, `openpyxl`)
3. Run `python generate_1pager_ppt.py`
4. Compare old vs. new PPTX (binary diff)
5. If changed: commit with `[skip ci]` tag and push to `main`
6. Dashboard updated within 2 minutes

### Monitor Workflow Status

1. Open [GitHub Actions tab](https://github.com/aswalsheshant-cell/mt-dashboard/actions)
2. Find **"Auto-Generate 1-Pager PPT"** workflow
3. Look for latest run:
   - ✅ **Success** = PPT updated and committed
   - ⏳ **In Progress** = Currently generating
   - ❌ **Failed** = Check error log and retry

---

## Troubleshooting

### Issue: Script fails with "float division by zero"
**Cause:** Excel cells contain `[Enter Value]` placeholders instead of numbers.
**Solution:** Fill all cells in rows 7–16 and 27–32 with actual numeric values.

### Issue: Generated PPT has "No data" in KPI cards
**Cause:** Excel cells are still empty or contain text (not numbers).
**Solution:** Ensure B7, B11, B15, and zone columns (B, C) contain numeric values (not formulas or text).

### Issue: GitHub Actions workflow didn't trigger after pushing Excel
**Possible causes:**
- Workflow file has a syntax error → Check `.github/workflows/generate_ppt.yml`
- File paths in trigger don't match → Verify file names exactly match
- Branch is not `main` → Push to `main` only

**Fix:**
```bash
# Manually trigger via CLI
gh workflow run generate_ppt.yml --ref main

# Or visit GitHub > Actions > Auto-Generate 1-Pager PPT > Run workflow > main
```

### Issue: Alerts are generic instead of custom
**Cause:** Column F (alerts) is empty in Excel.
**Solution:** Fill cells F8–F11 with custom alert text:
```
F8: "West Zone: Secondary inventory build-up exceeds 34 days; freeze non-moving SKUs."
F9: "Top 5 Chains: Reliance and DMart drive 68% of total conversion; DMart fill rate slipped 3%."
```

### Issue: Can't download PPT from GitHub
**Solution:**
```bash
# Clone or pull the repo
git pull origin main

# Find the file
ls -lh MT_Primary_vs_Offtake_1Pager.pptx

# Or download raw file via URL
curl -o MT_PPT.pptx https://raw.githubusercontent.com/aswalsheshant-cell/mt-dashboard/main/MT_Primary_vs_Offtake_1Pager.pptx
```

---

## Advanced: Customize the Script

### Edit Colors
Open `generate_1pager_ppt.py` and modify RGB values:
```python
COLOR_RED = RGBColor(190, 40, 40)      # Red alerts
COLOR_AMBER = RGBColor(200, 120, 0)    # Amber alerts
COLOR_GREEN = RGBColor(40, 140, 40)    # Green status
COLOR_DARK = RGBColor(24, 43, 73)      # Dark blue (headers)
```

### Edit RAG Thresholds
Find the `get_rag_status()` function and adjust thresholds:
```python
if gap <= 2.0:
    return ("Green", COLOR_GREEN)
elif gap <= 5.0:
    return ("Amber", COLOR_AMBER)
else:
    return ("Red", COLOR_RED)
```

### Change Font Sizes
Modify `Pt()` values (in points) throughout the script:
```python
p.font.size = Pt(22)   # Title: 22pt
p.font.size = Pt(18)   # KPI value: 18pt
p.font.size = Pt(10)   # Table cell: 10pt
```

---

## Monthly Workflow

**Week 1 (Month-End):**
1. Receive offtake files from Data team
2. Open `MT_Primary_vs_Offtake_Analysis_Template.xlsx`
3. Fill Executive Summary (B7–B16) and Zone Breakdown (rows 27–32)
4. Save and push to Git: `git add ... && git commit -m "data: ..." && git push`

**Automatic (GitHub Actions):**
5. Workflow triggers → regenerates PPT → commits to `main`

**Week 2 (Leadership Review):**
6. Download latest PPT from GitHub
7. Share with Zone Heads, Category Managers, Sales Leadership
8. Use as reference for Weekly RAG Review meeting

---

## FAQ

**Q: Can I customize the slide layout?**
A: Yes. The script is fully modular. Edit `build_presentation()` function to reorder KPI cards, change table layout, or add new sections.

**Q: What if I need multiple slides (zone detail, chain breakdown)?**
A: Extend the script to loop through zones/chains and create slides programmatically using `prs.slides.add_slide()`.

**Q: Can I generate PDF instead of PPTX?**
A: Install `python-pptx-pdf` or use PowerPoint CLI: `python -m pptx_pdf <file>.pptx <file>.pdf`.

**Q: How often is the PPTX auto-updated?**
A: Only when you push changes to the Excel template. Manual edits to Excel locally require you to either:
- Run `python generate_1pager_ppt.py` locally, or
- Push the Excel file to trigger GitHub Actions

**Q: Can I use this with other templates?**
A: Yes. Modify `load_excel_metrics()` to read different cell ranges and data structures.

---

## Technical Details

### Files Modified
- `.github/workflows/generate_ppt.yml` — GitHub Actions workflow (auto-regeneration)
- `generate_1pager_ppt.py` — Python script (PPT generator logic)
- `MT_Primary_vs_Offtake_1Pager.pptx` — Generated presentation (check into git)

### Dependencies
```bash
python-pptx>=0.6.21   # PowerPoint generation
openpyxl>=3.0.0      # Excel parsing
```

### Size
- Script: ~11 KB
- Generated PPT: ~29 KB (scales with data)
- Excel template: ~7.2 KB

### Performance
- Local generation: <1 second
- GitHub Actions run: ~30 seconds (including checkout, install, generate, commit, push)

---

## Support & Escalation

**Questions on using the generator?**
→ Refer to this guide or ask the Data team

**Technical issues (workflow not triggering)?**
→ Check GitHub Actions logs: [Actions tab](https://github.com/aswalsheshant-cell/mt-dashboard/actions)

**Want to add new metrics or customize the slide?**
→ Modify `generate_1pager_ppt.py` and re-commit

**Need a different format (PDF, Google Slides)?**
→ Use the generated PPTX as a base; PowerPoint → Export as PDF/Google Slides

---

**Last Updated:** 2026-09-04  
**Version:** 1.0  
**Maintained By:** Engineering Team

