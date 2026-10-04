// =====================================================================
// QUERY: Fact Nielsen Pack  (grain = Month x Nielsen Category x Pack Size)
// Source = RawDataFolders\Nielsen_Pack_Monthly
// Written by scripts/build_nielsen_powerbi_seed.py from the Nielsen pack sheets
// (Category x Basepack and Brand x Basepack, Mamaearth only).
//   Basis      : "Value Cr" for Facewash, "Volume L" for Shampoo (the shampoo pack
//                sheets carry volume, WD and out-of-stock but no value)
//   Category Amount / Our Amount : in that basis; Category WD % : weighted distribution of the pack
// Relate Date Table[MonthStart] -> [MonthStart]; Nielsen Category -> Category Master[Nielsen Category].
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Nielsen_Pack_Monthly"),
    Typed = Table.TransformColumnTypes(Source, {
        {"Month", type text},
        {"FY Year", type text},
        {"Nielsen Category", type text},
        {"Pack Size ml", type number},
        {"Basis", type text},
        {"Category Amount", type number},
        {"Our Amount", type number},
        {"Category WD %", type number},
        {"Data Source Name", type text}
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
