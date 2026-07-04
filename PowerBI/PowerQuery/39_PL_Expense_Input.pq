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
    // build_dashboard_data.py's _fylabel() + _FY_START_YEAR exactly (two
    // separate steps -- do NOT collapse into a single digit-counting
    // heuristic, "FY26" the short form means a DIFFERENT thing than the
    // "26" in "FY25-26" would if read as a bare number).
    AddFyTag = Table.AddColumn(Typed, "_FyTag", each
        let fyText = Text.Upper(Text.Trim(Text.From([FY])))
        in  if Text.Contains(fyText, "23-24") then "FY24"
            else if Text.Contains(fyText, "24-25") then "FY25"
            else if Text.Contains(fyText, "25-26") then "FY26"
            else if Text.Contains(fyText, "26-27") then "FY27"
            else if fyText = "FY24" then "FY24"
            else if fyText = "FY25" then "FY25"
            else if fyText = "FY26" then "FY26"
            else if fyText = "FY27" then "FY27"
            else null,
        type text),
    AddFyStartYear = Table.AddColumn(AddFyTag, "_FyStartYear", each
        if [_FyTag] = "FY24" then 2023
        else if [_FyTag] = "FY25" then 2024
        else if [_FyTag] = "FY26" then 2025
        else if [_FyTag] = "FY27" then 2026
        else null,
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

    Cleaned = Table.SelectRows(RemoveHelpers, each [Expense Amount (INR Lakh)] <> null)
in
    Cleaned
