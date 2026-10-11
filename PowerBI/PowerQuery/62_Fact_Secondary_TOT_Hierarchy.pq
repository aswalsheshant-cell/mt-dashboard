// =====================================================================
// QUERY: Fact Secondary TOT Hierarchy   (article-grain distributor sell-out with TOT %)
// Grain: Source_Month x Distributor x Chain x Brand x EAN
//
// Source: PowerBI/RawDataFolders/SecondarySales_Monthly/
//         Files: secondary_sales_tot_hierarchy_*.csv ONLY
//                (today: secondary_sales_tot_hierarchy_Apr_Aug_2026.csv = Apr-Aug'26)
//
// Why the name filter: 44_Fact_SecondarySales.pq reads the distributor register
// files from the same folder, and these files repeat the same sales at article
// grain. Keeping them in their own table stops the same sales being counted twice.
// Promo measures (DAX/15_Promo_Measures.dax) read this table.
//
// Amounts: NSV_Value is rupees, NSV_Lakh is the same value in lakh.
// EAN arrives with a leading apostrophe (Excel text marker); it is removed.
//
// Refresh: a new period file named secondary_sales_tot_hierarchy_<period>.csv is
// picked up on Refresh. Do not leave two files that cover the same months.
// =====================================================================
let
    RequiredColumns = {"Source_Month", "Month_Label", "Distributor", "Dist_Monthly_Total",
                       "Chain", "Chain_Monthly_Total", "Chain_TOT_Pct", "Brand",
                       "Brand_Monthly_Total", "Brand_TOT_Pct", "EAN", "Article",
                       "NSV_Value", "NSV_Lakh"},

    Files = Folder.Files(pRootFolder & "\RawDataFolders\SecondarySales_Monthly"),
    TotFiles = Table.SelectRows(Files, each
        Text.StartsWith(Text.Lower([Name]), "secondary_sales_tot_hierarchy_")
        and Text.Lower([Extension]) = ".csv"),

    Parsed = Table.AddColumn(TotFiles, "Data", each
        let
            t = Table.PromoteHeaders(
                    Csv.Document([Content], [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
                    [PromoteAllScalars=true]),
            // a renamed or missing header fails the refresh instead of loading blanks
            cols = Table.SelectColumns(t, RequiredColumns, MissingField.Error)
        in
            Table.AddColumn(cols, "Data Source File", (r) => [Name], type text)),

    Source =
        if Table.RowCount(Parsed) = 0 then
            #table(RequiredColumns & {"Data Source File"}, {})
        else
            Table.Combine(Parsed[Data]),

    Typed = Table.TransformColumnTypes(Source, {
        {"Source_Month", type text}, {"Month_Label", type text},
        {"Distributor", type text}, {"Chain", type text}, {"Brand", type text},
        {"EAN", type text}, {"Article", type text},
        {"Dist_Monthly_Total", type number}, {"Chain_Monthly_Total", type number},
        {"Chain_TOT_Pct", type number}, {"Brand_Monthly_Total", type number},
        {"Brand_TOT_Pct", type number}, {"NSV_Value", type number}, {"NSV_Lakh", type number}
    }),

    CleanEAN = Table.TransformColumns(Typed, {{"EAN", each
        if _ = null then null else Text.Trim(Text.TrimStart(_, "'")), type text}}),

    AddMonthStart = Table.AddColumn(CleanEAN, "MonthStart", each
        try Date.FromText([Source_Month] & "-01") otherwise null, type date)
in
    AddMonthStart
