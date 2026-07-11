// =====================================================================
// QUERY: Fact Primary Sales   (grain = Week x Store x Article)
// Source = every file in RawDataFolders\Primary_Weekly
// Primary is maintained WEEKLY (date/week-wise) so MoM is built by rolling
// the weekly rows up to Month via the Date table.
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Primary_Weekly"),

    // enforce types on the standard columns
    Typed = Table.TransformColumnTypes(Source, {
        {"Week Start Date", type date},
        {"Month", type text},
        {"FY Year", type text},
        {"Quarter", type text},
        {"Chain", type text},
        {"Account", type text},
        {"Zone", type text},
        {"State", type text},
        {"City", type text},
        {"Store Code", type text},
        {"Store Name", type text},
        {"Brand", type text},
        {"Category", type text},
        {"Sub-category", type text},
        {"Range", type text},
        {"Pack Size", type text},
        {"Article Code", type text},
        {"Article Description", type text},
        {"EAN Code", type text},
        {"Primary NSV", type number},
        {"Primary Qty", type number},
        {"MRP Sales", type number},
        {"Data Source Name", type text}
    }),

    // P6: trim + strip hidden chars on all text dims; normalise Zone/State case
    Trimmed = Table.TransformColumns(Typed, {
        {"Store Code",   each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Store Name",   each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Article Code", each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"EAN Code",     each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Chain",        each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Brand",        each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Category",     each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Sub-category", each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Range",        each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"City",         each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Zone",         each Text.Proper(Text.Trim(Text.Clean(Text.From(_)))), type text},
        {"State",        each Text.Proper(Text.Trim(Text.Clean(Text.From(_)))), type text}
    }),

    // P2: strip a trailing ".0" from numeric-origin keys so they join to masters
    CleanKeys = Table.TransformColumns(Trimmed, List.Transform(
        {"EAN Code", "Article Code"},
        each {_, (v) => let s = if v = null then null else Text.From(v)
                        in if s <> null and Text.EndsWith(s, ".0")
                           then Text.Start(s, Text.Length(s) - 2) else s, type text})),

    // MonthStart = first day of the month, used to relate to the Date table at month grain
    AddMonthStart = Table.AddColumn(CleanKeys, "MonthStart",
        each Date.StartOfMonth([Week Start Date]), type date),

    // P3: keep rows with a value AND a parseable period (reconciliation-safe)
    Cleaned = Table.SelectRows(AddMonthStart,
        each [MonthStart] <> null and ([Primary NSV] <> null or [Primary Qty] <> null))
in
    Cleaned
