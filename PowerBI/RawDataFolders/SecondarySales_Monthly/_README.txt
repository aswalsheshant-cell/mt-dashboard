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

JUL-AUG 2026 (added 2026-09-27):
  secondary_sales_{distributor,chain,brand}_Jul_Aug_FY27.csv are built from the monthly
  Distributor_Chain_Brand_Article_Billing_<Month>_2026.xlsx workbooks:
    python scripts/build_secondary_register.py --src <folder with those xlsx files>
  Month = Invoice Date. Date repairs, late-reported invoices, GST-basis flags and missing
  registers are listed in SecondarySales_Monthly_TOT_Analysis/06_REGISTER_EXCEPTIONS_Jul_Aug_2026.csv.
  For Sep'26 onward: add the month name to MONTHS/COVERED in that script, then re-run.

DO NOT USE the 2026-08 rows of secondary_sales_tot_hierarchy_Apr_Aug_2026.csv as distributor
secondary: they are ship-to billing (Avenue Supermarts DCs, Apollo Healthco branches), not sell-out.

PENDING: North distributor registers (Q1 FY27, Jul'26, Aug'26) — once received, re-run.
