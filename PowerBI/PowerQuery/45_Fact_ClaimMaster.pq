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
// Only claim_master_chain_*.csv is read. The same folder also holds the brand
// and distributor claim files; combining the whole folder would add their
// totals to this chain fact. Only the six components are unpivoted:
// Total_Claim_Lakh is their sum, and the chain CSV's extra Entity /
// Amount_Lakh columns repeat it, so unpivoting them would count every claim
// twice in SUM('Fact Claim Master'[Amount_Lakh]).
// (Defect fix 2026-09-27, sibling of the #261 fix to 44_Fact_SecondarySales:
// the query previously passed a column list as fnCombineFolder's HeaderRow
// number argument and used a "\PowerBI\RawDataFolders" path under
// pRootFolder, which already points at the PowerBI folder - see 00_Parameters.pq.)
//
// The brand file has a commented example query below; no distributor-claim
// query exists in this kit.
//
// Refresh: drop a new claim_master_chain_<period>.csv into ClaimMaster_Quarterly/ → Refresh.
// =====================================================================
let
    IdColumns = {"Period", "FY_Year", "Quarter", "Chain", "Source_Chain"},
    ExpenseComponents = {"Chain_Promo_Lakh", "Rate_Diff_Lakh", "Freight_Lakh",
                         "Incentive_Lakh", "Off_Invoice_Lakh", "Visibility_Lakh"},
    RequiredColumns = IdColumns & ExpenseComponents & {"Total_Claim_Lakh"},

    // ── Chain claim files only (name filter before parsing) ─────────
    Files = Folder.Files(pRootFolder & "\RawDataFolders\ClaimMaster_Quarterly"),
    ChainFiles = Table.SelectRows(Files, each
        Text.StartsWith(Text.Lower([Name]), "claim_master_chain_")
        and Text.Lower([Extension]) = ".csv"),

    Parsed = Table.AddColumn(ChainFiles, "Data", each
        let
            t = Table.PromoteHeaders(
                    Csv.Document([Content], [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
                    [PromoteAllScalars=true])
        in
            // drops Entity / Amount_Lakh; a renamed header fails the refresh
            Table.SelectColumns(t, RequiredColumns, MissingField.Error)),

    Source =
        if Table.RowCount(Parsed) = 0 then
            #table(RequiredColumns, {})
        else
            Table.Combine(Parsed[Data]),

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

    // ── Unpivot the six components only (never Total_Claim_Lakh) ──
    Unpivoted = Table.Unpivot(Typed, ExpenseComponents,
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
//     Files = Folder.Files(pRootFolder & "\RawDataFolders\ClaimMaster_Quarterly"),
//     BrandFiles = Table.SelectRows(Files, each
//         Text.StartsWith(Text.Lower([Name]), "claim_master_brand_")
//         and Text.Lower([Extension]) = ".csv"),
//     Source = Table.Combine(List.Transform(BrandFiles[Content], each
//         Table.SelectColumns(Table.PromoteHeaders(Csv.Document(_,
//             [Delimiter=",", Encoding=65001]), [PromoteAllScalars=true]),
//             {"Period","FY_Year","Quarter","Brand",
//              "Apr_Lakh","May_Lakh","Jun_Lakh","Total_Lakh"}, MissingField.Error))),
//     Typed = Table.TransformColumnTypes(Source,{
//         {"Period",type text},{"FY_Year",type text},{"Quarter",type text},
//         {"Brand",type text},{"Apr_Lakh",type number},
//         {"May_Lakh",type number},{"Jun_Lakh",type number},
//         {"Total_Lakh",type number}
//     }),
//     Unpivoted = Table.Unpivot(Typed,        // months only, never Total_Lakh
//         {"Apr_Lakh","May_Lakh","Jun_Lakh"},"Month_Key","Amount_Lakh"),
//     WithMonth = Table.AddColumn(Unpivoted,"Month_Label", each
//         if [Month_Key]="Apr_Lakh" then "Apr-2026"
//         else if [Month_Key]="May_Lakh" then "May-2026"
//         else if [Month_Key]="Jun_Lakh" then "Jun-2026"
//         else [Month_Key], type text),
//     Final = Table.SelectColumns(WithMonth,
//         {"Period","FY_Year","Quarter","Brand","Month_Label","Amount_Lakh"})
// in  Final
