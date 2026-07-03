// =====================================================================
// QUERY: GST Rate QC Table
// Source: SeedData\Masters\GST_Rate_QC_Table.csv  (repo-relative to pRootFolder)
// Role: the Finance/Tax sign-off sheet for TOT% (Trade Offer Terms % /
// On-Invoice Margin Pass-on %) — Category, HSN Code, Pre/Post-GST rate,
// per-category cutover override, Confidence, Finance approval status, and
// the auto-computed Impact_on_TOT_pct sensitivity. Read by the TOT%
// measures in DAX/12_TOT_Measures.dax. Kept DISCONNECTED (no modelled
// relationship) -- read via LOOKUPVALUE() so it stays a simple,
// hand-editable table with no relationship to wire up.
//
// EVERY row starts Finance_Approved = "Pending" and several are marked
// Confidence = "Low" (no official HSN-code-level source was available for
// the post-GST-2.0 category classification) -- verify against Honasa's
// Finance/Tax records and fill in HSN_Code + flip Finance_Approved to "Yes"
// per row as confirmed. TOT% still computes off whatever is in this file
// regardless of approval status -- Finance_Approved is an audit/tracking
// field, not a computational gate.
//
// Effective_From (optional, per-category): if blank, that category's
// cutover uses the GLOBAL default date from 'GST Config' (query 38). Fill
// this in only if Finance confirms a SPECIFIC category transitioned on a
// different date than the rest.
// =====================================================================
let
    Source = Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Masters\GST_Rate_QC_Table.csv"),
        [Delimiter=",", Columns=9, Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Category", type text},
        {"HSN_Code", type text},
        {"Pre_GST_Rate_Pct", type number},
        {"Post_GST_Rate_Pct", type number},
        {"Effective_From", type text},   // kept text: often blank ("use global default") -- parse to date only where non-blank, see DAX
        {"Confidence", type text},
        {"Finance_Approved", type text},
        {"Impact_on_TOT_pct", type number},
        {"Note", type text}
    })
in
    Typed
