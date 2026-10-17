# Data source map

Rebuilt by `scripts/audit_data_source_map.py`. Static map from the repo (model.bim, dashboard/*.html|js, config/data_source_registry.yml, Git, restricted_source_policy.yml).

Generated 2026-10-17. References: 130. Missing: 0. Files in use: 125. Folders with more than one column layout: 13. Unpinned layouts: 0. Unreferenced files: 36.

## Missing references

None. Every path a query, the HTML dashboard or the registry names exists. Folders that are meant to be empty until a file arrives (Primary_Weekly, TDP_Monthly) are not counted.

## Kept out of Git on purpose (must exist on the machine that builds the data)

- `data/raw_drops/MT_Provision_National_Aug26.xlsx` (Registry: mt_provision_national_aug26)
- `data/raw_drops/offtake_fy26/` (Registry: offtake_fy26_store_article)

## Folders whose files do not share one column layout

Each layout below is accepted and pinned in `config/data_header_pins.json`. A file with a layout that is not pinned fails `tests/test_data_source_map.py`.

### `PowerBI/RawDataFolders/ClaimMaster_Quarterly`
- layout `ed324bfb22` (14 columns): `claim_master_chain_AprJun_2026.csv`
- layout `ed32797022` (9 columns): `claim_master_distributor_AprJun_2026.csv`
- layout `ffce977ec2` (8 columns): `claim_master_brand_AprJun_2026.csv`
  - only in `ed324bfb22`: `Chain`, `Source_Chain`, `Chain_Promo_Lakh`, `Rate_Diff_Lakh`, `Freight_Lakh`, `Incentive_Lakh`, `Off_Invoice_Lakh`, `Visibility_Lakh`, `Total_Claim_Lakh`, `Entity`
  - only in `ed32797022`: `Distributor`, `Source_Name`, `Apr_Lakh`, `May_Lakh`, `Jun_Lakh`, `Total_Claim_Lakh`
  - only in `ffce977ec2`: `Brand`, `Apr_Lakh`, `May_Lakh`, `Jun_Lakh`, `Total_Lakh`

### `PowerBI/RawDataFolders/Master_Data`
- layout `11dae1e7bb` (9 columns): `Chain_Article_EAN_Mapping.csv`
- layout `7e7173b6f4` (4 columns): `Chain_Summary.csv`
  - only in `11dae1e7bb`: `Sr_No`, `Chain_Canonical`, `Brand_Canonical`, `Article_Code`, `FY25_Total_NSV_Lakh`, `Months_Covered`, `Derivation_Method`, `Brand_Aliases`, `Data_Status`
  - only in `7e7173b6f4`: `Chain`, `Total_Articles`, `Brands_Carried`, `Chain_Total_NSV_Lakh`

### `PowerBI/RawDataFolders/Offtake_Monthly`
- layout `15345ae9f7` (39 columns): `offtake_store_article_Jun_26.csv`
- layout `3f3e5153bc` (35 columns): `offtake_store_article_Jul_26.csv`
- layout `b935bb811b` (37 columns): `offtake_store_article_Apr_26.csv`
- layout `bdaf71530d` (34 columns): `offtake_store_article_Aug_26.csv`, `offtake_store_article_Sep_26.csv`
- layout `eef7db576a` (35 columns): `offtake_store_article_May_26.csv`
  - only in `15345ae9f7`: `col0`, `Unique`, `SO/ASE Name`, `DC Name`, `Internal Code`, `With Tax`, `MRP 2`, `M-Value`, `MRP In Lac`, `Stock report`
  - only in `3f3e5153bc`: `Unique`, `SO/ASE Name`, `DC Name`, `Internal Code`, `With Tax`, `Offtake Status`
  - only in `b935bb811b`: `col0`, `Unique`, `0xf`, `MRP 2`, `M-Value`, `MRP In Lac`, `0x2a`, ```
  - only in `bdaf71530d`: `Unique Code`, `SO/ASE Name`, `DC Name`, `Internal Code`, `With Tax`
  - only in `eef7db576a`: `col0`, `Unique`, `SO/ASE Name`, `DC Name`, `Internal Code`, `With Tax`

### `PowerBI/RawDataFolders/Primary_Article_Monthly`
- layout `66159ab92c` (25 columns): `primary_article_Aug_26.csv`, `primary_article_Jul_26.csv`, `primary_article_Jun_26.csv`, `primary_article_Sep_26.csv`
- layout `a8659e9661` (35 columns): `primary_article_Apr_25.csv`, `primary_article_Apr_26.csv`, `primary_article_Aug_25.csv`, `primary_article_Dec_25.csv`, `primary_article_Feb_26.csv`, `primary_article_Jan_26.csv` ...
  - only in `66159ab92c`: `MRP`, `Chain name for Dashboard`
  - only in `a8659e9661`: `Purchase Order Number`, `Inv No.`, `Category`, `Article Code`, `SO No`, `MRP Rate`, `Plant`, `Chain name`, `Dist chain ten`, `Store Code`

### `PowerBI/RawDataFolders/SecondarySales_Monthly`
- layout `0064875d29` (5 columns): `secondary_sales_brand_Jul_Aug_FY27.csv`, `secondary_sales_brand_Q1_FY27.csv`
- layout `13fa01b41a` (7 columns): `secondary_sales_distributor_Jul_Aug_FY27.csv`, `secondary_sales_distributor_Q1_FY27.csv`
- layout `50d9767ab9` (13 columns): `secondary_sales_tot_hierarchy_Apr_Jul_2026.csv`
- layout `8b0a18a51b` (5 columns): `secondary_sales_chain_Jul_Aug_FY27.csv`, `secondary_sales_chain_Q1_FY27.csv`
- layout `a65c49f45f` (14 columns): `secondary_sales_tot_hierarchy_Apr_Aug_2026.csv`
  - only in `0064875d29`: `Month_Label`, `FY_Year`, `Brand`
  - only in `13fa01b41a`: `Month_Label`, `FY_Year`, `Distributor`, `Data_Source`, `Notes`
  - only in `50d9767ab9`: `Distributor`, `Dist_Monthly_Total`, `Chain`, `Chain_Monthly_Total`, `Chain_TOT_Pct`, `Brand`, `Brand_Monthly_Total`, `Brand_TOT_Pct`, `EAN`, `Article`
  - only in `8b0a18a51b`: `Month_Label`, `FY_Year`, `Chain`
  - only in `a65c49f45f`: `Month_Label`, `Distributor`, `Dist_Monthly_Total`, `Chain`, `Chain_Monthly_Total`, `Chain_TOT_Pct`, `Brand`, `Brand_Monthly_Total`, `Brand_TOT_Pct`, `EAN`

### `PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis`
- layout `24aa574c8b` (6 columns): `06_REGISTER_EXCEPTIONS_Jul_Aug_2026.csv`
- layout `50d9767ab9` (13 columns): `01_FULL_HIERARCHY_Apr_Jul_2026.csv`
- layout `68e59323c7` (17 columns): `05_ARTICLE_REGISTER_Jul_Aug_2026.csv`
- layout `8c33780ef3` (6 columns): `04_DISTRIBUTOR_CHAIN_MoM_TOT_Pivot.csv`
- layout `ab52758e57` (6 columns): `03_CHAIN_BRAND_TOT_Apr_Jul_2026.csv`
- layout `be04a7c560` (6 columns): `02_DISTRIBUTOR_CHAIN_TOT_Apr_Jul_2026.csv`
- layout `c668a051e7` (2 columns): `00_SUMMARY_Statistics.csv`
  - only in `24aa574c8b`: `Exception`, `Distributor`, `Month`, `Lines`, `NSV_Lakh`, `Detail`
  - only in `50d9767ab9`: `Source_Month`, `Distributor`, `Dist_Monthly_Total`, `Chain`, `Chain_Monthly_Total`, `Chain_TOT_Pct`, `Brand`, `Brand_Monthly_Total`, `Brand_TOT_Pct`, `EAN`
  - only in `68e59323c7`: `Source_Month`, `Register_Month`, `FY_Year`, `Distributor_Code`, `Distributor`, `Distributor_Source`, `Chain`, `Chain_Source`, `Brand`, `EAN`
  - only in `8c33780ef3`: `Distributor`, `Chain`, `2026-04`, `2026-05`, `2026-06`, `2026-07`
  - only in `ab52758e57`: `Month`, `Chain`, `Brand`, `Brand_NSV_Lakh`, `Chain_Total_Lakh`, `Brand_TOT_Percent`
  - only in `be04a7c560`: `Month`, `Distributor`, `Chain`, `Chain_NSV_Lakh`, `Dist_Total_Lakh`, `Chain_TOT_Percent`
  - only in `c668a051e7`: `Metric`, `Value`

### `PowerBI/SeedData/Account`
- layout `2279f70841` (13 columns): `Account_Category_Geo.csv`
- layout `848bdb3fb9` (3 columns): `Account_Category_Map.csv`
- layout `a7d254d3fc` (7 columns): `Account_Assortment.csv`
- layout `c6ce769af3` (11 columns): `Account_Category_Monthly.csv`
  - only in `2279f70841`: `Month`, `Zone`, `State`, `City`, `Account Sales Rs L`, `Honasa Sales Rs L`, `Stores`, `Share %`, `Source`, `Relevant For Us`
  - only in `a7d254d3fc`: `Month`, `Articles`, `Stores`, `Relevant For Us`
  - only in `c6ce769af3`: `Month`, `Account Sales Rs L`, `Honasa Sales Rs L`, `Share %`, `Source`, `Level`, `Scope`, `Relevant For Us`

### `PowerBI/SeedData/DIST`
- layout `041b1a58a6` (5 columns): `ChainAllocationWeights.csv`
- layout `18dba9ac89` (11 columns): `DistPrimaryContWeightsArticle.csv`
  - only in `041b1a58a6`: `Ship To Name`, `Chain Name`, `NSV`
  - only in `18dba9ac89`: `Distributor`, `Ship_To_Name`, `Chain_Name`, `Cont_Pct`, `Source`, `Approved_Date`, `Approval_Status`, `Basis`, `Patch_File`

### `PowerBI/SeedData/Forecast`
- layout `0c763a2a08` (11 columns): `PO_vs_Target_Monthly_FY27.csv`
- layout `1d951c0689` (9 columns): `PO_Unfilled_Reasons_Monthly_Apr25_to_Aug26.csv`
- layout `de32378443` (19 columns): `PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv`
  - only in `0c763a2a08`: `FY Year`, `PO_Value_All_L`, `Billed_Value_All_L`, `PO_Value_MT_L`, `Billed_Value_MT_L`, `Target_L`, `PO_vs_Target_All_Pct`, `Abs_Error_All_Pct`, `PO_vs_Target_MT_Pct`, `Abs_Error_MT_Pct`
  - only in `1d951c0689`: `FY`, `Channel`, `Chain`, `Chain_Resolved`, `Reason`, `SO_Lines`, `Unfilled_Qty`, `Unfilled_Value_L`
  - only in `de32378443`: `FY`, `Channel`, `Customer_Group`, `Zone`, `Chain`, `Chain_Raw`, `Chain_Resolved`, `Brand`, `Category`, `SO_Lines`

### `PowerBI/SeedData/Mapping`
- layout `0543b5d449` (10 columns): `MT_Chain_Wise_NPI_Article_Aug26.csv`
- layout `25c0c6fd59` (10 columns): `DistCont_Patch_Approved_2026-07-04.csv`, `DistCont_Patch_Proposed.csv`
- layout `2f7ee619af` (7 columns): `ClaimDriver_Alias_Decisions_Q1_FY27.csv`
- layout `3499ce614f` (25 columns): `ChainAccount_Mapping_Inferred.csv`
- layout `3e07f960b5` (9 columns): `DistAllocationGovernance_FlaggedRows.csv`
- layout `42a258a350` (11 columns): `Store_SO_Mapping.csv`
- layout `4afd85a7ec` (12 columns): `CustomerCode_Zone_State_Mapping.csv`
- layout `509ce16be0` (17 columns): `DistPrimary_FY24-25_CategorySplit_offtakemix.csv`
- layout `6aa6914fe1` (26 columns): `ChainAccount_Mapping_PriorityView.csv`
- layout `82148423d1` (15 columns): `DistPrimary_Sheet1_FY24-25.csv`
- layout `b3dd0a3d9e` (9 columns): `CustomerCode_Zone_State_Exceptions.csv`
- layout `b86d56f505` (2 columns): `DistPrimary_FY24-25_CategorySplit_summary.csv`
- layout `bbc0cb9bb1` (10 columns): `Mapping_Corrections.csv`
- layout `caf99b1125` (10 columns): `Vidarbha_Central_Zone_Stores.csv`
- layout `d0d4430ab1` (5 columns): `ChainWisePrimarySale_Dump_Snapshot.csv`
- layout `e4b5483b33` (11 columns): `EanAffinity_ResidualProposal.csv`
  - only in `0543b5d449`: ``, ``, ``, ``, ``, `EAN`, ``, ``, ``, ``
  - only in `25c0c6fd59`: `Ship To Name`, `Direct/Distributor`, `Chain Name`, `Brand`, `Revised month`, `FY`, `Channel`, `Secondary contribution %`, `Confidence`, `Basis`
  - only in `2f7ee619af`: `Secondary_Name`, `Proposed_Chain`, `Evidence`, `Owner_Decision`, `Approver`, `Approval_Date`, `Approval_Reference`
  - only in `3499ce614f`: `Chain Name`, `Ship-To Name`, `Bill-To / Account (inferred)`, `Direct/Distributor`, `Brand`, `Month Logic`, `Months Covered`, `Month Range`, `Avg Cont%`, `Min Cont%`
  - only in `3e07f960b5`: `Eligibility_Tier`, `Month`, `Ship To Name`, `Brand`, `NSV (Lakh)`, `Eligibility Reasoning`, `Override_Action`, `Override_Chain`, `Override_Remarks`
  - only in `42a258a350`: `Month`, `Store Code`, `Employee ID 1`, `SO Name 1`, `Employee ID 2`, `SO Name 2`, `Employee ID 3`, `SO Name 3`, `Cont% 1`, `Cont% 2`
  - only in `4afd85a7ec`: `Customer Code`, `Customer Name / Ship-to Name`, `State`, `Zone`, `City / Location`, `Business Region / Sub-region`, `Chain Name`, `Account`, `Channel`, `Mapping Source`
  - only in `509ce16be0`: `Format`, `Ship To Direct/Distributor`, `Chain Name`, `State`, `Zone`, `Brand`, `Category`, `Sub_category`, `Range`, `Net Weight`
  - only in `6aa6914fe1`: `Priority Buckets`, `Chain Name`, `Ship-To Name`, `Bill-To / Account (inferred)`, `Direct/Distributor`, `Brand`, `Month Logic`, `Months Covered`, `Month Range`, `Avg Cont%`
  - only in `82148423d1`: `Ship To Name`, `Direct/Distributor`, `Chain Name`, `State`, `Zone`, `NSV`, `MRP value`, `Brand`, `Revised month`, `Month`
  - only in `b3dd0a3d9e`: `Exception Type`, `Customer Code`, `Customer Name / Ship-to Name`, `Chain Name`, `Zone(s)`, `State(s)`, `Business Region`, `Detail`, `Action`
  - only in `b86d56f505`: `Category`, `NSV (Cr)`
  - only in `bbc0cb9bb1`: `Date`, `Type`, `Month`, `Ship To / Distributor`, `Chain`, `Brand`, `Field`, `Original Value`, `Corrected Value`, `Remarks`
  - only in `caf99b1125`: `s.no`, `Site Code`, `Site Name`, `Chain Name`, `City`, `State`, `Zone`, `Zone_Revised`, `Sub_Zone`, `Remap_Date`
  - only in `d0d4430ab1`: `Month`, `Bill to customer`, `Brand`, `Chain Name`, `NSV`
  - only in `e4b5483b33`: `Ship To Name`, `Month`, `Brand`, `Article/EAN`, `Current Chain`, `Proposed Chain`, `Affinity %`, `Confidence`, `Primary NSV (Lakh)`, `Evidence Basis`

### `PowerBI/SeedData/Masters`
- layout `03a13bfe94` (4 columns): `BrandMaster.csv`
- layout `099be552e7` (8 columns): `PrimaryAllocationOverride.csv`
- layout `16235bc545` (4 columns): `NielsenCompetitorMaster.csv`
- layout `25b2875d7f` (8 columns): `NPI_List.csv`
- layout `25e70e0b67` (7 columns): `Store_Universe_Overrides.csv`
- layout `3a88b0eeb5` (10 columns): `Q3_FY27_Chain_Target_Primary.csv`
- layout `3edce78ea2` (8 columns): `ForecastOverride.csv`
- layout `438642d9f3` (8 columns): `ArticleMaster.csv`
- layout `4672240f2a` (14 columns): `FY27_Monthly_GMV_MRP.csv`
- layout `4b503b3dfb` (8 columns): `TDP_New_Articles_Since_Jan26.csv`
- layout `6027ba4a46` (3 columns): `ChannelMap_Store.csv`
- layout `793fa1cb17` (11 columns): `AssumptionTable.csv`
- layout `8577bd4bc5` (14 columns): `TDP_Focus_Articles.csv`
- layout `8784758dec` (6 columns): `Store_Key_Aliases.csv`
- layout `8cbeafdeea` (8 columns): `EAN_Product_Master.csv`
- layout `90d08ac177` (3 columns): `ChannelMap_Chain.csv`
- layout `990e530053` (12 columns): `PL_Distributor_Claim_Input_Q1_FY27.csv`
- layout `9fbb11e0c8` (15 columns): `PL_Distributor_Claim_Monthly_Allocated_Q1_FY27.csv`
- layout `9ffb465dd5` (6 columns): `ChainMaster.csv`
- layout `a01eaefa33` (5 columns): `Visit_City_List.csv`
- layout `a9ac52368d` (4 columns): `CategoryMaster.csv`
- layout `ab0f367da0` (4 columns): `Store_City_Master_QC.csv`
- layout `ac6334895f` (4 columns): `ZoneStateMaster.csv`
- layout `b2fc5d465c` (14 columns): `Nielsen_Deck_StateExposure.csv`
- layout `b4923765ed` (22 columns): `Store_City_Master.csv`
- layout `b5e89a9bb5` (17 columns): `PL_Expense_Input.csv`
- layout `c507599dea` (4 columns): `Store_City_Corrections.csv`
- layout `c5f9ee47ca` (6 columns): `ShipToMaster.csv`
- layout `d1601b6772` (3 columns): `ShipToChannelMap.csv`
- layout `d40d0bef37` (9 columns): `GST_Rate_QC_Table.csv`
- layout `e1525ba683` (2 columns): `GST_Config.csv`
- layout `fc04845269` (7 columns): `StoreMaster.csv`
  - only in `03a13bfe94`: `Brand`, `Brand Group`, `Brand Sort Order`, `Active`
  - only in `099be552e7`: `Month`, `Ship To Name`, `Chain`, `Brand`, `Override Cont%`, `Remarks`, `Evidence_Alignment`, `Evidence_Reference`
  - only in `16235bc545`: `Nielsen Category`, `Brand`, `Is Honasa`, `Competitor Sort Order`
  - only in `25b2875d7f`: `EAN`, `Primary Article Code`, `Description`, `Brand`, `Category`, `Sub-category`, `First Primary Month`, `NPI FY`
  - only in `25e70e0b67`: `Chain`, `Offtake Chain`, `Store Count`, `Status`, `Note`, `Source`, `As Of`
  - only in `3a88b0eeb5`: `FY`, `Quarter`, `Chain`, `Basis`, `Q3_Old_Target_L`, `Q3_New_Target_L`, `Unit`, `Source`, `Approved_By`, `Approved_Date`
  - only in `3edce78ea2`: `Month`, `Chain`, `Brand`, `Category`, `Article Code`, `Manual Forecast NSV`, `Growth Assumption %`, `Remarks`
  - only in `438642d9f3`: `Article Code`, `Article Description`, `EAN Code`, `Brand`, `Category`, `Sub-category`, `Range`, `Pack Size`
  - only in `4672240f2a`: `Month`, `GMV_MRP_Sales_L`, `NSV_Control_L`, `Source_File`, `Source_SHA256`, `Source_Sheet`, `Field`, `Extraction_Rule`, `Rows_Total`, `Rows_After_Exclusion`
  - only in `4b503b3dfb`: `EAN`, `Brand`, `Article Description`, `Type`, `First Sale`, `Chains New To`, `Primary NSV to Aug-26 (Rs L)`, `Offtake FY27 YTD NSV (Rs L)`
  - only in `6027ba4a46`: `Store Code`, `Channel`, `Remarks`
  - only in `793fa1cb17`: `Month`, `Chain`, `Brand`, `Category`, `Gross Margin %`, `Trade Spend %`, `Visibility Spend`, `Scheme Spend`, `Other Spend`, `Contribution Margin %`
  - only in `8577bd4bc5`: `Chain`, `Brand`, `EAN`, `Article Description`, `Rank in Chain-Brand`, `FY27 YTD NSV (Rs L)`, `Avg Monthly NSV (Rs L)`, `Share %`, `Cum Share %`, `Chain-Brand FY27 YTD NSV (Rs L)`
  - only in `8784758dec`: `Alias Store Key`, `Alias Match Key`, `Alias Site Code`, `Store Key`, `Store Match Key`, `Reason`
  - only in `8cbeafdeea`: `EAN`, `Brand`, `Category`, `SubCategory`, `Range`, `PackSize`, `EAN_Lifecycle`, `Biz_Lifecycle`
  - only in `90d08ac177`: `Chain`, `Channel`, `Remarks`
  - only in `990e530053`: `Period`, `FY`, `Quarter`, `Chain`, `Source Chain`, `Expense Head`, `Expense Type`, `Expense Amount (INR Lakh)`, `Remarks`, `Source`
  - only in `9fbb11e0c8`: `Month`, `FY`, `Quarter`, `Chain`, `Expense Head`, `Expense Type`, `Expense Amount (INR Lakh)`, `Status`, `Q1 Claim (INR Lakh)`, `Driver Share`
  - only in `9ffb465dd5`: `Chain`, `Account`, `Chain Type`, `Primary Zone`, `Channel`, `Active`
  - only in `a01eaefa33`: `Region`, `City`, `Beats Planned (rule)`, `Aliases`, `Near Listed (not on list)`
  - only in `a9ac52368d`: `Category`, `Sub-category`, `Nielsen Category`, `Category Sort Order`
  - only in `ab0f367da0`: `Severity`, `Check`, `Count`, `Examples`
  - only in `ac6334895f`: `Zone`, `Zone Sort Order`, `State`, `Region`
  - only in `b2fc5d465c`: `State`, `Market FW Cr`, `Market SH Cr`, `ME Share FW %`, `ME Share SH %`, `Dmart FW %`, `Dmart SH %`, `Reliance FW %`, `Reliance SH %`, `Apollo FW %`
  - only in `b4923765ed`: `Store Key`, `Chain Name`, `Chain (as in source)`, `Site Code`, `Store Name`, `Zone`, `State`, `State (as in source)`, `State Note`, `City (store list)`
  - only in `b5e89a9bb5`: `Month`, `FY`, `Chain`, `Customer Code`, `Customer Name`, `Zone`, `State`, `Brand`, `Category`, `Sub Category`
  - only in `c507599dea`: `Chain Name`, `Site Code`, `City`, `Basis`
  - only in `c5f9ee47ca`: `Ship To Name`, `Direct/Distributor`, `Primary Chain`, `Zone`, `State`, `Chains Served`
  - only in `d1601b6772`: `Ship To Name`, `Channel`, `Source`
  - only in `d40d0bef37`: `Category`, `HSN_Code`, `Pre_GST_Rate_Pct`, `Post_GST_Rate_Pct`, `Effective_From`, `Confidence`, `Finance_Approved`, `Impact_on_TOT_pct`, `Note`
  - only in `e1525ba683`: `GST_Cutover_Date`, `Note`
  - only in `fc04845269`: `Store Code`, `Store Name`, `Chain`, `Account`, `Zone`, `State`, `City`

### `PowerBI/SeedData/Offtake_Monthly`
- layout `0fc3f07cd5` (9 columns): `offtake_monthly.csv`
- layout `1b3d67554e` (6 columns): `offtake_store_article_dms_sep2026.csv`
  - only in `0fc3f07cd5`: `Year-Month`, `Chain/Account`, `Distributor`, `EAN`, `Brand`, `Category`, `Sub_Category`, `NSV`
  - only in `1b3d67554e`: `Article`, `Article Name`, `Month`, `Chain Name`, `NSV_Lakhs`

### `PowerBI/SeedData/Store_Cuts`
- layout `3a384d7627` (11 columns): `store_type_aug26.csv`
- layout `4c7158a055` (9 columns): `sales_cuts_fy27.csv`
- layout `5971fce502` (6 columns): `pack_size_monthly_fy27.csv`
- layout `7adea61b6f` (10 columns): `inhouse_distribution_fy27.csv`
  - only in `3a384d7627`: `Store Key`, `Chain`, `State`, `Zone`, `Store Type`, `NFL Kind`, `NSV This Year Rs`, `NSV Last Year Same Months Rs`, `LY Months Sold`, `Growth Basis`
  - only in `4c7158a055`: `Month`, `FY Year`, `Zone`, `Brand`, `Category`, `Sub Category`, `Store Type`, `NSV Rs`, `Stores Selling`
  - only in `5971fce502`: `Month`, `FY Year`, `Category`, `Pack`, `NSV Rs`, `Stores Selling`
  - only in `7adea61b6f`: `Month`, `FY Year`, `Level`, `Name`, `Stores Selling`, `SKUs Selling`, `SKU Listings`, `Stores In Master`, `NSV Rs`, `Basis`

## Files the queries and dashboards use

| File | In Git | Restricted class | Used by |
|---|---|---|---|
| `PowerBI/PowerQuery/42_PackSizeBuckets.pq` | yes | - | Registry: article_category_mapping |
| `PowerBI/RawDataFolders/ClaimMaster_Quarterly/claim_master_brand_AprJun_2026.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Claim Master |
| `PowerBI/RawDataFolders/ClaimMaster_Quarterly/claim_master_chain_AprJun_2026.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Claim Master |
| `PowerBI/RawDataFolders/ClaimMaster_Quarterly/claim_master_distributor_AprJun_2026.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Claim Master |
| `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Apr_26.csv` | yes | EMPLOYEE_RAW | Power Query: Fact Offtake Sales |
| `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Aug_26.csv` | yes | EMPLOYEE_RAW | Power Query: Fact Offtake Sales |
| `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Jul_26.csv` | yes | EMPLOYEE_RAW | Power Query: Fact Offtake Sales |
| `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Jun_26.csv` | yes | EMPLOYEE_RAW | Power Query: Fact Offtake Sales |
| `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_May_26.csv` | yes | EMPLOYEE_RAW | Power Query: Fact Offtake Sales |
| `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Sep_26.csv` | no | EMPLOYEE_RAW | Power Query: Fact Offtake Sales |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Apr_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Apr_26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Aug_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Aug_26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Dec_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Feb_26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jan_26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jul_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jul_26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jun_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jun_26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Mar_26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_May_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_May_26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Nov_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Oct_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Sep_25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Sep_26.csv` | no | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary Article |
| `PowerBI/RawDataFolders/Primary_Aug26_FY27.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Registry: primary_aug26_adhoc |
| `PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY24-25.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary ShipTo |
| `PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY24-26_Composite.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Primary ShipTo |
| `PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Dist Cont Weights; Power Query: Fact Primary ShipTo |
| `PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Dim Promo Calendar |
| `PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_brand_Jul_Aug_FY27.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Secondary Sales; Power Query: Fact Secondary TOT Hierarchy |
| `PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_brand_Q1_FY27.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Secondary Sales; Power Query: Fact Secondary TOT Hierarchy |
| `PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_chain_Jul_Aug_FY27.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Secondary Sales; Power Query: Fact Secondary TOT Hierarchy |
| `PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_chain_Q1_FY27.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Secondary Sales; Power Query: Fact Secondary TOT Hierarchy |
| `PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_distributor_Jul_Aug_FY27.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Secondary Sales; Power Query: Fact Secondary TOT Hierarchy |
| `PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_distributor_Q1_FY27.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Secondary Sales; Power Query: Fact Secondary TOT Hierarchy |
| `PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_tot_hierarchy_Apr_Aug_2026.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Secondary Sales; Power Query: Fact Secondary TOT Hierarchy |
| `PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_tot_hierarchy_Apr_Jul_2026.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Power Query: Fact Secondary Sales; Power Query: Fact Secondary TOT Hierarchy |
| `PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/05_ARTICLE_REGISTER_Jul_Aug_2026.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Registry: distributor_secondary_register_fy27 |
| `PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv` | yes | - | Registry: cm2_cogs |
| `PowerBI/Reference/CM2_Provisional/recovered_governance_20260724/cm2_expense_taxonomy_v0.2-DRAFT.csv` | yes | - | Registry: cm2_ba_supervisor_visibility_rental |
| `PowerBI/SeedData/Account/Account_Assortment.csv` | yes | - | Power Query: Fact Account Assortment |
| `PowerBI/SeedData/Account/Account_Category_Geo.csv` | yes | - | Power Query: Fact Account Category Geo |
| `PowerBI/SeedData/Account/Account_Category_Monthly.csv` | yes | - | Power Query: Fact Account Category |
| `PowerBI/SeedData/Distribution/UniverseMT.csv` | yes | - | Registry: mt_universe_store_master |
| `PowerBI/SeedData/Forecast/PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv` | yes | - | Registry: po_fill_rate_monthly |
| `PowerBI/SeedData/Mapping/ClaimDriver_Alias_Decisions_Q1_FY27.csv` | yes | - | Registry: distributor_claim_q1_fy27 |
| `PowerBI/SeedData/Mapping/CustomerCode_Zone_State_Mapping.csv` | yes | - | Power Query: Customer Code Zone Master |
| `PowerBI/SeedData/Mapping/DistCont_Patch_Approved_2026-07-04.csv` | yes | - | Power Query: Dist Cont Weights |
| `PowerBI/SeedData/Mapping/DistPrimary_Sheet1_FY24-25.csv` | yes | - | Registry: fy25_secondary_chain_brand_detail |
| `PowerBI/SeedData/Mapping/Store_SO_Mapping.csv` | yes | EMPLOYEE_RAW | Power Query: Store SO Mapping |
| `PowerBI/SeedData/Masters/ArticleMaster.csv` | yes | - | Power Query: Article Master |
| `PowerBI/SeedData/Masters/AssumptionTable.csv` | yes | - | Power Query: Assumption Table |
| `PowerBI/SeedData/Masters/BrandMaster.csv` | yes | - | Power Query: Brand Master |
| `PowerBI/SeedData/Masters/CategoryMaster.csv` | yes | - | Power Query: Category Master |
| `PowerBI/SeedData/Masters/ChainMaster.csv` | yes | - | Power Query: Chain Master |
| `PowerBI/SeedData/Masters/ChannelMap_Chain.csv` | yes | - | Power Query: Channel Map Chain |
| `PowerBI/SeedData/Masters/ChannelMap_Store.csv` | yes | - | Power Query: Channel Map Store |
| `PowerBI/SeedData/Masters/EAN_Product_Master.csv` | yes | - | Registry: ean_product_master |
| `PowerBI/SeedData/Masters/ForecastOverride.csv` | yes | - | Power Query: Forecast Override |
| `PowerBI/SeedData/Masters/GST_Config.csv` | yes | - | Power Query: GST Config |
| `PowerBI/SeedData/Masters/GST_Rate_QC_Table.csv` | yes | - | Power Query: GST Rate QC Table |
| `PowerBI/SeedData/Masters/NPI_List.csv` | yes | - | Registry: npi_list_fy27 |
| `PowerBI/SeedData/Masters/NielsenCompetitorMaster.csv` | yes | - | Power Query: Nielsen Competitor Master |
| `PowerBI/SeedData/Masters/Nielsen_Deck_StateExposure.csv` | yes | - | Power Query: Nielsen Deck State Exposure |
| `PowerBI/SeedData/Masters/PL_Distributor_Claim_Input_Q1_FY27.csv` | yes | - | Registry: distributor_claim_q1_fy27 |
| `PowerBI/SeedData/Masters/PL_Distributor_Claim_Monthly_Allocated_Q1_FY27.csv` | yes | - | Power Query: PL Expense Input |
| `PowerBI/SeedData/Masters/PL_Expense_Input.csv` | yes | - | Power Query: PL Expense Input |
| `PowerBI/SeedData/Masters/PrimaryAllocationOverride.csv` | yes | - | Power Query: Primary Allocation Override |
| `PowerBI/SeedData/Masters/Q3_FY27_Chain_Target_Primary.csv` | no | - | Registry: q3_fy27_chain_target_primary |
| `PowerBI/SeedData/Masters/ShipToChannelMap.csv` | yes | - | Power Query: Fact Primary ShipTo |
| `PowerBI/SeedData/Masters/ShipToMaster.csv` | yes | - | Power Query: Ship-To Master |
| `PowerBI/SeedData/Masters/StoreMaster.csv` | yes | - | Power Query: Store Master |
| `PowerBI/SeedData/Masters/Store_City_Master.csv` | yes | - | Power Query: Store City Master |
| `PowerBI/SeedData/Masters/Store_Key_Aliases.csv` | yes | - | Power Query: Store Key Alias |
| `PowerBI/SeedData/Masters/Store_Universe_Overrides.csv` | yes | - | Power Query: Store Universe Overrides |
| `PowerBI/SeedData/Masters/TDP_Focus_Articles.csv` | yes | - | Power Query: Fact TDP Focus Articles |
| `PowerBI/SeedData/Masters/Visit_City_List.csv` | yes | - | Power Query: Visit City List |
| `PowerBI/SeedData/Masters/ZoneStateMaster.csv` | yes | - | Power Query: Zone State Master |
| `PowerBI/SeedData/NPI_Master.csv` | yes | - | Registry: forecast_npd_master |
| `PowerBI/SeedData/Nielsen/Nielsen_Brand_Cut_Monthly/nielsen_brand_cut_urban_mt_aug26.csv` | yes | - | Power Query: Fact Nielsen Brand Cut |
| `PowerBI/SeedData/Nielsen/Nielsen_Monthly/nielsen_urban_mt_aug26.csv` | yes | - | Power Query: Fact Nielsen |
| `PowerBI/SeedData/Nielsen/Nielsen_Pack_Brand_Monthly/nielsen_pack_brand_urban_mt_aug26.csv` | yes | - | Power Query: Fact Nielsen Pack Brand |
| `PowerBI/SeedData/Nielsen/Nielsen_Pack_Monthly/nielsen_pack_urban_mt_aug26.csv` | yes | - | Power Query: Fact Nielsen Pack |
| `PowerBI/SeedData/Store_Cuts/inhouse_distribution_fy27.csv` | yes | - | Power Query: Fact Inhouse Distribution |
| `PowerBI/SeedData/Store_Cuts/pack_size_monthly_fy27.csv` | yes | - | Power Query: Fact Pack Size |
| `PowerBI/SeedData/Store_Cuts/sales_cuts_fy27.csv` | yes | - | Power Query: Fact Sales Cuts |
| `PowerBI/SeedData/Store_Cuts/store_type_aug26.csv` | yes | - | Power Query: Fact Store Type |
| `PowerBI/SeedData/Targets/FY2627_Targets.csv` | yes | - | Power Query: Targets |
| `PowerBI/templates/Template_Visibility_Tracker.csv` | yes | - | Registry: store_audit_template |
| `config/restricted_source_policy.yml` | yes | - | Registry: offtake_aug26_storewise_refresh |
| `dashboard/alert_controller.js` | yes | - | HTML dashboard: index.html |
| `dashboard/alerts_feed.json` | yes | - | HTML dashboard: index.html |
| `dashboard/chart.umd.js` | yes | - | HTML dashboard: index.html |
| `dashboard/compliance_metrics.json` | yes | - | HTML dashboard: index.html |
| `dashboard/data.js` | yes | - | HTML dashboard: index.html |
| `dashboard/enriched_metrics.json` | yes | - | HTML dashboard: index.html |
| `dashboard/html2canvas.min.js` | yes | - | HTML dashboard: index.html |
| `dashboard/inventory_engine.js` | yes | - | HTML dashboard: index.html |
| `dashboard/jspdf.umd.min.js` | yes | - | HTML dashboard: index.html |
| `dashboard/nielsen.js` | yes | - | HTML dashboard: index.html |
| `dashboard/sj_kpis.js` | yes | - | HTML dashboard: index.html |
| `dashboard/store_cuts.js` | yes | - | HTML dashboard: index.html |
| `dashboard/store_universe.js` | yes | - | HTML dashboard: index.html |
| `dashboard/tdp.js` | yes | - | HTML dashboard: index.html |
| `dashboard/tdp_focus.js` | yes | - | HTML dashboard: index.html |
| `dashboard/tdp_inhouse.js` | yes | - | HTML dashboard: index.html |
| `dashboard/xlsx.core.min.js` | yes | - | HTML dashboard: index.html |
| `data/monthly/Aug26_primary_detailed.csv` | yes | CUSTOMER_STORE_ARTICLE_RAW | Registry: primary_aug26_adhoc |
| `data/offtake_fy26/Store_Month_NSV_FY26.csv` | yes | - | Registry: offtake_fy26_store_article |
| `data/store_cuts_aug26.json` | yes | - | Registry: store_cuts_lfl_pack |
| `scripts/aug26_data_readiness_gate.py` | yes | - | Registry: chain_allocation_tool |
| `scripts/batch_load_promos.py` | yes | - | Registry: promotions_offtake_correlation |
| `scripts/build_account_share.py` | yes | - | Registry: retailer_category_share_monthly |
| `scripts/build_dashboard_data.py` | yes | - | Registry: chain_allocation_tool |
| `scripts/build_store_city_master.py` | yes | - | Registry: store_city_master |
| `scripts/build_store_cuts.py` | yes | - | Registry: store_cuts_lfl_pack |
| `scripts/build_tdp.py` | yes | - | Registry: tdp_monthly |
| `scripts/build_tdp_focus_articles.py` | yes | - | Registry: tdp_focus_articles |
| `scripts/build_tdp_inhouse.py` | yes | - | Registry: tdp_inhouse_from_offtake |
| `scripts/clean_offtake_fy26_store_article.py` | yes | - | Registry: offtake_fy26_store_article |
| `scripts/split_offtake_store_article_xlsb.py` | yes | - | Registry: offtake_aug26_storewise_refresh |

## Files in the data folders that no query, dashboard or registry entry names

- `PowerBI/RawDataFolders/Master_Data/Chain_Article_EAN_Mapping.csv`
- `PowerBI/RawDataFolders/Master_Data/Chain_Summary.csv`
- `PowerBI/RawDataFolders/Primary_Derived_FY25/Primary_Article_Synthesized_FY25.csv`
- `PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/00_SUMMARY_Statistics.csv`
- `PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/01_FULL_HIERARCHY_Apr_Jul_2026.csv`
- `PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/02_DISTRIBUTOR_CHAIN_TOT_Apr_Jul_2026.csv`
- `PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/03_CHAIN_BRAND_TOT_Apr_Jul_2026.csv`
- `PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/04_DISTRIBUTOR_CHAIN_MoM_TOT_Pivot.csv`
- `PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/06_REGISTER_EXCEPTIONS_Jul_Aug_2026.csv`
- `PowerBI/SeedData/Account/Account_Category_Map.csv`
- `PowerBI/SeedData/DIST/ChainAllocationWeights.csv`
- `PowerBI/SeedData/DIST/ChainAllocationWeights_provenance.json`
- `PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv`
- `PowerBI/SeedData/Forecast/PO_Fill_Rate_QC.json`
- `PowerBI/SeedData/Forecast/PO_Unfilled_Reasons_Monthly_Apr25_to_Aug26.csv`
- `PowerBI/SeedData/Forecast/PO_vs_Target_Monthly_FY27.csv`
- `PowerBI/SeedData/Mapping/ChainAccount_Mapping_Inferred.csv`
- `PowerBI/SeedData/Mapping/ChainAccount_Mapping_PriorityView.csv`
- `PowerBI/SeedData/Mapping/ChainWisePrimarySale_Dump_Snapshot.csv`
- `PowerBI/SeedData/Mapping/CustomerCode_Zone_State_Exceptions.csv`
- `PowerBI/SeedData/Mapping/DistAllocationGovernance_FlaggedRows.csv`
- `PowerBI/SeedData/Mapping/DistCont_Patch_Proposed.csv`
- `PowerBI/SeedData/Mapping/DistPrimary_FY24-25_CategorySplit_offtakemix.csv`
- `PowerBI/SeedData/Mapping/DistPrimary_FY24-25_CategorySplit_summary.csv`
- `PowerBI/SeedData/Mapping/EanAffinity_ResidualProposal.csv`
- `PowerBI/SeedData/Mapping/MT_Chain_Wise_NPI_Article_Aug26.csv`
- `PowerBI/SeedData/Mapping/Mapping_Corrections.csv`
- `PowerBI/SeedData/Mapping/Vidarbha_Central_Zone_Stores.csv`
- `PowerBI/SeedData/Masters/FY27_Monthly_GMV_MRP.csv`
- `PowerBI/SeedData/Masters/Store_City_Corrections.csv`
- `PowerBI/SeedData/Masters/Store_City_Master_QC.csv`
- `PowerBI/SeedData/Masters/TDP_New_Articles_Since_Jan26.csv`
- `PowerBI/SeedData/NPI_Performance_TestData.csv`
- `PowerBI/SeedData/Offtake_Monthly/offtake_monthly.csv`
- `PowerBI/SeedData/Offtake_Monthly/offtake_store_article_dms_sep2026.csv`
- `PowerBI/SeedData/Primary/Primary_FY202426_10.csv`
