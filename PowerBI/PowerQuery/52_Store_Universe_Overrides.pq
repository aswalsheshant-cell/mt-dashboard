// =====================================================================
// QUERY: Store Universe Overrides  (chains whose offtake has no usable store codes)
// Source = SeedData\Masters\Store_Universe_Overrides.csv (also feeds dashboard/store_universe.js)
//   TENTATIVE = working estimate that is counted in the store universe (Reliance Retail ~1,000, More Retail ~400)
//   NA        = not applicable, not counted (Nykaa / FSN is online)
// [Offtake Chain] is the chain spelling in Fact Offtake Sales; the measures below use it to avoid double counting.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\Store_Universe_Overrides.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Chain", type text}, {"Offtake Chain", type text}, {"Store Count", Int64.Type}, {"Status", type text},
        {"Note", type text}, {"Source", type text}, {"As Of", type text}
    })
in
    Typed
