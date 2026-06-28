// =====================================================================
// QUERY: Fact Primary ShipTo   (grain = Month x Ship-To x Chain x Brand)
// Source = RawDataFolders\Primary_ShipTo_Monthly
//
// This is the ship-to-party primary feed where primary NSV is ALREADY
// allocated to Chain based on the secondary/offtake contribution % that
// month. (Direct ship-tos => one chain, Cont% = 100%. Distributor ship-tos
// => split across chains by Cont%.)
//
// The Cont% column is the dynamic, month-wise allocation driver (the
// "separate mapping table"). It is NOT hardcoded - it arrives in the monthly
// file and is also projected out as 'Primary Allocation Map' (query 34).
//
// Cleaning here is reproducible every month: brand/chain spellings are
// normalised and NSV (received in Lacs) is converted to absolute rupees so
// it lines up with Fact Offtake Sales.
// =====================================================================
let
    Source = fnCombineFolder(pRootFolder & "\RawDataFolders\Primary_ShipTo_Monthly"),

    Typed = Table.TransformColumnTypes(Source, {
        {"Month", type text},
        {"MonthStart", type date},
        {"FY Year", type text},
        {"Ship To Name", type text},
        {"Direct/Distributor", type text},
        {"Chain", type text},
        {"Zone", type text},
        {"State", type text},
        {"Brand", type text},
        {"Primary NSV", type number},
        {"MRP Value", type number},
        {"Cont%", type number}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Ship To Name", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text}
    }),

    // --- normalise brand spellings (keep in sync with Brand Master) ---
    FixBrand = Table.ReplaceValue(Trimmed, "BBLUNT", "BBlunt", Replacer.ReplaceText, {"Brand"}),

    // --- normalise chain spellings (keep in sync with Chain Master) ---
    FixChain1 = Table.ReplaceValue(FixBrand, "Vmm",       "Vishal Mega Mart", Replacer.ReplaceValue, {"Chain"}),
    FixChain2 = Table.ReplaceValue(FixChain1,"VMM",       "Vishal Mega Mart", Replacer.ReplaceValue, {"Chain"}),
    FixChain3 = Table.ReplaceValue(FixChain2,"ARAMBAGH",  "Arambagh",         Replacer.ReplaceValue, {"Chain"}),
    FixChain4 = Table.ReplaceValue(FixChain3,"Reliance",  "Reliance Retail",  Replacer.ReplaceValue, {"Chain"}),
    FixChain5 = Table.ReplaceValue(FixChain4,"Dmart",     "D-Mart",           Replacer.ReplaceValue, {"Chain"}),
    FixChain6 = Table.ReplaceValue(FixChain5,"Spencer",   "Spencers",         Replacer.ReplaceValue, {"Chain"}),
    FixChain7 = Table.ReplaceValue(FixChain6,"H&G",       "Health & Glow",    Replacer.ReplaceValue, {"Chain"}),

    // If the file ever arrives in Lacs again instead of absolute rupees,
    // flip this flag. The seed already stores absolute rupees, so default = false.
    ConvertFromLacs = false,
    Scaled = if ConvertFromLacs
        then Table.TransformColumns(FixChain7, {
                {"Primary NSV", each _ * 100000, type number},
                {"MRP Value",  each _ * 100000, type number}})
        else FixChain7,

    // Direct rows may have blank Cont% -> treat as 100%
    FillCont = Table.ReplaceValue(Scaled, null, 1.0, Replacer.ReplaceValue, {"Cont%"}),

    // rebuild MonthStart if the source only had the text label
    AddMonthStart = Table.AddColumn(FillCont, "MonthStartCalc", each
        if [MonthStart] <> null then [MonthStart]
        else
            let m = Text.Start(Text.BeforeDelimiter([Month], "'"), 3),
                yy = Text.AfterDelimiter([Month], "'"),
                mn = Record.FieldOrDefault([Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
            in if mn = null then null else #date(2000 + Number.FromText(yy), mn, 1),
        type date),

    Cleaned = Table.SelectRows(AddMonthStart, each [Primary NSV] <> null)
in
    Cleaned
