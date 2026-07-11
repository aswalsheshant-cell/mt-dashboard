// =====================================================================
// QUERY: Fact Nielsen Market Share  (grain = Month x Nielsen Category x Brand x Zone)
// Source = RawDataFolders\Nielsen_Monthly
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Nielsen_Monthly"),
    Typed = Table.TransformColumnTypes(Source, {
        {"Month", type text},
        {"FY Year", type text},
        {"Nielsen Category", type text},
        {"Brand", type text},
        {"Zone", type text},
        {"Market Value Sales", type number},
        {"Our Brand Sales", type number},
        {"Value Market Share %", type number},
        {"Volume Market Share %", type number},
        {"Data Source Name", type text}
    }),
    // P6: strip hidden chars + trim on text dims; normalise Zone case (West/WEST -> West)
    CleanText = Table.TransformColumns(Typed, {
        {"Nielsen Category", each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Brand",            each Text.Trim(Text.Clean(Text.From(_))), type text},
        {"Zone",             each Text.Proper(Text.Trim(Text.Clean(Text.From(_)))), type text}
    }),

    // P1: robust month parse — handles "April'24" / "Apr'24" / a real date, and
    // guards a blank/non-numeric year so one bad label nulls a row (not the refresh).
    AddMonthStart = Table.AddColumn(CleanText, "MonthStart", each
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

    // P3: drop rows whose period could not be parsed — they'd never relate to the
    // Date table and would break time-vs-total reconciliation. Review the source label.
    Cleaned = Table.SelectRows(AddMonthStart, each [MonthStart] <> null)
in
    Cleaned
