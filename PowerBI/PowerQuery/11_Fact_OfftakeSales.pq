// =====================================================================
// QUERY: Fact Offtake Sales   (grain = Month x Store x Article)
// Source = every file in RawDataFolders\Offtake_Monthly
// Offtake is maintained on a MONTHLY basis.
// =====================================================================
let
    // Offtake workbooks include a blank first row, so the actual headers begin on row 1.
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Offtake_Monthly", 1),

    Typed = Table.TransformColumnTypes(Source, {
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
        {"Offtake NSV", type number},
        {"Offtake Qty", type number},
        {"MRP Sales", type number},
        {"Data Source Name", type text}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Store Code", each Text.Trim(Text.From(_)), type text},
        {"Article Code", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text}
    }),

    Cleaned = Table.SelectRows(Trimmed, each [Offtake NSV] <> null or [Offtake Qty] <> null),

    // Convert "May'26" -> month start date for the relationship to the Date table.
    // Expects the form  MMM'yy  (Apr'26).  Adjust here if your label differs.
    AddMonthStart = Table.AddColumn(Cleaned, "MonthStart", each
        let
            m = Text.BetweenDelimiters([Month], "", "'"),
            yy = Text.AfterDelimiter([Month], "'"),
            monthNum = Record.FieldOrDefault(
                [Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
        in
            if monthNum = null then null
            else #date(2000 + Number.FromText(yy), monthNum, 1),
        type date)
in
    AddMonthStart
