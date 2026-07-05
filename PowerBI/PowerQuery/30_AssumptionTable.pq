// =====================================================================
// QUERY: Assumption Table  (P&L inputs - editable monthly, NOT hardcoded)
// Edit SeedData\Masters\AssumptionTable.csv each month to change margin %,
// trade/visibility/scheme spend by Month x Chain x Brand x Category.
// Use "ALL" in any dimension column to mean "applies to everything".
// DAX resolves the most specific matching row first, then falls back to ALL.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\AssumptionTable.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Month", type text},{"Chain", type text},{"Brand", type text},{"Category", type text},
        {"Gross Margin %", type number},{"Trade Spend %", type number},
        {"Visibility Spend", type number},{"Scheme Spend", type number},
        {"Other Spend", type number},{"Contribution Margin %", type number},{"Remarks", type text}})
in
    Typed
