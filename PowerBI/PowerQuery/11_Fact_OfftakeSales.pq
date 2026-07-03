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
// Offtake is maintained MONTHLY (store x article). NSV = offtake net value
// (rupees). This is the secondary/offtake validation base for the article
// eligibility gate (DAX 09) — no allocation logic changed here.
// =====================================================================
let
    // Offtake workbooks include a blank first row, so the actual headers begin on row 1.
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Offtake_Monthly", 1),

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

    Trimmed = Table.TransformColumns(Typed, {
        {"Store Code", each Text.Trim(Text.From(_)), type text},
        {"Article Code", each Text.Trim(Text.From(_)), type text},
        {"EAN Code", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text}
    }),

    // brand spelling normalisation (keep in sync with Brand Master)
    FixBrand = Table.ReplaceValue(Trimmed, "BBLUNT", "BBlunt", Replacer.ReplaceText, {"Brand"}),

    // constant audit column
    AddSource = Table.AddColumn(FixBrand, "Data Source Name", each "Chain Offtake Store Wise", type text),

    // article key: EAN -> Article Code -> cleaned Description (matches File 2 side)
    AddKey = Table.AddColumn(AddSource, "Article Key", each
        if [EAN Code] <> null and Text.Trim([EAN Code]) <> "" then "EAN:" & [EAN Code]
        else if [Article Code] <> null and Text.Trim([Article Code]) <> "" then "CODE:" & [Article Code]
        else "DESC:" & Text.Upper(Text.Trim(Text.From([Article Description]))), type text),

    // period = "Month" (April'24 / Apr'24 text or a date). "Revised Month" kept
    // as an alternate period column if you later prefer the adjusted month.
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

    Cleaned = Table.SelectRows(AddMonthStart, each [Offtake NSV] <> null or [Offtake Qty] <> null)
in
    Cleaned
