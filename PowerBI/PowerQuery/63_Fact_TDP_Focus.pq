// =====================================================================
// QUERY: Fact TDP Focus Articles  (grain = Chain x Brand x EAN; FY27 year to date)
// Source = SeedData\Masters\TDP_Focus_Articles.csv (aggregate; rebuild with scripts/build_tdp_focus_articles.py)
// NOT TDP: no ACV % and no weighted distribution. It is the article list to track:
//   Selection contains TOP95            = article is in the top 95% of NSV for that chain and brand
//   Selection contains NEW_SINCE_JAN26  = first sale in primary or offtake is Jan-26 or later (checked against primary from Apr-25)
//   Selection contains NPI_NEW_TO_CHAIN = no offtake in that chain in Apr-26, first seen there later (offtake only)
// Offtake leaves Reliance Brand Counter rows out (offtake de-duplication rule). Primary is never filtered.
// Rupee columns are in Rs lakh. No relationship: use the Chain, Brand and Selection columns as slicers.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\TDP_Focus_Articles.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Renamed = Table.RenameColumns(Promoted, {
        {"Rank in Chain-Brand", "Rank In Chain Brand"}, {"FY27 YTD NSV (Rs L)", "FY27 YTD NSV Rs L"},
        {"Avg Monthly NSV (Rs L)", "Avg Monthly NSV Rs L"}, {"Share %", "Share Pct"}, {"Cum Share %", "Cum Share Pct"},
        {"Chain-Brand FY27 YTD NSV (Rs L)", "Chain Brand FY27 YTD NSV Rs L"},
        {"First Month in Chain", "First Month In Chain"}}),
    Typed = Table.TransformColumnTypes(Renamed, {
        {"Chain", type text}, {"Brand", type text}, {"EAN", type text}, {"Article Description", type text},
        {"Rank In Chain Brand", Int64.Type}, {"FY27 YTD NSV Rs L", type number}, {"Avg Monthly NSV Rs L", type number},
        {"Share Pct", type number}, {"Cum Share Pct", type number}, {"Chain Brand FY27 YTD NSV Rs L", type number},
        {"Selection", type text}, {"First Sale", type text}, {"First Month In Chain", type text}, {"Newness Evidence", type text}
    })
in
    Typed
