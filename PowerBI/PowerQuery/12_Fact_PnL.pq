// =====================================================================
// QUERY: Fact P&L  (built, not hardcoded)
// P&L is DERIVED at refresh time from Offtake NSV + the Assumption Table.
// If a future raw P&L file with actual cost/spend exists, drop it into a
// RawDataFolders\PnL_Monthly folder and union it here; otherwise the model
// computes P&L from assumptions via DAX (see 02_PnL_Measures.dax).
//
// This query produces an Offtake-NSV-by-Chain/Brand/Category/Month base
// that the P&L DAX measures sit on top of. No spend is hardcoded here.
// =====================================================================
let
    Source = #"Fact Offtake Sales",
    Grouped = Table.Group(
        Source,
        {"MonthStart", "Month", "FY Year", "Chain", "Brand", "Category"},
        {
            {"Offtake NSV", each List.Sum([Offtake NSV]), type number},
            {"Offtake Qty", each List.Sum([Offtake Qty]), type number},
            {"MRP Sales",   each List.Sum([MRP Sales]),   type number}
        }
    )
in
    Grouped
