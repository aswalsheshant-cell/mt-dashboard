// =====================================================================
// QUERY: Dist Cont Weights
// Source: RawDataFolders\Dist_primary_cont_based_on_secondary_MOM.xlsx
//         sheet "Dist Primary Conv to Chain Art"
// Role: the business's secondary-derived monthly Distributor -> Chain split,
// used by 'Fact Primary Article' (query 16) to allocate PO Type='Dist.'
// primary rows (whose "Chain name for Dashboard" is blank) onto real chains
// at Customer x Article grain. Key = Ship To Name x Brand x Month; NOTE the
// sheet has NO Cust-SAP Code column -- the code<->ship-to bridge lives in
// the primary file itself, so the join is on the normalised Ship To Name.
//
// Fractions are NORMALISED to sum to exactly 1 per key, so the allocation
// reconciles to the input by construction. Keys whose RAW cont% sum
// deviates from 100 are surfaced via the [Raw Pct Sum] column -- put a
// table visual on it filtered to ABS([Raw Pct Sum]-100) > 0.5 for QC
// rule 19 ("flag the variance before allocation").
// =====================================================================
let
    Source = Excel.Workbook(
        File.Contents(pRootFolder & "\RawDataFolders\Dist_primary_cont_based_on_secondary_MOM.xlsx"),
        null, true),
    Sheet = Source{[Item="Dist Primary Conv to Chain Art", Kind="Sheet"]}[Data],
    // row 1 of the sheet is blank padding; row 2 is the real header
    Skipped = Table.Skip(Sheet, 1),
    Promoted = Table.PromoteHeaders(Skipped, [PromoteAllScalars=true]),
    Picked = Table.SelectColumns(Promoted, {
        "Ship To Name", "Chain Name", "Brand", "Revised month", "Secondary contribution %"
    }, MissingField.UseNull),
    Typed = Table.TransformColumnTypes(Picked, {
        {"Ship To Name", type text}, {"Chain Name", type text}, {"Brand", type text},
        {"Revised month", type date}, {"Secondary contribution %", type number}
    }),
    Cleaned = Table.SelectRows(Typed, each [Ship To Name] <> null and [Chain Name] <> null
        and [Secondary contribution %] <> null and [Secondary contribution %] <> 0),
    AddKeys = Table.AddColumn(Cleaned, "ShipTo Key", each Text.Lower(Text.Trim([Ship To Name])), type text),
    AddBrandKey = Table.AddColumn(AddKeys, "Brand Key", each Text.Lower(Text.Trim([Brand])), type text),
    AddMonthStart = Table.AddColumn(AddBrandKey, "MonthStart", each Date.StartOfMonth([Revised month]), type date),
    // normalise cont% to fractions summing to exactly 1 per key
    Grouped = Table.Group(AddMonthStart, {"ShipTo Key", "Brand Key", "MonthStart"}, {
        {"Raw Pct Sum", each List.Sum([#"Secondary contribution %"]), type number},
        {"Rows", each _, type table}
    }),
    Expanded = Table.ExpandTableColumn(Grouped, "Rows",
        {"Ship To Name", "Chain Name", "Secondary contribution %"}),
    AddFrac = Table.AddColumn(Expanded, "Frac", each
        [#"Secondary contribution %"] / [Raw Pct Sum], type number),
    Final = Table.SelectColumns(AddFrac,
        {"ShipTo Key", "Brand Key", "MonthStart", "Chain Name", "Frac", "Raw Pct Sum"})
in
    Final
