// =====================================================================
// QUERY: Fact Nielsen Market Share  (grain = Month x Nielsen Category x Brand x Zone)
// Source = RawDataFolders\Nielsen_Monthly
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Nielsen_Monthly", null, {"Month", "FY Year", "Nielsen Category", "Brand", "Zone", "Market Value Sales", "Our Brand Sales", "Value Market Share %", "Volume Market Share %", "Data Source Name", "Volume 000 L", "Price Per Ml"}),
    // Volume 000 L and Price Per Ml are optional (older drops lack them); add them as null when missing
    WithOptional = List.Accumulate({"Volume 000 L", "Price Per Ml"}, Source,
        (tbl, col) => if Table.HasColumns(tbl, col) then tbl else Table.AddColumn(tbl, col, each null, type number)),
    Typed = Table.TransformColumnTypes(WithOptional, {
        {"Month", type text},
        {"FY Year", type text},
        {"Nielsen Category", type text},
        {"Brand", type text},
        {"Zone", type text},
        {"Market Value Sales", type number},
        {"Our Brand Sales", type number},
        {"Value Market Share %", type number},
        {"Volume Market Share %", type number},
        {"Data Source Name", type text},
        {"Volume 000 L", type number},
        {"Price Per Ml", type number}
    }),
    AddMonthStart = Table.AddColumn(Typed, "MonthStart", each
        let
            m = Text.BetweenDelimiters([Month], "", "'"),
            yy = Text.AfterDelimiter([Month], "'"),
            monthNum = Record.FieldOrDefault(
                [Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
        in if monthNum = null then null else #date(2000 + Number.FromText(yy), monthNum, 1),
        type date)
in
    AddMonthStart
