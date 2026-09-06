// =====================================================================
// QUERY: Fact Secondary Sales  (Distributor sell-out registers)
// Grain: Source_Month × Distributor × NSV_Lakh
//
// Source: PowerBI/RawDataFolders/SecondarySales_Monthly/
//         Files: secondary_sales_distributor_Q1_FY27.csv  (and future quarters)
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
// Refresh: drop a new CSV for each quarter into SecondarySales_Monthly/
//          and click Refresh — no query edits needed.
//
// Note: North distributor registers not yet available (Q1 FY27).
//       Rows will appear automatically once included in the export.
// =====================================================================
let
    Source = fnCombineFolder(
        pRootFolder & "\PowerBI\RawDataFolders\SecondarySales_Monthly",
        {"Source_Month", "Month_Label", "FY_Year", "Distributor",
         "NSV_Lakh", "Data_Source", "Notes"}
    ),

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
