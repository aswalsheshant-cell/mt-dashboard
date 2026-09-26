// =====================================================================
// QUERY: PL Expense Input
// Source: SeedData\Masters\PL_Expense_Input.csv  (repo-relative to pRootFolder)
// Role: month-on-month P&L expense input for CM2 (Contribution Margin 2)
// tracking. Editable by Finance/Ops -- NEVER hardcoded in this model or in
// the HTML dashboard. Matched to 'Fact Primary Article' by
// DAX/13_CM2_Measures.dax: Customer Code first (via query 40's
// CustCode-Chain map), Chain name fallback.
//
// Expense Amount is in INR LAKH (named explicitly in the column header to
// avoid unit-mismatch bugs) -- same unit convention as every other reporting
// measure in this model (values divided down to Lakh/Cr for display).
//
// MonthStart is parsed here (not left as free text) using the SAME two-step
// text -> FY-tag -> start-year logic as
// dashboard/scripts/build_dashboard_data.py's _fylabel()/_mlabel(), so this
// table relates to Date Table[MonthStart] exactly like every other
// fact/input table in the model (see docs/DataModel.md). Both "FYyy-yy"
// (e.g. "FY25-26", matches the SAP-exported source files) and the
// dashboard's own short form ("FY26") are accepted, since this file is
// manually typed and a Finance user is more likely to reach for the short
// form than the SAP export's hyphenated convention.
// =====================================================================
let
    Source = Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Masters\PL_Expense_Input.csv"),
        [Delimiter=",", Columns=17, Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Month", type text}, {"FY", type text}, {"Chain", type text},
        {"Customer Code", type text}, {"Customer Name", type text},
        {"Zone", type text}, {"State", type text}, {"Brand", type text},
        {"Category", type text}, {"Sub Category", type text},
        {"Expense Head", type text}, {"Expense Type", type text},
        {"Expense Amount (INR Lakh)", type number},
        {"Remarks", type text}, {"Source", type text},
        {"Updated By", type text}, {"Updated Date", type text}
    }),

    // FY text -> internal tag -> start calendar year, mirroring
    // build_dashboard_data.py's _fylabel() + fy_start_year() step for step
    // (THE ONE FY RULE): arithmetic, no list of years, so FY28, FY29, ...
    // work without a code change. Two separate forms -- do NOT collapse into
    // a single digit-counting heuristic: "FY26" (short) names the FY ending
    // in 2026, and so does "FY25-26" (span, named by its END year).
    //   span:  first "dd-dd" anywhere, second = first + 1 -> "FY" & second
    //          ("FY25-26", "FY'25-26", "FY_25-26", "2025-26")
    //   short: whole text (spaces removed) is "FY" + optional 0 + 2 digits
    //          ("FY26", "FY 26", "FY026")
    //   anything else (including a missing FY) -> null.
    // tests/powerbi/pq39_fy_parser_cases.pq runs this exact function over
    // tests/powerbi/fy_parser_cases.csv in Desktop (text kept identical by
    // tests/test_pq39_fy_parser.py).
    fnFyTag = (fy as any) as nullable text =>
        let
            _s = if fy = null then "" else Text.Remove(Text.Upper(Text.Trim(Text.From(fy))), {" "}),
            _isDD = (t as text) as logical =>
                Text.Length(t) = 2 and List.AllTrue(List.Transform(Text.ToList(t), each Text.Contains("0123456789", _))),
            _spans = List.Select(Text.PositionOf(_s, "-", Occurrence.All), each
                _ >= 2 and _ + 3 <= Text.Length(_s)
                and _isDD(Text.Middle(_s, _ - 2, 2)) and _isDD(Text.Middle(_s, _ + 1, 2))),
            _p = List.First(_spans, null),
            _a = if _p = null then null else Number.FromText(Text.Middle(_s, _p - 2, 2)),
            _b = if _p = null then null else Number.FromText(Text.Middle(_s, _p + 1, 2)),
            _span = if _p <> null and _b = Number.Mod(_a + 1, 100) then "FY" & Text.PadStart(Text.From(_b), 2, "0") else null,
            _body = if Text.StartsWith(_s, "FY") then Text.Middle(_s, 2) else null,
            _digits = if _body <> null and Text.Length(_body) = 3 and Text.StartsWith(_body, "0") then Text.Middle(_body, 1) else _body,
            _short = if _digits <> null and _isDD(_digits) then "FY" & _digits else null
        in
            if _span <> null then _span else _short,
    AddFyTag = Table.AddColumn(Typed, "_FyTag", each fnFyTag([FY]), type text),
    AddFyStartYear = Table.AddColumn(AddFyTag, "_FyStartYear", each
        if [_FyTag] = null then null
        else 2000 + Number.FromText(Text.Middle([_FyTag], 2)) - 1,
        Int64.Type),
    AddMonthNum = Table.AddColumn(AddFyStartYear, "_MonthNum", each
        Record.FieldOrDefault(
            [Apr=4, April=4, May=5, Jun=6, June=6, Jul=7, July=7,
             Aug=8, August=8, Sep=9, Sept=9, September=9,
             Oct=10, October=10, Nov=11, November=11, Dec=12, December=12,
             Jan=1, January=1, Feb=2, February=2, Mar=3, March=3],
            Text.Proper(Text.Trim(Text.From([Month]))), null),
        Int64.Type),
    AddMonthStart = Table.AddColumn(AddMonthNum, "MonthStart", each
        if [_FyStartYear] = null or [_MonthNum] = null then null
        else #date(if [_MonthNum] >= 4 then [_FyStartYear] else [_FyStartYear] + 1, [_MonthNum], 1),
        type date),
    RemoveHelpers = Table.RemoveColumns(AddMonthStart, {"_FyTag", "_FyStartYear", "_MonthNum"}),

    // The seed file ships 3 template rows marked "EXAMPLE ROW" in Remarks to show
    // Finance the schema. They are never real expense -- same rule as the HTML
    // loader's load_pl_expense_input() (FM-01, FM-33). Real rows are untouched.
    NoTemplateRows = Table.SelectRows(RemoveHelpers, each
        [Remarks] = null or not Text.Contains(Text.Upper([Remarks]), "EXAMPLE ROW")),
    Cleaned = Table.SelectRows(NoTemplateRows, each [Expense Amount (INR Lakh)] <> null)
in
    Cleaned
