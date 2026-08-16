// =====================================================================
// QUERY: Secondary Sales Efficiency  (pre-aggregated helper table)
// Grain: FY Year x Month x Chain x Brand
// Computes sell-through (offtake / primary) at chain x brand x month level,
// returning the core efficiency metrics for the Distribution tab's
// "Offtake Efficiency" sub-section and the Chain-wise Performance page.
//
// Columns:
//   FY Year, Month, MonthStart, Chain, Brand
//   Primary NSV      — Lakh, from Fact Primary Article (DIST-allocated)
//   Offtake NSV      — Lakh, from Fact Offtake Sales
//   Sell-Through Pct — Offtake NSV / Primary NSV (null-safe, capped at 200%
//                      to exclude months where primary = 0 but offtake > 0
//                      due to pipeline stock; un-capped rows surfaced in
//                      Sell-Through Outlier flag)
//   Coverage Gap Pct — 1 − Sell-Through (positive = under-liquidation)
//   Inventory Signal  — "Over-stocked" / "On-track" / "Under-liquidation"
//                      thresholds: ≥ 120% over-stocked, 80–120% on-track,
//                      < 80% under-liquidation (adjust in Assumption Table)
//   Outlier Flag     — true when Primary NSV = 0 and Offtake NSV > 0
//                      (pipeline / opening-stock liquidation — exclude from
//                      efficiency KPIs, review in Distribution Gap page)
//
// Join: this query aggregates both facts separately then merges — it does NOT
// require a shared row-level key between primary and offtake. Chain and Brand
// are the natural join keys; "Reliance Retail" / "Reliance Retail Limited"
// divergence is resolved by the canonical Chain names established in
// Fact Primary Article ([Chain]) and Fact Offtake Sales ([Chain]).
// =====================================================================
let
    // ---- 1. Aggregate Primary to Chain x Brand x Month ----
    PrimSrc = Table.SelectColumns(
        #"Fact Primary Article",
        {"FY Year", "Month", "MonthStart", "Chain", "Brand", "Primary NSV"}),

    PrimAgg = Table.Group(PrimSrc,
        {"FY Year", "Month", "MonthStart", "Chain", "Brand"},
        {{"Primary NSV", each List.Sum([Primary NSV]), type number}}),

    // ---- 2. Aggregate Offtake to Chain x Brand x Month ----
    OftSrc = Table.SelectColumns(
        #"Fact Offtake Sales",
        {"FY Year", "Month", "MonthStart", "Chain", "Brand", "Offtake NSV"}),

    OftAgg = Table.Group(OftSrc,
        {"FY Year", "Month", "MonthStart", "Chain", "Brand"},
        {{"Offtake NSV", each List.Sum([Offtake NSV]), type number}}),

    // ---- 3. Full outer join (keep rows present in either fact) ----
    Joined = Table.NestedJoin(
        PrimAgg, {"FY Year", "Month", "MonthStart", "Chain", "Brand"},
        OftAgg,  {"FY Year", "Month", "MonthStart", "Chain", "Brand"},
        "Oft", JoinKind.FullOuter),

    Expanded = Table.ExpandTableColumn(Joined, "Oft", {"Offtake NSV"}),

    FillPrim = Table.ReplaceValue(Expanded, null, 0, Replacer.ReplaceValue, {"Primary NSV"}),
    FillOft  = Table.ReplaceValue(FillPrim,  null, 0, Replacer.ReplaceValue, {"Offtake NSV"}),

    // ---- 4. Outlier flag: offtake from pipeline stock (Primary = 0) ----
    AddOutlier = Table.AddColumn(FillOft, "Outlier Flag", each
        [Primary NSV] = 0 and [Offtake NSV] > 0, type logical),

    // ---- 5. Sell-Through Pct (null when Primary=0 to avoid ÷0 distortion) ----
    AddST = Table.AddColumn(AddOutlier, "Sell-Through Pct", each
        if [Primary NSV] = 0 then null
        else Number.Round([Offtake NSV] / [Primary NSV] * 100, 1),
        type number),

    // ---- 6. Raw (uncapped) for outlier review ----
    AddSTRaw = Table.AddColumn(AddST, "Sell-Through Raw", each
        if [Primary NSV] = 0 then null
        else [Offtake NSV] / [Primary NSV] * 100,
        type number),

    // ---- 7. Capped Sell-Through (≤ 200%) for efficiency KPI visuals ----
    AddSTCapped = Table.AddColumn(AddSTRaw, "Sell-Through Capped", each
        if [Sell-Through Raw] = null then null
        else Number.Min([Sell-Through Raw], 200),
        type number),

    // ---- 8. Coverage Gap ----
    AddGap = Table.AddColumn(AddSTCapped, "Coverage Gap Pct", each
        if [Sell-Through Pct] = null then null
        else Number.Round(100 - [Sell-Through Pct], 1),
        type number),

    // ---- 9. Inventory Signal (thresholds sourced from Assumption Table) ----
    //   Over-stocked      : ST ≥ 120%  (high offtake vs. primary = inventory clearing)
    //   On-track          : 80% ≤ ST < 120%
    //   Under-liquidation : ST < 80%   (slow sell-through = excess stock risk)
    //   No Primary        : Primary = 0 (outlier/pipeline — review separately)
    AddSignal = Table.AddColumn(AddGap, "Inventory Signal", each
        if [Outlier Flag]               then "No Primary Data"
        else if [Sell-Through Pct] = null then "No Primary Data"
        else if [Sell-Through Pct] >= 120 then "Over-stocked"
        else if [Sell-Through Pct] >= 80  then "On-track"
        else                                   "Under-liquidation",
        type text),

    // ---- 10. Signal Sort (for consistent legend ordering) ----
    AddSignalSort = Table.AddColumn(AddSignal, "Signal Sort", each
        Record.FieldOrDefault(
            [#"On-track"=1, #"Under-liquidation"=2, #"Over-stocked"=3, #"No Primary Data"=4],
            [Inventory Signal], 5),
        type number),

    // ---- 11. Final select and type ----
    Final = Table.SelectColumns(AddSignalSort, {
        "FY Year", "Month", "MonthStart", "Chain", "Brand",
        "Primary NSV", "Offtake NSV",
        "Sell-Through Pct", "Sell-Through Raw", "Sell-Through Capped",
        "Coverage Gap Pct", "Inventory Signal", "Signal Sort", "Outlier Flag"
    }),

    Typed = Table.TransformColumnTypes(Final, {
        {"FY Year", type text}, {"Month", type text}, {"MonthStart", type date},
        {"Chain", type text}, {"Brand", type text},
        {"Primary NSV", type number}, {"Offtake NSV", type number},
        {"Sell-Through Pct", type number}, {"Sell-Through Raw", type number},
        {"Sell-Through Capped", type number}, {"Coverage Gap Pct", type number},
        {"Inventory Signal", type text}, {"Signal Sort", Int64.Type},
        {"Outlier Flag", type logical}
    })
in
    Typed
