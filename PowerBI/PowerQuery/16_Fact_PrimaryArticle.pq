// =====================================================================
// QUERY: Fact Primary Article  (File 2 — article-wise primary, DIST-allocated)
// Source: RawDataFolders\Primary_Article_Monthly\
//   (month-wise CSVs from the article-wise primary .xlsb, produced by
//    scripts/split_primary_article_xlsb.py — pass --header-row 1: the current
//    business format has a reference/annotation row ABOVE the real header)
// Grain: Month x Customer(Ship-to) x Chain x Brand x Article — after the
//   DIST allocation below, one source Dist. row becomes one row PER CHAIN.
//
// MAPPING LOCKED to the CURRENT business headers (per the maintained file --
// do not assume old names):
//   FY, Month, Channel, Inv. Date, Cust-SAP Code, Ship To Name, EAN No.,
//   net_content, brand, PPT Category, category, sub_category, range,
//   Description, MRP (article MRP), Inv Qty, Inv. Net value(LOC),
//   Inv. Tax Amount(LOC), Total MRP sales, Avg Tot, MTD-Sale type, PO Type,
//   "Chain name for Dashboard" (one header cell containing a line break --
//   normalised to a single space below), Zone, State
//
// DIST ALLOCATION (mirrors allocate_dist_primary() in
// scripts/build_dashboard_data.py exactly):
//   * PO Type = 'Dist.' rows have a BLANK "Chain name for Dashboard" -- they
//     are exploded across chains by 'Dist Cont Weights' (query 41), joined on
//     Ship To Name x Brand x Month. Inv Qty / Total MRP sales / NSV / Tax are
//     scaled by the normalised cont% (sums to exactly 1 per key, so totals
//     reconcile to the input by construction). Article MRP is per-unit and is
//     NOT scaled. Avg Tot is a ratio, invariant under the split.
//   * Direct rows keep their own "Chain name for Dashboard".
//   * Dist. rows with no cont-sheet entry get Chain = "Unmapped Chain" --
//     never blank, never the distributor's Ship To Name.
//   * Ship To Name stays a CUSTOMER/distributor field; the dashboard chain
//     field is always [Chain].
// NOTE the flag lives in **PO Type** (Direct / Dist.), NOT in MTD-Sale type
// (which holds Sales / MRN / Cancel Invoice / FOC).
// =====================================================================
// Grain confirmed: Month x Customer(Ship-to) x Chain x Brand x Article (after DIST allocation
// each Dist. row becomes one row per Chain). To verify: group by {MonthStart, Chain, EAN Code}
// and check for unexpected duplicates from the allocation join.
// Diagnostic row-count checkpoints (click the named step in Applied Steps):
//   Source -> FixedNames -> RequiredCols -> Picked -> Renamed -> Typed -> CleanKeys -> Cleaned
//   -> DirectRows / DistRows -> Combined -> FixBrand
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Primary_Article_Monthly"),

    // normalise headers: collapse the embedded line break in
    // "Chain name(lf)for Dashboard" and squeeze doubled spaces
    FixedNames = Table.TransformColumnNames(Source, each
        Text.Trim(Text.Replace(Text.Replace(Text.Replace(_, "#(lf)", " "), "#(cr)", " "), "  ", " "))),

    // Fail-fast if any required column is absent after header normalisation.
    RequiredCols = let
        required = {"FY", "Month", "Ship To Name", "EAN No.", "brand",
                    "Inv Qty", "Inv. Net value(LOC)", "PO Type", "Chain name for Dashboard"},
        missing = List.Select(required, each not List.Contains(Table.ColumnNames(FixedNames), _))
        in if List.Count(missing) > 0
           then error Error.Record("Missing required columns",
                    "Absent from Primary Article source (after header normalisation): "
                    & Text.Combine(missing, ", "), null)
           else FixedNames,

    Picked = Table.SelectColumns(RequiredCols, {
        "FY", "Month", "Channel", "Inv. Date", "Cust-SAP Code", "Ship To Name",
        "EAN No.", "net_content", "brand", "PPT Category",
        "category", "sub_category", "range", "Description", "MRP",
        "Inv Qty", "Inv. Net value(LOC)", "Inv. Tax Amount(LOC)", "Total MRP sales", "Avg Tot",
        "MTD-Sale type", "PO Type", "Chain name for Dashboard", "Zone", "State"
    }, MissingField.UseNull),

    Renamed = Table.RenameColumns(Picked, {
        {"FY", "FY Year"},
        {"Cust-SAP Code", "Customer Code"},
        {"EAN No.", "EAN Code"},
        {"Description", "Article Description"},
        {"brand", "Brand"},
        {"PPT Category", "PPT Category"},
        {"category", "Category"},
        {"sub_category", "Sub-category"},
        {"range", "Range"},
        {"MRP", "Article MRP"},
        {"Inv Qty", "Primary Qty"},
        {"Inv. Net value(LOC)", "Primary NSV"},
        {"Inv. Tax Amount(LOC)", "Primary Tax Amount"},
        {"Total MRP sales", "Primary MRP"},
        {"Avg Tot", "Avg TOT"},
        {"Chain name for Dashboard", "Chain Dash"}
    }),

    Typed = Table.TransformColumnTypes(Renamed, {
        {"FY Year", type text}, {"Month", type text}, {"Channel", type text},
        {"Customer Code", type text}, {"Ship To Name", type text},
        {"EAN Code", type text}, {"net_content", type text}, {"Brand", type text},
        {"PPT Category", type text}, {"Category", type text}, {"Sub-category", type text},
        {"Range", type text}, {"Article Description", type text},
        {"Article MRP", type number}, {"Primary Qty", type number},
        {"Primary NSV", type number}, {"Primary Tax Amount", type number},
        {"Primary MRP", type number}, {"Avg TOT", type number},
        {"MTD-Sale type", type text}, {"PO Type", type text},
        {"Chain Dash", type text}, {"Zone", type text}, {"State", type text}
    }),

    // P2 + P6: strip trailing ".0" from the numeric-origin EAN key; normalise Zone/State case
    CleanKeys = Table.TransformColumns(Typed, {
        {"EAN Code", each let s = if _ = null then null else Text.From(_)
                          in if s <> null and Text.EndsWith(s, ".0")
                             then Text.Start(s, Text.Length(s) - 2) else s, type text},
        {"Zone",  each Text.Proper(Text.Trim(Text.Clean(Text.From(_)))), type text},
        {"State", each Text.Proper(Text.Trim(Text.Clean(Text.From(_)))), type text}
    }),

    // MonthStart from "April'24"/"Apr'24" text, a date value, or an Excel serial
    AddMonthStart = Table.AddColumn(CleanKeys, "MonthStart", each
        let v = [Month]
        in  if v = null then null
            else if Value.Is(v, type date) then Date.StartOfMonth(v)
            else if Value.Is(v, type number) then Date.StartOfMonth(Date.From(v))
            else
                let m = Text.Start(Text.BeforeDelimiter(Text.From(v), "'"), 3),
                    yy = Text.AfterDelimiter(Text.From(v), "'"),
                    mn = Record.FieldOrDefault([Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
                in if mn = null or yy = "" then null else #date(2000 + Number.FromText(yy), mn, 1),
        type date),

    // P3: require a parseable period so time-view and grand totals reconcile.
    // null-vs-zero: NSV = 0 kept (FOC / promo lines); NSV < 0 kept (MRN /
    // Cancel Invoice rows — VALID returns, not data errors).
    Cleaned = Table.SelectRows(AddMonthStart,
        each [MonthStart] <> null and ([Primary NSV] <> null or [Primary Qty] <> null)),

    // ---------- DIST -> Chain allocation ----------
    AddIsDist = Table.AddColumn(Cleaned, "Is Dist", each
        Text.Lower(Text.Trim(Text.From([PO Type] ?? ""))) = "dist."
        or Text.Lower(Text.Trim(Text.From([PO Type] ?? ""))) = "dist", type logical),

    DirectRows = Table.SelectRows(AddIsDist, each not [Is Dist]),
    DirectFinal = Table.AddColumn(DirectRows, "Chain", each [Chain Dash], type text),

    DistRows = Table.SelectRows(AddIsDist, each [Is Dist]),
    DistKeys1 = Table.AddColumn(DistRows, "ShipTo Key", each Text.Lower(Text.Trim([Ship To Name] ?? "")), type text),
    DistKeys2 = Table.AddColumn(DistKeys1, "Brand Key", each Text.Lower(Text.Trim([Brand] ?? "")), type text),
    Merged = Table.NestedJoin(DistKeys2, {"ShipTo Key", "Brand Key", "MonthStart"},
        #"Dist Cont Weights", {"ShipTo Key", "Brand Key", "MonthStart"},
        "W", JoinKind.LeftOuter),
    ExpandedW = Table.ExpandTableColumn(Merged, "W", {"Chain Name", "Frac"}),
    // scale measures by cont% (unmatched rows keep Frac=1 and go to "Unmapped Chain")
    FillFrac = Table.ReplaceValue(ExpandedW, null, 1, Replacer.ReplaceValue, {"Frac"}),
    Alloc1 = Table.AddColumn(FillFrac, "Primary Qty Alloc", each ([Primary Qty] ?? 0) * [Frac], type number),
    Alloc2 = Table.AddColumn(Alloc1, "Primary NSV Alloc", each ([Primary NSV] ?? 0) * [Frac], type number),
    Alloc3 = Table.AddColumn(Alloc2, "Primary MRP Alloc", each ([Primary MRP] ?? 0) * [Frac], type number),
    Alloc4 = Table.AddColumn(Alloc3, "Primary Tax Alloc", each
        if [Primary Tax Amount] = null then null else [Primary Tax Amount] * [Frac], type number),
    DistChain = Table.AddColumn(Alloc4, "Chain", each
        if [Chain Name] <> null then [Chain Name] else "Unmapped Chain", type text),
    DistSwap = Table.RemoveColumns(
        Table.RenameColumns(
            Table.RemoveColumns(DistChain, {"Primary Qty", "Primary NSV", "Primary MRP", "Primary Tax Amount"}),
            {{"Primary Qty Alloc", "Primary Qty"}, {"Primary NSV Alloc", "Primary NSV"},
             {"Primary MRP Alloc", "Primary MRP"}, {"Primary Tax Alloc", "Primary Tax Amount"}}),
        {"ShipTo Key", "Brand Key", "Chain Name", "Frac"}),

    Combined = Table.Combine({Table.RemoveColumns(DirectFinal, {"Is Dist"}),
                              Table.RemoveColumns(DistSwap, {"Is Dist"})}),

    // article key: EAN -> cleaned Description (the current format has no Article Code)
    AddKey = Table.AddColumn(Combined, "Article Key", each
        if [EAN Code] <> null and Text.Trim([EAN Code]) <> "" then "EAN:" & [EAN Code]
        else "DESC:" & Text.Upper(Text.Trim(Text.From([Article Description]))), type text),

    // brand spelling normalisation (keep in sync with Brand Master)
    FixBrand = Table.ReplaceValue(AddKey, "BBLUNT", "BBlunt", Replacer.ReplaceText, {"Brand"})
in
    FixBrand
