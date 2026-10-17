// =====================================================================
// QUERY: Dist Cont Weights  v3.0   (UNTESTED IN POWER BI DESKTOP - see below)
// Source priority chain:
//   P1 = SeedData\Mapping\DistCont_Patch_Approved_2026-07-04.csv
//        Finance-approved exact overrides (Secondary contribution % in 0-100 format)
//   P2 = SeedData\Mapping\ChainWisePrimarySale_Dump_Snapshot.csv
//        The business's chain-wise primary dump (Bill-to x Brand x Month x Chain NSV,
//        Apr'24 - Aug'26). Chain mix = chain NSV / net NSV of the key. Naming variants
//        of one distributor (SeedData\Mapping\ShipTo_Family_Aliases.csv) share one mix.
//        Replaces Primary_ShipTo_FY25-26_to_May26.csv, which held FY27 for Apr, May and
//        Jul only and split chains differently from the dump (Rs 474 L, Apr-Aug'26).
//   P3 = Nearest-month fallback: the last known split of a Ship-To x Brand is carried
//        forward for up to 3 months it has no data for (e.g. Sep'26 until the dump gets it)
//        PROVISIONAL - replaced automatically once the dump holds that month
//   P4 = "Unmapped Chain" emitted by Query 16 for any key not covered here
//
// For an exact (ShipTo Key x Brand Key x MonthStart) match, P1 overrides P2.
// Fractions are normalised to sum = 1 per group (same guarantee as the old query).
// A key whose chain rows mostly offset each other (returns) uses absolute weights.
// Governance columns (Source Type, Approval Status, Provisional Flag, etc.) are
// propagated into 'Fact Primary Article' (query 16) and surfaced on the QC page.
//
// Same rules as scripts/build_dashboard_data.py load_chain_dump_weights(), which the
// HTML dashboard uses, so both dashboards give the same chain split. Written outside
// Desktop: paste into a COPY of the query first, refresh, then compare the chain
// totals with the MoM chain-wise primary pivot. Desktop is the authority.
//
// Brand keys: the files spell two brands two ways ("The Derma Co" / "The Derma Co.",
// "Dr. Sheth" / "Dr. Sheth's"). One mix is built per brand and emitted under both
// spellings, because Query 16 joins on the raw lower-cased brand text.
// =====================================================================
let
    // ── Load Timestamp (shared across all rows this refresh) ──────────────
    LoadTs = DateTime.ToText(DateTime.LocalNow(), "yyyy-MM-dd HH:mm"),

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
    // P2: Chain-wise primary dump (all rows; Direct ship-tos are never looked up
    //     because Query 16 only joins Dist. rows)
    // ======================================================================
    // Same parsing for the snapshot and for the additions file (months newer than the snapshot).
    // No MissingField.UseNull: a renamed or missing column must fail the refresh, not blank out rows.
    LoadDump = (hdr as table) as table =>
        let
            picked = Table.SelectColumns(hdr, {"Month", "Bill to customer", "Brand", "Chain Name", "NSV"}),
            typed  = Table.TransformColumnTypes(picked, {
                {"Month",             type text},
                {"Bill to customer",  type text},
                {"Brand",             type text},
                {"Chain Name",        type text},
                {"NSV",               type number}
            }, "en-US"),
            // MonthStart from "April'26" / "Sept'25" / "Jun'26" (same parsing as Query 16)
            withMonth = Table.AddColumn(typed, "MonthStart", each
                let v  = Text.From([Month] ?? ""),
                    m  = Text.Start(Text.BeforeDelimiter(v, "'"), 3),
                    yy = Text.AfterDelimiter(v, "'"),
                    mn = Record.FieldOrDefault([Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
                in if mn = null or yy = "" then null else #date(2000 + Number.FromText(yy), mn, 1),
                type date),
            valid = Table.SelectRows(withMonth,
                each [MonthStart] <> null and [#"Bill to customer"] <> null
                  and [Chain Name] <> null and [NSV] <> null)
        in valid,
    DumpSnapHeaders = Table.PromoteHeaders(Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Mapping\ChainWisePrimarySale_Dump_Snapshot.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]), [PromoteAllScalars = true]),
    DumpAddHeaders = Table.PromoteHeaders(Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Mapping\ChainWisePrimarySale_Dump_Additions.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]), [PromoteAllScalars = true]),
    DumpSnap = LoadDump(DumpSnapHeaders),
    DumpAdd  = LoadDump(DumpAddHeaders),
    // A month in the additions file replaces that month in the snapshot
    AddMonths = Table.Distinct(Table.SelectColumns(DumpAdd, {"MonthStart"})),
    DumpSnapKept = Table.Join(DumpSnap, {"MonthStart"}, AddMonths, {"MonthStart"}, JoinKind.LeftAnti),
    DumpValid = Table.Combine({DumpSnapKept, DumpAdd}),
    // Keys exactly as Query 16 builds them: Text.Lower(Text.Trim(...))
    DumpKey1 = Table.AddColumn(DumpValid, "ShipTo Key",
        each Text.Lower(Text.Trim([#"Bill to customer"])), type text),
    // One canonical brand key; the two known double spellings are folded to one
    DumpKey2 = Table.AddColumn(DumpKey1, "Brand Key", each
        let b = Text.Lower(Text.Trim([Brand] ?? ""))
        in if b = "the derma co." then "the derma co"
           else if b = "dr. sheth" then "dr. sheth's"
           else b, type text),

    // Ship-to naming variants of one distributor share one key ("family")
    AliasHeaders = Table.PromoteHeaders(Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Mapping\ShipTo_Family_Aliases.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]), [PromoteAllScalars = true]),
    AliasPicked = Table.SelectColumns(AliasHeaders, {"Family", "Ship_To_Name"}),
    AliasMembers = Table.AddColumn(AliasPicked, "Member Key",
        each Text.Lower(Text.Trim([Ship_To_Name])), type text),
    DumpFamJoin = Table.NestedJoin(DumpKey2, {"ShipTo Key"}, AliasMembers, {"Member Key"}, "F", JoinKind.LeftOuter),
    DumpFam = Table.ExpandTableColumn(DumpFamJoin, "F", {"Family"}),
    DumpGroup = Table.AddColumn(DumpFam, "Group Key",
        each if [Family] <> null then "family:" & [Family] else [ShipTo Key], type text),

    // Chain NSV per (group, brand, month, chain)
    DumpAgg = Table.Group(DumpGroup, {"Group Key", "Brand Key", "MonthStart", "Chain Name"}, {
        {"NSV",          each List.Sum([NSV]), type number},
        {"Ship To Name", each List.First([#"Bill to customer"]), type text}
    }),
    // Net and absolute NSV per (group, brand, month)
    DumpTotals = Table.Group(DumpAgg, {"Group Key", "Brand Key", "MonthStart"}, {
        {"Net",    each List.Sum([NSV]), type number},
        {"AbsSum", each List.Sum(List.Transform([NSV], each Number.Abs(_))), type number}
    }),
    DumpWithTot = Table.ExpandTableColumn(
        Table.NestedJoin(DumpAgg, {"Group Key", "Brand Key", "MonthStart"},
                         DumpTotals, {"Group Key", "Brand Key", "MonthStart"}, "T", JoinKind.Inner),
        "T", {"Net", "AbsSum"}),
    // Signed share of the net; if the chain rows mostly offset (returns) use absolute shares
    DumpWeight = Table.AddColumn(DumpWithTot, "RawCont", each
        if [AbsSum] = 0 then null
        else if Number.Abs([Net]) < 0.5 * [AbsSum] then Number.Abs([NSV]) / [AbsSum]
        else [NSV] / [Net], type number),
    DumpWeightRows = Table.SelectRows(DumpWeight, each [RawCont] <> null and [RawCont] <> 0),

    // A family's mix is shared by every name in the family
    FamMembers = Table.AddColumn(AliasMembers, "Group Key", each "family:" & [Family], type text),
    DumpMemJoin = Table.NestedJoin(DumpWeightRows, {"Group Key"}, FamMembers, {"Group Key"}, "M", JoinKind.LeftOuter),
    DumpMem = Table.ExpandTableColumn(DumpMemJoin, "M", {"Member Key"}),
    DumpSetKey = Table.AddColumn(DumpMem, "ShipTo Key",
        each if [Member Key] <> null then [Member Key] else [Group Key], type text),
    // Each folded brand is also emitted under its other spelling
    DumpBrandAlt = Table.TransformColumns(
        Table.SelectRows(DumpSetKey, each List.Contains({"the derma co", "dr. sheth's"}, [Brand Key])),
        {{"Brand Key", each if _ = "the derma co" then "the derma co." else "dr. sheth", type text}}),
    DumpAllBrands = Table.Combine({DumpSetKey, DumpBrandAlt}),
    DumpAddBrand = Table.AddColumn(DumpAllBrands, "Brand", each [Brand Key], type text),
    // Governance
    DumpGov1 = Table.AddColumn(DumpAddBrand,
        "Source File", each "ChainWisePrimarySale_Dump_Snapshot.csv", type text),
    DumpGov2 = Table.AddColumn(DumpGov1,
        "Source Type", each "Chain-wise primary dump", type text),
    DumpGov3 = Table.AddColumn(DumpGov2,
        "Approval Status", each "Approved", type text),
    DumpGov4 = Table.AddColumn(DumpGov3,
        "Allocation Method", each "Exact Match – chain-wise primary dump", type text),
    DumpGov5 = Table.AddColumn(DumpGov4,
        "Provisional Flag", each false, type logical),
    DumpGov6 = Table.AddColumn(DumpGov5,
        "Fallback Flag", each false, type logical),
    DumpGov7 = Table.AddColumn(DumpGov6,
        "Fallback Source Month", each null, type date),
    ShipToFinal = Table.SelectColumns(DumpGov7, {
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
    // P3: Nearest-month fallback (generic, replaces the Jun'26-only rule)
    // For every Ship-To x Brand, the rows of its LAST known month are carried forward
    // 1, 2 and 3 months (the same 3-month window the HTML build uses), unless the key
    // already has data for that month. Marked Provisional; real data replaces it.
    // ======================================================================
    KeyLast = Table.Group(CombinedBase, {"ShipTo Key", "Brand Key"},
        {{"LastMonth", each List.Max([MonthStart]), type date}}),
    LastJoin = Table.ExpandTableColumn(
        Table.NestedJoin(CombinedBase, {"ShipTo Key", "Brand Key"},
                         KeyLast, {"ShipTo Key", "Brand Key"}, "K", JoinKind.Inner),
        "K", {"LastMonth"}),
    LastRows = Table.SelectRows(LastJoin, each [MonthStart] = [LastMonth]),
    CarryRows = (n as number) as table =>
        let a = Table.RemoveColumns(LastRows, {"Fallback Source Month"}),
            b = Table.AddColumn(a, "Fallback Source Month", each [LastMonth], type date),
            c = Table.TransformColumns(b, {
                    {"MonthStart",        each Date.AddMonths(_, n), type date},
                    {"Source Type",       each "Nearest-Month Fallback", type text},
                    {"Approval Status",   each "Provisional – month not in source; last known split carried forward", type text},
                    {"Allocation Method", each "Nearest-Month Fallback – last known month carried forward (max 3 months)", type text},
                    {"Provisional Flag",  each true, type logical},
                    {"Fallback Flag",     each true, type logical}
                }),
            d = Table.RemoveColumns(c, {"LastMonth"})
        in d,
    CarryAll = Table.Combine({CarryRows(1), CarryRows(2), CarryRows(3)}),
    ExistingKeys = Table.Distinct(Table.SelectColumns(CombinedBase,
        {"ShipTo Key", "Brand Key", "MonthStart"})),
    Jun26Fallback = Table.Join(
        CarryAll,      {"ShipTo Key", "Brand Key", "MonthStart"},
        ExistingKeys,  {"ShipTo Key", "Brand Key", "MonthStart"},
        JoinKind.LeftAnti),

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
