CLAIM MASTER — WATCH FOLDER
============================
Drop quarterly claim expense CSVs here. Power BI will pick them up on the next Refresh.

REQUIRED FILE NAMING:
  claim_master_chain_<period>.csv         ← chain-level expense by category
  claim_master_brand_<period>.csv         ← brand-level MoM expense
  claim_master_distributor_<period>.csv   ← distributor-level MoM expense

GENERATE FROM dashboard/data.js:
  python scripts/export_pbi_csvs.py --blocks claims --out PowerBI/RawDataFolders

CHAIN FILE COLUMNS:
  Period, FY_Year, Quarter, Chain, Source_Chain,
  Chain_Promo_Lakh, Rate_Diff_Lakh, Freight_Lakh, Incentive_Lakh,
  Off_Invoice_Lakh, Visibility_Lakh, Total_Claim_Lakh

BRAND FILE COLUMNS:
  Period, FY_Year, Quarter, Brand, Apr_Lakh, May_Lakh, Jun_Lakh, Total_Lakh

DISTRIBUTOR FILE COLUMNS:
  Period, FY_Year, Quarter, Distributor, Source_Name,
  Apr_Lakh, May_Lakh, Jun_Lakh, Total_Claim_Lakh

QUARTERLY REFRESH PROCEDURE:
  1. Receive updated Claim Excel from Finance (invoice-mapped version)
  2. Run ingest_claims_and_secondary.py --claim <new_excel>
  3. Run export_pbi_csvs.py --blocks claims
  4. Replace CSVs in this folder for the same quarter
  5. Power BI Desktop: Home → Refresh

FINANCE SIGN-OFF REQUIRED for: AirPlaza, Combined Charge, Fleet Labs,
  Transportation, Beauty & Nutrition (currently ₹0 — confirm reclassification).
