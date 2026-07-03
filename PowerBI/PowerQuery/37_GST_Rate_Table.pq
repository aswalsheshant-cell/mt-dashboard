// =====================================================================
// QUERY: GST Rate Table
// Source: SeedData\Masters\GST_Rate_Table.csv  (repo-relative to pRootFolder)
// Role: Category -> post-GST-2.0-cutover (Nov'25) tax rate %, used by the
// TOT% (Trade Offer Terms % / On-Invoice Margin Pass-on %) measures in
// DAX/12_TOT_Measures.dax. Kept DISCONNECTED (no modelled relationship) --
// read via LOOKUPVALUE() so it stays a simple, hand-editable table with no
// relationship to wire up. Several rows are LOW-confidence best-effort
// assumptions (no official HSN-code-level source was available) -- see the
// Confidence/Note columns and verify against Finance/Tax records before
// treating TOT% as final.
// =====================================================================
let
    Source = Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Masters\GST_Rate_Table.csv"),
        [Delimiter=",", Columns=4, Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Category", type text},
        {"GST_Rate_From_Nov25_Pct", type number},
        {"Confidence", type text},
        {"Note", type text}
    })
in
    Typed
