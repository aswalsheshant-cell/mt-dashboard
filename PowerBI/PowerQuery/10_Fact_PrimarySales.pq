// =====================================================================
// QUERY: Fact Primary Sales   (grain = Week x Store x Article)
// Source = every file in RawDataFolders\Primary_Weekly
// Primary is maintained WEEKLY (date/week-wise) so MoM is built by rolling
// the weekly rows up to Month via the Date table.
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Primary_Weekly"),

    // enforce types on the standard columns
    Typed = Table.TransformColumnTypes(Source, {
        {"Week Start Date", type date},
        {"Month", type text},
        {"FY Year", type text},
        {"Quarter", type text},
        {"Chain", type text},
        {"Account", type text},
        {"Zone", type text},
        {"State", type text},
        {"City", type text},
        {"Store Code", type text},
        {"Store Name", type text},
        {"Brand", type text},
        {"Category", type text},
        {"Sub-category", type text},
        {"Range", type text},
        {"Pack Size", type text},
        {"Article Code", type text},
        {"Article Description", type text},
        {"EAN Code", type text},
        {"Primary NSV", type number},
        {"Primary Qty", type number},
        {"MRP Sales", type number},
        {"Data Source Name", type text}
    }),

    // trim text keys so joins to masters are clean
    Trimmed = Table.TransformColumns(Typed, {
        {"Store Code", each Text.Trim(Text.From(_)), type text},
        {"Article Code", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text}
    }),

    // remove fully blank rows (no NSV and no Qty)
    Cleaned = Table.SelectRows(Trimmed, each [Primary NSV] <> null or [Primary Qty] <> null),

    // MonthStart = first day of the month, used to relate to the Date table at month grain
    AddMonthStart = Table.AddColumn(Cleaned, "MonthStart",
        each Date.StartOfMonth([Week Start Date]), type date)
in
    AddMonthStart
