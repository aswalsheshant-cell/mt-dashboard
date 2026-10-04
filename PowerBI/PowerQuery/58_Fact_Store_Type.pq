// =====================================================================
// QUERY: Fact Store Type  (grain = one row per store: LFL / NFL / No LY store data / Lost)
// Source = RawDataFolders\Store_Cuts (copy store_type_aug26.csv from SeedData\Store_Cuts; rebuild it each month with scripts/build_store_cuts.py)
// LFL = sold this year and in the same months last year. NFL = no sales last year in those months. Lost = sold last year, nothing this year (State and Zone are "Not available").
// NFL Kind: New = no sales anywhere last year; Restarted = sold last year in another month (Sep-Mar) so not a new store; "Not NFL" for the other types.
// LY Months Sold = months (of Apr-Aug last year) the store had sales; Growth Basis = "Enough history" when 3 or more. Store-level growth is shown only for those stores.
// "No LY store data" = Reliance Retail non-counter: last year came state-level only, so it is kept out of LFL. Brand Counter stores are not in this table (offtake rule).
// NSV is in rupees. Relate Chain -> the chain dimension if you want chain slicers to cut it; State and Zone are text columns for direct use.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\RawDataFolders\Store_Cuts\store_type_aug26.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Store Key", type text}, {"Chain", type text}, {"State", type text}, {"Zone", type text}, {"Store Type", type text}, {"NFL Kind", type text}, {"LY Months Sold", Int64.Type}, {"Growth Basis", type text},
        {"NSV This Year Rs", type number}, {"NSV Last Year Same Months Rs", type number}, {"Period", type text}
    })
in
    Typed
