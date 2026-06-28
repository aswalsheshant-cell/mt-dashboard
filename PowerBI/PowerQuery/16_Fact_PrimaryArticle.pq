// =====================================================================
// QUERY: Fact Primary Article  (File 2 — Distributor article-wise primary)
// Source: RawDataFolders\Primary_Article_Monthly\
//   (month-wise CSVs from "MT, Eb2B & SIS primary April_23 to May_26.xlsb",
//    produced by scripts/split_primary_article_xlsb.py)
// Grain: Month x Ship-to(Distributor) x Chain x Brand x Article (EAN/Code).
//
// MAPPING LOCKED to the confirmed File 2 headers (SAP invoice export):
//   FY, Month, Article Code, Ship To Name, EAN No., brand, category,
//   sub_category, range, Description, Inv Qty, Inv. Net value(LOC),
//   Total MRP sales, Cust-SAP Code, Zone, State, Chain name, Store Code,
//   Format, Channel   (+ many invoice columns kept out of the model)
//
// Units: "Inv. Net value(LOC)" is in rupees (local currency) -> Primary NSV.
//        (The file also has "sale in lac"; LOC is used to match the model's
//         absolute-rupee convention. Flip in the marked step if you prefer lac.)
// Article key priority: EAN -> Article Code -> cleaned Description.
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Primary_Article_Monthly"),

    // keep only the columns the model needs (first 'Cust-SAP Code' instance).
    // duplicate source headers (Customer Name, Cust-SAP Code) are de-duped by
    // the combine step; we reference the canonical first occurrence here.
    Picked = Table.SelectColumns(Source, {
        "FY", "Month", "Ship To Name", "Chain name", "brand",
        "Article Code", "EAN No.", "Description",
        "category", "sub_category", "range",
        "Inv Qty", "Inv. Net value(LOC)", "Total MRP sales",
        "Cust-SAP Code", "Store Code", "Zone", "State", "Format", "Channel"
    }, MissingField.UseNull),

    Renamed = Table.RenameColumns(Picked, {
        {"FY", "FY Year"},
        {"Ship To Name", "Ship To Name"},
        {"Chain name", "Chain"},
        {"brand", "Brand"},
        {"Article Code", "Article Code"},
        {"EAN No.", "EAN Code"},
        {"Description", "Article Description"},
        {"category", "Category"},
        {"sub_category", "Sub-category"},
        {"range", "Range"},
        {"Inv Qty", "Primary Qty"},
        {"Inv. Net value(LOC)", "Primary NSV"},
        {"Total MRP sales", "Primary MRP"},
        {"Cust-SAP Code", "Customer Code"},
        {"Store Code", "Store Code"},
        {"Zone", "Zone"},
        {"State", "State"},
        {"Format", "Format"},
        {"Channel", "Channel"}
    }),

    Typed = Table.TransformColumnTypes(Renamed, {
        {"FY Year", type text}, {"Month", type text},
        {"Ship To Name", type text}, {"Chain", type text}, {"Brand", type text},
        {"Article Code", type text}, {"EAN Code", type text}, {"Article Description", type text},
        {"Category", type text}, {"Sub-category", type text}, {"Range", type text},
        {"Primary Qty", type number}, {"Primary NSV", type number}, {"Primary MRP", type number},
        {"Customer Code", type text}, {"Store Code", type text},
        {"Zone", type text}, {"State", type text}, {"Format", type text}, {"Channel", type text}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Article Code", each Text.Trim(Text.From(_)), type text},
        {"EAN Code", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text},
        {"Customer Code", each Text.Trim(Text.From(_)), type text}
    }),

    // OPTIONAL unit switch: set true only if you mapped Primary NSV to "sale in lac"
    NsvIsLac = false,
    Scaled = if NsvIsLac
        then Table.TransformColumns(Trimmed, {{"Primary NSV", each _ * 100000, type number}})
        else Trimmed,

    // brand spelling normalisation (keep in sync with Brand Master)
    FixBrand = Table.ReplaceValue(Scaled, "BBLUNT", "BBlunt", Replacer.ReplaceText, {"Brand"}),

    // article key: EAN -> Article Code -> cleaned Description
    AddKey = Table.AddColumn(FixBrand, "Article Key", each
        if [EAN Code] <> null and Text.Trim([EAN Code]) <> "" then "EAN:" & [EAN Code]
        else if [Article Code] <> null and Text.Trim([Article Code]) <> "" then "CODE:" & [Article Code]
        else "DESC:" & Text.Upper(Text.Trim(Text.From([Article Description]))), type text),

    // MonthStart from "April'24" / "Apr'24" text, or from a date value
    AddMonthStart = Table.AddColumn(AddKey, "MonthStart", each
        let v = [Month]
        in  if v = null then null
            else if Value.Is(v, type date) then Date.StartOfMonth(v)
            else
                let m = Text.Start(Text.BeforeDelimiter(Text.From(v), "'"), 3),
                    yy = Text.AfterDelimiter(Text.From(v), "'"),
                    mn = Record.FieldOrDefault([Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
                in if mn = null or yy = "" then null else #date(2000 + Number.FromText(yy), mn, 1),
        type date),

    Cleaned = Table.SelectRows(AddMonthStart, each [Primary NSV] <> null or [Primary Qty] <> null)
in
    Cleaned
