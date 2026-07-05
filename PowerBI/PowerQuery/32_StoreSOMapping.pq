// =====================================================================
// QUERY: Store-SO Mapping  (which Sales Officer owns each store, with split)
// From the shared FY2627_TGT_and_sales_team_mapping file (Sheet2).
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Mapping\Store_SO_Mapping.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Month", type text},{"Store Code", type text},
        {"Employee ID 1", type text},{"SO Name 1", type text},
        {"Employee ID 2", type text},{"SO Name 2", type text},
        {"Employee ID 3", type text},{"SO Name 3", type text},
        {"Cont% 1", type number},{"Cont% 2", type number},{"Cont% 3", type number}}),
    Trimmed = Table.TransformColumns(Typed, {{"Store Code", each Text.Trim(Text.From(_)), type text}})
in
    Trimmed
