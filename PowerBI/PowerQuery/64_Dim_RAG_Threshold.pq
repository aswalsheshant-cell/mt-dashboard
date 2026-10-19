// =====================================================================
// QUERY: Dim RAG Threshold
// Source: SeedData\Masters\RAG_Thresholds.csv  (repo-relative to pRootFolder)
// Role: the Green / Amber / Red bands for status and colour measures (Achievement Status, Growth Colour, Run Rate
// Status in DAX/01_CoreMeasures.dax). Generated from config/analytics_config.json ("rag") by
// scripts/build_rag_threshold_seed.py, so Power BI and the HTML dashboard use the same numbers.
// Do not edit the CSV by hand: change the config, regenerate, and the CI test keeps the two in step.
// Units: Unit = pct means the value is in percent (100 = 100%); ratio means a plain ratio.
// Kept DISCONNECTED (no modelled relationship); measures look a row up by Metric.
// =====================================================================
let
    Source = Csv.Document(
        File.Contents(pRootFolder & "\SeedData\Masters\RAG_Thresholds.csv"),
        [Delimiter=",", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"Metric", type text},
        {"Green", type number},
        {"Amber", type number},
        {"Red", type number},
        {"Lower_Is_Better", type logical},
        {"Unit", type text}
    }, "en-US")
in
    Typed
