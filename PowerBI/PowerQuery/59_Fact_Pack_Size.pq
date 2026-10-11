// =====================================================================
// QUERY: Fact Pack Size  (grain = Month x Category x Pack size)
// Source = SeedData\Store_Cuts\pack_size_monthly_fy27.csv (store-level data stays in SeedData, not RawDataFolders, per the restricted-source rule; rebuild each month with scripts/build_store_cuts.py)
// Pack = net weight in g / ml as in the offtake file ("Not stated" when blank). Last year's store file carries no pack, so pack YoY is not possible: use MoM.
// NSV is in rupees. "Stores Selling" is per row: do not add it up across packs or months. Relate MonthStart -> Date Table[MonthStart].
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Store_Cuts\pack_size_monthly_fy27.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Month", type text}, {"FY Year", type text}, {"Category", type text}, {"Pack", type text}, {"NSV Rs", type number}, {"Stores Selling", type number}
    }),
    AddMonthStart = Table.AddColumn(Typed, "MonthStart", each
        let
            m = Text.BetweenDelimiters([Month], "", "'"),
            yy = Text.AfterDelimiter([Month], "'"),
            monthNum = Record.FieldOrDefault(
                [Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
        in if monthNum = null then null else #date(2000 + Number.FromText(yy), monthNum, 1),
        type date),
    AddPackSort = Table.AddColumn(AddMonthStart, "Pack Sort", each try Number.FromText([Pack]) otherwise 99999, type number)
in
    AddPackSort
