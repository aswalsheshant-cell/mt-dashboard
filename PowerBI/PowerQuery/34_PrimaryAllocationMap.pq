// =====================================================================
// QUERY: Primary Allocation Map   (the dynamic, month-wise Cont% table)
// =====================================================================
// This is the "separate mapping / assumption table" the business asked for.
// It is DERIVED from the monthly ship-to primary feed, so it updates itself
// every month with no formula changes:
//
//   Cont%(Month, Ship-To, Chain, Brand)
//
// Use it to allocate ANY raw, un-split primary that arrives at Ship-To x
// Brand level: Allocated Primary = raw ship-to primary * Cont% for the chain.
// (When the feed already arrives pre-split - as today - 'Fact Primary ShipTo'
//  already carries the allocated NSV and this table is the audit/driver view.)
//
// To override an allocation manually, add the same Month/Ship-To/Chain/Brand
// key to 'Primary Allocation Override' (query 35) - DAX prefers the override.
// =====================================================================
let
    Source = #"Fact Primary ShipTo",
    Keep = Table.SelectColumns(Source,
        {"Month","MonthStartCalc","FY Year","Ship To Name","Direct/Distributor","Chain","Brand","Cont%"}),
    Renamed = Table.RenameColumns(Keep, {{"MonthStartCalc","MonthStart"}}),
    // one row per Month x Ship-To x Chain x Brand (Cont% is constant within the group)
    Grouped = Table.Group(Renamed,
        {"Month","MonthStart","FY Year","Ship To Name","Direct/Distributor","Chain","Brand"},
        {{"Cont%", each List.Max([Cont%]), type number}})
in
    Grouped
