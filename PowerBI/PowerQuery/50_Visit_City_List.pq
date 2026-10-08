// =====================================================================
// QUERY: Visit City List  (the corporate-visit cities, one row per city)
// Source = SeedData\Masters\Visit_City_List.csv: Region, City, aliases (Cochin = Kochi etc.) and the near-listed cities that roll up to it.
// Relate Visit City List[City] -> Store City Master[Visit City] (1 to many).
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\Visit_City_List.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Region", type text}, {"City", type text}, {"Beats Planned (rule)", type text},
        {"Aliases", type text}, {"Near Listed (not on list)", type text}
    })
in
    Typed
