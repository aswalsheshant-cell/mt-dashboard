// =====================================================================
// QUERY: Fact Nielsen Brand Cut  (grain = Month x Nielsen Category x Brand; one "(Category)" row per month and category)
// Source = RawDataFolders\Nielsen_Brand_Cut_Monthly (copy the file from SeedData\Nielsen\Nielsen_Brand_Cut_Monthly)
// The brand cuts of the Nielsen Cuts tab: value, value and volume share, price per ml, weighted (WD) and numeric (ND) distribution, stores,
// sales per store and share among stores that stock the brand (SAH). WD, ND and SAH are percentage points (89.5 = 89.5%); shares are decimals
// (0.128 = 12.8%), as in Fact Nielsen. The "(Category)" row carries the category value and price per ml: Is Category Row = "Yes".
// Relate Date Table[MonthStart] -> [MonthStart]; Brand -> Nielsen Competitor Master[Brand] (not for the "(Category)" row).
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Nielsen_Brand_Cut_Monthly"),
    Typed = Table.TransformColumnTypes(Source, {
        {"Month", type text}, {"FY Year", type text}, {"Nielsen Category", type text}, {"Brand", type text}, {"Is Category Row", type text}, {"Zone", type text},
        {"Value Cr", type number}, {"Value Share %", type number}, {"Volume Share %", type number}, {"Price Per Ml", type number},
        {"WD %", type number}, {"ND %", type number}, {"Stores", type number}, {"Sales Per Store Rs", type number}, {"SAH %", type number}, {"Data Source Name", type text}
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
