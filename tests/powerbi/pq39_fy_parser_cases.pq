// =====================================================================
// PQ 39 FY parser -- behaviour check for Power BI Desktop
// CI has no Power Query engine, so tests/test_pq39_fy_parser.py checks the
// structure of query 39 and checks every expected value in
// tests/powerbi/fy_parser_cases.csv against the pipeline's own Python rule
// (_fylabel + fy_start_year). This query runs the SAME function text as
// query 39 (the pytest keeps the two copies identical) over that table.
//
// How to run: Power BI Desktop -> Transform data -> New Source -> Blank
// Query -> Advanced Editor -> paste this file. Delete the query afterwards;
// it is a test, not part of the model.
// CasesFile below assumes pRootFolder is the repo's PowerBI folder (the one
// holding SeedData\ and RawDataFolders\), so the case table is one level up
// in tests\powerbi\. If your pRootFolder is a copy outside the repo, replace
// CasesFile with the full path to tests\powerbi\fy_parser_cases.csv.
// EXPECT: the "Failures" step returns 0 rows (every row Result = "OK").
// =====================================================================
let
    CasesFile = pRootFolder & "\..\tests\powerbi\fy_parser_cases.csv",
    Cases = Table.PromoteHeaders(
        Csv.Document(
            File.Contents(CasesFile),
            [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
        [PromoteAllScalars=true]),

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

    // Same steps as query 39 from here: tag -> start year -> month -> MonthStart.
    WithTag = Table.AddColumn(Cases, "Got FY Tag", each fnFyTag(if [FY] = "" then null else [FY]), type text),
    WithStart = Table.AddColumn(WithTag, "_FyStartYear", each
        if [Got FY Tag] = null then null
        else 2000 + Number.FromText(Text.Middle([Got FY Tag], 2)) - 1, Int64.Type),
    WithMonth = Table.AddColumn(WithStart, "_MonthNum", each
        Record.FieldOrDefault(
            [Apr=4, April=4, May=5, Jun=6, June=6, Jul=7, July=7,
             Aug=8, August=8, Sep=9, Sept=9, September=9,
             Oct=10, October=10, Nov=11, November=11, Dec=12, December=12,
             Jan=1, January=1, Feb=2, February=2, Mar=3, March=3],
            Text.Proper(Text.Trim(Text.From([Month]))), null), Int64.Type),
    WithMonthStart = Table.AddColumn(WithMonth, "Got MonthStart", each
        if [_FyStartYear] = null or [_MonthNum] = null then null
        else #date(if [_MonthNum] >= 4 then [_FyStartYear] else [_FyStartYear] + 1, [_MonthNum], 1), type date),
    Checked = Table.AddColumn(WithMonthStart, "Result", each
        if (if [Got FY Tag] = null then "" else [Got FY Tag]) = [Expected FY Tag]
           and (if [Got MonthStart] = null then "" else Date.ToText([Got MonthStart], [Format="yyyy-MM-dd", Culture="en-US"])) = [Expected MonthStart]
        then "OK" else "FAIL", type text),
    Failures = Table.SelectRows(Checked, each [Result] <> "OK")
in
    Failures
