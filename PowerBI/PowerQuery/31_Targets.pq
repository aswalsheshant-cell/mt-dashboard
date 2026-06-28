// =====================================================================
// QUERY: Targets  (FY26-27 monthly targets, from the shared TGT file)
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Targets\FY2627_Targets.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"MonthStart", type date},{"Month", type text},{"FY Year", type text},
        {"Quarter", type text},{"Target NSV Cr", type number}}),
    // store target in absolute rupees too, for measure convenience
    AddAbs = Table.AddColumn(Typed, "Target NSV", each [Target NSV Cr] * 10000000, type number)
in
    AddAbs
