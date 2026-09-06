SECONDARY SALES — WATCH FOLDER
================================
Drop distributor sell-out CSV files here. Power BI will pick them up on the next Refresh.

REQUIRED FILE NAMING:
  secondary_sales_distributor_<period>.csv   ← by distributor × month
  secondary_sales_chain_<period>.csv         ← by chain × month
  secondary_sales_brand_<period>.csv         ← by brand × month

GENERATE FROM dashboard/data.js:
  python scripts/export_pbi_csvs.py --blocks secondary --out PowerBI/RawDataFolders

REQUIRED COLUMN HEADERS (do NOT rename):
  Distributor file:  Source_Month, Month_Label, FY_Year, Distributor, NSV_Lakh, Data_Source, Notes
  Chain file:        Source_Month, Month_Label, FY_Year, Chain, NSV_Lakh
  Brand file:        Source_Month, Month_Label, FY_Year, Brand, NSV_Lakh

MONTHLY REFRESH PROCEDURE:
  1. Run ingest_claims_and_secondary.py with updated All_Sancus_Months.xlsx
  2. Run export_pbi_csvs.py --blocks secondary
  3. Drop new CSV files here (replace existing for same period, append for new period)
  4. In Power BI Desktop: Home → Refresh

PENDING: North distributor registers (Q1 FY27) — once received, re-run step 1-4.
