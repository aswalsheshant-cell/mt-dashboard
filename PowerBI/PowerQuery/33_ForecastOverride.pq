// =====================================================================
// QUERY: Forecast Override  (manual forecast input - editable)
// Forecast NEVER overwrites actuals. The statistical forecast (L3M, L6M,
// MoM trend, YoY) is computed in DAX; this table only lets you type a
// manual number or a growth assumption that DAX prefers when present.
// Use "ALL" to apply broadly. Leave Manual Forecast NSV blank to let the
// statistical Final Forecast stand.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\ForecastOverride.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Month", type text},{"Chain", type text},{"Brand", type text},{"Category", type text},
        {"Article Code", type text},{"Manual Forecast NSV", type number},
        {"Growth Assumption %", type number},{"Remarks", type text}})
in
    Typed
