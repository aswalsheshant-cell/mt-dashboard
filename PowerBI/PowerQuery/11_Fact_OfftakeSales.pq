// =====================================================================
// QUERY: Fact Offtake Sales   (grain = Month x Store(Site) x Article)
// Source = every file in RawDataFolders\Offtake_Monthly
//   (month-wise CSVs from "FY-24-26 Chain offtake Store Wise File till May.xlsb",
//    produced by scripts/split_offtake_store_article_xlsb.py)
//
// MAPPING LOCKED to the confirmed store x article offtake headers:
//   Unique, Zone, State, City, SO/ASE Emp Code, SO/ASE Name, Chain Name,
//   Store Type, DC Code, DC Name, Internal Code, Site Code, Site Name,
//   Article, Article_1, EAN, Chain Article Description, Net Weight,
//   Description as per Fountain, Brand, Category, Sub_category, Range, MRP,
//   Sales Qty, MRP Sales Value, NSV, Per pc, With Tax, Margin, Revised Month,
//   Month, Year, PPT Category
//
// Offtake is maintained MONTHLY (store x article). Source NSV is in lakh;
// convert it to the model's absolute-rupee contract at import. MRP Sales Value
// already arrives in rupees. This is the secondary/offtake validation base for the article
// eligibility gate (DAX 09) — no allocation logic changed here.
// =====================================================================
let
    // Workflow A: drop the splitter's month CSVs (clean header on row 0).
    // (If instead you drop the RAW offtake workbook — blank first row — pass 1.)
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Offtake_Monthly", 0),

    // keep the columns the model needs (renaming only where required to hit the
    // canonical Fact Offtake Sales fields used by relationships & measures)
    Picked = Table.SelectColumns(Source, {
        "Month", "Year", "Revised Month",
        "Chain Name", "Zone", "State", "City",
        "Site Code", "Site Name", "Store Type", "DC Name",
        "Brand", "Category", "Sub_category", "Range", "Net Weight",
        "Article", "Article_1", "EAN",
        "Description as per Fountain", "Chain Article Description",
        "Sales Qty", "NSV", "MRP Sales Value", "MRP", "Margin",
        "SO/ASE Emp Code", "SO/ASE Name", "PPT Category"
    }, MissingField.UseNull),

    Renamed = Table.RenameColumns(Picked, {
        {"Month", "Month"},
        {"Year", "FY Year"},
        {"Chain Name", "Chain"},
        {"Zone", "Zone"},
        {"State", "State"},
        {"City", "City"},
        {"Site Code", "Store Code"},
        {"Site Name", "Store Name"},
        {"Store Type", "Store Type"},
        {"DC Name", "DC Name"},
        {"Brand", "Brand"},
        {"Category", "Category"},
        {"Sub_category", "Sub-category"},
        {"Range", "Range"},
        {"Net Weight", "Pack Size"},
        {"Article", "Article Code"},
        {"Article_1", "Article Code Alt"},
        {"EAN", "EAN Code"},
        {"Description as per Fountain", "Article Description"},
        {"Chain Article Description", "Chain Article Description"},
        {"Sales Qty", "Offtake Qty"},
        {"NSV", "Offtake NSV"},
        {"MRP Sales Value", "MRP Sales"},
        {"MRP", "MRP Rate"},
        {"Margin", "Margin"},
        {"SO/ASE Emp Code", "SO Emp Code"},
        {"SO/ASE Name", "Sales Person"},
        {"PPT Category", "PPT Category"}
    }),

    Typed = Table.TransformColumnTypes(Renamed, {
        {"Month", type text}, {"FY Year", type text},
        {"Chain", type text}, {"Zone", type text}, {"State", type text}, {"City", type text},
        {"Store Code", type text}, {"Store Name", type text}, {"Store Type", type text}, {"DC Name", type text},
        {"Brand", type text}, {"Category", type text}, {"Sub-category", type text},
        {"Range", type text}, {"Pack Size", type text},
        {"Article Code", type text}, {"Article Code Alt", type text}, {"EAN Code", type text},
        {"Article Description", type text}, {"Chain Article Description", type text},
        {"Offtake Qty", type number}, {"Offtake NSV", type number}, {"MRP Sales", type number},
        {"MRP Rate", type number}, {"Margin", type number},
        {"SO Emp Code", type text}, {"Sales Person", type text}, {"PPT Category", type text}
    }),

    // Source NSV is lakh (docs/DATA_LINEAGE.md); model currency is absolute rupees.
    // Keep negative returns signed and nulls null. MRP Sales is already rupees.
    Scaled = Table.TransformColumns(Typed, {
        {"Offtake NSV", each if _ = null then null else _ * 100000, type number}
    }),

    Trimmed = Table.TransformColumns(Scaled, {
        {"Store Code", each Text.Trim(Text.From(_)), type text},
        {"Article Code", each Text.Trim(Text.From(_)), type text},
        {"EAN Code", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text}
    }),

    // Chain spellings in the offtake CSVs that differ from Chain Master (case, spacing,
    // short forms). Without this the rows have no Chain Master match and drop out of
    // [Total MT NSV]. Each pair is lowercase alias -> Chain Master name. Checked against
    // build_dashboard_data.py CHAIN_ALIASES for the same entity. FSN/Fsn maps to Nykaa (FSN),
    // a Chain Master row with Channel EB2B (owner decision 2026-10-10), so it stays out of MT.
    ChainAliases = {
        {"dmart", "D-Mart"}, {"h&g", "Health & Glow"}, {"metro cnc", "Metro CNC"},
        {"sancus(rmt)", "RMT-Sancus"}, {"vmm", "Vishal Mega Mart"}, {"spencer", "Spencers"},
        {"frankros", "Frank Ross"}, {"arambagh", "Arambagh"}, {"ratnadeep", "Ratnadeep"},
        {"ratandeep", "Ratnadeep"}, {"ratanadeep", "Ratnadeep"}, {"sasta sundar", "SastaSundar"},
        {"ssl", "SastaSundar"}, {"beauty & nutrie", "B&N"}, {"wh-smith", "WH-Smith"},
        {"shoppers stop", "Shoppers Stop"}, {"azorte", "Azorte"}, {"trends", "Trent"},
        {"fsn", "Nykaa (FSN)"}
    },
    AliasChain = Table.TransformColumns(Trimmed, {{"Chain", each
        let k = Text.Lower(Text.Trim(Text.From(_ ?? ""))),
            hit = List.First(List.Select(ChainAliases, (a) => a{0} = k))
        in if hit = null then _ else hit{1}, type text}}),

    // The early FY27 CSVs call both Reliance streams "Reliance"; later files
    // name the Brand Counter stream explicitly. Keep every row and map them to
    // separate Chain Master members so MT excludes only the duplicate breakout.
    AddGovernedChain = Table.AddColumn(AliasChain, "Governed Chain", each
        if Text.Contains(Text.Lower([Chain] ?? ""), "reliance") then
            if Text.Lower(Text.Trim([Store Type] ?? "")) = "brand counter"
            then "Reliance Brand Counter" else "Reliance Retail"
        else [Chain], type text),
    RemoveOldChain = Table.RemoveColumns(AddGovernedChain, {"Chain"}),
    RenameChain = Table.RenameColumns(RemoveOldChain, {{"Governed Chain", "Chain"}}),

    // brand spelling normalisation (keep in sync with Brand Master)
    FixBrand = Table.ReplaceValue(RenameChain, "BBLUNT", "BBlunt", Replacer.ReplaceText, {"Brand"}),

    // constant audit column
    AddSource = Table.AddColumn(FixBrand, "Data Source Name", each "Chain Offtake Store Wise", type text),

    // article key: EAN -> Article Code -> cleaned Description (matches File 2 side)
    AddKey = Table.AddColumn(AddSource, "Article Key", each
        if [EAN Code] <> null and Text.Trim([EAN Code]) <> "" then "EAN:" & [EAN Code]
        else if [Article Code] <> null and Text.Trim([Article Code]) <> "" then "CODE:" & [Article Code]
        else "DESC:" & Text.Upper(Text.Trim(Text.From([Article Description]))), type text),

    // Month has quoted labels, bare names and Excel serials across these CSVs.
    // The monthly file name supplies a year for bare names; disagreement or
    // missing period fails refresh rather than silently orphaning the row.
    AddMonthStart = Table.AddColumn(AddKey, "MonthStart", each
        let
            v = [Month],
            label = if v = null then "" else Text.Trim(Text.From(v)),
            serial = try Number.FromText(label) otherwise null,
            labelMonth = if Text.Contains(label, "'") then
                Record.FieldOrDefault([Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12],
                    Text.Proper(Text.Start(label, 3)), null) else null,
            labelYear = if labelMonth = null then null
                else try Number.FromText(Text.Trim(Text.AfterDelimiter(label, "'"))) otherwise null,
            fromLabel = if Value.Is(v, type date) then Date.StartOfMonth(v)
                else if serial <> null then try Date.StartOfMonth(Date.From(serial)) otherwise null
                else if labelMonth <> null and labelYear <> null then #date(2000 + labelYear, labelMonth, 1)
                else null,
            file = Text.From([Data Source File] ?? ""),
            filePeriod = try Text.BetweenDelimiters(file, "offtake_store_article_", ".csv") otherwise null,
            parts = if filePeriod = null then {} else Text.Split(filePeriod, "_"),
            fileMonth = if List.Count(parts) = 2 then
                Record.FieldOrDefault([Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12],
                    Text.Proper(parts{0}), null) else null,
            fileYear = if List.Count(parts) = 2 then try Number.FromText(parts{1}) otherwise null else null,
            fromFile = if fileMonth <> null and fileYear <> null then #date(2000 + fileYear, fileMonth, 1) else null,
            result = if fromLabel <> null then fromLabel else fromFile
        in
            if result = null then error Error.Record("OfftakeMonth", "Unparseable source month", [File=file, Month=label])
            else if fromFile <> null and result <> fromFile then
                error Error.Record("OfftakeMonth", "Source month disagrees with file name", [File=file, Month=label])
            else result,
        type date),

    Cleaned = Table.SelectRows(AddMonthStart, each [Offtake NSV] <> null or [Offtake Qty] <> null),

    // Derive FY from the parsed month, as in the Date Table; do not trust the
    // inconsistent source FY text after a month was recovered from the file.
    FYNew = Table.AddColumn(Cleaned, "FY Year New", each fnFYLabel([MonthStart]), type text),
    FYDropOld = Table.RemoveColumns(FYNew, {"FY Year"}),
    FYDerived = Table.RenameColumns(FYDropOld, {{"FY Year New", "FY Year"}})
in
    FYDerived

