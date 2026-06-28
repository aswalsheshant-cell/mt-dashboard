// =====================================================================
// QUERY: Fact Primary Article  (File 2 — Distributor article-wise primary)
// Source: RawDataFolders\Primary_Article_Monthly\
//   e.g. "MT, Eb2B & SIS primary April_23 to May_26.xlsb"
// Grain: Month x Distributor/Ship-to x Chain x Brand x Article (EAN/Code).
//
// This is the article-level primary that the offtake-eligibility gate
// (DAX 09) allocates. Because the file is large (~175 MB .xlsb), load it on
// the machine running Power BI Desktop via the folder refresh — do NOT try to
// process it in any lightweight/cloud sandbox.
//
// >> Column names below are the REQUIRED canonical names. Map the source's
//    actual headers to these in the first step (Table.RenameColumns) once the
//    real headers are confirmed. EAN is the priority article key, then Article
//    Code, then cleaned Article Description.
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Primary_Article_Monthly"),

    // --- map source headers -> canonical names here once confirmed ---
    // Renamed = Table.RenameColumns(Source, {
    //     {"<src month>","Month"}, {"<src ship to>","Ship To Name"},
    //     {"<src chain>","Chain"}, {"<src brand>","Brand"},
    //     {"<src ean>","EAN Code"}, {"<src code>","Article Code"},
    //     {"<src desc>","Article Description"},
    //     {"<src nsv>","Primary NSV"}, {"<src qty>","Primary Qty"},
    //     {"<src mrp>","Primary MRP"} }),
    Renamed = Source,

    Typed = Table.TransformColumnTypes(Renamed, {
        {"Month", type text},
        {"Ship To Name", type text},
        {"Direct/Distributor", type text},
        {"Chain", type text},
        {"Brand", type text},
        {"Article Code", type text},
        {"EAN Code", type text},
        {"Article Description", type text},
        {"Primary NSV", type number},
        {"Primary Qty", type number},
        {"Primary MRP", type number}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Article Code", each Text.Trim(Text.From(_)), type text},
        {"EAN Code", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text}
    }),

    // article key priority: EAN -> Article Code -> cleaned Description
    AddKey = Table.AddColumn(Trimmed, "Article Key", each
        if [EAN Code] <> null and Text.Trim([EAN Code]) <> "" then "EAN:" & [EAN Code]
        else if [Article Code] <> null and Text.Trim([Article Code]) <> "" then "CODE:" & [Article Code]
        else "DESC:" & Text.Upper(Text.Trim(Text.From([Article Description]))), type text),

    AddMonthStart = Table.AddColumn(AddKey, "MonthStart", each
        let m = Text.Start(Text.BeforeDelimiter([Month], "'"), 3),
            yy = Text.AfterDelimiter([Month], "'"),
            mn = Record.FieldOrDefault([Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
        in if mn = null then null else #date(2000 + Number.FromText(yy), mn, 1),
        type date)
in
    AddMonthStart
