// =====================================================================
// QUERY: Fact Sales Cuts  (grain = Month x Zone x Brand x Sub Category x Store Type)
// Source = SeedData\Store_Cuts\sales_cuts_fy27.csv (store-level data stays in SeedData, not RawDataFolders, per the restricted-source rule; rebuild each month with scripts/build_store_cuts.py)
// FY27 offtake NSV (Brand Counter left out) split by store type: LFL, NFL New, NFL Restarted, No LY store data. Last year has no brand or sub-category
// in the store file, so there is no brand / sub-category YoY here; zone growth comes from the main offtake fact. NSV is in rupees.
// "Stores Selling" is per row: do not add it up across rows. Relate MonthStart -> Date Table[MonthStart].
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Store_Cuts\sales_cuts_fy27.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Month", type text}, {"FY Year", type text}, {"Zone", type text}, {"Brand", type text}, {"Category", type text}, {"Sub Category", type text},
        {"Store Type", type text}, {"NSV Rs", type number}, {"Stores Selling", type number}
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
