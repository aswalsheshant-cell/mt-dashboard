// =====================================================================
// QUERY: Fact Account Category Geo  (grain = Chain x Month x Zone x State x City x Category; city is the store city for Lulu, the DC city for More Retail, the store city for Reliance Brand Counter)
// Source = SeedData\Account\Account_Category_Geo.csv, built by scripts/build_account_share.py from the retailer-side files
// (Lulu compiled monthly files, More MS, Reliance BA store file; Wellness Forever has no zone or state). Value is Rs lakh without GST (Reliance: gross sales as supplied). Share % = our sales / the chain's own category sales.
// Scope: Lulu and More Retail cover the categories and stores where Honasa sells; More Retail months before Jun 26 cover fewer categories
// (see the Scope column), so compare More Retail only within Jun-Aug 26. Relate Date Table[MonthStart] -> [MonthStart]; Chain -> Chain Master[Chain].
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Account\Account_Category_Geo.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Chain", type text},
        {"Month", type text},
        {"Zone", type text},
        {"State", type text},
        {"City", type text},
        {"Category", type text},
        {"Account Sales Rs L", type number},
        {"Honasa Sales Rs L", type number},
        {"Stores", type number},
        {"Common Category", type text},
        {"Share %", type number},
        {"Source", type text},
        {"Relevant For Us", type text}
    }),
    AddMonthStart = Table.AddColumn(Typed, "MonthStart", each
        let
            m = Text.Start([Month], 3),
            yy = Text.End([Month], 2),
            monthNum = Record.FieldOrDefault(
                [Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
        in if monthNum = null then null else #date(2000 + Number.FromText(yy), monthNum, 1),
        type date)
in
    AddMonthStart
