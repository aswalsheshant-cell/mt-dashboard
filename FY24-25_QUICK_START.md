# FY24-25 Data Restoration - Quick Start (5 Minutes)

## TL;DR

```bash
# 1. Download 2 XLSB files from Google Drive to ~/Downloads/MT-Sources/
# 2. Run automated processing:
python scripts/process_fy24_25_data.py \
    --primary ~/Downloads/MT-Sources/"MT, Eb2B & SIS primary April_23 to May_26.xlsb" \
    --offtake ~/Downloads/MT-Sources/"FY-24-26 Chain offtake Store Wise File till May.xlsb"

# 3. Commit CSVs:
git add PowerBI/RawDataFolders/
git commit -m "Add FY24-25 monthly data splits"
git push

# 4. Rebuild dashboard:
python scripts/build_dashboard_data.py --src PowerBI/RawDataFolders --out dashboard/data.js

# 5. Open dashboard/index.html → Select FY25 from dropdown
```

---

## File Downloads

| File | Size | Where | Link |
|------|------|-------|------|
| Primary Article | 174 MB | `pRIMARY/` folder | [Link](https://drive.google.com/file/d/1R8sg2YONPcPUWb-Qky7eIUdiFXAwweMt/view) |
| Offtake Store Article | 185 MB | `oFFTAKE/` folder | [Link](https://drive.google.com/file/d/1cl2eR8nDwip7IUVYbLEU2b_26iy---EO/view) |

**Save to:** `~/Downloads/MT-Sources/` (or any local path)

---

## What Gets Created

| Step | Output | Location |
|------|--------|----------|
| **Split Primary** | 26 CSV files (Apr'24-May'26) | `PowerBI/RawDataFolders/Primary_Article_Monthly/` |
| **Split Offtake** | Monthly offtake data | `PowerBI/RawDataFolders/Offtake_Monthly/` |
| **Rebuild Dashboard** | New data.js with FY25 | `dashboard/data.js` (21 MB) |

---

## Expected Result

✓ FY25 filter appears on dashboard
✓ Primary tab shows Apr'24-Mar'25 data
✓ Offtake tab shows FY25 offtake (if split succeeded)
✓ All metrics and exports work for FY25

---

## If Something Fails

**Scripts won't run:**
```bash
pip install pyxlsb
```

**File not found errors:**
- Check file paths have correct quotes: `"Path with spaces/file.xlsb"`
- Use full paths: `/Users/yourname/Downloads/MT-Sources/...`

**Split hangs or takes > 10 min:**
- XLSB file may be corrupted
- Check file downloaded completely (compare file size to Google Drive)

**Dashboard still no FY25:**
- Hard refresh browser: `Ctrl+Shift+R`
- Check new data.js was created: `ls -lht dashboard/data.js`

---

## Full Documentation

See **FY24-25_DATA_RESTORATION_GUIDE.md** for complete step-by-step instructions, troubleshooting, and verification steps.
