// =====================================================================
// QUERY: Dist Cont Weights  v2.0
// Source priority chain:
//   P1 = SeedData\Mapping\DistCont_Patch_Approved_2026-07-04.csv
//        Finance-approved exact overrides (Secondary contribution % in 0-100 format)
//   P2 = RawDataFolders\Primary_ShipTo_Monthly\Primary_ShipTo_FY25-26_to_May26.csv
//        Dist. rows only; Cont% already 0-1 fractions; covers May'25 – May'26
//   P3 = Jun'26 nearest-month fallback (May'26 data promoted to Jun'26)
//        PROVISIONAL – awaiting Finance approval of Jun'26 DistCont patch
//   P4 = "Unmapped Chain" emitted by Query 16 for any key not covered here
//
// For an exact (ShipTo Key × Brand Key × MonthStart) match, P1 overrides P2.
// Fractions are normalised to sum = 1 per group (same guarantee as the old query).
// Governance columns (Source Type, Approval Status, Provisional Flag, etc.) are
// propagated into 'Fact Primary Article' (query 16) and surfaced on the QC page.
//
// REPLACED: Dist_primary_cont_based_on_secondary_MOM.xlsx (gitignored, never
// committed). The two CSV sources above are checked into the repo and are the
// authoritative allocation inputs going forward.
// =====================================================================
let
    // ── Load Timestamp (shared across all rows this refresh) ──────────────
    LoadTs = DateTime.ToText(DateTime.LocalNow(), "yyyy-MM-dd HH:mm"),

    // ── CONSTANT: Jun'26 and May'26 month starts ──────────────────────────
    Jun26Start = #date(2026, 6, 1),
    May26Start = #date(2026, 5, 1),

    // ======================================================================
    // P1: Finance-Approved Patch
    //     Secondary contribution % is in 0-100 format → divide by 100
    // ======================================================================
    PatchRaw = Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Mapping\DistCont_Patch_Approved_2026-07-04.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    PatchHeaders = Table.PromoteHeaders(PatchRaw, [PromoteAllScalars = true]),
    PatchPicked = Table.SelectColumns(PatchHeaders, {
        "Ship To Name", "Chain Name", "Brand", "Revised month", "Secondary contribution %"
    }, MissingField.UseNull),
    PatchTyped = Table.TransformColumnTypes(PatchPicked, {
        {"Ship To Name",               type text},
        {"Chain Name",                 type text},
        {"Brand",                      type text},
        {"Revised month",              type date},
        {"Secondary contribution %",   type number}
    }),
    PatchCleaned = Table.SelectRows(PatchTyped,
        each [Ship To Name] <> null and [Chain Name] <> null
          and [#"Secondary contribution %"] <> null
          and [#"Secondary contribution %"] <> 0),
    PatchAddShipToKey = Table.AddColumn(PatchCleaned, "ShipTo Key",
        each Text.Lower(Text.Trim([Ship To Name])), type text),
    PatchAddBrandKey = Table.AddColumn(PatchAddShipToKey, "Brand Key",
        each Text.Lower(Text.Trim([Brand])), type text),
    PatchAddMonthStart = Table.AddColumn(PatchAddBrandKey, "MonthStart",
        each Date.StartOfMonth([Revised month]), type date),
    // Divide by 100 to get raw 0-1 contribution for normalisation
    PatchRawCont = Table.AddColumn(PatchAddMonthStart, "RawCont",
        each [#"Secondary contribution %"] / 100, type number),
    // Governance
    PatchGov1 = Table.AddColumn(PatchRawCont,
        "Source File", each "DistCont_Patch_Approved_2026-07-04.csv", type text),
    PatchGov2 = Table.AddColumn(PatchGov1,
        "Source Type", each "Approved Patch", type text),
    PatchGov3 = Table.AddColumn(PatchGov2,
        "Approval Status", each "Approved", type text),
    PatchGov4 = Table.AddColumn(PatchGov3,
        "Allocation Method", each "Exact Match – Approved Patch", type text),
    PatchGov5 = Table.AddColumn(PatchGov4,
        "Provisional Flag", each false, type logical),
    PatchGov6 = Table.AddColumn(PatchGov5,
        "Fallback Flag", each false, type logical),
    PatchGov7 = Table.AddColumn(PatchGov6,
        "Fallback Source Month", each null, type date),
    PatchFinal = Table.SelectColumns(PatchGov7, {
        "ShipTo Key", "Brand Key", "MonthStart",
        "Ship To Name", "Chain Name", "Brand", "RawCont",
        "Source File", "Source Type", "Approval Status",
        "Allocation Method", "Provisional Flag", "Fallback Flag", "Fallback Source Month"
    }),

    // ======================================================================
    // P2: ShipTo CSV — Dist. rows only
    //     Cont% is already in 0-1 fraction form; Chain column = Chain Name
    // ======================================================================
    ShipToRaw = Csv.Document(
        File.Contents(pRootFolder & "\RawDataFolders\Primary_ShipTo_Monthly\Primary_ShipTo_FY25-26_to_May26.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    ShipToHeaders = Table.PromoteHeaders(ShipToRaw, [PromoteAllScalars = true]),
    ShipToPicked = Table.SelectColumns(ShipToHeaders, {
        "Ship To Name", "Direct/Distributor", "Chain", "Brand", "MonthStart", "Cont%"
    }, MissingField.UseNull),
    ShipToTyped = Table.TransformColumnTypes(ShipToPicked, {
        {"Ship To Name",         type text},
        {"Direct/Distributor",   type text},
        {"Chain",                type text},
        {"Brand",                type text},
        {"MonthStart",           type date},
        {"Cont%",                type number}
    }),
    // Keep only Distributor rows with a valid chain and non-zero contribution
    ShipToDistOnly = Table.SelectRows(ShipToTyped,
        each [Direct/Distributor] <> null
          and Text.Lower(Text.Trim([Direct/Distributor])) = "dist."
          and [Chain] <> null
          and [#"Cont%"] <> null and [#"Cont%"] <> 0),
    ShipToRenChain = Table.RenameColumns(ShipToDistOnly, {{"Chain", "Chain Name"}}),
    ShipToAddShipToKey = Table.AddColumn(ShipToRenChain, "ShipTo Key",
        each Text.Lower(Text.Trim([Ship To Name])), type text),
    ShipToAddBrandKey = Table.AddColumn(ShipToAddShipToKey, "Brand Key",
        each Text.Lower(Text.Trim([Brand])), type text),
    // Rename Cont% to RawCont (already 0-1 fraction, no scaling needed)
    ShipToRawCont = Table.RenameColumns(ShipToAddBrandKey, {{"Cont%", "RawCont"}}),
    // Governance
    ShipToGov1 = Table.AddColumn(ShipToRawCont,
        "Source File", each "Primary_ShipTo_FY25-26_to_May26.csv", type text),
    ShipToGov2 = Table.AddColumn(ShipToGov1,
        "Source Type", each "ShipTo CSV", type text),
    ShipToGov3 = Table.AddColumn(ShipToGov2,
        "Approval Status", each "Approved", type text),
    ShipToGov4 = Table.AddColumn(ShipToGov3,
        "Allocation Method", each "Exact Match – ShipTo CSV", type text),
    ShipToGov5 = Table.AddColumn(ShipToGov4,
        "Provisional Flag", each false, type logical),
    ShipToGov6 = Table.AddColumn(ShipToGov5,
        "Fallback Flag", each false, type logical),
    ShipToGov7 = Table.AddColumn(ShipToGov6,
        "Fallback Source Month", each null, type date),
    ShipToFinal = Table.SelectColumns(ShipToGov7, {
        "ShipTo Key", "Brand Key", "MonthStart",
        "Ship To Name", "Chain Name", "Brand", "RawCont",
        "Source File", "Source Type", "Approval Status",
        "Allocation Method", "Provisional Flag", "Fallback Flag", "Fallback Source Month"
    }),

    // ======================================================================
    // PRIORITY MERGE: P1 overrides P2 for exact (ShipTo Key × Brand Key × MonthStart)
    // Remove ShipTo rows whose group key is entirely covered by the Approved Patch
    // ======================================================================
    PatchKeyGroups = Table.Distinct(Table.SelectColumns(PatchFinal,
        {"ShipTo Key", "Brand Key", "MonthStart"})),
    ShipToNotOverridden = Table.Join(
        ShipToFinal,  {"ShipTo Key", "Brand Key", "MonthStart"},
        PatchKeyGroups, {"ShipTo Key", "Brand Key", "MonthStart"},
        JoinKind.LeftAnti),
    CombinedBase = Table.Combine({PatchFinal, ShipToNotOverridden}),

    // ======================================================================
    // P3: Jun'26 nearest-month fallback
    // The ShipTo CSV ends May'26. For any (ShipTo Key × Brand Key) with May'26 data
    // but no Jun'26 data, copy May'26 rows to Jun'26 and mark as Provisional.
    // These rows must be superseded by a Finance-approved DistCont patch for Jun'26.
    // ======================================================================
    May26Rows = Table.SelectRows(CombinedBase, each [MonthStart] = May26Start),
    Jun26Rows = Table.SelectRows(CombinedBase, each [MonthStart] = Jun26Start),
    // Keys already covered for Jun'26 (from Approved Patch, if any)
    Jun26Keys = Table.Distinct(Table.SelectColumns(Jun26Rows, {"ShipTo Key", "Brand Key"})),
    // May'26 rows whose ShipTo+Brand key has no Jun'26 coverage
    May26ForFallback = Table.Join(
        May26Rows,  {"ShipTo Key", "Brand Key"},
        Jun26Keys,  {"ShipTo Key", "Brand Key"},
        JoinKind.LeftAnti),
    Jun26Fallback = Table.TransformColumns(May26ForFallback, {
        {"MonthStart",        each Jun26Start,
            type date},
        {"Source File",       each "Primary_ShipTo_FY25-26_to_May26.csv (Jun'26 fallback from May'26)",
            type text},
        {"Source Type",       each "Nearest-Month Fallback",
            type text},
        {"Approval Status",   each "Provisional – Jun'26 gap; awaiting Finance approval",
            type text},
        {"Allocation Method", each "Nearest-Month Fallback – May'26 applied to Jun'26",
            type text},
        {"Provisional Flag",  each true,
            type logical},
        {"Fallback Flag",     each true,
            type logical},
        {"Fallback Source Month", each May26Start,
            type date}
    }),

    // ======================================================================
    // COMBINE all sources; normalise fractions per group
    // ======================================================================
    AllRows = Table.Combine({CombinedBase, Jun26Fallback}),

    Grouped = Table.Group(AllRows, {"ShipTo Key", "Brand Key", "MonthStart"}, {
        {"Raw Pct Sum", each List.Sum([RawCont]), type number},
        {"Rows",        each _, type table}
    }),
    Expanded = Table.ExpandTableColumn(Grouped, "Rows", {
        "Ship To Name", "Chain Name", "Brand", "RawCont",
        "Source File", "Source Type", "Approval Status",
        "Allocation Method", "Provisional Flag", "Fallback Flag", "Fallback Source Month"
    }),
    // Normalised fraction: sums to 1 per group by construction
    AddFrac = Table.AddColumn(Expanded, "Frac",
        each [RawCont] / [Raw Pct Sum], type number),

    AddLoadTs = Table.AddColumn(AddFrac, "Load Timestamp", each LoadTs, type text),

    Final = Table.SelectColumns(AddLoadTs, {
        "ShipTo Key", "Brand Key", "MonthStart",
        "Ship To Name", "Chain Name", "Brand",
        "Frac", "Raw Pct Sum",
        "Source File", "Source Type", "Approval Status",
        "Allocation Method", "Provisional Flag", "Fallback Flag",
        "Fallback Source Month", "Load Timestamp"
    })
in
    Final
