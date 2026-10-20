// =====================================================================
// QUERY: NPD Article Chain  (grain = one chain x EAN launch; FY26 and FY27 cohorts)
// Source = SeedData\Masters\NPD_Article_Chain.csv  (rebuild with scripts/build_npd_seed.py)
// Mirrors the HTML NPD tracker (npd_block): the FY holding a pair's first valid commercial sale,
// except a March first sale rolls into the next FY. Counts and timing only; no NSV is stored here.
// Launch Confirmation: confirmed = 12+ months of history before the first sale;
// observed_only = first sale visible in the available history only (not proof of a new product).
// No relationship: use Chain, NPI Cohort FY and Launch Confirmation as slicers.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\NPD_Article_Chain.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Chain", type text}, {"EAN", type text}, {"Article", type text},
        {"NPI Cohort FY", type text}, {"First Sale FY", type text}, {"First Sale Month", type text},
        {"History Months Before First Sale", Int64.Type}, {"Launch Confirmation", type text}
    }, "en-US")
in
    Typed
