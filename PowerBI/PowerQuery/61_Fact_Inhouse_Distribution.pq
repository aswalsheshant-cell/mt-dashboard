// =====================================================================
// QUERY: Fact Inhouse Distribution  (grain = Month x Level x Name; Level = Total / Chain / State / Pack)
// Source = SeedData\Store_Cuts\inhouse_distribution_fy27.csv (store-level data stays in SeedData, not RawDataFolders, per the restricted-source rule; rebuild with scripts/build_tdp_inhouse.py)
// FROM OUR OFFTAKE, NOT TDP: no ACV % and no weighted distribution. Stores Selling = stores with offtake in the month; SKU Listings = distinct store x SKU pairs
// (in-house distribution points); SKUs per store = listings / stores. "Stores In Master" is blank for Pack and where the state name does not match the master.
// Filter the Level column on every visual (Total, Chain, State or Pack), because the rows of different levels must not be added together.
// NSV is in rupees. Relate MonthStart -> Date Table[MonthStart]. Replace with 'Fact TDP' (query 14) when the real TDP file arrives.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Store_Cuts\inhouse_distribution_fy27.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Month", type text}, {"FY Year", type text}, {"Level", type text}, {"Name", type text}, {"Stores Selling", type number}, {"SKUs Selling", type number},
        {"SKU Listings", type number}, {"Stores In Master", type number}, {"NSV Rs", type number}, {"Basis", type text}
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
