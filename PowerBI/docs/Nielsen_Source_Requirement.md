# Nielsen Market Share — Source Requirement

**Status:** PARTLY AUTOMATED (updated 2026-10-04) — real Nielsen workbook cut for Facewash and Shampoo, market IN URB MT  
**Current state:** `PowerBI/SeedData/Nielsen/Nielsen_Monthly/nielsen_urban_mt_aug26.csv` and `Nielsen_Pack_Monthly/nielsen_pack_urban_mt_aug26.csv`, built by `scripts/build_nielsen_powerbi_seed.py` from `data/nielsen/*.csv` (extracted from the two Aug-26 Nielsen workbooks). Other categories (Sunscreen, Face Serum) still need a Nielsen export, and state / chain level share needs a state-level Nielsen cut (the deck's Jun'26 state table is typed into `SeedData/Masters/Nielsen_Deck_StateExposure.csv`, labelled as deck figures)  

---

## Why Nielsen Is Not Automated

The repository contains only three presentation-slide values extracted manually
from Nielsen RMS reports (2 categories × ~3 time points). These are in
`build_dashboard_data.py` and power the HTML dashboard's Market Share tab.

They are **not** a usable Power BI data source because:
- They are not at the grain the report needs (chain × category × month)
- They are not refreshable without Nielsen RMS system access
- The values are hardcoded strings, not structured tabular data

---

## What Power BI Needs

To fully automate the Market Share module, upload a Nielsen RMS export with these columns:

| Column | Type | Example |
|--------|------|---------|
| Month | Text | `Apr'26` |
| Category | Text | `Face Care` |
| Nielsen Category | Text | `Face Care - RMS` |
| Brand | Text | `Mamaearth` |
| Market Share % | Number | 4.32 |
| Market Size ₹ Cr | Number | 1247.5 |
| Source | Text | `Nielsen RMS` |

Save as `PowerBI/RawDataFolders/Nielsen/nielsen_<YYYY_MM>.csv` and refresh.

---

## Current Workaround

The DAX measures in `11_MarketShare.dax` reference `Fact Nielsen[Nielsen Category]`
and `Fact Nielsen[Market Share %]`. As long as no Nielsen CSV is loaded, these
measures return BLANK() and the Market Share visuals show no data — which is
correct and honest behaviour.

Do **not** hard-code Nielsen values into DAX. When real data is available, load
the CSV and the measures will populate automatically.

---

## Template

A template CSV with the correct column headers is at:
`PowerBI/SeedData/Templates/Nielsen_Template.csv`
