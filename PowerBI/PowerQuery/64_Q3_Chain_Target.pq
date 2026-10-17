// =====================================================================
// QUERY: Q3 Chain Target  (grain = FY x Quarter x Chain; Primary basis; Rs lakh)
// Source = SeedData\Masters\Q3_FY27_Chain_Target_Primary.csv
//   (written by scripts/ingest_rkam_q3_targets.py from the RKAM target plan;
//    chain totals only, no RKAM/NKAM names. Basis Primary, owner 2026-10-17.)
// Chain names are aligned to the Primary fact: V Mart -> V-Mart, Wh Smith -> WH-Smith.
// Others, Rmt and Spar have no Primary chain of that name and stay as they are (no match, no guess).
// Relationship: none. Measures use TREATAS on Chain (DAX 23).
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\Q3_FY27_Chain_Target_Primary.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"FY", type text}, {"Quarter", type text}, {"Chain", type text}, {"Basis", type text},
        {"Q3_Old_Target_L", type number}, {"Q3_New_Target_L", type number},
        {"Unit", type text}, {"Source", type text}, {"Approved_By", type text}, {"Approved_Date", type text}
    }, "en-US"),
    Renamed = Table.RenameColumns(Typed, {
        {"Q3_Old_Target_L", "Q3 Old Target Rs L"}, {"Q3_New_Target_L", "Q3 New Target Rs L"},
        {"Approved_By", "Approved By"}, {"Approved_Date", "Approved Date"}}),
    Aligned = Table.TransformColumns(Renamed, {{"Chain", each
        if _ = "V Mart" then "V-Mart" else if _ = "Wh Smith" then "WH-Smith" else _, type text}})
in
    Aligned
