// =====================================================================
// QUERY: Primary Allocation Override  (manual, editable - optional)
// Type a Cont% here to override the secondary-derived allocation for a
// specific Month x Ship-To x Chain x Brand. Use "ALL" wildcards as needed.
// DAX prefers this value when a matching row exists. Never hardcoded in
// measures - it lives in this editable table.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\PrimaryAllocationOverride.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Month", type text},{"Ship To Name", type text},{"Chain", type text},
        {"Brand", type text},{"Override Cont%", type number},{"Remarks", type text}})
in
    Typed
