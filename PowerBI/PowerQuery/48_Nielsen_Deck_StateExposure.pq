// =====================================================================
// QUERY: Nielsen Deck State Exposure  (state x chain exposure from MT_Review_Big3_v3_1.pptx)
// Typed from the review deck (Nielsen Jun'26 state cut + internal MT sell-out). It is NOT in
// the Aug-26 Nielsen workbooks, which carry IN URB MT only. Read it as the deck's own figures.
// Source = SeedData\Masters\Nielsen_Deck_StateExposure.csv (blank = not applicable in the deck)
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\Nielsen_Deck_StateExposure.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"State", type text},
        {"Market FW Cr", type number}, {"Market SH Cr", type number},
        {"ME Share FW %", type number}, {"ME Share SH %", type number},
        {"Dmart FW %", type number}, {"Dmart SH %", type number},
        {"Reliance FW %", type number}, {"Reliance SH %", type number},
        {"Apollo FW %", type number}, {"Apollo SH %", type number},
        {"Main Lever", type text}, {"Source", type text}, {"Period", type text}
    })
in
    Typed
