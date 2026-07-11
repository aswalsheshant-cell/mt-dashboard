// =====================================================================
// QUERY: Fact TDP / Distribution  (grain = Month x Chain x Article ...)
// Source = RawDataFolders\TDP_Monthly
// TDP (Total Distribution Points) = SUM of ACV % across SKUs. The SUM is
// done in DAX so it rolls up correctly at Brand / Category / Chain / Zone /
// Article / Pack-size level. This query just lands the per-SKU ACV %.
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\TDP_Monthly"),
    Typed = Table.TransformColumnTypes(Source, {
        {"Month", type text},
        {"FY Year", type text},
        {"Chain", type text},
        {"Zone", type text},
        {"State", type text},
        {"Brand", type text},
        {"Category", type text},
        {"Sub-category", type text},
        {"Pack Size", type text},
        {"Article Code", type text},
        {"Article Description", type text},
        {"ACV %", type number},
        {"AIC", type number},
        {"Numeric Distribution", type number},
        {"Weighted Distribution", type number},
        {"Data Source Name", type text}
    }),
    // P6: trim + strip hidden chars on all text dims; normalise Zone/State case
    Trimmed = Table.TransformColumns(Typed, {
        {"Chain",         each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Brand",         each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Category",      each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Sub-category",  each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Zone",          each Text.Proper(Text.Trim(Text.Clean(Text.From(_)))), type text},
        {"State",         each Text.Proper(Text.Trim(Text.Clean(Text.From(_)))), type text}
    }),

    // P2: numeric-origin keys arrive as "10100062.0" — strip a trailing ".0" so
    // the key joins to the masters (a bare ".0" on an ID is always an artefact).
    CleanKeys = Table.TransformColumns(Trimmed, {
        {"Article Code", each let s = if _ = null then null else Text.From(_)
                              in if s <> null and Text.EndsWith(s, ".0")
                                 then Text.Start(s, Text.Length(s) - 2) else s, type text}
    }),

    // P1: robust month parse (see Nielsen/Offtake) with a year guard.
    AddMonthStart = Table.AddColumn(CleanKeys, "MonthStart", each
        let v = [Month] in
        if v = null then null
        else if Value.Is(v, type date) then Date.StartOfMonth(v)
        else
            let m  = Text.Start(Text.BeforeDelimiter(Text.From(v), "'"), 3),
                yy = Text.AfterDelimiter(Text.From(v), "'"),
                mn = Record.FieldOrDefault(
                     [Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
            in if mn = null or yy = "" or (try Number.FromText(yy) otherwise null) = null
               then null else #date(2000 + Number.FromText(yy), mn, 1),
        type date),

    // P3: exclude rows with an unparseable period (won't relate to the Date table).
    Cleaned = Table.SelectRows(AddMonthStart, each [MonthStart] <> null)
in
    Cleaned
