// =====================================================================
// QUERY: Fact Secondary Sales  (Distributor sell-out registers)
// Grain: Source_Month × Distributor × NSV_Lakh
//
// Source: PowerBI/RawDataFolders/SecondarySales_Monthly/
//         Files: secondary_sales_distributor_*.csv ONLY
//                (today: _Q1_FY27.csv = Apr-Jun'26, _Jul_Aug_FY27.csv = Jul-Aug'26)
//
// Why the name filter: the same folder also holds the chain and brand
// registers and two tot_hierarchy files that repeat Apr-Aug'26 at article
// grain with Distributor/NSV_Lakh columns. Combining the whole folder would
// count the same sales two or three times. Only distributor register files
// are read. (Defect fix 2026-09-27: the query previously passed a column list
// as fnCombineFolder's HeaderRow number argument, and used a
// "\PowerBI\RawDataFolders" path under pRootFolder, which already points at
// the PowerBI folder - see 00_Parameters.pq.)
//
// Required columns (exact headers — do not rename in source files):
//   Source_Month  — YYYY-MM  (e.g. 2026-04)
//   Month_Label   — Apr-2026
//   FY_Year       — FY27
//   Distributor   — canonical name matching Fact Primary Article[Distributor]
//   NSV_Lakh      — secondary sell-out NSV in Lakh (ex-GST where confirmed)
//   Data_Source   — free-text source tag
//   Notes         — any provisional flag
//
// Refresh: drop a new secondary_sales_distributor_<period>.csv into
//          SecondarySales_Monthly/ and click Refresh — no query edits needed.
//
// Note: North distributor registers not yet available (Q1 FY27).
//       Rows will appear automatically once included in the export.
// =====================================================================
let
    RequiredColumns = {"Source_Month", "Month_Label", "FY_Year", "Distributor",
                       "NSV_Lakh", "Data_Source", "Notes"},

    // ── Distributor register files only (name filter before parsing) ─
    Files = Folder.Files(pRootFolder & "\RawDataFolders\SecondarySales_Monthly"),
    DistributorFiles = Table.SelectRows(Files, each
        Text.StartsWith(Text.Lower([Name]), "secondary_sales_distributor_")
        and Text.Lower([Extension]) = ".csv"),

    Parsed = Table.AddColumn(DistributorFiles, "Data", each
        let
            t = Table.PromoteHeaders(
                    Csv.Document([Content], [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
                    [PromoteAllScalars=true]),
            // a renamed/missing header fails the refresh instead of loading nulls
            cols = Table.SelectColumns(t, RequiredColumns, MissingField.Error)
        in
            Table.AddColumn(cols, "Data Source File", (r) => [Name], type text)),

    Source =
        if Table.RowCount(Parsed) = 0 then
            #table(RequiredColumns & {"Data Source File"}, {})
        else
            Table.Combine(Parsed[Data]),

    // ── Type coercions ─────────────────────────────────────────────
    Typed = Table.TransformColumnTypes(Source, {
        {"Source_Month",  type text},
        {"Month_Label",   type text},
        {"FY_Year",       type text},
        {"Distributor",   type text},
        {"NSV_Lakh",      type number},
        {"Data_Source",   type text},
        {"Notes",         type text}
    }),

    // ── Derive date fields from YYYY-MM ────────────────────────────
    WithMonth = Table.AddColumn(Typed, "MonthStart", each
        try Date.FromText([Source_Month] & "-01") otherwise null,
        type date),

    WithFY = Table.AddColumn(WithMonth, "FY_Derived", each
        let m = Date.Month([MonthStart])
        in if m >= 4 then "FY" & Text.From(Date.Year([MonthStart]) + 1)
                     else "FY" & Text.From(Date.Year([MonthStart])),
        type text),

    // ── Provisional flag ───────────────────────────────────────────
    WithProvisional = Table.AddColumn(WithFY, "Is_Provisional", each
        Text.Contains([Notes], "provisional") or Text.Contains([Notes], "GST"),
        type logical),

    // ── NSV in Crore (for cross-table consistency) ─────────────────
    WithCr = Table.AddColumn(WithProvisional, "NSV_Cr", each
        [NSV_Lakh] / 100, type number),

    // ── Remove helper columns not needed in the model ──────────────
    Final = Table.SelectColumns(WithCr, {
        "Source_Month", "Month_Label", "MonthStart",
        "FY_Year", "FY_Derived",
        "Distributor", "NSV_Lakh", "NSV_Cr",
        "Is_Provisional", "Data_Source"
    })
in
    Final
