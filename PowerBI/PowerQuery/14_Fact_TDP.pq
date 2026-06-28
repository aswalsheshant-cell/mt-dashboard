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
    Trimmed = Table.TransformColumns(Typed, {
        {"Article Code", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text}
    }),
    AddMonthStart = Table.AddColumn(Trimmed, "MonthStart", each
        let
            m = Text.BetweenDelimiters([Month], "", "'"),
            yy = Text.AfterDelimiter([Month], "'"),
            monthNum = Record.FieldOrDefault(
                [Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
        in if monthNum = null then null else #date(2000 + Number.FromText(yy), monthNum, 1),
        type date)
in
    AddMonthStart
