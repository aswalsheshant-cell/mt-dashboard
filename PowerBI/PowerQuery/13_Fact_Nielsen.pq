// =====================================================================
// QUERY: Fact Nielsen Market Share  (grain = Month x Nielsen Category x Brand x Zone)
// Source = RawDataFolders\Nielsen_Monthly
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Nielsen_Monthly"),
    Typed = Table.TransformColumnTypes(Source, {
        {"Month", type text},
        {"FY Year", type text},
        {"Nielsen Category", type text},
        {"Brand", type text},
        {"Zone", type text},
        {"Market Value Sales", type number},
        {"Our Brand Sales", type number},
        {"Value Market Share %", type number},
        {"Volume Market Share %", type number},
        {"Data Source Name", type text}
    }),
    AddMonthStart = Table.AddColumn(Typed, "MonthStart", each
        let
            m = Text.BetweenDelimiters([Month], "", "'"),
            yy = Text.AfterDelimiter([Month], "'"),
            monthNum = Record.FieldOrDefault(
                [Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
        in if monthNum = null then null else #date(2000 + Number.FromText(yy), monthNum, 1),
        type date),

    // FY Year is DERIVED from the month (MonthStart) with fnFYLabel -- never copied from
    // the source file -- so it always matches 'Date Table'[FY Year]. Falls back to
    // the source text only when the month itself is missing.
    FYNew = Table.AddColumn(AddMonthStart, "FY Year New",
        each if [MonthStart] = null then [FY Year] else fnFYLabel([MonthStart]), type text),
    FYDropOld = Table.RemoveColumns(FYNew, {"FY Year"}),
    FYDerived = Table.RenameColumns(FYDropOld, {{"FY Year New", "FY Year"}})
in
    FYDerived
