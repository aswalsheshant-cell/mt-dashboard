// =====================================================================
// QUERY: Fact Nielsen Pack Brand  (grain = Month x Nielsen Category x Pack Size x Brand)
// Source = RawDataFolders\Nielsen_Pack_Brand_Monthly (copy the file from SeedData\Nielsen\Nielsen_Pack_Brand_Monthly)
// Which brands sell which pack size: Nielsen Brand x Basepack, all brands in the sheet. Value in Rs Crore, volume in litres.
// Relate Date Table[MonthStart] -> [MonthStart]; Brand -> Nielsen Competitor Master[Brand].
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Nielsen_Pack_Brand_Monthly"),
    Typed = Table.TransformColumnTypes(Source, {
        {"Month", type text}, {"FY Year", type text}, {"Nielsen Category", type text}, {"Pack Size ml", type number},
        {"Brand", type text}, {"Value Cr", type number}, {"Volume L", type number}, {"WD %", type number}, {"Data Source Name", type text}
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
