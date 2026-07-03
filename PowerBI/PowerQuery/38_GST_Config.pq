// =====================================================================
// QUERY: GST Config
// Source: SeedData\Masters\GST_Config.csv  (repo-relative to pRootFolder)
// Role: single-row, single-editable-cell GST cutover date used by TOT%
// (DAX/12_TOT_Measures.dax) as the DEFAULT cutover for any category whose
// own Effective_From (in GST Rate QC Table, query 37) is blank.
//
// Default = 2025-09-22 (GST Council's confirmed GST 2.0 rate-rationalisation
// effective date). Edit the single GST_Cutover_Date cell in the CSV if
// Honasa's internal billing/invoicing system actually reflected the new
// rates on a different date -- TOT% recomputes from whatever date is here
// on the next refresh. Kept DISCONNECTED (no modelled relationship).
// =====================================================================
let
    Source = Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Masters\GST_Config.csv"),
        [Delimiter=",", Columns=2, Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"GST_Cutover_Date", type date},
        {"Note", type text}
    })
in
    Typed
