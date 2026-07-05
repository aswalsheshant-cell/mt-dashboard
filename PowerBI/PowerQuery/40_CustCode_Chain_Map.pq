// =====================================================================
// QUERY: CustCode Chain Map
// Source: 'Fact Primary Article' (query 16) -- DEPENDS ON IT. Add this query
// AFTER 16_Fact_PrimaryArticle.pq exists in your Power BI file (Home ▸
// Transform data ▸ this query references that one by name, same as
// referencing any other already-loaded query).
//
// Role: Customer Code -> most-common Chain, so a PL_Expense_Input.csv row
// that only gives a Customer Code (no Chain) can still resolve to a chain
// for CM2 (mirrors dashboard/scripts/build_dashboard_data.py's
// _build_custcode_chain_lookup() exactly -- same List.Mode / value_counts-
// idxmax "most frequent" resolution, not just "first seen").
//
// Kept DISCONNECTED (no modelled relationship) -- read via LOOKUPVALUE by
// DAX/13_CM2_Measures.dax.
// =====================================================================
let
    Source = #"Fact Primary Article",
    Filtered = Table.SelectRows(Source, each [Customer Code] <> null and Text.Trim(Text.From([Customer Code])) <> ""),
    Grouped = Table.Group(Filtered, {"Customer Code"}, {
        {"Chain", each List.Mode(List.RemoveNulls(Table.Column(_, "Chain"))), type text}
    })
in
    Grouped
