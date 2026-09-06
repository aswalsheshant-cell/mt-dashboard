// =====================================================================
// QUERY: Fact Claim Master  (Chain-level Q1 FY27 expense)
// Grain: Quarter × Chain × Expense Category
//
// Source: PowerBI/RawDataFolders/ClaimMaster_Quarterly/
//         Files: claim_master_chain_AprJun_2026.csv  (and future quarters)
//
// Required columns:
//   Period           — e.g. "Apr-Jun 2026"
//   FY_Year          — FY27
//   Quarter          — Q1
//   Chain            — canonical chain name
//   Chain_Promo_Lakh — on-invoice promo passed to chain
//   Rate_Diff_Lakh   — extra margin / rate difference
//   Freight_Lakh     — freight / transportation
//   Incentive_Lakh   — incentive
//   Off_Invoice_Lakh — off-invoice / debit note promo
//   Visibility_Lakh  — visibility spend
//   Total_Claim_Lakh — sum of all above
//
// Companion queries (same folder, same refresh cycle):
//   claim_master_brand_AprJun_2026.csv    → loaded in 45b_ClaimBrand
//   claim_master_distributor_AprJun_2026.csv → loaded in 45c_ClaimDistributor
//
// Refresh: drop a new quarterly CSV into ClaimMaster_Quarterly/ → Refresh.
// =====================================================================
let
    Source = fnCombineFolder(
        pRootFolder & "\PowerBI\RawDataFolders\ClaimMaster_Quarterly",
        {"Period", "FY_Year", "Quarter", "Chain", "Source_Chain",
         "Chain_Promo_Lakh", "Rate_Diff_Lakh", "Freight_Lakh",
         "Incentive_Lakh", "Off_Invoice_Lakh", "Visibility_Lakh",
         "Total_Claim_Lakh"}
    ),

    // Filter to chain-level file pattern
    ChainOnly = Table.SelectRows(Source, each
        Table.RowCount(Table.SelectRows(Source, each [Chain] <> null)) > 0),

    Typed = Table.TransformColumnTypes(Source, {
        {"Period",            type text},
        {"FY_Year",           type text},
        {"Quarter",           type text},
        {"Chain",             type text},
        {"Source_Chain",      type text},
        {"Chain_Promo_Lakh",  type number},
        {"Rate_Diff_Lakh",    type number},
        {"Freight_Lakh",      type number},
        {"Incentive_Lakh",    type number},
        {"Off_Invoice_Lakh",  type number},
        {"Visibility_Lakh",   type number},
        {"Total_Claim_Lakh",  type number}
    }),

    // ── Unpivot to long form: Chain × Expense_Category × Amount ────
    Unpivoted = Table.UnpivotOtherColumns(Typed,
        {"Period", "FY_Year", "Quarter", "Chain", "Source_Chain"},
        "Expense_Category_Raw", "Amount_Lakh"),

    // ── Clean category names (strip "_Lakh" suffix) ─────────────────
    WithCatClean = Table.AddColumn(Unpivoted, "Expense_Category", each
        let raw = [Expense_Category_Raw]
        in  if raw = "Chain_Promo_Lakh"  then "Chain Promo (On Invoice)"
            else if raw = "Rate_Diff_Lakh"   then "Extra Margin / Rate Difference"
            else if raw = "Freight_Lakh"     then "Freight / Transportation"
            else if raw = "Incentive_Lakh"   then "Incentive"
            else if raw = "Off_Invoice_Lakh" then "Off Invoice / Debit Note Promo"
            else if raw = "Visibility_Lakh"  then "Visibility"
            else raw,
        type text),

    // ── Exclude zero rows (cleaner model) ──────────────────────────
    NonZero = Table.SelectRows(WithCatClean, each [Amount_Lakh] <> 0),

    Final = Table.SelectColumns(NonZero, {
        "Period", "FY_Year", "Quarter",
        "Chain", "Source_Chain",
        "Expense_Category", "Amount_Lakh"
    })
in
    Final


// ─────────────────────────────────────────────────────────────────────
// COMPANION QUERY — paste as a SEPARATE Blank Query named:
//   45b_ClaimBrand
// ─────────────────────────────────────────────────────────────────────
// let
//     Source = fnCombineFolder(
//         pRootFolder & "\PowerBI\RawDataFolders\ClaimMaster_Quarterly",
//         {"Period","FY_Year","Quarter","Brand",
//          "Apr_Lakh","May_Lakh","Jun_Lakh","Total_Lakh"}
//     ),
//     Typed = Table.TransformColumnTypes(Source,{
//         {"Period",type text},{"FY_Year",type text},{"Quarter",type text},
//         {"Brand",type text},{"Apr_Lakh",type number},
//         {"May_Lakh",type number},{"Jun_Lakh",type number},
//         {"Total_Lakh",type number}
//     }),
//     Unpivoted = Table.UnpivotOtherColumns(Typed,
//         {"Period","FY_Year","Quarter","Brand"},"Month_Key","Amount_Lakh"),
//     WithMonth = Table.AddColumn(Unpivoted,"Month_Label", each
//         if [Month_Key]="Apr_Lakh" then "Apr-2026"
//         else if [Month_Key]="May_Lakh" then "May-2026"
//         else if [Month_Key]="Jun_Lakh" then "Jun-2026"
//         else [Month_Key], type text),
//     Final = Table.SelectColumns(WithMonth,
//         {"Period","FY_Year","Quarter","Brand","Month_Label","Amount_Lakh"})
// in  Final
